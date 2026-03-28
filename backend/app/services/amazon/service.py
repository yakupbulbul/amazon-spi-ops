from __future__ import annotations

from functools import cached_property
from typing import Any

from app.core.config import Settings, settings
from app.services.amazon.adapters import (
    AmazonSpApiAdapter,
    LiveAmazonSpApiAdapter,
    MockAmazonSpApiAdapter,
)
from app.services.amazon.client import AmazonSpApiClient


class AmazonSpApiService:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    @cached_property
    def client(self) -> AmazonSpApiClient:
        return AmazonSpApiClient(self.settings)

    @cached_property
    def adapter(self) -> AmazonSpApiAdapter:
        if self._should_use_mock_adapter():
            return MockAmazonSpApiAdapter(self.settings)
        return LiveAmazonSpApiAdapter(self.client, self.settings)

    def _should_use_mock_adapter(self) -> bool:
        return not all(
            [
                self.settings.lwa_client_id,
                self.settings.lwa_client_secret,
                self.settings.lwa_refresh_token,
                self.settings.aws_access_key_id,
                self.settings.aws_secret_access_key,
                self.settings.seller_id,
                self.settings.marketplace_id,
            ]
        )

    def get_catalog_item(self, asin: str, *, marketplace_id: str | None = None) -> dict[str, Any]:
        return self.adapter.get_catalog_item(asin, marketplace_id=marketplace_id)

    def get_inventory_summaries(
        self,
        *,
        marketplace_id: str | None = None,
        seller_skus: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.adapter.get_inventory_summaries(
            marketplace_id=marketplace_id,
            seller_skus=seller_skus,
        )

