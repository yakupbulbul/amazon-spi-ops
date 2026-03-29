from app.schemas.aplus import AplusDraftPayload
from app.services.amazon.aplus_contract import (
    AmazonContractMapper,
    PreparedAmazonImageAsset,
)


def build_supported_draft(*, include_comparison: bool = False) -> AplusDraftPayload:
    modules = [
        {
            "module_id": "hero-module-1001",
            "module_type": "hero",
            "headline": "Daily comfort without bulk",
            "body": "The hero section explains the main shopper outcome clearly and keeps the promise grounded in daily use.",
            "bullets": [
                "Soft contact surface for longer wear",
                "Low-profile shape that keeps the fit tidy",
            ],
            "image_brief": "Product in use with a concise overlay cue.",
            "image_mode": "generated",
            "generated_image_url": "/media/aplus-assets/hero.jpg",
            "overlay_text": "Comfort that stays in place",
        },
        {
            "module_id": "feature-module-1001",
            "module_type": "feature",
            "headline": "Why the fit matters",
            "body": "Explain how the tailored fit improves comfort, reduces bunching, and keeps the product easier to use every day.",
            "bullets": [
                "Stays smoother during daily movement",
                "Reduces extra adjustment during setup",
                "Keeps the product looking more intentional",
            ],
            "image_brief": "Close-up detail showing the fit and surface.",
            "image_mode": "uploaded",
            "uploaded_image_url": "/media/aplus-assets/feature.jpg",
        },
        {
            "module_id": "faq-module-1001",
            "module_type": "faq",
            "headline": "Built for everyday use",
            "body": "Use this text block to reassure shoppers about the intended usage context, care expectations, and practical ownership details.",
            "bullets": [],
            "image_brief": "No image required.",
        },
    ]
    if include_comparison:
        modules.append(
            {
                "module_id": "comparison-module-1001",
                "module_type": "comparison",
                "headline": "Comparison",
                "body": "Editorial comparison block.",
                "bullets": ["Fit | Better support | Basic support"],
                "image_brief": "Comparison image brief.",
            }
        )
    return AplusDraftPayload(
        headline="Comfort that converts",
        subheadline="Clear benefits that stay concise for the supported Amazon modules.",
        brand_story="The brand story explains materials, usage context, and the practical reason this product feels different from generic alternatives.",
        key_features=[
            "Explains the benefit in shopper language",
            "Clarifies the day-to-day use case",
            "Makes the point of difference concrete",
        ],
        modules=modules,
        compliance_notes=[
            "Verify all factual claims before publish.",
            "Check imagery and image text before submission.",
        ],
    )


def build_prepared_assets() -> dict[str, PreparedAmazonImageAsset]:
    return {
        "hero-module-1001": PreparedAmazonImageAsset(
            upload_destination_id="sc/hero-asset.jpg",
            alt_text="Hero product shot",
            width_pixels=1200,
            height_pixels=700,
        ),
        "feature-module-1001": PreparedAmazonImageAsset(
            upload_destination_id="sc/feature-asset.jpg",
            alt_text="Feature detail image",
            width_pixels=900,
            height_pixels=900,
        ),
    }


def test_contract_mapper_builds_real_supported_amazon_payload() -> None:
    mapper = AmazonContractMapper()

    request = mapper.map_content_document(
        product_title="Publishable Product",
        locale="de-DE",
        draft_payload=build_supported_draft(),
        prepared_assets_by_module_id=build_prepared_assets(),
    )

    payload = request.model_dump(mode="json")
    modules = payload["contentDocument"]["contentModuleList"]

    assert payload["contentDocument"]["contentType"] == "EBC"
    assert modules[0]["contentModuleType"] == "STANDARD_HEADER_IMAGE_TEXT"
    assert modules[0]["standardHeaderImageText"]["block"]["image"]["uploadDestinationId"] == "sc/hero-asset.jpg"
    assert modules[1]["contentModuleType"] == "STANDARD_SINGLE_IMAGE_HIGHLIGHTS"
    assert modules[1]["standardSingleImageHighlights"]["image"]["uploadDestinationId"] == "sc/feature-asset.jpg"
    assert modules[2]["contentModuleType"] == "STANDARD_TEXT"


def test_contract_mapper_rejects_editorial_only_modules() -> None:
    mapper = AmazonContractMapper()

    try:
        mapper.map_content_document(
            product_title="Publishable Product",
            locale="de-DE",
            draft_payload=build_supported_draft(include_comparison=True),
            prepared_assets_by_module_id=build_prepared_assets(),
        )
    except ValueError as exc:
        assert "Unsupported modules present: comparison" in str(exc)
    else:
        raise AssertionError("comparison modules must be rejected from the real publish subset")


def test_contract_mapper_requires_image_assets_for_supported_image_modules() -> None:
    mapper = AmazonContractMapper()

    try:
        mapper.map_content_document(
            product_title="Publishable Product",
            locale="de-DE",
            draft_payload=build_supported_draft(),
            prepared_assets_by_module_id={},
        )
    except ValueError as exc:
        assert "missing an Amazon-prepared image asset" in str(exc)
    else:
        raise AssertionError("hero and feature modules must require prepared Amazon image assets")
