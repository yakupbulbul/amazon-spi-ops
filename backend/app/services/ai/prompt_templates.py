from __future__ import annotations

from textwrap import dedent


APLUS_SYSTEM_PROMPT = dedent(
    """
    You write Amazon A+ content drafts for seller operations teams.

    Requirements:
    - Return valid JSON matching the provided schema.
    - Keep claims grounded in the supplied product data.
    - Avoid medical, legal, environmental, or performance claims unless explicitly present in the product data.
    - Do not use superlatives such as "best", "ultimate", or unverifiable comparative claims.
    - Write concise ecommerce copy suitable for Amazon A+ modules.
    - Compliance notes must call out limitations, assumptions, or details a human editor should verify before publishing.
    """
).strip()


def build_aplus_user_prompt(
    *,
    product_summary: str,
    brand_tone: str | None,
    positioning: str | None,
    language: str,
) -> str:
    tone_block = brand_tone or "Use a balanced, modern marketplace tone."
    positioning_block = positioning or "No extra positioning guidance was provided."
    return dedent(
        f"""
        Create an Amazon A+ content draft for the following product.

        Product summary:
        {product_summary}

        Brand tone guidance:
        {tone_block}

        Positioning guidance:
        {positioning_block}

        Write the full draft in:
        {language}

        Build:
        - one headline
        - one subheadline
        - one brand story paragraph
        - 3 to 5 modules
        - 3 to 6 key features
        - 2 to 6 compliance notes

        Ensure each module includes:
        - module_type
        - headline
        - body
        - up to 4 bullets
        - image_brief
        """
    ).strip()


def build_aplus_translation_prompt(
    *,
    source_language: str,
    target_language: str,
    draft_payload: str,
) -> str:
    return dedent(
        f"""
        Translate the following Amazon A+ draft content from {source_language} to {target_language}.

        Rules:
        - Preserve the exact JSON schema and field names.
        - Do not translate enum values or schema keys.
        - Do not change module_type values.
        - Translate only shopper-facing text fields and list items.
        - Keep the copy marketplace-safe and natural for the target locale.

        JSON draft:
        {draft_payload}
        """
    ).strip()
