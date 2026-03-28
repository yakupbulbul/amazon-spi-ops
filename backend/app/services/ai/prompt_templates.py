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
    - Make the copy benefit-driven, not feature-dumped. Explain why each feature matters to the shopper.
    - Keep headings short, punchy, and scannable.
    - Ensure each section contributes distinct value and avoid repeating the same claim in multiple fields.
    - Prefer practical differentiation over vague quality language.
    - Compliance notes must call out limitations, assumptions, or details a human editor should verify before publishing.
    """
).strip()


def get_language_market_guidance(language: str) -> str:
    mapping = {
        "de-DE": "Use a precise, trust-driven, technically grounded tone with strong clarity and restrained hype.",
        "en-GB": "Use a benefit-led, polished tone with lifestyle context and concise emotional framing.",
        "en-US": "Use energetic, conversion-focused language with clear shopper benefits and easy scanning.",
        "fr-FR": "Use elegant, informative copy with balanced persuasion and refined phrasing.",
        "it-IT": "Use warm, design-aware, benefit-led copy with practical lifestyle context.",
        "es-ES": "Use approachable, persuasive copy with clear everyday-use benefits and strong readability.",
    }
    return mapping.get(
        language,
        "Use concise, benefit-led marketplace copy that feels natural for the target locale.",
    )


def build_aplus_user_prompt(
    *,
    product_summary: str,
    brand_tone: str | None,
    positioning: str | None,
    language: str,
) -> str:
    tone_block = brand_tone or "Use a balanced, modern marketplace tone."
    positioning_block = positioning or "No extra positioning guidance was provided."
    market_guidance = get_language_market_guidance(language)
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

        Language and market guidance:
        {market_guidance}

        Build:
        - one headline
        - one subheadline
        - one brand story paragraph
        - 3 to 5 modules
        - 3 to 6 key features
        - 2 to 6 compliance notes

        Strategic intent:
        - Infer the target customer segment and usage scenario from the product data and positioning guidance when they are not explicit.
        - Lead with a clear value proposition in the hero section.
        - Use feature modules to explain specific shopper benefits, not generic product facts.
        - Include at least one module that covers usage scenarios or lifestyle context.
        - Include a comparison-oriented module that contrasts the product with generic alternatives rather than named competitors.
        - Include a trust, craftsmanship, or quality-reassurance section where appropriate.
        - Make image_brief useful for creatives by including the visual direction and a short overlay-style text suggestion.

        Ensure each module includes:
        - module_type
        - headline
        - body
        - up to 4 bullets
        - image_brief

        Preferred module roles:
        - hero: main value proposition
        - feature: shopper benefits, use cases, differentiation, or quality/trust proof
        - comparison: comparison against generic alternatives or buying considerations
        - faq: reassuring clarification or confidence-building shopper guidance when useful
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
        - Translate headings, body copy, captions, and short overlay-style text when present in image briefs.
        - Keep the copy marketplace-safe and natural for the target locale.
        - Preserve differentiation and shopper intent rather than translating word-for-word.

        JSON draft:
        {draft_payload}
        """
    ).strip()
