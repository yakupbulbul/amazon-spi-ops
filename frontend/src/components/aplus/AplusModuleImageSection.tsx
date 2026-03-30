import {
  ImageOff,
  Images,
  Info,
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
  canGenerate: boolean;
  onGenerate: () => void;
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

type PublishImageRequirement = {
  minWidth: number;
  minHeight: number;
  aspectRatioLabel: string;
  autoPrepLabel: string;
};

function getPublishImageRequirement(
  moduleType: AplusModulePayload["module_type"],
): PublishImageRequirement | null {
  if (moduleType === "hero") {
    return {
      minWidth: 970,
      minHeight: 600,
      aspectRatioLabel: "97:60",
      autoPrepLabel: "Uploads are auto-prepared to 970 x 600 for publish.",
    };
  }

  if (moduleType === "feature") {
    return {
      minWidth: 300,
      minHeight: 300,
      aspectRatioLabel: "1:1",
      autoPrepLabel: "Uploads are auto-prepared to 300 x 300 for publish.",
    };
  }

  return null;
}

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
  canGenerate,
  onGenerate,
}: AplusModuleImageSectionProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const activeImageUrl = getActiveImageUrl(module, assets);
  const publishRequirement = getPublishImageRequirement(module.module_type);

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

      {publishRequirement ? (
        <div className="rounded-[1rem] border border-emerald-300/15 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
          <div className="flex items-start gap-3">
            <Info className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium text-white">Amazon publish image requirement</p>
              <p className="mt-1 leading-6 text-emerald-100/90">
                Minimum {publishRequirement.minWidth} x {publishRequirement.minHeight} px, target ratio {publishRequirement.aspectRatioLabel}.
              </p>
              <p className="mt-1 text-xs leading-5 text-emerald-100/80">
                {publishRequirement.autoPrepLabel}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-[1rem] border border-amber-300/15 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-amber-100">
          This module type is text-only in the current Amazon publish subset. If you add an image here,
          the readiness panel will ask you to remove it before publish.
        </div>
      )}

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
                  {publishRequirement ? ` ${publishRequirement.autoPrepLabel}` : ""}
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
                    {publishRequirement
                      ? ` Choose assets that already meet at least ${publishRequirement.minWidth} x ${publishRequirement.minHeight} px.`
                      : ""}
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
                {publishRequirement
                  ? ` Target at least ${publishRequirement.minWidth} x ${publishRequirement.minHeight} px.`
                  : ""}
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

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={onGenerate}
                  disabled={!canGenerate || module.image_status === "queued" || module.image_status === "generating"}
                  className="inline-flex items-center gap-2 rounded-full bg-amber-300 px-3 py-2 text-xs font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {module.image_status === "queued" || module.image_status === "generating" ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}
                  {module.image_status === "queued" || module.image_status === "generating"
                    ? "Generating image..."
                    : "Generate with OpenAI"}
                </button>
                {!canGenerate ? (
                  <span className="text-xs text-slate-500">
                    Save or validate the draft before running background image generation.
                  </span>
                ) : null}
              </div>

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
            <div className="rounded-[1rem] border border-dashed border-white/10 bg-slate-950/60 px-4 py-5 text-sm leading-6 text-slate-400">
              No image is attached to this module yet. You can keep it text-only or add one of the supported image sources.
            </div>
          ) : null}

          {uploadError ? (
            <div className="rounded-[1rem] border border-rose-300/20 bg-rose-500/10 px-4 py-3 text-sm leading-6 text-rose-100">
              {uploadError}
            </div>
          ) : null}

          {module.image_error_message ? (
            <div className="rounded-[1rem] border border-rose-300/20 bg-rose-500/10 px-4 py-3 text-sm leading-6 text-rose-100">
              {module.image_error_message}
            </div>
          ) : null}
        </div>

        <div className="space-y-3">
          <div className="overflow-hidden rounded-[1rem] border border-white/10 bg-slate-950/70">
            {activeImageUrl ? (
              <img
                src={activeImageUrl}
                alt={module.headline || "Module image preview"}
                className="aspect-[4/3] w-full object-cover"
              />
            ) : (
              <div className="flex aspect-[4/3] items-center justify-center text-slate-500">
                <ImageOff className="h-6 w-6" />
              </div>
            )}
          </div>
          <div className="rounded-[1rem] border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Active source</p>
            <p className="mt-2 text-sm font-medium text-white">{imageModeLabel(module.image_mode)}</p>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              {activeImageUrl
                ? "This image will be used for preview and publish preparation when the module type supports it."
                : "No image selected yet."}
            </p>
          </div>
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
  if (module.image_mode === "existing_asset" && module.selected_asset_id) {
    return assets.find((asset) => asset.id === module.selected_asset_id)?.public_url ?? null;
  }
  return null;
}

function imageModeLabel(mode: AplusModulePayload["image_mode"]): string {
  const mapping: Record<AplusModulePayload["image_mode"], string> = {
    none: "Text-only module",
    uploaded: "Uploaded image",
    existing_asset: "Existing asset",
    generated: "AI-generated image",
  };

  return mapping[mode];
}
