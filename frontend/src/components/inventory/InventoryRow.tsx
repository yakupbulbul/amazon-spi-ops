import type { KeyboardEvent } from "react";

import { ChevronRight } from "lucide-react";

import type { InventoryItem } from "../../lib/api";
import {
  formatAbsoluteTimestamp,
  formatMarketplaceLabel,
  formatQuantity,
  formatRelativeTimestamp,
} from "./formatters";
import { StatusBadge } from "./StatusBadge";

type InventoryRowProps = {
  item: InventoryItem;
  variant: "desktop" | "mobile";
  onSelect: (sku: string) => void;
};

function QuantityCell({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-white">{formatQuantity(value)}</p>
    </div>
  );
}

export function InventoryRow({ item, variant, onSelect }: InventoryRowProps) {
  const accentStyles: Record<string, string> = {
    healthy: "border-emerald-400/20",
    low: "border-amber-400/20",
    out_of_stock: "border-rose-400/20",
    critical: "border-rose-400/20",
  };

  const accentDotStyles: Record<string, string> = {
    healthy: "bg-emerald-400",
    low: "bg-amber-400",
    out_of_stock: "bg-rose-400",
    critical: "bg-rose-400",
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(item.sku);
    }
  };

  if (variant === "mobile") {
    return (
      <article
        role="button"
        tabIndex={0}
        onClick={() => onSelect(item.sku)}
        onKeyDown={handleKeyDown}
        className={[
          "rounded-[1.5rem] border bg-white/[0.03] p-4 transition hover:border-white/20 hover:bg-white/[0.05] focus:outline-none focus:ring-2 focus:ring-sky-400/40",
          accentStyles[item.alert_status] ?? accentStyles.critical,
        ].join(" ")}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="truncate text-base font-semibold text-white">{item.product_name}</p>
            <div className="mt-2 space-y-1 text-xs text-slate-400">
              <p>SKU {item.sku}</p>
              <p>ASIN {item.asin}</p>
              <p>{formatMarketplaceLabel(item.marketplace_id)}</p>
            </div>
          </div>
          <StatusBadge status={item.alert_status} />
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/50 p-3">
            <QuantityCell label="Available" value={item.available_quantity} />
          </div>
          <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/50 p-3">
            <QuantityCell label="Reserved" value={item.reserved_quantity} />
          </div>
          <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/50 p-3">
            <QuantityCell label="Inbound" value={item.inbound_quantity} />
          </div>
          <div className="rounded-[1.1rem] border border-white/10 bg-slate-950/50 p-3">
            <QuantityCell label="Threshold" value={item.low_stock_threshold} />
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-400">
          <span>{formatRelativeTimestamp(item.captured_at)}</span>
          <span className="inline-flex items-center gap-1 rounded-full border border-white/10 px-2.5 py-1">
            Open product
            <ChevronRight className="h-3.5 w-3.5" />
          </span>
        </div>
      </article>
    );
  }

  return (
    <tr
      role="button"
      tabIndex={0}
      onClick={() => onSelect(item.sku)}
      onKeyDown={handleKeyDown}
      className="group cursor-pointer border-b border-white/10 transition hover:bg-white/[0.03] focus:outline-none focus:ring-2 focus:ring-sky-400/40"
      title={formatAbsoluteTimestamp(item.captured_at ?? new Date().toISOString())}
    >
      <td className="px-5 py-4 align-middle">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className={[
              "mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full",
              accentDotStyles[item.alert_status] ?? accentDotStyles.critical,
            ].join(" ")}
          />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{item.product_name}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
              <span className="rounded-full border border-white/10 px-2.5 py-1">SKU {item.sku}</span>
              <span className="rounded-full border border-white/10 px-2.5 py-1">ASIN {item.asin}</span>
              <span className="rounded-full border border-white/10 px-2.5 py-1">
                {formatMarketplaceLabel(item.marketplace_id)}
              </span>
            </div>
          </div>
        </div>
      </td>
      <td className="px-5 py-4 align-middle">
        <div className="rounded-[1rem] border border-white/10 bg-white/[0.03] px-3 py-3 text-center">
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Available</p>
          <p className="mt-1 text-xl font-semibold text-white">{formatQuantity(item.available_quantity)}</p>
        </div>
      </td>
      <td className="px-5 py-4 align-middle">
        <div className="rounded-[1rem] border border-white/10 bg-white/[0.03] px-3 py-3 text-center">
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Reserved</p>
          <p className="mt-1 text-xl font-semibold text-white">{formatQuantity(item.reserved_quantity)}</p>
        </div>
      </td>
      <td className="px-5 py-4 align-middle">
        <div className="rounded-[1rem] border border-white/10 bg-white/[0.03] px-3 py-3 text-center">
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Inbound</p>
          <p className="mt-1 text-xl font-semibold text-white">{formatQuantity(item.inbound_quantity)}</p>
        </div>
      </td>
      <td className="px-5 py-4 align-middle">
        <div className="rounded-[1rem] border border-white/10 bg-white/[0.03] px-3 py-3 text-center">
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Threshold</p>
          <p className="mt-1 text-lg font-semibold text-white">{formatQuantity(item.low_stock_threshold)}</p>
        </div>
      </td>
      <td className="px-5 py-4 align-middle">
        <StatusBadge status={item.alert_status} />
      </td>
      <td className="px-5 py-4 align-middle text-sm text-slate-300">
        <div className="flex items-center justify-between gap-3">
          <span title={item.captured_at ? formatAbsoluteTimestamp(item.captured_at) : "Not synced"}>
            {formatRelativeTimestamp(item.captured_at)}
          </span>
          <ChevronRight className="h-4 w-4 text-slate-500 transition group-hover:text-slate-300" />
        </div>
      </td>
    </tr>
  );
}
