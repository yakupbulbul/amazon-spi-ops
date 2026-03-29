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

    def search_listings_items(
        self,
        *,
        marketplace_id: str | None = None,
        next_token: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        if self._has_listing_credentials():
            return self.live_adapter.search_listings_items(
                marketplace_id=marketplace_id,
                next_token=next_token,
                page_size=page_size,
            )
        if self._has_core_sp_api_credentials():
            raise AmazonAuthorizationError(
                "SELLER_ID is required for live listing imports. Configure it before importing Amazon products."
            )
        return self.mock_adapter.search_listings_items(
            marketplace_id=marketplace_id,
            next_token=next_token,
            page_size=page_size,
        )

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

    def create_aplus_upload_destination(
        self,
        *,
        marketplace_id: str | None,
        content_md5: str,
        content_type: str,
    ) -> dict[str, Any]:
        if not self._has_core_sp_api_credentials():
            raise AmazonAuthorizationError(
                "Live Amazon A+ publishing requires SP-API credentials and marketplace configuration."
            )
        return self.live_adapter.create_aplus_upload_destination(
            marketplace_id=marketplace_id,
            content_md5=content_md5,
            content_type=content_type,
        )

    def upload_asset_to_destination(
        self,
        *,
        url: str,
        form_fields: dict[str, Any],
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> None:
        if not self._has_core_sp_api_credentials():
            raise AmazonAuthorizationError(
                "Live Amazon A+ publishing requires SP-API credentials and marketplace configuration."
            )
        self.live_adapter.upload_asset_to_destination(
            url=url,
            form_fields=form_fields,
            file_name=file_name,
            content=content,
            content_type=content_type,
        )

    def validate_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        asin_set: list[str],
        document_request: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._has_core_sp_api_credentials():
            raise AmazonAuthorizationError(
                "Live Amazon A+ publishing requires SP-API credentials and marketplace configuration."
            )
        return self.live_adapter.validate_aplus_content_document(
            marketplace_id=marketplace_id,
            asin_set=asin_set,
            document_request=document_request,
        )

    def create_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        document_request: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._has_core_sp_api_credentials():
            raise AmazonAuthorizationError(
                "Live Amazon A+ publishing requires SP-API credentials and marketplace configuration."
            )
        return self.live_adapter.create_aplus_content_document(
            marketplace_id=marketplace_id,
            document_request=document_request,
        )

    def post_aplus_content_document_asin_relations(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        asin_set: list[str],
    ) -> dict[str, Any]:
        if not self._has_core_sp_api_credentials():
            raise AmazonAuthorizationError(
                "Live Amazon A+ publishing requires SP-API credentials and marketplace configuration."
            )
        return self.live_adapter.post_aplus_content_document_asin_relations(
            marketplace_id=marketplace_id,
            content_reference_key=content_reference_key,
            asin_set=asin_set,
        )

    def submit_aplus_content_document_for_approval(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
    ) -> dict[str, Any]:
        if not self._has_core_sp_api_credentials():
            raise AmazonAuthorizationError(
                "Live Amazon A+ publishing requires SP-API credentials and marketplace configuration."
            )
        return self.live_adapter.submit_aplus_content_document_for_approval(
            marketplace_id=marketplace_id,
            content_reference_key=content_reference_key,
        )

    def get_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        included_data_set: list[str],
    ) -> dict[str, Any]:
        if not self._has_core_sp_api_credentials():
            raise AmazonAuthorizationError(
                "Live Amazon A+ publishing requires SP-API credentials and marketplace configuration."
            )
        return self.live_adapter.get_aplus_content_document(
            marketplace_id=marketplace_id,
            content_reference_key=content_reference_key,
            included_data_set=included_data_set,
        )
