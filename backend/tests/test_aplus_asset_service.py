from __future__ import annotations

from app.services.aplus_asset_service import AplusAssetService

def test_detect_mime_type_rejects_spoofed_image_content() -> None:
    assert AplusAssetService._detect_mime_type(b"<html>not really an image</html>") is None


def test_detect_mime_type_accepts_png_signature() -> None:
    assert (
        AplusAssetService._detect_mime_type(b"\x89PNG\r\n\x1a\nrest-of-payload")
        == "image/png"
    )
