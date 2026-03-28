import type { KeyboardEvent } from "react";

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
        className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4 transition hover:border-white/20 hover:bg-white/[0.05] focus:outline-none focus:ring-2 focus:ring-sky-400/40"
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
          <span className="rounded-full border border-white/10 px-2.5 py-1">Open product</span>
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
      className="cursor-pointer border-b border-white/10 transition hover:bg-white/[0.03] focus:outline-none focus:ring-2 focus:ring-sky-400/40"
      title={formatAbsoluteTimestamp(item.captured_at ?? new Date().toISOString())}
    >
      <td className="px-5 py-4 align-middle">
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
      </td>
      <td className="px-5 py-4 align-middle">
        <p className="text-xl font-semibold text-white">{formatQuantity(item.available_quantity)}</p>
      </td>
      <td className="px-5 py-4 align-middle">
        <p className="text-xl font-semibold text-white">{formatQuantity(item.reserved_quantity)}</p>
      </td>
      <td className="px-5 py-4 align-middle">
        <p className="text-xl font-semibold text-white">{formatQuantity(item.inbound_quantity)}</p>
      </td>
      <td className="px-5 py-4 align-middle">
        <p className="text-base font-semibold text-white">{formatQuantity(item.low_stock_threshold)}</p>
      </td>
      <td className="px-5 py-4 align-middle">
        <StatusBadge status={item.alert_status} />
      </td>
      <td className="px-5 py-4 align-middle text-sm text-slate-300">
        <span title={item.captured_at ? formatAbsoluteTimestamp(item.captured_at) : "Not synced"}>
          {formatRelativeTimestamp(item.captured_at)}
        </span>
      </td>
    </tr>
  );
}
