from decimal import Decimal

from app.services.amazon.mappers import map_search_listings_item


def test_map_search_listings_item_extracts_core_listing_fields() -> None:
    record = map_search_listings_item(
        {
            "sku": "DF-LPER-Z2CC",
            "summaries": [
                {
                    "marketplaceId": "A1PA6795UKMFR9",
                    "asin": "B0GS3SHBNH",
                    "itemName": "Seat Cover",
                    "status": ["DISCOVERABLE", "BUYABLE"],
                }
            ],
            "attributes": {
                "brand": [{"value": "PYATO"}],
                "fulfillment_availability": [
                    {"fulfillment_channel_code": "DEFAULT", "quantity": 7}
                ],
            },
            "offers": [
                {
                    "price": {
                        "currency": "EUR",
                        "currencyCode": "EUR",
                        "amount": "29.95",
                    }
                }
            ],
            "fulfillmentAvailability": [{"fulfillmentChannelCode": "DEFAULT", "quantity": 7}],
        },
        marketplace_id="A1PA6795UKMFR9",
    )

    assert record is not None
    assert record.sku == "DF-LPER-Z2CC"
    assert record.asin == "B0GS3SHBNH"
    assert record.title == "Seat Cover"
    assert record.brand == "PYATO"
    assert record.is_active is True
    assert record.price_amount == Decimal("29.95")
    assert record.price_currency == "EUR"
    assert record.quantity == 7
