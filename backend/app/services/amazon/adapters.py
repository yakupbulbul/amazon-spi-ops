from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from app.core.config import Settings
from app.services.amazon.client import AmazonSpApiClient


class AmazonSpApiAdapter(ABC):
    @abstractmethod
    def search_listings_items(
        self,
        *,
        marketplace_id: str | None = None,
        next_token: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_catalog_item(self, asin: str, *, marketplace_id: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_inventory_summaries(
        self,
        *,
        marketplace_id: str | None = None,
        seller_skus: list[str] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_listing_price(
        self,
        *,
        sku: str,
        price: Decimal,
        currency: str,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_listing_stock(
        self,
        *,
        sku: str,
        quantity: int,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def prepare_aplus_content_payload(
        self,
        *,
        asin: str,
        draft_content: dict[str, Any],
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def process_notification_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class LiveAmazonSpApiAdapter(AmazonSpApiAdapter):
    def __init__(self, client: AmazonSpApiClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    def search_listings_items(
        self,
        *,
        marketplace_id: str | None = None,
        next_token: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        params: dict[str, Any] = {
            "marketplaceIds": resolved_marketplace_id,
            "pageSize": page_size,
            "includedData": "summaries,attributes,offers,fulfillmentAvailability",
        }
        if next_token:
            params["nextToken"] = next_token

        return self.client.request(
            "GET",
            f"/listings/2021-08-01/items/{self.settings.seller_id}",
            marketplace_id=resolved_marketplace_id,
            params=params,
        )

    def get_catalog_item(self, asin: str, *, marketplace_id: str | None = None) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "GET",
            f"/catalog/2022-04-01/items/{asin}",
            marketplace_id=resolved_marketplace_id,
            params={"marketplaceIds": resolved_marketplace_id},
        )

    def get_inventory_summaries(
        self,
        *,
        marketplace_id: str | None = None,
        seller_skus: list[str] | None = None,
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        params: dict[str, Any] = {
            "granularityType": "Marketplace",
            "granularityId": resolved_marketplace_id,
            "marketplaceIds": resolved_marketplace_id,
            "details": "true",
        }
        if seller_skus:
            params["sellerSkus"] = ",".join(seller_skus)

        return self.client.request(
            "GET",
            "/fba/inventory/v1/summaries",
            marketplace_id=resolved_marketplace_id,
            params=params,
        )

    def update_listing_price(
        self,
        *,
        sku: str,
        price: Decimal,
        currency: str,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "PATCH",
            f"/listings/2021-08-01/items/{self.settings.seller_id}/{sku}",
            marketplace_id=resolved_marketplace_id,
            params={"marketplaceIds": resolved_marketplace_id},
            json_body={
                "productType": "PRODUCT",
                "patches": [
                    {
                        "op": "replace",
                        "path": "/attributes/purchasable_offer",
                        "value": [
                            {
                                "marketplace_id": resolved_marketplace_id,
                                "currency": currency,
                                "our_price": [{"schedule": [{"value_with_tax": float(price)}]}],
                            }
                        ],
                    }
                ],
            },
        )

    def update_listing_stock(
        self,
        *,
        sku: str,
        quantity: int,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "PATCH",
            f"/listings/2021-08-01/items/{self.settings.seller_id}/{sku}",
            marketplace_id=resolved_marketplace_id,
            params={"marketplaceIds": resolved_marketplace_id},
            json_body={
                "productType": "PRODUCT",
                "patches": [
                    {
                        "op": "replace",
                        "path": "/attributes/fulfillment_availability",
                        "value": [
                            {
                                "fulfillment_channel_code": "DEFAULT",
                                "quantity": quantity,
                            }
                        ],
                    }
                ],
            },
        )

    def prepare_aplus_content_payload(
        self,
        *,
        asin: str,
        draft_content: dict[str, Any],
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "asin": asin,
            "marketplace_id": marketplace_id or self.settings.marketplace_id,
            "content_type": "EMC",
            "content_subtype": "aplus",
            "draft_content": draft_content,
        }

    def process_notification_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "amazon_sp_api",
            "status": "received",
            "payload": payload,
        }


class MockAmazonSpApiAdapter(AmazonSpApiAdapter):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search_listings_items(
        self,
        *,
        marketplace_id: str | None = None,
        next_token: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        items = [
            {
                "sku": "MOCK-AMZ-001",
                "summaries": [
                    {
                        "marketplaceId": resolved_marketplace_id,
                        "asin": "B0MOCKSKU01",
                        "itemName": "Mock Amazon Imported Product",
                        "status": ["BUYABLE"],
                    }
                ],
                "attributes": {
                    "brand": [{"value": "Mock Brand"}],
                    "fulfillment_availability": [
                        {"fulfillment_channel_code": "DEFAULT", "quantity": 12}
                    ],
                },
                "offers": [
                    {"price": {"currency": "EUR", "currencyCode": "EUR", "amount": "19.99"}}
                ],
                "fulfillmentAvailability": [{"fulfillmentChannelCode": "DEFAULT", "quantity": 12}],
            },
            {
                "sku": "MOCK-AMZ-002",
                "summaries": [
                    {
                        "marketplaceId": resolved_marketplace_id,
                        "asin": "B0MOCKSKU02",
                        "itemName": "Mock Imported Accessory",
                        "status": ["DISCOVERABLE"],
                    }
                ],
                "attributes": {
                    "manufacturer": [{"value": "Mock Manufacturer"}],
                    "fulfillment_availability": [
                        {"fulfillment_channel_code": "DEFAULT", "quantity": 4}
                    ],
                },
                "offers": [
                    {"price": {"currency": "EUR", "currencyCode": "EUR", "amount": "9.49"}}
                ],
                "fulfillmentAvailability": [{"fulfillmentChannelCode": "DEFAULT", "quantity": 4}],
            },
        ]
        return {
            "mock": True,
            "numberOfResults": len(items),
            "pagination": {"nextToken": None if next_token else ""},
            "items": items[:page_size],
        }

    def get_catalog_item(self, asin: str, *, marketplace_id: str | None = None) -> dict[str, Any]:
        return {
            "mock": True,
            "asin": asin,
            "marketplace_id": marketplace_id or self.settings.marketplace_id,
            "title": "Mock catalog item",
        }

    def get_inventory_summaries(
        self,
        *,
        marketplace_id: str | None = None,
        seller_skus: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "mock": True,
            "marketplace_id": marketplace_id or self.settings.marketplace_id,
            "seller_skus": seller_skus or [],
            "summaries": [],
        }

    def update_listing_price(
        self,
        *,
        sku: str,
        price: Decimal,
        currency: str,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "mock": True,
            "sku": sku,
            "price": str(price),
            "currency": currency,
            "marketplace_id": marketplace_id or self.settings.marketplace_id,
            "status": "accepted",
        }

    def update_listing_stock(
        self,
        *,
        sku: str,
        quantity: int,
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "mock": True,
            "sku": sku,
            "quantity": quantity,
            "marketplace_id": marketplace_id or self.settings.marketplace_id,
            "status": "accepted",
        }

    def prepare_aplus_content_payload(
        self,
        *,
        asin: str,
        draft_content: dict[str, Any],
        marketplace_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "mock": True,
            "asin": asin,
            "marketplace_id": marketplace_id or self.settings.marketplace_id,
            "draft_content": draft_content,
        }

    def process_notification_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "mock": True,
            "status": "received",
            "payload": payload,
        }
