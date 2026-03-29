from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.aplus import AplusDraftPayload, AplusModulePayload

SUPPORTED_REAL_PUBLISH_MODULE_TYPES = frozenset({"hero", "feature", "faq"})
EDITORIAL_ONLY_MODULE_TYPES = frozenset({"comparison"})

_HIGHLIGHTS_LABELS: dict[str, str] = {
    "de-DE": "Highlights",
    "en-GB": "Highlights",
    "en-US": "Highlights",
    "fr-FR": "Points forts",
    "it-IT": "Punti chiave",
    "es-ES": "Puntos clave",
}


@dataclass(frozen=True)
class PreparedAmazonImageAsset:
    upload_destination_id: str
    alt_text: str
    width_pixels: int
    height_pixels: int
    crop_width_pixels: int
    crop_height_pixels: int
    crop_offset_x_pixels: int = 0
    crop_offset_y_pixels: int = 0
    asset_id: str | None = None


class AmazonTextComponent(BaseModel):
    value: str


class AmazonParagraphComponent(BaseModel):
    textList: list[AmazonTextComponent] = Field(min_length=1)


class AmazonTextItem(BaseModel):
    position: int
    text: AmazonTextComponent


class AmazonIntegerWithUnits(BaseModel):
    value: int
    units: Literal["pixels"] = "pixels"


class AmazonImageDimensions(BaseModel):
    width: AmazonIntegerWithUnits
    height: AmazonIntegerWithUnits


class AmazonImageOffsetSpecification(BaseModel):
    x: AmazonIntegerWithUnits
    y: AmazonIntegerWithUnits


class AmazonImageCropSpecification(BaseModel):
    size: AmazonImageDimensions
    offset: AmazonImageOffsetSpecification | None = None


class AmazonImageComponent(BaseModel):
    uploadDestinationId: str
    imageCropSpecification: AmazonImageCropSpecification
    altText: str


class AmazonStandardTextBlock(BaseModel):
    headline: AmazonTextComponent | None = None
    body: AmazonParagraphComponent | None = None


class AmazonStandardTextListBlock(BaseModel):
    textList: list[AmazonTextItem] = Field(default_factory=list, max_length=8)


class AmazonStandardHeaderTextListBlock(BaseModel):
    headline: AmazonTextComponent | None = None
    block: AmazonStandardTextListBlock


class AmazonStandardImageTextBlock(BaseModel):
    image: AmazonImageComponent
    headline: AmazonTextComponent | None = None
    body: AmazonParagraphComponent | None = None


class AmazonStandardHeaderImageTextModule(BaseModel):
    headline: AmazonTextComponent | None = None
    block: AmazonStandardImageTextBlock


class AmazonStandardSingleImageHighlightsModule(BaseModel):
    image: AmazonImageComponent
    headline: AmazonTextComponent | None = None
    textBlock1: AmazonStandardTextBlock | None = None
    textBlock2: AmazonStandardTextBlock | None = None
    textBlock3: AmazonStandardTextBlock | None = None
    bulletedListBlock: AmazonStandardHeaderTextListBlock | None = None


class AmazonStandardTextModule(BaseModel):
    headline: AmazonTextComponent | None = None
    body: AmazonParagraphComponent


class AmazonContentModule(BaseModel):
    contentModuleType: Literal[
        "STANDARD_HEADER_IMAGE_TEXT",
        "STANDARD_SINGLE_IMAGE_HIGHLIGHTS",
        "STANDARD_TEXT",
    ]
    standardHeaderImageText: AmazonStandardHeaderImageTextModule | None = None
    standardSingleImageHighlights: AmazonStandardSingleImageHighlightsModule | None = None
    standardText: AmazonStandardTextModule | None = None


class AmazonContentDocument(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    contentType: Literal["EBC"] = "EBC"
    locale: str
    contentModuleList: list[AmazonContentModule] = Field(min_length=1, max_length=7)


class AmazonPostContentDocumentRequest(BaseModel):
    contentDocument: AmazonContentDocument


class AmazonPostContentDocumentAsinRelationsRequest(BaseModel):
    asinSet: list[str] = Field(min_length=1)


class AmazonContractMapper:
    def map_content_document(
        self,
        *,
        product_title: str,
        locale: str,
        draft_payload: AplusDraftPayload,
        prepared_assets_by_module_id: dict[str, PreparedAmazonImageAsset],
    ) -> AmazonPostContentDocumentRequest:
        hero_module = next((module for module in draft_payload.modules if module.module_type == "hero"), None)
        if hero_module is None:
            raise ValueError("Real Amazon publish requires a hero module.")

        unsupported_modules = [
            module.module_type
            for module in draft_payload.modules
            if module.module_type not in SUPPORTED_REAL_PUBLISH_MODULE_TYPES
        ]
        if unsupported_modules:
            unsupported = ", ".join(sorted(set(unsupported_modules)))
            raise ValueError(
                "Real Amazon publish currently supports only hero, feature, and faq modules. "
                f"Unsupported modules present: {unsupported}."
            )

        content_modules: list[AmazonContentModule] = [
            self._map_hero_module(
                draft_payload=draft_payload,
                module=hero_module,
                prepared_asset=self._required_image_asset(
                    prepared_assets_by_module_id=prepared_assets_by_module_id,
                    module=hero_module,
                ),
            )
        ]

        feature_modules = [
            module for module in draft_payload.modules if module.module_type == "feature"
        ]
        for module in feature_modules:
            content_modules.append(
                self._map_feature_module(
                    module=module,
                    locale=locale,
                    key_feature_pool=draft_payload.key_features,
                    prepared_asset=self._required_image_asset(
                        prepared_assets_by_module_id=prepared_assets_by_module_id,
                        module=module,
                    ),
                )
            )

        faq_modules = [module for module in draft_payload.modules if module.module_type == "faq"]
        for module in faq_modules:
            content_modules.append(self._map_text_module(module=module))

        if len(content_modules) > 7:
            raise ValueError(
                "Amazon seller A+ content supports a maximum of 7 modules in the current flow."
            )

        document_name = f"{product_title[:72]} A+ Content".strip()
        return AmazonPostContentDocumentRequest(
            contentDocument=AmazonContentDocument(
                name=document_name[:100] or "A+ Content",
                locale=locale,
                contentModuleList=content_modules,
            )
        )

    def build_asin_relations(self, *, asin: str) -> AmazonPostContentDocumentAsinRelationsRequest:
        return AmazonPostContentDocumentAsinRelationsRequest(asinSet=[asin])

    def _map_hero_module(
        self,
        *,
        draft_payload: AplusDraftPayload,
        module: AplusModulePayload,
        prepared_asset: PreparedAmazonImageAsset,
    ) -> AmazonContentModule:
        self._validate_text_length("Draft headline", draft_payload.headline, 150)
        self._validate_text_length("Hero module headline", module.headline, 150)
        self._validate_text_length("Hero image alt text", prepared_asset.alt_text, 100)
        self._validate_image_size(
            label="Hero image",
            prepared_asset=prepared_asset,
            min_width=970,
            min_height=600,
        )

        hero_body_parts = [draft_payload.subheadline.strip(), module.body.strip(), draft_payload.brand_story.strip()]
        hero_body = [part for part in hero_body_parts if part]
        for index, paragraph in enumerate(hero_body, start=1):
            self._validate_text_length(f"Hero body paragraph {index}", paragraph, 6000)

        return AmazonContentModule(
            contentModuleType="STANDARD_HEADER_IMAGE_TEXT",
            standardHeaderImageText=AmazonStandardHeaderImageTextModule(
                headline=AmazonTextComponent(value=draft_payload.headline.strip()),
                block=AmazonStandardImageTextBlock(
                    image=self._build_image_component(prepared_asset=prepared_asset),
                    headline=AmazonTextComponent(value=module.headline.strip()),
                    body=AmazonParagraphComponent(
                        textList=[AmazonTextComponent(value=paragraph) for paragraph in hero_body]
                    ),
                ),
            ),
        )

    def _map_feature_module(
        self,
        *,
        module: AplusModulePayload,
        locale: str,
        key_feature_pool: list[str],
        prepared_asset: PreparedAmazonImageAsset,
    ) -> AmazonContentModule:
        self._validate_text_length("Feature headline", module.headline, 160)
        self._validate_text_length("Feature image alt text", prepared_asset.alt_text, 100)
        self._validate_image_size(
            label="Feature image",
            prepared_asset=prepared_asset,
            min_width=300,
            min_height=300,
        )

        supporting_points = self._feature_supporting_points(
            module=module,
            key_feature_pool=key_feature_pool,
        )
        if len(supporting_points) < 2:
            raise ValueError(
                f"Feature module '{module.headline}' needs at least two supporting shopper points for the real Amazon contract."
            )

        self._validate_text_length("Feature body", module.body, 1000)
        self._validate_text_length("Feature point 1", supporting_points[0], 400)
        self._validate_text_length("Feature point 2", supporting_points[1], 400)

        bullet_items = module.bullets[:8] or supporting_points[: min(len(supporting_points), 8)]
        for index, bullet in enumerate(bullet_items, start=1):
            self._validate_text_length(f"Feature bullet {index}", bullet, 100)

        highlights_label = _HIGHLIGHTS_LABELS.get(locale, "Highlights")
        self._validate_text_length("Feature highlights label", highlights_label, 160)

        return AmazonContentModule(
            contentModuleType="STANDARD_SINGLE_IMAGE_HIGHLIGHTS",
            standardSingleImageHighlights=AmazonStandardSingleImageHighlightsModule(
                image=self._build_image_component(prepared_asset=prepared_asset),
                headline=AmazonTextComponent(value=module.headline.strip()),
                textBlock1=AmazonStandardTextBlock(
                    headline=AmazonTextComponent(value=self._short_heading(module.headline, 200)),
                    body=AmazonParagraphComponent(
                        textList=[AmazonTextComponent(value=module.body.strip())]
                    ),
                ),
                textBlock2=AmazonStandardTextBlock(
                    headline=AmazonTextComponent(value=self._short_heading(supporting_points[0], 200)),
                    body=AmazonParagraphComponent(
                        textList=[AmazonTextComponent(value=supporting_points[0])]
                    ),
                ),
                textBlock3=AmazonStandardTextBlock(
                    headline=AmazonTextComponent(value=self._short_heading(supporting_points[1], 200)),
                    body=AmazonParagraphComponent(
                        textList=[AmazonTextComponent(value=supporting_points[1])]
                    ),
                ),
                bulletedListBlock=AmazonStandardHeaderTextListBlock(
                    headline=AmazonTextComponent(value=highlights_label),
                    block=AmazonStandardTextListBlock(
                        textList=[
                            AmazonTextItem(
                                position=index,
                                text=AmazonTextComponent(value=bullet.strip()),
                            )
                            for index, bullet in enumerate(bullet_items, start=1)
                        ]
                    ),
                ),
            ),
        )

    def _map_text_module(self, *, module: AplusModulePayload) -> AmazonContentModule:
        self._validate_text_length("Text module headline", module.headline, 160)
        self._validate_text_length("Text module body", module.body, 5000)
        return AmazonContentModule(
            contentModuleType="STANDARD_TEXT",
            standardText=AmazonStandardTextModule(
                headline=AmazonTextComponent(value=module.headline.strip()),
                body=AmazonParagraphComponent(
                    textList=[AmazonTextComponent(value=module.body.strip())]
                ),
            ),
        )

    def _required_image_asset(
        self,
        *,
        prepared_assets_by_module_id: dict[str, PreparedAmazonImageAsset],
        module: AplusModulePayload,
    ) -> PreparedAmazonImageAsset:
        prepared_asset = prepared_assets_by_module_id.get(module.module_id)
        if prepared_asset is None:
            raise ValueError(
                f"Module '{module.headline}' is missing an Amazon-prepared image asset."
            )
        return prepared_asset

    @staticmethod
    def _build_image_component(*, prepared_asset: PreparedAmazonImageAsset) -> AmazonImageComponent:
        return AmazonImageComponent(
            uploadDestinationId=prepared_asset.upload_destination_id,
            altText=prepared_asset.alt_text,
            imageCropSpecification=AmazonImageCropSpecification(
                size=AmazonImageDimensions(
                    width=AmazonIntegerWithUnits(value=prepared_asset.crop_width_pixels),
                    height=AmazonIntegerWithUnits(value=prepared_asset.crop_height_pixels),
                ),
                offset=AmazonImageOffsetSpecification(
                    x=AmazonIntegerWithUnits(value=prepared_asset.crop_offset_x_pixels),
                    y=AmazonIntegerWithUnits(value=prepared_asset.crop_offset_y_pixels),
                ),
            ),
        )

    @staticmethod
    def _feature_supporting_points(
        *,
        module: AplusModulePayload,
        key_feature_pool: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        ordered_points: list[str] = []
        for candidate in [*module.bullets, *key_feature_pool]:
            normalized = candidate.strip()
            if not normalized:
                continue
            lowered = normalized.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            ordered_points.append(normalized)
        return ordered_points

    @staticmethod
    def _short_heading(value: str, limit: int) -> str:
        cleaned = " ".join(value.strip().split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip() + "…"

    @staticmethod
    def _validate_text_length(label: str, value: str, max_length: int) -> None:
        if len(value.strip()) > max_length:
            raise ValueError(f"{label} exceeds Amazon's maximum length of {max_length} characters.")

    @staticmethod
    def _validate_image_size(
        *,
        label: str,
        prepared_asset: PreparedAmazonImageAsset,
        min_width: int,
        min_height: int,
    ) -> None:
        if prepared_asset.width_pixels < min_width or prepared_asset.height_pixels < min_height:
            raise ValueError(
                f"{label} must be at least {min_width} x {min_height} pixels for the supported Amazon module."
            )
        if prepared_asset.crop_width_pixels <= 0 or prepared_asset.crop_height_pixels <= 0:
            raise ValueError(f"{label} is missing a valid crop specification for Amazon publish.")
