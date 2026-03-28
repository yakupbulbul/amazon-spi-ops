import {
  ImageOff,
  Images,
  LoaderCircle,
  Sparkles,
  Upload,
} from "lucide-react";
import { useRef } from "react";

import type { AplusAsset, AplusModulePayload } from "../../lib/api";

type AplusModuleImageSectionProps = {
  module: AplusModulePayload;
  assets: AplusAsset[];
  isLoadingAssets: boolean;
  isUploading: boolean;
  uploadError: string | null;
  onUpdate: (patch: Partial<AplusModulePayload>) => void;
  onUpload: (file: File) => void;
  onSelectAsset: (asset: AplusAsset) => void;
  onClearImage: () => void;
};

const imageModes: Array<{
  value: AplusModulePayload["image_mode"];
  label: string;
  description: string;
  icon: typeof ImageOff;
}> = [
  {
    value: "none",
    label: "No image",
    description: "Keep this module text-only.",
    icon: ImageOff,
  },
  {
    value: "uploaded",
    label: "Upload image",
    description: "Add your own module image.",
    icon: Upload,
  },
  {
    value: "existing_asset",
    label: "Existing asset",
    description: "Reuse product or brand assets.",
    icon: Images,
  },
  {
    value: "generated",
    label: "Generate with AI",
    description: "Prepare prompt and references for generation.",
    icon: Sparkles,
  },
];

export function AplusModuleImageSection({
  module,
  assets,
  isLoadingAssets,
  isUploading,
  uploadError,
  onUpdate,
  onUpload,
  onSelectAsset,
  onClearImage,
}: AplusModuleImageSectionProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const activeImageUrl = getActiveImageUrl(module, assets);

  return (
    <section className="space-y-4 rounded-[1.25rem] border border-white/10 bg-white/[0.03] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-white">Module image</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Images remain optional. Choose one source per module or keep the block text-only.
          </p>
        </div>
        {activeImageUrl ? (
          <button
            type="button"
            onClick={onClearImage}
            className="rounded-full border border-rose-300/20 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-100 transition hover:bg-rose-500/20"
          >
            Remove image
          </button>
        ) : null}
      </div>

      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        {imageModes.map((mode) => {
          const Icon = mode.icon;
          const isActive = module.image_mode === mode.value;
          return (
            <button
              key={mode.value}
              type="button"
              onClick={() => onUpdate({ image_mode: mode.value, image_error_message: null })}
              className={[
                "rounded-[1rem] border px-3 py-3 text-left transition",
                isActive
                  ? "border-amber-300/20 bg-amber-300/10"
                  : "border-white/10 bg-slate-950/60 hover:bg-white/[0.05]",
              ].join(" ")}
            >
              <div className="flex items-center gap-2">
                <Icon className={["h-4 w-4", isActive ? "text-amber-200" : "text-slate-400"].join(" ")} />
                <p className="text-sm font-medium text-white">{mode.label}</p>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">{mode.description}</p>
            </button>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(220px,0.9fr)]">
        <div className="space-y-4">
          {module.image_mode === "uploaded" ? (
            <div className="space-y-4">
              <div className="rounded-[1rem] border border-dashed border-white/10 bg-slate-950/60 p-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  onChange={(event) => {
                    const nextFile = event.target.files?.[0];
                    if (nextFile) {
                      onUpload(nextFile);
                    }
                    event.currentTarget.value = "";
                  }}
                />
                <p className="text-sm text-white">Upload module image</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  JPG, PNG, or WEBP. Uploaded assets are added to the reusable asset library.
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-xs font-medium text-slate-100 transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {isUploading ? (
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    {activeImageUrl ? "Replace uploaded image" : "Upload image"}
                  </button>
                </div>
              </div>
            </div>
          ) : null}

          {module.image_mode === "existing_asset" ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm text-white">Asset library</p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    Select from product, brand, logo, or previously generated assets.
                  </p>
                </div>
                {isLoadingAssets ? (
                  <span className="inline-flex items-center gap-2 text-xs text-slate-400">
                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                    Loading assets
                  </span>
                ) : null}
              </div>

              {assets.length === 0 ? (
                <div className="rounded-[1rem] border border-dashed border-white/10 bg-slate-950/60 px-4 py-4 text-sm leading-6 text-slate-400">
                  No reusable assets yet. Upload an image first or generate one later.
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {assets.map((asset) => {
                    const isSelected = module.selected_asset_id === asset.id;
                    return (
                      <button
                        key={asset.id}
                        type="button"
                        onClick={() => onSelectAsset(asset)}
                        className={[
                          "overflow-hidden rounded-[1rem] border text-left transition",
                          isSelected
                            ? "border-amber-300/20 bg-amber-300/10"
                            : "border-white/10 bg-slate-950/60 hover:bg-white/[0.05]",
                        ].join(" ")}
                      >
                        <div className="aspect-[4/3] overflow-hidden bg-slate-900">
                          <img
                            src={asset.public_url}
                            alt={asset.label ?? asset.file_name}
                            className="h-full w-full object-cover"
                          />
                        </div>
                        <div className="px-3 py-3">
                          <p className="truncate text-sm font-medium text-white">
                            {asset.label ?? asset.file_name}
                          </p>
                          <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                            {asset.asset_scope.replace("_", " ")}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ) : null}

          {module.image_mode === "generated" ? (
            <div className="space-y-4">
              <div className="rounded-[1rem] border border-sky-300/15 bg-sky-500/10 px-4 py-3 text-sm leading-6 text-sky-100">
                AI generation will use these prompt fields and optional reference assets in the next step.
              </div>
              <label className="block space-y-2">
                <span className="text-sm text-slate-300">Image prompt</span>
                <textarea
                  value={module.image_prompt ?? ""}
                  onChange={(event) => onUpdate({ image_prompt: event.target.value })}
                  rows={4}
                  className="w-full rounded-[1rem] border border-white/10 bg-slate-950/60 px-4 py-3 text-sm leading-6 text-white outline-none"
                  placeholder="Describe the composition, product angle, environment, and shopper context."
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-slate-300">Overlay text</span>
                <input
                  type="text"
                  value={module.overlay_text ?? ""}
                  onChange={(event) => onUpdate({ overlay_text: event.target.value })}
                  className="w-full rounded-[1rem] border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-white outline-none"
                  placeholder="Short shopper-facing overlay copy"
                />
              </label>

              <div className="space-y-2">
                <p className="text-sm text-slate-300">Reference assets</p>
                <p className="text-xs leading-5 text-slate-500">
                  Select reusable assets that should guide AI generation toward the real product and brand.
                </p>
                {assets.length === 0 ? (
                  <div className="rounded-[1rem] border border-dashed border-white/10 bg-slate-950/60 px-4 py-4 text-sm leading-6 text-slate-400">
                    Upload or reuse assets first to enable reference-based generation.
                  </div>
                ) : (
                  <div className="grid gap-2 sm:grid-cols-2">
                    {assets.map((asset) => {
                      const isSelected = module.reference_asset_ids.includes(asset.id);
                      return (
                        <button
                          key={asset.id}
                          type="button"
                          onClick={() =>
                            onUpdate({
                              reference_asset_ids: isSelected
                                ? module.reference_asset_ids.filter((assetId) => assetId !== asset.id)
                                : [...module.reference_asset_ids, asset.id],
                            })
                          }
                          className={[
                            "flex items-center gap-3 rounded-[1rem] border px-3 py-3 text-left transition",
                            isSelected
                              ? "border-amber-300/20 bg-amber-300/10"
                              : "border-white/10 bg-slate-950/60 hover:bg-white/[0.05]",
                          ].join(" ")}
                        >
                          <img
                            src={asset.public_url}
                            alt={asset.label ?? asset.file_name}
                            className="h-12 w-12 rounded-lg object-cover"
                          />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-white">
                              {asset.label ?? asset.file_name}
                            </p>
                            <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                              {asset.asset_scope}
                            </p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {module.image_mode === "none" ? (
            <div className="rounded-[1rem] border border-dashed border-white/10 bg-slate-950/60 px-4 py-4 text-sm leading-6 text-slate-400">
              This module will stay text-only until you choose an image source.
            </div>
          ) : null}

          {uploadError || module.image_error_message ? (
            <div className="rounded-[1rem] border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {uploadError ?? module.image_error_message}
            </div>
          ) : null}
        </div>

        <div className="rounded-[1rem] border border-white/10 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Active image source</p>
          <p className="mt-2 text-sm font-medium text-white">{imageModeLabel(module.image_mode)}</p>
          <div className="mt-4 overflow-hidden rounded-[1rem] border border-white/10 bg-slate-900">
            {activeImageUrl ? (
              <img
                src={activeImageUrl}
                alt={module.headline}
                className="aspect-[4/3] h-full w-full object-cover"
              />
            ) : (
              <div className="flex aspect-[4/3] items-center justify-center px-4 text-center text-sm leading-6 text-slate-500">
                No image selected for this module yet.
              </div>
            )}
          </div>
          {module.overlay_text ? (
            <div className="mt-4 rounded-full bg-white/[0.06] px-3 py-2 text-xs text-slate-200">
              Overlay: {module.overlay_text}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function getActiveImageUrl(module: AplusModulePayload, assets: AplusAsset[]): string | null {
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

function imageModeLabel(mode: AplusModulePayload["image_mode"]): string {
  const mapping: Record<AplusModulePayload["image_mode"], string> = {
    none: "No image",
    uploaded: "Uploaded image",
    existing_asset: "Existing asset",
    generated: "AI-generated image",
  };
  return mapping[mode];
}
