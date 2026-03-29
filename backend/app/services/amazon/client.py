from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.services.amazon.auth import AmazonLwaAuthService
from app.services.amazon.exceptions import AmazonRequestError
from app.services.amazon.marketplaces import get_marketplace_definition
from app.services.amazon.signing import AwsCredentials, AwsSigV4Signer

logger = logging.getLogger(__name__)


class AmazonSpApiClient:
    def __init__(self, settings: Settings, http_client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.http_client = http_client or httpx.Client(timeout=30.0)
        self.auth_service = AmazonLwaAuthService(settings, self.http_client)
        self.signer = AwsSigV4Signer()

    def request(
        self,
        method: str,
        path: str,
        *,
        marketplace_id: str | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        marketplace = get_marketplace_definition(
            marketplace_id or self.settings.marketplace_id,
            override_endpoint=self.settings.sp_api_endpoint,
            override_region=self.settings.aws_region,
        )
        access_token = self.auth_service.get_access_token()
        request = self.http_client.build_request(
            method.upper(),
            f"{marketplace.endpoint}{path}",
            params=params,
            json=json_body,
            headers={
                "content-type": "application/json",
                "x-amz-access-token": access_token,
                "user-agent": "amazon-seller-ops/0.1.0",
            },
        )
        signed_request = self.signer.sign(
            request,
            region=marketplace.region,
            credentials=AwsCredentials(
                access_key_id=self.settings.aws_access_key_id,
                secret_access_key=self.settings.aws_secret_access_key,
            ),
        )
        response = self.http_client.send(signed_request)
        if response.is_error:
            logger.error("SP-API request failed: %s %s", response.status_code, response.text)
            raise AmazonRequestError(
                f"SP-API request failed with status {response.status_code}: {response.text}"
            )
        return response.json()

    def upload_to_destination(
        self,
        *,
        url: str,
        form_fields: dict[str, Any],
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> None:
        response = self.http_client.post(
            url,
            data=form_fields,
            files={"file": (file_name, content, content_type)},
            headers={"user-agent": "amazon-seller-ops/0.1.0"},
        )
        if response.is_error:
            logger.error("Amazon upload destination failed: %s %s", response.status_code, response.text)
            raise AmazonRequestError(
                f"Amazon upload destination request failed with status {response.status_code}: {response.text}"
            )
