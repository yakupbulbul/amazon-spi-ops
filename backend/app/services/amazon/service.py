from __future__ import annotations

from functools import cached_property
from decimal import Decimal
from typing import Any

from app.core.config import Settings, settings
from app.services.amazon.adapters import (
    AmazonSpApiAdapter,
    LiveAmazonSpApiAdapter,
    MockAmazonSpApiAdapter,
)
from app.services.amazon.client import AmazonSpApiClient
from app.services.amazon.exceptions import AmazonAuthorizationError


class AmazonSpApiService:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    @cached_property
    def client(self) -> AmazonSpApiClient:
        return AmazonSpApiClient(self.settings)

    @cached_property
    def live_adapter(self) -> AmazonSpApiAdapter:
        return LiveAmazonSpApiAdapter(self.client, self.settings)

    @cached_property
    def mock_adapter(self) -> AmazonSpApiAdapter:
        return MockAmazonSpApiAdapter(self.settings)

    def _has_core_sp_api_credentials(self) -> bool:
        return all(
            [
                self.settings.lwa_client_id,
                self.settings.lwa_client_secret,
                self.settings.lwa_refresh_token,
                self.settings.aws_access_key_id,
                self.settings.aws_secret_access_key,
                self.settings.marketplace_id,
            ]
        )

    def _has_listing_credentials(self) -> bool:
        return self._has_core_sp_api_credentials() and bool(self.settings.seller_id)

    def get_catalog_item(self, asin: str, *, marketplace_id: str | None = None) -> dict[str, Any]:
        adapter = self.live_adapter if self._has_core_sp_api_credentials() else self.mock_adapter
        return adapter.get_catalog_item(asin, marketplace_id=marketplace_id)

    def get_inventory_summaries(
        self,
        *,
        marketplace_id: str | None = None,
        seller_skus: list[str] | None = None,
    ) -> dict[str, Any]:
        adapter = self.live_adapter if self._has_core_sp_api_credentials() else self.mock_adapter
        return adapter.get_inventory_summaries(
            marketplace_id=marketplace_id,
            seller_skus=seller_skus,
        )

    def update_listing_price(
        self,
        *,
        sku: str,
        price: Decimal,
        currency: str,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        if not self._has_listing_credentials():
            raise AmazonAuthorizationError(
                "SELLER_ID is required for live listing mutations. Configure it before using real price updates."
            )
        return self.live_adapter.update_listing_price(
            sku=sku,
            price=price,
            currency=currency,
            marketplace_id=marketplace_id,
        )

    def update_listing_stock(
        self,
        *,
        sku: str,
        quantity: int,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        if not self._has_listing_credentials():
            raise AmazonAuthorizationError(
                "SELLER_ID is required for live listing mutations. Configure it before using real stock updates."
            )
        return self.live_adapter.update_listing_stock(
            sku=sku,
            quantity=quantity,
            marketplace_id=marketplace_id,
        )
