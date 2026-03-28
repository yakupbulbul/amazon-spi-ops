from __future__ import annotations

import re
from statistics import mean

from app.schemas.aplus import (
    AplusDraftPayload,
    AplusOptimizationReport,
    AplusOptimizationSectionInsight,
    AplusOptimizationSuggestion,
)

_GENERIC_PHRASES: tuple[str, ...] = (
    "high quality",
    "premium quality",
    "great for everyday use",
    "ideal for everyday use",
    "designed for everyday use",
    "premium design",
    "top choice",
    "perfect for",
    "high-quality",
    "hochwertig",
    "premium qualität",
    "ideal für den alltag",
    "für den alltag",
)

_BENEFIT_TERMS: tuple[str, ...] = (
    "helps",
    "keeps",
    "reduces",
    "supports",
    "lets you",
    "so you can",
    "so that",
    "gives you",
    "für",
    "damit",
    "sorgt",
    "reduziert",
    "erleichtert",
    "verbessert",
    "easier",
    "clearer",
    "confidence",
    "comfortable",
    "dependable",
    "protects",
    "fits",
    "built to",
    "designed to",
)

_USAGE_TERMS: tuple[str, ...] = (
    "commute",
    "travel",
    "daily",
    "weekend",
    "office",
    "home",
    "outdoor",
    "gym",
    "family",
    "workflow",
    "unterwegs",
    "alltag",
    "reise",
    "büro",
    "zuhause",
    "arbeit",
    "freizeit",
)

_TECHNICAL_TERMS: tuple[str, ...] = (
    "material",
    "fabric",
    "capacity",
    "size",
    "weight",
    "finish",
    "coating",
    "fit",
    "compatib",
    "wasser",
    "größe",
    "gewicht",
    "material",
    "maß",
    "oberfläche",
)

_QUESTION_TERMS: tuple[str, ...] = (
    "how",
    "when",
    "why",
    "which",
    "fits",
    "works",
    "care",
    "clean",
    "setup",
    "use",
    "wie",
    "wann",
    "warum",
    "passt",
    "pflege",
    "reinigen",
    "nutzen",
)

_DIFFERENTIATION_TERMS: tuple[str, ...] = (
    "unlike",
    "instead of",
    "compared with",
    "compared to",
    "generic",
    "tailored",
    "precise",
    "targeted",
    "instead",
    "im Gegensatz",
    "generisch",
    "gezielt",
    "präzise",
    "passgenau",
)

_IMAGE_GENERIC_TERMS: tuple[str, ...] = (
    "beautiful image",
    "premium image",
    "generic",
    "clean background",
    "lifestyle shot",
    "nice lighting",
    "schönes bild",
    "lifestyle",
    "freigestellt",
)


def build_aplus_optimization_report(*, draft_payload: AplusDraftPayload) -> AplusOptimizationReport:
    critical_issues: list[AplusOptimizationSuggestion] = []
    warnings: list[AplusOptimizationSuggestion] = []
    section_insights: list[AplusOptimizationSectionInsight] = []
    missing_sections: list[str] = []

    def add_issue(
        *,
        severity: str,
        section: str,
        title: str,
        message: str,
    ) -> None:
        suggestion = AplusOptimizationSuggestion(
            severity=severity, section=section, title=title, message=message
        )
        insight = AplusOptimizationSectionInsight(
            section=section, severity=severity, summary=title
        )
        if severity == "critical":
            critical_issues.append(suggestion)
        else:
            warnings.append(suggestion)
        if not any(
            existing.section == insight.section and existing.summary == insight.summary
            for existing in section_insights
        ):
            section_insights.append(insight)

    modules = draft_payload.modules
    feature_modules = [module for module in modules if module.module_type == "feature"]
    comparison_module = next((module for module in modules if module.module_type == "comparison"), None)
    hero_module = next((module for module in modules if module.module_type == "hero"), None)

    if hero_module is None:
        missing_sections.append("Hero section")
        add_issue(
            severity="critical",
            section="Hero section",
            title="Add a clearer hero module",
            message="Add a hero section with a concise value proposition that leads the shopper into the rest of the draft.",
        )

    if len(feature_modules) < 2:
        missing_sections.append("Feature blocks")
        add_issue(
            severity="critical",
            section="Feature blocks",
            title="Add more feature depth",
            message="Expand to at least three feature blocks so the draft covers multiple shopper benefits instead of one narrow angle.",
        )
    elif len(feature_modules) < 3 and len(draft_payload.key_features) < 4:
        missing_sections.append("Feature depth")
        add_issue(
            severity="warning",
            section="Feature blocks",
            title="Broaden the benefit story",
            message="Add one more feature angle or expand the key features so the draft covers three to four convincing benefit points.",
        )
    elif len(feature_modules) > 4:
        add_issue(
            severity="warning",
            section="Feature blocks",
            title="Feature set feels crowded",
            message="Trim the feature stack to the strongest three or four blocks so the layout stays scannable.",
        )

    if not _has_usage_context(draft_payload):
        missing_sections.append("Usage or lifestyle section")
        add_issue(
            severity="warning",
            section="Usage scenario",
            title="Clarify usage scenario",
            message="Show where the product fits into daily use so the shopper can picture it in context.",
        )

    if comparison_module is None:
        missing_sections.append("Comparison table")
        add_issue(
            severity="critical",
            section="Comparison module",
            title="Add comparison section",
            message="Add a comparison module that shows why this product is stronger than generic alternatives.",
        )

    if len(normalize_text(draft_payload.brand_story)) < 90:
        missing_sections.append("Brand story")
        add_issue(
            severity="warning",
            section="Brand story",
            title="Strengthen brand story",
            message="Use the brand story to explain why the product approach is trustworthy, not just what the brand is called.",
        )

    structure_score = _bounded_score(
        100
        - (20 if hero_module is None else 0)
        - (25 if len(feature_modules) < 2 else 0)
        - (10 if len(feature_modules) < 3 and len(draft_payload.key_features) < 4 else 0)
        - (10 if len(feature_modules) > 4 else 0)
        - (15 if comparison_module is None else 0)
        - (10 if not _has_usage_context(draft_payload) else 0)
        - (10 if len(normalize_text(draft_payload.brand_story)) < 90 else 0)
    )

    clarity_penalty = 0
    all_copy = _collect_copy(draft_payload)
    repeated_sections = _find_repeated_sections(all_copy)
    if repeated_sections:
        clarity_penalty += 10
        add_issue(
            severity="warning",
            section="Cross-section copy",
            title="Reduce repeated copy",
            message=f"Too much copy is repeated across {', '.join(repeated_sections[:3])}. Give each section a distinct job.",
        )

    weak_headings = [
        label
        for label, text in _heading_entries(draft_payload)
        if _is_heading_weak(normalize_text(text))
    ]
    if weak_headings:
        clarity_penalty += 10
        add_issue(
            severity="warning",
            section="Headlines",
            title="Improve heading clarity",
            message=f"Shorten and sharpen {weak_headings[0]} so the benefit is obvious at a glance.",
        )

    dense_sections = [
        label
        for label, text in all_copy
        if label.startswith("Module") and len(text.strip()) > 380
    ]
    if dense_sections:
        clarity_penalty += 8
        add_issue(
            severity="warning",
            section="Module copy",
            title="Reduce content density",
            message=f"{dense_sections[0]} is too dense for module-based reading. Break the idea into sharper benefits.",
        )

    if not _has_benefit_driven_copy(draft_payload):
        clarity_penalty += 18
        add_issue(
            severity="critical",
            section="Benefit messaging",
            title="Explain why features matter",
            message="The draft lists features but does not consistently explain the shopper outcome those features create.",
        )

    clarity_score = _bounded_score(100 - clarity_penalty)

    differentiation_penalty = 0
    generic_hits = [
        label for label, text in all_copy if any(term in normalize_text(text) for term in _GENERIC_PHRASES)
    ]
    if generic_hits:
        differentiation_penalty += 24
        add_issue(
            severity="warning",
            section="Differentiation",
            title="Too generic",
            message=f"{generic_hits[0]} relies on generic quality language. Replace it with a product-specific advantage.",
        )

    if not _has_differentiation_signals(draft_payload):
        differentiation_penalty += 22
        add_issue(
            severity="critical",
            section="Differentiation",
            title="No clear differentiation",
            message="Call out what is tailored, more precise, or more useful than a generic alternative.",
        )

    if comparison_module and not _comparison_is_meaningful(comparison_module):
        differentiation_penalty += 16
        add_issue(
            severity="warning",
            section="Comparison module",
            title="Make advantages more concrete",
            message="The comparison section exists, but the product advantages still read too broad to persuade a shopper.",
        )

    differentiation_score = _bounded_score(100 - differentiation_penalty)

    completeness_penalty = 0
    if not _has_technical_detail(draft_payload):
        completeness_penalty += 18
        add_issue(
            severity="warning",
            section="Technical detail",
            title="Add practical product detail",
            message="Add sizing, material, compatibility, or build details so the shopper can judge fit with confidence.",
        )

    if not _answers_customer_questions(draft_payload):
        completeness_penalty += 18
        add_issue(
            severity="warning",
            section="Customer education",
            title="Answer likely shopper questions",
            message="Clarify usage, fit, care, or setup questions before the customer has to infer them.",
        )

    if not _has_usage_context(draft_payload):
        completeness_penalty += 14
    if comparison_module is None:
        completeness_penalty += 12

    completeness_score = _bounded_score(100 - completeness_penalty)

    image_quality_score = _score_images(draft_payload, add_issue=add_issue)

    component_scores = [
        structure_score,
        clarity_score,
        differentiation_score,
        completeness_score,
    ]
    if image_quality_score is not None:
        component_scores.append(image_quality_score)
    overall_score = int(round(mean(component_scores)))

    return AplusOptimizationReport(
        overall_score=overall_score,
        structure_score=structure_score,
        clarity_score=clarity_score,
        differentiation_score=differentiation_score,
        completeness_score=completeness_score,
        image_quality_score=image_quality_score,
        missing_sections=missing_sections,
        critical_issues=critical_issues,
        warnings=warnings,
        section_insights=section_insights,
    )


def _collect_copy(draft_payload: AplusDraftPayload) -> list[tuple[str, str]]:
    entries = [
        ("Headline", draft_payload.headline),
        ("Subheadline", draft_payload.subheadline),
        ("Brand story", draft_payload.brand_story),
    ]
    entries.extend(
        (f"Key feature {index}", feature)
        for index, feature in enumerate(draft_payload.key_features, start=1)
    )
    for index, module in enumerate(draft_payload.modules, start=1):
        entries.append((f"Module {index} headline", module.headline))
        entries.append((f"Module {index} body", module.body))
        entries.extend(
            (f"Module {index} bullet {bullet_index}", bullet)
            for bullet_index, bullet in enumerate(module.bullets, start=1)
        )
        entries.append((f"Module {index} image brief", module.image_brief))
    return entries


def _heading_entries(draft_payload: AplusDraftPayload) -> list[tuple[str, str]]:
    entries = [("Headline", draft_payload.headline), ("Subheadline", draft_payload.subheadline)]
    entries.extend(
        (f"Module {index} headline", module.headline)
        for index, module in enumerate(draft_payload.modules, start=1)
    )
    return entries


def _find_repeated_sections(entries: list[tuple[str, str]]) -> list[str]:
    duplicates: dict[str, list[str]] = {}
    for label, text in entries:
        if "bullet" in label.lower() or "key feature" in label.lower():
            continue
        normalized = normalize_text(text)
        if len(normalized) < 24:
            continue
        duplicates.setdefault(normalized, []).append(label)
    repeated: list[str] = []
    for labels in duplicates.values():
        if len(labels) > 1:
            repeated.extend(labels[:2])
    return repeated


def _has_usage_context(draft_payload: AplusDraftPayload) -> bool:
    searchable_copy = " ".join(text for _, text in _collect_copy(draft_payload))
    normalized = normalize_text(searchable_copy)
    return any(term in normalized for term in _USAGE_TERMS)


def _has_benefit_driven_copy(draft_payload: AplusDraftPayload) -> bool:
    normalized_entries = [normalize_text(text) for _, text in _collect_copy(draft_payload)]
    hit_count = sum(
        1
        for entry in normalized_entries
        if any(term in entry for term in _BENEFIT_TERMS)
    )
    return hit_count >= 3


def _has_technical_detail(draft_payload: AplusDraftPayload) -> bool:
    normalized_entries = [normalize_text(text) for _, text in _collect_copy(draft_payload)]
    return any(any(term in entry for term in _TECHNICAL_TERMS) for entry in normalized_entries)


def _answers_customer_questions(draft_payload: AplusDraftPayload) -> bool:
    normalized_entries = [normalize_text(text) for _, text in _collect_copy(draft_payload)]
    return any(any(term in entry for term in _QUESTION_TERMS) for entry in normalized_entries)


def _has_differentiation_signals(draft_payload: AplusDraftPayload) -> bool:
    normalized_entries = [
        normalize_text(text)
        for label, text in _collect_copy(draft_payload)
        if "image brief" not in label.lower()
    ]
    hit_count = sum(
        1 for entry in normalized_entries if any(term in entry for term in _DIFFERENTIATION_TERMS)
    )
    return hit_count >= 2


def _comparison_is_meaningful(module: object) -> bool:
    normalized_body = normalize_text(getattr(module, "body", ""))
    bullets = getattr(module, "bullets", [])
    normalized_bullets = [normalize_text(bullet) for bullet in bullets]
    if "generic" not in normalized_body and "generisch" not in normalized_body:
        return False
    concrete_rows = sum(
        1
        for bullet in normalized_bullets
        if any(token in bullet for token in ("vs", "instead", "statt", "more", "weniger", "präzise"))
    )
    return concrete_rows >= 1 or len(normalized_bullets) >= 3


def _score_images(
    draft_payload: AplusDraftPayload,
    *,
    add_issue,
) -> int | None:
    image_modules = [
        module
        for module in draft_payload.modules
        if module.image_mode != "none"
        or module.generated_image_url
        or module.uploaded_image_url
        or module.selected_asset_id
    ]
    if not image_modules:
        return None

    penalty = 0
    for index, module in enumerate(image_modules, start=1):
        text = normalize_text(" ".join(filter(None, [module.image_prompt, module.image_brief, module.overlay_text])))
        if not text:
            penalty += 22
            add_issue(
                severity="warning",
                section=f"Module {index} image",
                title="Add image direction",
                message="This module uses imagery but the creative direction is too thin to keep the output product-focused.",
            )
            continue

        if any(term in text for term in _IMAGE_GENERIC_TERMS):
            penalty += 18
            add_issue(
                severity="warning",
                section=f"Module {index} image",
                title="Improve image specificity",
                message="Use product-in-context guidance, close-up detail, or a more realistic usage scene instead of a generic visual prompt.",
            )

        if not any(term in text for term in _USAGE_TERMS + _TECHNICAL_TERMS):
            penalty += 12
            add_issue(
                severity="warning",
                section=f"Module {index} image",
                title="Align image with the selling point",
                message="Tie the image direction to product details, usage context, or a specific shopper benefit.",
            )

    return _bounded_score(100 - penalty)


def _is_heading_weak(value: str) -> bool:
    words = [word for word in value.split(" ") if word]
    if len(words) < 2 or len(words) > 12:
        return True
    return any(phrase in value for phrase in _GENERIC_PHRASES)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9äöüß# ]+", " ", value.lower())).strip()


def _bounded_score(value: int) -> int:
    return max(0, min(100, value))
