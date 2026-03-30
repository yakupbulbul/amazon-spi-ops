import {
  ChevronDown,
  ChevronUp,
  LayoutTemplate,
  Plus,
  Rows3,
  Trash2,
} from "lucide-react";

import type { AplusAsset, AplusModulePayload } from "../../lib/api";
import { AplusModuleImageSection } from "./AplusModuleImageSection";
import {
  moduleIsEditorialOnly,
  moduleSupportsPublishImage,
} from "./previewImage";

type AplusModuleEditorCardProps = {
  index: number;
  module: AplusModulePayload;
  isExpanded: boolean;
  canRemove: boolean;
  onToggle: () => void;
  onRemove: () => void;
  onUpdate: (patch: Partial<AplusModulePayload>) => void;
  moduleLabels: Record<AplusModulePayload["module_type"], string>;
  assets: AplusAsset[];
  isLoadingAssets: boolean;
  isUploadingImage: boolean;
  imageUploadError: string | null;
  onUploadImage: (file: File) => void;
  onSelectAsset: (asset: AplusAsset) => void;
  onClearImage: () => void;
  canGenerateImage: boolean;
  onGenerateImage: () => void;
};

export function AplusModuleEditorCard({
  index,
  module,
  isExpanded,
  canRemove,
  onToggle,
  onRemove,
  onUpdate,
  moduleLabels,
  assets,
  isLoadingAssets,
  isUploadingImage,
  imageUploadError,
  onUploadImage,
  onSelectAsset,
  onClearImage,
  canGenerateImage,
  onGenerateImage,
}: AplusModuleEditorCardProps) {
  const comparisonRows = module.bullets.map(parseComparisonRow);

  function updateComparisonRow(
    rowIndex: number,
    patch: Partial<ComparisonRow>,
  ) {
    const nextRows = comparisonRows.map((row, index) =>
      index === rowIndex ? { ...row, ...patch } : row,
    );
    onUpdate({
      bullets: nextRows.map(serializeComparisonRow).filter(Boolean),
    });
  }

  function addComparisonRow() {
    onUpdate({
      bullets: [
        ...module.bullets,
        serializeComparisonRow({
          criterion: "Comparison point",
          thisProduct: "Clear product advantage",
          genericAlternative: "Basic alternative outcome",
        }),
      ],
    });
  }

  function removeComparisonRow(rowIndex: number) {
    onUpdate({
      bullets: module.bullets.filter((_, index) => index !== rowIndex),
    });
  }

  const publishSupported = !moduleIsEditorialOnly(module.module_type);
  const requiresPublishImage = moduleSupportsPublishImage(module.module_type);

  return (
    <article className="rounded-[1.5rem] bg-white/[0.03] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs uppercase tracking-[0.22em] text-slate-400">
              Module {index + 1}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-sky-300/20 bg-sky-500/10 px-2.5 py-1 text-xs text-sky-100">
              <LayoutTemplate className="h-3.5 w-3.5" />
              {moduleLabels[module.module_type]}
            </span>
            <span
              className={[
                "rounded-full px-2.5 py-1 text-xs",
                publishSupported
                  ? "border border-emerald-300/20 bg-emerald-500/10 text-emerald-100"
                  : "border border-amber-300/20 bg-amber-500/10 text-amber-100",
              ].join(" ")}
            >
              {publishSupported ? "Real publish supported" : "Editorial only"}
            </span>
          </div>
          <p className="mt-3 text-sm font-medium text-white">{module.headline || "Untitled module"}</p>
          <p className="mt-1 text-xs text-slate-500">
            {module.body.slice(0, 120)}
            {module.body.length > 120 ? "..." : ""}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onToggle}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-2 text-xs text-slate-200 transition hover:bg-white/[0.06]"
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            {isExpanded ? "Collapse" : "Expand"}
          </button>
          <button
            type="button"
            onClick={onRemove}
            disabled={!canRemove}
            className="inline-flex items-center gap-2 rounded-full border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Trash2 className="h-4 w-4" />
            Remove
          </button>
        </div>
      </div>

      {isExpanded ? (
        <div className="mt-5 space-y-5 border-t border-white/10 pt-5">
          <div
            className={[
              "rounded-[1.1rem] px-4 py-3 text-sm leading-6",
              publishSupported
                ? "border border-emerald-300/15 bg-emerald-500/10 text-emerald-100"
                : "border border-amber-300/15 bg-amber-500/10 text-amber-100",
            ].join(" ")}
          >
            {publishSupported
              ? requiresPublishImage
                ? "This module is part of the current real Amazon publish subset and must have a valid prepared image before publish."
                : "This module is part of the current real Amazon publish subset and will publish as text-only content."
              : "This module stays in the Studio for editorial planning only. It is not included in the real Amazon publish request yet."}
          </div>

          <div className="grid gap-4 lg:grid-cols-[180px_minmax(0,1fr)]">
            <label className="block space-y-2">
              <span className="text-sm text-slate-300">Module type</span>
              <select
                value={module.module_type}
                onChange={(event) =>
                  onUpdate({
                    module_type: event.target.value as AplusModulePayload["module_type"],
                  })
                }
                className="w-full rounded-[1.1rem] border border-white/10 bg-slate-950 px-3 py-3 text-sm text-white outline-none"
              >
                {Object.entries(moduleLabels).map(([value, label]) => (
                  <option key={value} value={value} className="bg-slate-950">
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label className="block space-y-2">
              <span className="text-sm text-slate-300">Headline</span>
              <input
                type="text"
                value={module.headline}
                onChange={(event) => onUpdate({ headline: event.target.value })}
                className="w-full rounded-[1.1rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
              />
            </label>
          </div>

          <label className="block space-y-2">
            <span className="text-sm text-slate-300">Body</span>
            <textarea
              value={module.body}
              onChange={(event) => onUpdate({ body: event.target.value })}
              rows={5}
              className="w-full rounded-[1.1rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-7 text-white outline-none"
            />
          </label>

          {requiresPublishImage ? (
            <AplusModuleImageSection
              module={module}
              assets={assets}
              isLoadingAssets={isLoadingAssets}
              isUploading={isUploadingImage}
              uploadError={imageUploadError}
              onUpdate={onUpdate}
              onUpload={onUploadImage}
              onSelectAsset={onSelectAsset}
              onClearImage={onClearImage}
              canGenerate={canGenerateImage}
              onGenerate={onGenerateImage}
            />
          ) : null}

          <div className="grid gap-4 xl:grid-cols-2">
            {module.module_type === "comparison" ? (
              <div className="space-y-3 rounded-[1.25rem] border border-white/10 bg-white/[0.03] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-white">Comparison rows</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                      Each row maps to the comparison table preview: criteria, this product, and a generic alternative.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={addComparisonRow}
                    className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/[0.08]"
                  >
                    <Rows3 className="h-3.5 w-3.5" />
                    Add row
                  </button>
                </div>

                <div className="space-y-3">
                  {comparisonRows.map((row, rowIndex) => (
                    <div
                      key={`${row.criterion}-${rowIndex}`}
                      className="rounded-[1rem] border border-white/10 bg-slate-950/60 p-3"
                    >
                      <div className="grid gap-3">
                        <label className="block space-y-2">
                          <span className="text-xs uppercase tracking-[0.2em] text-slate-500">
                            Criteria
                          </span>
                          <input
                            type="text"
                            value={row.criterion}
                            onChange={(event) =>
                              updateComparisonRow(rowIndex, { criterion: event.target.value })
                            }
                            className="w-full rounded-[0.9rem] border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none"
                          />
                        </label>
                        <div className="grid gap-3 md:grid-cols-2">
                          <label className="block space-y-2">
                            <span className="text-xs uppercase tracking-[0.2em] text-slate-500">
                              This product
                            </span>
                            <input
                              type="text"
                              value={row.thisProduct}
                              onChange={(event) =>
                                updateComparisonRow(rowIndex, { thisProduct: event.target.value })
                              }
                              className="w-full rounded-[0.9rem] border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none"
                            />
                          </label>
                          <label className="block space-y-2">
                            <span className="text-xs uppercase tracking-[0.2em] text-slate-500">
                              Generic alternative
                            </span>
                            <input
                              type="text"
                              value={row.genericAlternative}
                              onChange={(event) =>
                                updateComparisonRow(rowIndex, {
                                  genericAlternative: event.target.value,
                                })
                              }
                              className="w-full rounded-[0.9rem] border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none"
                            />
                          </label>
                        </div>
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={() => removeComparisonRow(rowIndex)}
                            disabled={comparisonRows.length <= 1}
                            className="inline-flex items-center gap-2 rounded-full border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Remove row
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <label className="block space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm text-slate-300">Bullets</span>
                  <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                    <Plus className="h-3.5 w-3.5" />
                    One line per bullet
                  </span>
                </div>
                <textarea
                  value={module.bullets.join("\n")}
                  onChange={(event) =>
                    onUpdate({
                      bullets: event.target.value
                        .split("\n")
                        .map((item) => item.trim())
                        .filter(Boolean),
                    })
                  }
                  rows={4}
                  className="w-full rounded-[1.1rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-7 text-white outline-none"
                />
              </label>
            )}

            {requiresPublishImage ? (
              <label className="block space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-slate-300">Image brief</span>
                  <span className="text-xs text-slate-500">
                    Amazon alt text auto-uses the first 100 characters
                  </span>
                </div>
                <textarea
                  value={module.image_brief}
                  onChange={(event) => onUpdate({ image_brief: event.target.value })}
                  rows={4}
                  className="w-full rounded-[1.1rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-7 text-white outline-none"
                />
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-slate-500">
                    Keep the first sentence concise. Longer creative direction can continue after that.
                  </span>
                  <span className={module.image_brief.trim().length > 100 ? "text-amber-300" : "text-slate-500"}>
                    {module.image_brief.trim().length}/100 alt-text chars
                  </span>
                </div>
              </label>
            ) : null}
          </div>
        </div>
      ) : null}
    </article>
  );
}

type ComparisonRow = {
  criterion: string;
  thisProduct: string;
  genericAlternative: string;
};

function parseComparisonRow(value: string): ComparisonRow {
  const [criterion = "", thisProduct = "", genericAlternative = ""] = value
    .split("|")
    .map((item) => item.trim());

  return {
    criterion,
    thisProduct,
    genericAlternative,
  };
}

function serializeComparisonRow(row: ComparisonRow): string {
  const parts = [row.criterion, row.thisProduct, row.genericAlternative].map((item) =>
    item.trim(),
  );

  if (parts[1] || parts[2]) {
    return parts.join(" | ");
  }

  return parts[0];
}
