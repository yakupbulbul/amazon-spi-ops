from app.core.config import Settings
from app.schemas.aplus import AplusDraftPayload
from app.services.ai.openai_service import OpenAiAplusService
from app.services.aplus_optimization import build_aplus_optimization_report


def test_optimization_report_scores_missing_structure_and_generic_copy() -> None:
    payload = AplusDraftPayload(
        headline="Premium quality comfort",
        subheadline="A strong solution for everyday use in every situation.",
        brand_story=(
            "This premium quality product delivers high quality support and feels great for everyday use "
            "without clearly explaining why it is different."
        ),
        key_features=[
            "Premium quality feel for everyday use",
            "Great for everyday use",
            "High quality support for daily comfort",
        ],
        modules=[
            {
                "module_type": "hero",
                "headline": "Premium quality comfort",
                "body": "Premium quality comfort for everyday use without showing why it matters.",
                "bullets": [
                    "Premium quality feel for everyday use",
                    "Great for everyday use",
                ],
                "image_brief": "Generic lifestyle shot with a premium image look.",
                "image_mode": "generated",
                "image_prompt": "Beautiful lifestyle shot on a clean background.",
            },
            {
                "module_type": "feature",
                "headline": "Great for everyday use",
                "body": "Great for everyday use and premium quality comfort in every routine.",
                "bullets": [
                    "Great for everyday use",
                ],
                "image_brief": "Beautiful image on a clean background.",
            },
            {
                "module_type": "faq",
                "headline": "Easy comfort",
                "body": "Great for everyday use and premium quality comfort in every routine.",
                "bullets": [
                    "Great for everyday use",
                ],
                "image_brief": "Nice lighting and a generic product scene.",
            },
        ],
        compliance_notes=[
            "Review every claim before publishing.",
            "Check visuals before launch.",
        ],
    )

    report = build_aplus_optimization_report(draft_payload=payload)

    assert report.overall_score < 70
    assert report.structure_score < 80
    assert report.differentiation_score < 65
    assert report.image_quality_score is not None
    assert "Feature blocks" in report.missing_sections
    assert "Comparison table" in report.missing_sections
    assert any(issue.title == "Add comparison section" for issue in report.critical_issues)
    assert any(issue.title == "Too generic" for issue in report.warnings)
    assert any(insight.section == "Comparison module" for insight in report.section_insights)


def test_optimization_report_rewards_complete_differentiated_mock_draft() -> None:
    generator = OpenAiAplusService(
        Settings(
            OPENAI_API_KEY="",
            OPENAI_MODEL="gpt-4o-mini",
        )
    )

    draft = generator.generate_aplus_draft(
        product_context={
            "title": "Trail Backpack",
            "brand": "Nordvale",
            "sku": "TRAIL-42",
            "asin": "B0TESTEN01",
            "marketplace_id": "A1F83G8C2ARO7P",
        },
        brand_tone="premium and technical",
        positioning="commuters and day-hike users",
        source_language="en-GB",
    )

    report = build_aplus_optimization_report(draft_payload=draft)

    assert report.overall_score >= 75
    assert report.structure_score >= 80
    assert report.clarity_score >= 70
    assert report.differentiation_score >= 70
    assert report.completeness_score >= 70
    assert report.critical_issues == []
