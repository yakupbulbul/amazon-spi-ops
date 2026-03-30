import { Clock3, Globe, Languages, Package2, RotateCcw } from "lucide-react";

import type { AplusDraftResponse, ProductListItem } from "../../lib/api";
import { AplusDraftStateBadge } from "./AplusDraftStateBadge";
import { formatLanguageLabel } from "./languages";

type DraftMetadataBarProps = {
  draft: AplusDraftResponse | null;
  product: ProductListItem | null;
  sourceLanguage: string;
  targetLanguage: string;
  autoTranslate: boolean;
  formatTimestamp: (value: string) => string;
  availableVariants: AplusDraftResponse[];
  activeDraftId: string | null;
  switchingVariantId: string | null;
  onSwitchVariant: (draft: AplusDraftResponse) => void;
  canRecoverSourceVariant: boolean;
  isRecoveringSourceVariant: boolean;
  onRecoverSourceVariant: () => void;
};

function formatVariantLabel(draft: AplusDraftResponse): string {
  const language = formatLanguageLabel(
    (draft.variant_role === "translated" ? draft.target_language : draft.source_language) as never,
  );
  return draft.variant_role === "translated" ? `Translated (${language})` : `Source (${language})`;
}

export function DraftMetadataBar({
  draft,
  product,
  sourceLanguage,
  targetLanguage,
  autoTranslate,
  formatTimestamp,
  availableVariants,
  activeDraftId,
  switchingVariantId,
  onSwitchVariant,
  canRecoverSourceVariant,
  isRecoveringSourceVariant,
  onRecoverSourceVariant,
}: DraftMetadataBarProps) {
  return (
    <div className="rounded-[1.5rem] bg-white/[0.03] px-4 py-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-slate-400">
            <Package2 className="h-4 w-4" />
            <p className="text-xs uppercase tracking-[0.22em]">Draft metadata</p>
          </div>
          <p className="mt-2 text-sm font-medium leading-6 text-white">
            {product?.title ?? "No product selected"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {product ? `SKU ${product.sku} · ASIN ${product.asin}` : "Select a catalog item to start."}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-200">
            <Globe className="h-3.5 w-3.5 text-slate-400" />
            {draft?.marketplace_id ?? product?.marketplace_id ?? "Marketplace pending"}
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-200">
            <Languages className="h-3.5 w-3.5 text-slate-400" />
            {formatLanguageLabel(sourceLanguage as never)}
            {autoTranslate ? ` -> ${formatLanguageLabel(targetLanguage as never)}` : ""}
          </span>
          <span
            className={[
              "rounded-full border px-3 py-1.5 text-xs",
              draft?.variant_role === "translated"
                ? "border-sky-300/20 bg-sky-500/10 text-sky-100"
                : "border-emerald-400/20 bg-emerald-500/10 text-emerald-100",
            ].join(" ")}
          >
            {draft?.variant_role === "translated" ? "Translated draft" : "Source draft"}
          </span>
          {draft ? <AplusDraftStateBadge status={draft.status} /> : null}
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          {availableVariants.map((variant) => (
            <button
              key={variant.id}
              type="button"
              onClick={() => onSwitchVariant(variant)}
              disabled={switchingVariantId !== null}
              className={[
                "rounded-full border px-3 py-1.5 text-xs font-medium transition",
                variant.id === activeDraftId
                  ? "border-sky-300/30 bg-sky-500/10 text-sky-100"
                  : "border-white/10 bg-white/[0.04] text-slate-300 hover:bg-white/[0.08]",
              ].join(" ")}
            >
              {switchingVariantId === variant.id ? "Switching..." : formatVariantLabel(variant)}
            </button>
          ))}

          {canRecoverSourceVariant ? (
            <button
              type="button"
              onClick={onRecoverSourceVariant}
              disabled={isRecoveringSourceVariant}
              className="inline-flex items-center gap-2 rounded-full border border-amber-300/20 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-100 transition hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              {isRecoveringSourceVariant ? `Creating source (${formatLanguageLabel(sourceLanguage as never)})...` : `Create source (${formatLanguageLabel(sourceLanguage as never)})`}
            </button>
          ) : null}
        </div>

        {availableVariants.length <= 1 && !canRecoverSourceVariant ? (
          <p className="text-xs text-slate-500">Only one stored language variant is currently available for this draft.</p>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-500">
        <span className="inline-flex items-center gap-2">
          <Clock3 className="h-3.5 w-3.5" />
          {draft ? `Generated ${formatTimestamp(draft.created_at)}` : "Not generated yet"}
        </span>
        {draft ? <span>Updated {formatTimestamp(draft.updated_at)}</span> : null}
      </div>
    </div>
  );
}
