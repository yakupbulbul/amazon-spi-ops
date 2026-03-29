import type { AplusAsset, AplusModulePayload } from "../../lib/api";

export function moduleIsRealPublishSupported(
  moduleType: AplusModulePayload["module_type"],
): boolean {
  return moduleType === "hero" || moduleType === "feature" || moduleType === "faq";
}

export function moduleSupportsPublishImage(moduleType: AplusModulePayload["module_type"]): boolean {
  return moduleType === "hero" || moduleType === "feature";
}

export function moduleSupportsPublishOverlay(moduleType: AplusModulePayload["module_type"]): boolean {
  return moduleSupportsPublishImage(moduleType);
}

export function moduleHasUnsupportedPublishImageConfig(module: AplusModulePayload): boolean {
  return (
    !moduleSupportsPublishImage(module.module_type) &&
    (module.image_mode !== "none" || Boolean(module.overlay_text))
  );
}

export function moduleIsEditorialOnly(
  moduleType: AplusModulePayload["module_type"],
): boolean {
  return !moduleIsRealPublishSupported(moduleType);
}

export function resolveModulePublishableImageUrl(
  module: AplusModulePayload | undefined,
  assets: AplusAsset[],
): string | null {
  if (!module || !moduleSupportsPublishImage(module.module_type) || module.image_mode === "none") {
    return null;
  }
  if (module.image_mode === "uploaded" && module.uploaded_image_url) {
    return module.uploaded_image_url;
  }
  if (module.image_mode === "generated" && module.generated_image_url) {
    return module.generated_image_url;
  }
  if (module.image_mode === "existing_asset" && module.selected_asset_id) {
    return assets.find((asset) => asset.id === module.selected_asset_id)?.public_url ?? null;
  }
  return null;
}
