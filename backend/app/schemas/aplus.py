from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AplusModulePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_type: Literal["hero", "feature", "comparison", "faq"]
    headline: str = Field(min_length=5, max_length=120)
    body: str = Field(min_length=20, max_length=600)
    bullets: list[str] = Field(min_length=0, max_length=4)
    image_brief: str = Field(min_length=10, max_length=240)


class AplusDraftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=8, max_length=140)
    subheadline: str = Field(min_length=12, max_length=180)
    brand_story: str = Field(min_length=40, max_length=900)
    key_features: list[str] = Field(min_length=3, max_length=6)
    modules: list[AplusModulePayload] = Field(min_length=3, max_length=5)
    compliance_notes: list[str] = Field(min_length=2, max_length=6)


SupportedAplusLanguage = Literal["de-DE", "en-US", "en-GB", "fr-FR", "it-IT", "es-ES"]


class AplusGenerateRequest(BaseModel):
    product_id: str
    brand_tone: str | None = Field(default=None, max_length=255)
    positioning: str | None = Field(default=None, max_length=512)
    source_language: SupportedAplusLanguage
    target_language: SupportedAplusLanguage | None = None
    auto_translate: bool = False

    @model_validator(mode="after")
    def validate_translation_combination(self) -> "AplusGenerateRequest":
        effective_target = self.target_language or self.source_language
        if self.auto_translate and effective_target == self.source_language:
            raise ValueError("Choose a different target language when auto-translate is enabled.")
        return self


class AplusValidateRequest(BaseModel):
    draft_id: str
    draft_payload: AplusDraftPayload


class AplusPublishRequest(BaseModel):
    draft_id: str


class AplusDraftResponse(BaseModel):
    id: str
    product_id: str
    product_sku: str
    product_asin: str
    product_title: str
    marketplace_id: str
    status: str
    brand_tone: str | None
    positioning: str | None
    source_language: SupportedAplusLanguage
    target_language: SupportedAplusLanguage
    auto_translate: bool
    draft_payload: AplusDraftPayload
    validated_payload: AplusDraftPayload | None
    created_at: datetime
    updated_at: datetime


class AplusDraftListResponse(BaseModel):
    items: list[AplusDraftResponse]


class AplusPublishResponse(BaseModel):
    draft: AplusDraftResponse
    publish_job_id: str
    status: str
    message: str
    prepared_payload: dict[str, object]
