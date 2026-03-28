import {
  AlertTriangle,
  RefreshCcw,
  Search,
  Warehouse,
} from "lucide-react";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { useAuth } from "../hooks/useAuth";
import {
  getInventory,
  getInventoryAlerts,
  syncInventory,
  type InventoryAlertItem,
  type InventoryItem,
} from "../lib/api";

const inventoryBadgeStyles: Record<string, string> = {
  healthy: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200",
  low: "border-amber-400/20 bg-amber-500/10 text-amber-100",
  out_of_stock: "border-rose-400/20 bg-rose-500/10 text-rose-100",
  critical: "border-rose-400/20 bg-rose-500/10 text-rose-100",
};

function formatStatusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function InventoryPage() {
  const { token } = useAuth();
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [alerts, setAlerts] = useState<InventoryAlertItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const deferredSearchQuery = useDeferredValue(searchQuery);

  useEffect(() => {
    let cancelled = false;

    async function loadInventory() {
      if (!token) {
        return;
      }

      try {
        const [inventoryResponse, alertsResponse] = await Promise.all([
          getInventory(token),
          getInventoryAlerts(token),
        ]);
        if (!cancelled) {
          startTransition(() => {
            setInventoryItems(inventoryResponse.items);
            setAlerts(alertsResponse.items);
            setError(null);
          });
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load inventory.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadInventory();

    return () => {
      cancelled = true;
    };
  }, [token]);

  const filteredItems = useMemo(() => {
    const normalizedQuery = deferredSearchQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return inventoryItems;
    }

    return inventoryItems.filter((item) =>
      [item.product_name, item.sku, item.asin, item.marketplace_id]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [deferredSearchQuery, inventoryItems]);

  const lowOrCriticalCount = filteredItems.filter(
    (item) => item.alert_status !== "healthy",
  ).length;

  async function handleSync() {
    if (!token) {
      return;
    }

    setIsSyncing(true);
    setSyncMessage(null);
    try {
      const syncResponse = await syncInventory(token);
      const [inventoryResponse, alertsResponse] = await Promise.all([
        getInventory(token),
        getInventoryAlerts(token),
      ]);
      startTransition(() => {
        setInventoryItems(inventoryResponse.items);
        setAlerts(alertsResponse.items);
        setError(null);
      });
      setSyncMessage(
        `Inventory sync completed from ${syncResponse.source} for ${syncResponse.synced_count} products.`,
      );
    } catch (syncError) {
      setError(syncError instanceof Error ? syncError.message : "Unable to sync inventory.");
    } finally {
      setIsSyncing(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(16,185,129,0.16),_rgba(15,23,42,0.95)_42%,_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-xs uppercase tracking-[0.32em] text-emerald-100/70">Inventory operations</p>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
            Inventory posture across tracked SKUs with manual sync and alert visibility.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            This screen now reflects the local inventory snapshot store and alert log. Manual sync
            already flows through the Amazon adapter abstraction, using the mock adapter until live
            SP-API credentials are configured.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Visible inventory rows</p>
            <p className="mt-4 text-4xl font-semibold text-white">{filteredItems.length}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Filtered from the latest snapshot set.</p>
          </article>
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Rows needing attention</p>
            <p className="mt-4 text-4xl font-semibold text-white">{lowOrCriticalCount}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Low-stock or out-of-stock products.</p>
          </article>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
        <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Inventory table</p>
              <h3 className="mt-2 text-xl font-semibold text-white">Latest quantities</h3>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <label className="flex w-full items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 sm:min-w-80">
                <Search className="h-4 w-4 text-slate-500" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search by SKU, ASIN, title, or marketplace"
                  className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                />
              </label>
              <button
                type="button"
                onClick={handleSync}
                disabled={isSyncing}
                className="inline-flex items-center justify-center gap-2 rounded-[1.25rem] border border-emerald-300/20 bg-emerald-400/10 px-4 py-3 text-sm font-medium text-emerald-100 transition hover:bg-emerald-400/20 disabled:cursor-not-allowed disabled:opacity-70"
              >
                <RefreshCcw className={["h-4 w-4", isSyncing ? "animate-spin" : ""].join(" ")} />
                {isSyncing ? "Syncing..." : "Sync inventory"}
              </button>
            </div>
          </div>

          {syncMessage ? (
            <div className="mt-5 rounded-[1.25rem] border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              {syncMessage}
            </div>
          ) : null}

          {isLoading ? (
            <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-6 text-sm text-slate-300">
              Loading inventory...
            </div>
          ) : error ? (
            <div className="mt-6 flex items-start gap-3 rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 p-6 text-sm text-rose-100">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] px-6 py-12 text-center">
              <Warehouse className="mx-auto h-10 w-10 text-slate-500" />
              <h4 className="mt-4 text-lg font-medium text-white">No inventory rows match this search.</h4>
              <p className="mt-3 text-sm leading-6 text-slate-400">
                Clear the filter or search with a different SKU, ASIN, or product title.
              </p>
            </div>
          ) : (
            <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-white/10">
              <div className="hidden grid-cols-[minmax(0,2fr)_120px_120px_120px_140px] gap-4 border-b border-white/10 bg-white/[0.04] px-5 py-4 text-xs uppercase tracking-[0.24em] text-slate-500 lg:grid">
                <span>Product</span>
                <span>Available</span>
                <span>Reserved</span>
                <span>Inbound</span>
                <span>Health</span>
              </div>

              <div className="divide-y divide-white/10">
                {filteredItems.map((item) => (
                  <article
                    key={item.product_id}
                    className="grid gap-5 px-5 py-5 lg:grid-cols-[minmax(0,2fr)_120px_120px_120px_140px] lg:items-center"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-base font-medium text-white">{item.product_name}</p>
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                        <span className="rounded-full border border-white/10 px-2.5 py-1">{item.sku}</span>
                        <span className="rounded-full border border-white/10 px-2.5 py-1">{item.asin}</span>
                        <span className="rounded-full border border-white/10 px-2.5 py-1">
                          Threshold {item.low_stock_threshold}
                        </span>
                      </div>
                    </div>
                    <div className="text-sm text-slate-100">{item.available_quantity}</div>
                    <div className="text-sm text-slate-100">{item.reserved_quantity}</div>
                    <div className="text-sm text-slate-100">{item.inbound_quantity}</div>
                    <div>
                      <span
                        className={[
                          "inline-flex rounded-full border px-3 py-1 text-xs font-medium capitalize",
                          inventoryBadgeStyles[item.alert_status] ?? inventoryBadgeStyles.critical,
                        ].join(" ")}
                      >
                        {formatStatusLabel(item.alert_status)}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )}
        </article>

        <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Alert queue</p>
          <h3 className="mt-2 text-xl font-semibold text-white">Active inventory alerts</h3>
          <div className="mt-5 space-y-4">
            {alerts.length === 0 ? (
              <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300">
                Inventory alerts will appear here after the next sync if any SKUs drop below threshold.
              </div>
            ) : (
              alerts.map((alert) => (
                <div
                  key={`${alert.product_id}-${alert.created_at}`}
                  className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-white">{alert.product_name}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-300">{alert.message}</p>
                    </div>
                    <span
                      className={[
                        "inline-flex rounded-full border px-3 py-1 text-xs font-medium capitalize",
                        inventoryBadgeStyles[alert.severity] ?? inventoryBadgeStyles.critical,
                      ].join(" ")}
                    >
                      {alert.severity}
                    </span>
                  </div>
                  <div className="mt-3 text-xs text-slate-500">
                    Available {alert.available_quantity} of threshold {alert.low_stock_threshold}
                  </div>
                </div>
              ))
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
