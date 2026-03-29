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
        page_size: int = 20,
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
    def create_aplus_upload_destination(
        self,
        *,
        marketplace_id: str | None,
        content_md5: str,
        content_type: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def upload_asset_to_destination(
        self,
        *,
        url: str,
        form_fields: dict[str, Any],
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def validate_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        asin_set: list[str],
        document_request: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def create_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        document_request: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def post_aplus_content_document_asin_relations(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        asin_set: list[str],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def submit_aplus_content_document_for_approval(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        included_data_set: list[str],
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
        page_size: int = 20,
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        params: dict[str, Any] = {
            "marketplaceIds": resolved_marketplace_id,
            "pageSize": page_size,
            "includedData": "summaries,attributes,offers,fulfillmentAvailability",
        }
        if next_token:
            params["pageToken"] = next_token

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

    def create_aplus_upload_destination(
        self,
        *,
        marketplace_id: str | None,
        content_md5: str,
        content_type: str,
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "POST",
            "/uploads/2020-11-01/uploadDestinations/aplus/2020-11-01/contentDocuments",
            marketplace_id=resolved_marketplace_id,
            params={
                "marketplaceIds": resolved_marketplace_id,
                "contentMD5": content_md5,
                "contentType": content_type,
            },
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
        self.client.upload_to_destination(
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
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "POST",
            "/aplus/2020-11-01/contentAsinValidations",
            marketplace_id=resolved_marketplace_id,
            params={
                "marketplaceId": resolved_marketplace_id,
                "asinSet": ",".join(asin_set),
            },
            json_body=document_request,
        )

    def create_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        document_request: dict[str, Any],
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "POST",
            "/aplus/2020-11-01/contentDocuments",
            marketplace_id=resolved_marketplace_id,
            params={"marketplaceId": resolved_marketplace_id},
            json_body=document_request,
        )

    def post_aplus_content_document_asin_relations(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        asin_set: list[str],
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "POST",
            f"/aplus/2020-11-01/contentDocuments/{content_reference_key}/asins",
            marketplace_id=resolved_marketplace_id,
            params={"marketplaceId": resolved_marketplace_id},
            json_body={"asinSet": asin_set},
        )

    def submit_aplus_content_document_for_approval(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "POST",
            f"/aplus/2020-11-01/contentDocuments/{content_reference_key}/approvalSubmissions",
            marketplace_id=resolved_marketplace_id,
            params={"marketplaceId": resolved_marketplace_id},
        )

    def get_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        included_data_set: list[str],
    ) -> dict[str, Any]:
        resolved_marketplace_id = marketplace_id or self.settings.marketplace_id
        return self.client.request(
            "GET",
            f"/aplus/2020-11-01/contentDocuments/{content_reference_key}",
            marketplace_id=resolved_marketplace_id,
            params={
                "marketplaceId": resolved_marketplace_id,
                "includedDataSet": ",".join(included_data_set),
            },
        )

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
        page_size: int = 20,
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

    def create_aplus_upload_destination(
        self,
        *,
        marketplace_id: str | None,
        content_md5: str,
        content_type: str,
    ) -> dict[str, Any]:
        return {
            "payload": {
                "uploadDestinationId": "mock-upload-destination",
                "url": "https://example.com/mock-upload",
                "headers": {
                    "key": "mock/key",
                    "policy": "mock-policy",
                },
            }
        }

    def upload_asset_to_destination(
        self,
        *,
        url: str,
        form_fields: dict[str, Any],
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> None:
        return None

    def validate_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        asin_set: list[str],
        document_request: dict[str, Any],
    ) -> dict[str, Any]:
        return {"warnings": [], "errors": []}

    def create_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        document_request: dict[str, Any],
    ) -> dict[str, Any]:
        return {"warnings": [], "contentReferenceKey": "mock-content-reference"}

    def post_aplus_content_document_asin_relations(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        asin_set: list[str],
    ) -> dict[str, Any]:
        return {"warnings": []}

    def submit_aplus_content_document_for_approval(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
    ) -> dict[str, Any]:
        return {"warnings": []}

    def get_aplus_content_document(
        self,
        *,
        marketplace_id: str | None,
        content_reference_key: str,
        included_data_set: list[str],
    ) -> dict[str, Any]:
        return {
            "warnings": [],
            "contentRecord": {
                "contentReferenceKey": content_reference_key,
                "contentMetadata": {
                    "name": "Mock A+ Content",
                    "marketplaceId": marketplace_id or self.settings.marketplace_id,
                    "status": "SUBMITTED",
                    "badgeSet": [],
                    "updateTime": "2026-03-29T00:00:00Z",
                },
            },
        }

    def process_notification_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "mock": True,
            "status": "received",
            "payload": payload,
        }
