import { Clock3, Globe, Languages, Package2 } from "lucide-react";

import type { AplusDraftResponse, ProductListItem } from "../../lib/api";
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
    <div className="grid gap-3 rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4 lg:grid-cols-2 2xl:grid-cols-5">
      <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/60 px-4 py-3">
        <div className="flex items-center gap-2 text-slate-400">
          <Package2 className="h-4 w-4" />
          <p className="text-xs uppercase tracking-[0.22em]">Product</p>
        </div>
        <p className="mt-2 text-sm font-medium text-white">{product?.title ?? "No product selected"}</p>
        <p className="mt-1 text-xs text-slate-400">{product ? `SKU ${product.sku} · ASIN ${product.asin}` : "Select a catalog item to start."}</p>
      </div>

      <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/60 px-4 py-3">
        <div className="flex items-center gap-2 text-slate-400">
          <Globe className="h-4 w-4" />
          <p className="text-xs uppercase tracking-[0.22em]">Marketplace</p>
        </div>
        <p className="mt-2 text-sm font-medium text-white">{draft?.marketplace_id ?? product?.marketplace_id ?? "Not set"}</p>
      </div>

      <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/60 px-4 py-3">
        <div className="flex items-center gap-2 text-slate-400">
          <Languages className="h-4 w-4" />
          <p className="text-xs uppercase tracking-[0.22em]">Language</p>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-200">
            Source {formatLanguageLabel(sourceLanguage as never)}
          </span>
          <span
            className={[
              "rounded-full border px-2.5 py-1 text-xs",
              autoTranslate
                ? "border-sky-300/20 bg-sky-500/10 text-sky-100"
                : "border-white/10 text-slate-200",
            ].join(" ")}
          >
            {autoTranslate
              ? `Target ${formatLanguageLabel(targetLanguage as never)}`
              : `Original draft`}
          </span>
        </div>
      </div>

      <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/60 px-4 py-3">
        <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Draft type</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-100">
            {autoTranslate ? "Translated draft" : "Original draft"}
          </span>
          {draft ? (
            <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-200">
              {draft.status.replaceAll("_", " ")}
            </span>
          ) : null}
        </div>
      </div>

      <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/60 px-4 py-3">
        <div className="flex items-center gap-2 text-slate-400">
          <Clock3 className="h-4 w-4" />
          <p className="text-xs uppercase tracking-[0.22em]">Generated</p>
        </div>
        <p className="mt-2 text-sm font-medium text-white">
          {draft ? formatTimestamp(draft.created_at) : "Not generated yet"}
        </p>
        {draft ? <p className="mt-1 text-xs text-slate-400">Updated {formatTimestamp(draft.updated_at)}</p> : null}
      </div>
    </div>
  );
}
