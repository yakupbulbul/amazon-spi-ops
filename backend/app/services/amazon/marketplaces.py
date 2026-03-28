from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarketplaceDefinition:
    marketplace_id: str
    region: str
    endpoint: str


MARKETPLACE_REGISTRY: dict[str, MarketplaceDefinition] = {
    "ATVPDKIKX0DER": MarketplaceDefinition(
        marketplace_id="ATVPDKIKX0DER",
        region="us-east-1",
        endpoint="https://sellingpartnerapi-na.amazon.com",
    ),
    "A1AM78C64UM0Y8": MarketplaceDefinition(
        marketplace_id="A1AM78C64UM0Y8",
        region="us-east-1",
        endpoint="https://sellingpartnerapi-na.amazon.com",
    ),
    "A1PA6795UKMFR9": MarketplaceDefinition(
        marketplace_id="A1PA6795UKMFR9",
        region="eu-west-1",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
    ),
    "A1RKKUPIHCS9HS": MarketplaceDefinition(
        marketplace_id="A1RKKUPIHCS9HS",
        region="eu-west-1",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
    ),
    "A1F83G8C2ARO7P": MarketplaceDefinition(
        marketplace_id="A1F83G8C2ARO7P",
        region="eu-west-1",
        endpoint="https://sellingpartnerapi-eu.amazon.com",
    ),
}


def get_marketplace_definition(
    marketplace_id: str,
    *,
    override_endpoint: str = "",
    override_region: str = "",
) -> MarketplaceDefinition:
    definition = MARKETPLACE_REGISTRY.get(
        marketplace_id,
        MarketplaceDefinition(
            marketplace_id=marketplace_id,
            region=override_region or "us-east-1",
            endpoint=override_endpoint or "https://sellingpartnerapi-na.amazon.com",
        ),
    )
    if not override_endpoint and not override_region:
        return definition

    return MarketplaceDefinition(
        marketplace_id=definition.marketplace_id,
        region=override_region or definition.region,
        endpoint=override_endpoint or definition.endpoint,
    )
