from __future__ import annotations

from base64 import b64decode
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from app.core.config import Settings, settings


@dataclass(slots=True)
class GeneratedImageResult:
    content: bytes
    mime_type: str
    provider_name: str


class ImageProvider(Protocol):
    def generate_image(
        self,
        *,
        prompt: str,
        reference_image_paths: list[Path],
    ) -> GeneratedImageResult:
        ...


class OpenAiImageProvider:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def generate_image(
        self,
        *,
        prompt: str,
        reference_image_paths: list[Path],
    ) -> GeneratedImageResult:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured for image generation.")

        if reference_image_paths:
            return self._generate_with_references(prompt=prompt, reference_image_paths=reference_image_paths)
        return self._generate_without_references(prompt=prompt)

    def _generate_without_references(self, *, prompt: str) -> GeneratedImageResult:
        payload = {
            "model": self.settings.openai_image_model,
            "prompt": prompt,
            "size": "1536x1024",
            "quality": "medium",
            "output_format": "png",
        }

        with httpx.Client(timeout=180) as client:
            response = client.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()

        body = response.json()
        image_data = body["data"][0]["b64_json"]
        return GeneratedImageResult(
            content=b64decode(image_data),
            mime_type="image/png",
            provider_name="openai",
        )

    def _generate_with_references(
        self,
        *,
        prompt: str,
        reference_image_paths: list[Path],
    ) -> GeneratedImageResult:
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for image_path in reference_image_paths[:4]:
            mime_type = _guess_mime_type(image_path)
            files.append(
                (
                    "image[]",
                    (
                        image_path.name,
                        image_path.read_bytes(),
                        mime_type,
                    ),
                )
            )

        files.extend(
            [
                ("model", (None, self.settings.openai_image_model)),
                ("prompt", (None, prompt)),
                ("size", (None, "1536x1024")),
                ("quality", (None, "medium")),
                ("output_format", (None, "png")),
            ]
        )

        with httpx.Client(timeout=180) as client:
            response = client.post(
                "https://api.openai.com/v1/images/edits",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                },
                files=files,
            )
            response.raise_for_status()

        body = response.json()
        image_data = body["data"][0]["b64_json"]
        return GeneratedImageResult(
            content=b64decode(image_data),
            mime_type="image/png",
            provider_name="openai",
        )


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"
