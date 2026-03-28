from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class AmazonListingImportRecord:
    sku: str
    asin: str
    title: str
    brand: str | None
    is_active: bool
    price_amount: Decimal | None
    price_currency: str | None
    quantity: int | None


def map_search_listings_item(
    item: dict[str, Any], *, marketplace_id: str
) -> AmazonListingImportRecord | None:
    sku = item.get("sku")
    if not isinstance(sku, str) or not sku:
        return None

    summary = _get_marketplace_entry(item.get("summaries"), marketplace_id, "marketplaceId")
    if summary is None:
        return None

    asin = summary.get("asin")
    title = summary.get("itemName")
    if not isinstance(asin, str) or not asin:
        return None
    if not isinstance(title, str) or not title:
        title = sku

    attributes = item.get("attributes")
    offers = item.get("offers")
    fulfillment_availability = item.get("fulfillmentAvailability")

    return AmazonListingImportRecord(
        sku=sku,
        asin=asin,
        title=title,
        brand=_extract_brand(attributes),
        is_active=_extract_is_active(summary),
        price_amount=_extract_price_amount(offers),
        price_currency=_extract_price_currency(offers),
        quantity=_extract_quantity(fulfillment_availability, attributes),
    )


def _extract_brand(attributes: Any) -> str | None:
    if not isinstance(attributes, dict):
        return None

    for key in ("brand", "manufacturer"):
        values = attributes.get(key)
        if not isinstance(values, list):
            continue
        for entry in values:
            if not isinstance(entry, dict):
                continue
            value = entry.get("value")
            if isinstance(value, str) and value:
                return value
    return None


def _extract_is_active(summary: dict[str, Any]) -> bool:
    statuses = summary.get("status")
    if not isinstance(statuses, list):
        return False
    return any(status in {"BUYABLE", "DISCOVERABLE"} for status in statuses if isinstance(status, str))


def _extract_price_amount(offers: Any) -> Decimal | None:
    price = _extract_offer_price(offers)
    if price is None:
        return None

    amount = price.get("amount")
    if amount is None:
        return None
    try:
        return Decimal(str(amount))
    except (InvalidOperation, TypeError):
        return None


def _extract_price_currency(offers: Any) -> str | None:
    price = _extract_offer_price(offers)
    if price is None:
        return None

    currency = price.get("currency") or price.get("currencyCode")
    if isinstance(currency, str) and currency:
        return currency
    return None


def _extract_offer_price(offers: Any) -> dict[str, Any] | None:
    if not isinstance(offers, list):
        return None
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        price = offer.get("price")
        if isinstance(price, dict):
            return price
    return None


def _extract_quantity(fulfillment_availability: Any, attributes: Any) -> int | None:
    for candidate in (
        _extract_default_quantity(fulfillment_availability, "fulfillmentChannelCode"),
        _extract_attribute_quantity(attributes),
    ):
        if candidate is not None:
            return candidate
    return None


def _extract_default_quantity(entries: Any, code_key: str) -> int | None:
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get(code_key) != "DEFAULT":
            continue
        quantity = entry.get("quantity")
        if isinstance(quantity, int):
            return quantity
    return None


def _extract_attribute_quantity(attributes: Any) -> int | None:
    if not isinstance(attributes, dict):
        return None
    return _extract_default_quantity(attributes.get("fulfillment_availability"), "fulfillment_channel_code")


def _get_marketplace_entry(entries: Any, marketplace_id: str, key: str) -> dict[str, Any] | None:
    if not isinstance(entries, list):
        return None

    fallback: dict[str, Any] | None = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if fallback is None:
            fallback = entry
        if entry.get(key) == marketplace_id:
            return entry
    return fallback
