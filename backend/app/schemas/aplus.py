from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AplusModulePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_id: str = Field(default_factory=lambda: uuid4().hex, min_length=8, max_length=64)
    module_type: Literal["hero", "feature", "comparison", "faq"]
    headline: str = Field(min_length=5, max_length=120)
    body: str = Field(min_length=20, max_length=600)
    bullets: list[str] = Field(min_length=0, max_length=4)
    image_brief: str = Field(min_length=10, max_length=240)
    image_mode: Literal["generated", "uploaded", "existing_asset", "none"] = "none"
    image_prompt: str | None = Field(default=None, max_length=600)
    generated_image_url: str | None = Field(default=None, max_length=1024)
    uploaded_image_url: str | None = Field(default=None, max_length=1024)
    selected_asset_id: str | None = Field(default=None, max_length=64)
    reference_asset_ids: list[str] = Field(default_factory=list, max_length=8)
    overlay_text: str | None = Field(default=None, max_length=160)
    image_status: Literal["idle", "queued", "generating", "completed", "failed"] = "idle"
    image_error_message: str | None = Field(default=None, max_length=1024)
    image_request_fingerprint: str | None = Field(default=None, min_length=8, max_length=64)


class AplusDraftPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=8, max_length=140)
    subheadline: str = Field(min_length=12, max_length=180)
    brand_story: str = Field(min_length=40, max_length=900)
    key_features: list[str] = Field(min_length=3, max_length=6)
    modules: list[AplusModulePayload] = Field(min_length=3, max_length=5)
    compliance_notes: list[str] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def ensure_module_ids(self) -> "AplusDraftPayload":
        seen_ids: set[str] = set()
        for module in self.modules:
            if not module.module_id or module.module_id in seen_ids:
                module.module_id = uuid4().hex
            seen_ids.add(module.module_id)
        return self


SupportedAplusLanguage = Literal["de-DE", "en-US", "en-GB", "fr-FR", "it-IT", "es-ES"]


class AplusReadinessIssue(BaseModel):
    level: Literal["error", "warning"]
    code: str
    message: str
    field_label: str | None = None


class AplusReadinessReport(BaseModel):
    checked_payload: Literal["draft", "validated"]
    is_publish_ready: bool
    blocking_errors: list[AplusReadinessIssue]
    warnings: list[AplusReadinessIssue]
    missing_sections: list[str]


class AplusOptimizationSuggestion(BaseModel):
    severity: Literal["critical", "warning"]
    section: str
    title: str
    message: str


class AplusOptimizationSectionInsight(BaseModel):
    section: str
    severity: Literal["critical", "warning"]
    summary: str


class AplusOptimizationReport(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    structure_score: int = Field(ge=0, le=100)
    clarity_score: int = Field(ge=0, le=100)
    differentiation_score: int = Field(ge=0, le=100)
    completeness_score: int = Field(ge=0, le=100)
    image_quality_score: int | None = Field(default=None, ge=0, le=100)
    missing_sections: list[str]
    critical_issues: list[AplusOptimizationSuggestion]
    warnings: list[AplusOptimizationSuggestion]
    section_insights: list[AplusOptimizationSectionInsight]


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


class AplusGenerateImageRequest(BaseModel):
    draft_id: str
    module_id: str = Field(min_length=8, max_length=64)
    image_prompt: str | None = Field(default=None, max_length=600)
    overlay_text: str | None = Field(default=None, max_length=160)
    reference_asset_ids: list[str] = Field(default_factory=list, max_length=8)


class AplusPublishRequest(BaseModel):
    draft_id: str


class AplusPublishJobResponse(BaseModel):
    id: str
    draft_id: str
    status: str
    content_reference_key: str | None
    error_message: str | None
    rejection_reasons: list[str]
    warnings: list[str]
    submitted_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AplusAssetResponse(BaseModel):
    id: str
    product_id: str | None
    asset_scope: Literal["product", "brand", "logo", "generated"]
    label: str | None
    file_name: str
    mime_type: str
    file_size_bytes: int
    public_url: str
    created_at: datetime


class AplusAssetListResponse(BaseModel):
    items: list[AplusAssetResponse]


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
    readiness_report: AplusReadinessReport
    optimization_report: AplusOptimizationReport
    created_at: datetime
    updated_at: datetime


class AplusDraftListResponse(BaseModel):
    items: list[AplusDraftResponse]


class AplusPublishResponse(BaseModel):
    draft: AplusDraftResponse
    publish_job_id: str
    status: str
    message: str
    publish_job: AplusPublishJobResponse
    prepared_payload: dict[str, object]
