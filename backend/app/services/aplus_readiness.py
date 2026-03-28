from __future__ import annotations

import re
from typing import Literal

from app.schemas.aplus import AplusDraftPayload, AplusReadinessIssue, AplusReadinessReport

_BLOCKING_PHRASES: tuple[tuple[str, str], ...] = (
    ("best", "Avoid unverifiable superlatives such as 'best'."),
    ("ultimate", "Avoid unverifiable superlatives such as 'ultimate'."),
    ("perfect", "Avoid absolute claims such as 'perfect'."),
    ("#1", "Avoid ranking claims such as '#1' unless they are explicitly supported."),
    ("state-of-the-art", "Avoid unsupported superiority claims such as 'state-of-the-art'."),
    ("revolutionary", "Avoid unsupported breakthrough claims such as 'revolutionary'."),
    ("beste", "Avoid unverifiable superlatives such as 'beste'."),
    ("perfekt", "Avoid absolute claims such as 'perfekt'."),
    ("ultimative", "Avoid unverifiable superlatives such as 'ultimative'."),
    ("revolutionär", "Avoid unsupported superiority claims such as 'revolutionär'."),
)

_VAGUE_PHRASES: tuple[tuple[str, str], ...] = (
    ("high quality", "Replace vague quality claims with a concrete shopper benefit or proof point."),
    ("premium quality", "Replace vague quality claims with a concrete shopper benefit or proof point."),
    ("quality materials", "Call out the material benefit instead of using generic quality language."),
    ("premium materials", "Call out the material benefit instead of using generic quality language."),
    ("high-grade", "Explain why the build choice matters instead of saying 'high-grade'."),
    ("hochwertig", "Replace 'hochwertig' with a concrete benefit or verification point."),
    ("hohe qualität", "Replace vague quality claims with a concrete shopper benefit or proof point."),
    ("premium qualität", "Replace vague quality claims with a concrete shopper benefit or proof point."),
)


def build_aplus_readiness_report(
    *,
    draft_payload: AplusDraftPayload,
    checked_payload: Literal["draft", "validated"],
) -> AplusReadinessReport:
    blocking_errors: list[AplusReadinessIssue] = []
    warnings: list[AplusReadinessIssue] = []
    missing_sections: list[str] = []

    def add_issue(
        *,
        level: Literal["error", "warning"],
        code: str,
        message: str,
        field_label: str | None = None,
    ) -> None:
        issue = AplusReadinessIssue(
            level=level,
            code=code,
            message=message,
            field_label=field_label,
        )
        if level == "error":
            blocking_errors.append(issue)
        else:
            warnings.append(issue)

    text_rules = [
        ("Headline", draft_payload.headline, 60, 85),
        ("Subheadline", draft_payload.subheadline, 120, 160),
        ("Brand story", draft_payload.brand_story, 420, 620),
    ]
    text_rules.extend(
        (f"Key feature {index}", feature, 90, 130)
        for index, feature in enumerate(draft_payload.key_features, start=1)
    )
    text_rules.extend(
        (f"Compliance note {index}", note, 130, 200)
        for index, note in enumerate(draft_payload.compliance_notes, start=1)
    )
    for index, module in enumerate(draft_payload.modules, start=1):
        text_rules.extend(
            (
                (f"Module {index} headline", module.headline, 55, 85),
                (f"Module {index} body", module.body, 280, 420),
                (f"Module {index} image brief", module.image_brief, 150, 220),
            )
        )
        text_rules.extend(
            (f"Module {index} bullet {bullet_index}", bullet, 90, 130)
            for bullet_index, bullet in enumerate(module.bullets, start=1)
        )

    for field_label, text, warning_limit, error_limit in text_rules:
        text_length = len(text.strip())
        if text_length > error_limit:
            add_issue(
                level="error",
                code="too_long",
                field_label=field_label,
                message=f"{field_label} is too long for concise module-based A+ rendering.",
            )
        elif text_length > warning_limit:
            add_issue(
                level="warning",
                code="verbose",
                field_label=field_label,
                message=f"{field_label} is getting long and may feel dense in Amazon modules.",
            )

    module_types = [module.module_type for module in draft_payload.modules]
    if "hero" not in module_types:
        missing_sections.append("Hero section")
        add_issue(
            level="error",
            code="missing_hero",
            message="Add a hero module so the value proposition is immediately clear.",
            field_label="Modules",
        )
    if "comparison" not in module_types:
        missing_sections.append("Comparison section")
        add_issue(
            level="error",
            code="missing_comparison",
            message="Add a comparison module that frames the product against generic alternatives.",
            field_label="Modules",
        )
    if module_types.count("feature") < 2:
        missing_sections.append("Second benefit module")
        add_issue(
            level="warning",
            code="missing_benefit_depth",
            message="Consider adding a second feature module to cover more shopper benefits or usage context.",
            field_label="Modules",
        )
    if "faq" not in module_types:
        missing_sections.append("Trust or reassurance section")
        add_issue(
            level="warning",
            code="missing_reassurance",
            message="A reassurance or trust section helps reduce shopper hesitation before publish.",
            field_label="Modules",
        )

    all_text_entries = collect_text_entries(draft_payload)
    for field_label, text in all_text_entries:
        normalized = normalize_text(text)
        if not normalized:
            add_issue(
                level="error",
                code="empty_section",
                field_label=field_label,
                message=f"{field_label} is empty and must be completed before publish.",
            )
            continue

        for phrase, message in _BLOCKING_PHRASES:
            if phrase in normalized:
                add_issue(
                    level="error",
                    code="unsupported_claim",
                    field_label=field_label,
                    message=message,
                )

        for phrase, message in _VAGUE_PHRASES:
            if phrase in normalized:
                add_issue(
                    level="warning",
                    code="vague_claim",
                    field_label=field_label,
                    message=message,
                )

        if field_label.startswith("Module") and is_weak_section(normalized):
            add_issue(
                level="warning",
                code="weak_copy",
                field_label=field_label,
                message=f"{field_label} reads generic. Make the benefit or shopper outcome more specific.",
            )

    duplicate_map: dict[str, list[str]] = {}
    for field_label, text in all_text_entries:
        normalized = normalize_text(text)
        if len(normalized) < 16:
            continue
        duplicate_map.setdefault(normalized, []).append(field_label)

    for labels in duplicate_map.values():
        if len(labels) > 1:
            add_issue(
                level="warning",
                code="repeated_copy",
                field_label=" / ".join(labels[:2]),
                message=f"Repeated copy detected across {', '.join(labels[:3])}. Vary each section more clearly.",
            )

    return AplusReadinessReport(
        checked_payload=checked_payload,
        is_publish_ready=not blocking_errors,
        blocking_errors=blocking_errors,
        warnings=warnings,
        missing_sections=missing_sections,
    )


def collect_text_entries(draft_payload: AplusDraftPayload) -> list[tuple[str, str]]:
    entries = [
        ("Headline", draft_payload.headline),
        ("Subheadline", draft_payload.subheadline),
        ("Brand story", draft_payload.brand_story),
    ]
    entries.extend(
        (f"Key feature {index}", feature)
        for index, feature in enumerate(draft_payload.key_features, start=1)
    )
    entries.extend(
        (f"Compliance note {index}", note)
        for index, note in enumerate(draft_payload.compliance_notes, start=1)
    )
    for index, module in enumerate(draft_payload.modules, start=1):
        entries.extend(
            (
                (f"Module {index} headline", module.headline),
                (f"Module {index} body", module.body),
                (f"Module {index} image brief", module.image_brief),
            )
        )
        entries.extend(
            (f"Module {index} bullet {bullet_index}", bullet)
            for bullet_index, bullet in enumerate(module.bullets, start=1)
        )
    return entries


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9äöüß# ]+", " ", value.lower())).strip()


def is_weak_section(value: str) -> bool:
    weak_patterns = (
        "great for everyday use",
        "ideal for everyday use",
        "designed for everyday use",
        "good for daily use",
        "für den alltag",
        "ideal für den alltag",
        "hoher komfort",
        "premium design",
    )
    return any(pattern in value for pattern in weak_patterns)
