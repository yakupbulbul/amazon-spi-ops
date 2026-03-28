from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import Settings
from app.services.amazon.exceptions import AmazonAuthorizationError


@dataclass
class LwaAccessToken:
    access_token: str
    expires_at: datetime

    def is_valid(self) -> bool:
        return self.expires_at > datetime.now(UTC) + timedelta(seconds=30)


class AmazonLwaAuthService:
    def __init__(self, settings: Settings, http_client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.http_client = http_client or httpx.Client(timeout=20.0)
        self._lock = threading.Lock()
        self._cached_token: LwaAccessToken | None = None

    def get_access_token(self, *, force_refresh: bool = False) -> str:
        with self._lock:
            if not force_refresh and self._cached_token and self._cached_token.is_valid():
                return self._cached_token.access_token

            if not (
                self.settings.lwa_client_id
                and self.settings.lwa_client_secret
                and self.settings.lwa_refresh_token
            ):
                raise AmazonAuthorizationError(
                    "Amazon LWA credentials are not configured. Live SP-API calls are unavailable."
                )

            response = self.http_client.post(
                self.settings.sp_api_token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.settings.lwa_refresh_token,
                    "client_id": self.settings.lwa_client_id,
                    "client_secret": self.settings.lwa_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            payload = response.json()

            expires_in = int(payload.get("expires_in", 3600))
            self._cached_token = LwaAccessToken(
                access_token=payload["access_token"],
                expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            )
            return self._cached_token.access_token
