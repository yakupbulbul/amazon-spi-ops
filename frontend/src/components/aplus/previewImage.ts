import type { AplusAsset, AplusModulePayload } from "../../lib/api";

export function resolveModulePreviewImageUrl(
  module: AplusModulePayload | undefined,
  assets: AplusAsset[],
): string | null {
  if (!module) {
    return null;
  }
  if (module.image_mode === "uploaded" && module.uploaded_image_url) {
    return module.uploaded_image_url;
  }
  if (module.image_mode === "generated" && module.generated_image_url) {
    return module.generated_image_url;
  }
  if (module.selected_asset_id) {
    return assets.find((asset) => asset.id === module.selected_asset_id)?.public_url ?? null;
  }
  return null;
}
