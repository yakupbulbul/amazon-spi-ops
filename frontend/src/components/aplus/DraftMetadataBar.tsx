import { Clock3, Globe, Languages, Package2 } from "lucide-react";

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
};

export function DraftMetadataBar({
  draft,
  product,
  sourceLanguage,
  targetLanguage,
  autoTranslate,
  formatTimestamp,
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
            {draft?.variant_role === "translated" ? "Translated draft" : "Original draft"}
          </span>
          {draft ? <AplusDraftStateBadge status={draft.status} /> : null}
        </div>
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
