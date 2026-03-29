from app.core.config import Settings
from app.schemas.aplus import AplusDraftPayload
from app.services.ai.openai_service import OpenAiAplusService
from app.services.aplus_optimization import build_aplus_improvement_issues
from app.services.aplus_service import AplusService


def build_generic_draft() -> AplusDraftPayload:
    return AplusDraftPayload(
        headline="High quality comfort for daily use",
        subheadline="Premium quality support for everyday routines and general convenience.",
        brand_story=(
            "This brand story uses broad quality language and needs stronger product-specific"
            " reasons for why the shopper should choose it over a generic alternative."
        ),
        key_features=[
            "High quality comfort for everyday use",
            "Premium quality construction for daily routines",
            "Designed for everyday use with dependable support",
        ],
        modules=[
            {
                "module_id": "hero-module-001",
                "module_type": "hero",
                "headline": "Premium quality comfort",
                "body": "This hero uses broad quality claims without explaining the practical shopper benefit in clear terms.",
                "bullets": [
                    "High quality materials",
                    "Great for everyday use",
                ],
                "image_brief": "Show the product in use with a clear shopper-focused image direction.",
                "image_mode": "generated",
                "image_prompt": "Product in a clean lifestyle scene",
                "generated_image_url": "https://example.com/generated-hero.png",
                "uploaded_image_url": None,
                "selected_asset_id": "asset-hero-001",
                "reference_asset_ids": ["ref-asset-1"],
                "overlay_text": "Everyday comfort",
                "image_status": "completed",
                "image_error_message": None,
                "image_request_fingerprint": "fingerprint-hero-1",
            },
            {
                "module_id": "feature-module-001",
                "module_type": "feature",
                "headline": "Benefits that matter",
                "body": "This section is still too generic and does not explain why the feature is better than a generic alternative.",
                "bullets": [
                    "Premium quality feel",
                    "Ideal for everyday use",
                ],
                "image_brief": "Close-up detail shot of the product.",
                "image_mode": "uploaded",
                "image_prompt": None,
                "generated_image_url": None,
                "uploaded_image_url": "https://example.com/uploaded-feature.png",
                "selected_asset_id": "asset-feature-001",
                "reference_asset_ids": [],
                "overlay_text": "Built for daily use",
                "image_status": "completed",
                "image_error_message": None,
                "image_request_fingerprint": None,
            },
            {
                "module_id": "comparison-module-001",
                "module_type": "comparison",
                "headline": "Beyond the generic option",
                "body": "Compares against a generic alternative but still stays too broad to help a shopper decide.",
                "bullets": [
                    "Generic option | More comfort | Better support",
                    "Everyday use | Premium quality | High quality feel",
                ],
                "image_brief": "Simple comparison graphic.",
                "image_mode": "none",
                "image_prompt": None,
                "generated_image_url": None,
                "uploaded_image_url": None,
                "selected_asset_id": None,
                "reference_asset_ids": [],
                "overlay_text": None,
                "image_status": "idle",
                "image_error_message": None,
                "image_request_fingerprint": None,
            },
        ],
        compliance_notes=[
            "Verify every product claim before publishing.",
            "Review the final copy for marketplace-safe phrasing.",
        ],
    )


def test_build_aplus_improvement_issues_returns_category_specific_feedback() -> None:
    draft = build_generic_draft()

    issues = build_aplus_improvement_issues(
        draft_payload=draft,
        category="differentiation",
    )

    assert issues
    assert any("generic" in issue.title.lower() or "differentiation" in issue.section.lower() for issue in issues)


def test_mock_improvement_rewrites_targeted_copy_and_preserves_control_fields() -> None:
    service = OpenAiAplusService(
        Settings(
            OPENAI_API_KEY="",
            OPENAI_MODEL="gpt-4o-mini",
        )
    )
    draft = build_generic_draft()

    improved_payload, summary = service.improve_aplus_draft(
        draft_payload=draft,
        category="differentiation",
        issues=["Replace generic quality phrases with concrete everyday advantages."],
        language="en-US",
        product_context={
            "title": "Seat Cover",
            "brand": "PYATO",
            "sku": "DF-LPER-Z2CC",
            "asin": "B0GS3SHBNH",
            "marketplace_id": "A1PA6795UKMFR9",
        },
    )

    assert "generic alternatives" in summary.lower()
    assert improved_payload.subheadline != draft.subheadline
    assert improved_payload.modules[0].body != draft.modules[0].body
    assert improved_payload.modules[0].module_id == draft.modules[0].module_id
    assert improved_payload.modules[0].image_mode == draft.modules[0].image_mode
    assert improved_payload.modules[0].selected_asset_id == draft.modules[0].selected_asset_id
    assert improved_payload.modules[0].generated_image_url == draft.modules[0].generated_image_url
    assert improved_payload.modules[0].overlay_text == draft.modules[0].overlay_text
    assert improved_payload.modules[1].uploaded_image_url == draft.modules[1].uploaded_image_url
    assert improved_payload.modules[1].image_status == draft.modules[1].image_status


def test_improvement_change_builder_lists_only_changed_shopper_facing_fields() -> None:
    original = build_generic_draft()
    improved = AplusDraftPayload.model_validate(
        {
            **original.model_dump(mode="json"),
            "headline": "Clear everyday comfort",
            "modules": [
                {
                    **original.modules[0].model_dump(mode="json"),
                    "body": "A clearer hero that explains the practical shopper benefit first.",
                },
                original.modules[1].model_dump(mode="json"),
                original.modules[2].model_dump(mode="json"),
            ],
        }
    )

    changes = AplusService._build_improvement_changes(
        original_payload=original,
        improved_payload=improved,
    )

    assert any(change.path == "headline" for change in changes)
    assert any(change.path.endswith(".body") for change in changes)
    assert all("image" not in change.path for change in changes)
