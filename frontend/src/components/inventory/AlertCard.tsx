import { ArrowRight, AlertTriangle } from "lucide-react";

import type { InventoryAlertItem } from "../../lib/api";
import { formatRelativeTimestamp, formatStatusLabel } from "./formatters";

type AlertCardProps = {
  alert: InventoryAlertItem;
  onViewProduct: (sku: string) => void;
};

const severityStyles: Record<string, string> = {
  low: "border-amber-400/20 bg-amber-500/10",
  warning: "border-amber-400/20 bg-amber-500/10",
  critical: "border-rose-400/20 bg-rose-500/10",
  out_of_stock: "border-rose-400/20 bg-rose-500/10",
};

export function AlertCard({ alert, onViewProduct }: AlertCardProps) {
  return (
    <article
      className={[
        "rounded-[1.5rem] border p-4",
        severityStyles[alert.severity] ?? severityStyles.critical,
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{alert.product_name}</p>
          <p className="mt-1 text-xs text-slate-300">SKU {alert.sku}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-2 text-amber-100">
          <AlertTriangle className="h-4 w-4" />
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <p className="text-sm font-medium capitalize text-white">
          {formatStatusLabel(alert.severity)}
        </p>
        <p className="text-sm leading-6 text-slate-200">{alert.message}</p>
      </div>

      <div className="mt-4 rounded-[1.1rem] border border-white/10 bg-slate-950/40 px-3 py-3 text-sm text-slate-200">
        <div className="flex items-center justify-between gap-4">
          <span>Available</span>
          <span className="font-semibold">{alert.available_quantity}</span>
        </div>
        <div className="mt-2 flex items-center justify-between gap-4">
          <span>Threshold</span>
          <span className="font-semibold">{alert.low_stock_threshold}</span>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-xs text-slate-400">{formatRelativeTimestamp(alert.created_at)}</p>
        <button
          type="button"
          onClick={() => onViewProduct(alert.sku)}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-slate-950/50 px-3 py-2 text-xs font-medium text-white transition hover:bg-slate-900"
        >
          View product
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </article>
  );
}
