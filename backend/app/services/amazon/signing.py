from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.services.amazon.exceptions import AmazonAuthorizationError


@dataclass(frozen=True)
class AwsCredentials:
    access_key_id: str
    secret_access_key: str


class AwsSigV4Signer:
    def __init__(self, service: str = "execute-api") -> None:
        self.service = service

    def sign(self, request: httpx.Request, *, region: str, credentials: AwsCredentials) -> httpx.Request:
        if not credentials.access_key_id or not credentials.secret_access_key:
            raise AmazonAuthorizationError(
                "AWS credentials are not configured. Live SP-API signing is unavailable."
            )

        signed_request = request
        timestamp = datetime.now(timezone.utc)
        amz_date = timestamp.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = timestamp.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(request.content or b"").hexdigest()
        signed_request.headers["host"] = request.url.host
        signed_request.headers["x-amz-date"] = amz_date
        signed_request.headers["x-amz-content-sha256"] = payload_hash

        canonical_uri = quote(request.url.path or "/", safe="/-_.~")
        canonical_query = "&".join(
            [
                f"{quote(key, safe='-_.~')}={quote(value, safe='-_.~')}"
                for key, value in sorted(request.url.params.multi_items())
            ]
        )
        canonical_headers = "".join(
            f"{key}:{' '.join(value.strip().split())}\n"
            for key, value in sorted(
                (header.lower(), signed_request.headers[header])
                for header in signed_request.headers
            )
        )
        signed_headers = ";".join(
            header.lower() for header in sorted({header for header in signed_request.headers})
        )
        canonical_request = "\n".join(
            [
                request.method.upper(),
                canonical_uri,
                canonical_query,
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )
        credential_scope = f"{date_stamp}/{region}/{self.service}/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signing_key = self._derive_signing_key(credentials.secret_access_key, date_stamp, region)
        signature = hmac.new(
            signing_key,
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signed_request.headers["Authorization"] = (
            "AWS4-HMAC-SHA256 "
            f"Credential={credentials.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return signed_request

    def _derive_signing_key(self, secret_access_key: str, date_stamp: str, region: str) -> bytes:
        k_date = hmac.new(
            f"AWS4{secret_access_key}".encode("utf-8"),
            date_stamp.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
        k_service = hmac.new(k_region, self.service.encode("utf-8"), hashlib.sha256).digest()
        return hmac.new(k_service, b"aws4_request", hashlib.sha256).digest()
