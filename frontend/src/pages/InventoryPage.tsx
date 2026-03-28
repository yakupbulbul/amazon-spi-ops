import {
  AlertTriangle,
  Clock3,
  RefreshCcw,
  Search,
  ShieldAlert,
  Warehouse,
} from "lucide-react";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AlertCard } from "../components/inventory/AlertCard";
import {
  formatAbsoluteTimestamp,
  formatMarketplaceLabel,
  formatRelativeTimestamp,
} from "../components/inventory/formatters";
import { InventoryRow } from "../components/inventory/InventoryRow";
import { SummaryCard } from "../components/inventory/SummaryCard";
import { useAuth } from "../hooks/useAuth";
import {
  getInventory,
  getInventoryAlerts,
  syncInventory,
  type InventoryAlertItem,
  type InventoryItem,
} from "../lib/api";

export function InventoryPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
  const [alerts, setAlerts] = useState<InventoryAlertItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [marketplaceFilter, setMarketplaceFilter] = useState("all");
  const [healthFilter, setHealthFilter] = useState("all");
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
    return inventoryItems.filter((item) => {
      const matchesQuery =
        !normalizedQuery ||
        [item.product_name, item.sku, item.asin, item.marketplace_id]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery);
      const matchesMarketplace =
        marketplaceFilter === "all" || item.marketplace_id === marketplaceFilter;
      const matchesHealth = healthFilter === "all" || item.alert_status === healthFilter;

      return matchesQuery && matchesMarketplace && matchesHealth;
    });
  }, [deferredSearchQuery, healthFilter, inventoryItems, marketplaceFilter]);

  const marketplaceOptions = useMemo(
    () => Array.from(new Set(inventoryItems.map((item) => item.marketplace_id))).sort(),
    [inventoryItems],
  );

  const lowStockCount = inventoryItems.filter((item) => item.alert_status === "low").length;
  const outOfStockCount = inventoryItems.filter((item) => item.alert_status === "out_of_stock").length;

  const latestCapturedAt = useMemo(() => {
    const timestamps = inventoryItems
      .map((item) => item.captured_at)
      .filter((value): value is string => value !== null)
      .sort((left, right) => new Date(right).getTime() - new Date(left).getTime());

    return timestamps[0] ?? null;
  }, [inventoryItems]);

  const recentlyUpdatedCount = useMemo(() => {
    const dayAgo = Date.now() - 24 * 60 * 60 * 1000;
    return filteredItems.filter((item) => {
      if (!item.captured_at) {
        return false;
      }
      return new Date(item.captured_at).getTime() >= dayAgo;
    }).length;
  }, [filteredItems]);

  const filteredAlerts = useMemo(() => {
    const normalizedQuery = deferredSearchQuery.trim().toLowerCase();

    return alerts.filter((alert) => {
      const matchesQuery =
        !normalizedQuery ||
        [alert.product_name, alert.sku, alert.message].join(" ").toLowerCase().includes(normalizedQuery);

      const matchesHealth =
        healthFilter === "all" ||
        alert.severity === healthFilter ||
        (healthFilter === "low" && alert.severity === "warning") ||
        (healthFilter === "out_of_stock" && alert.severity === "critical");

      return matchesQuery && matchesHealth;
    });
  }, [alerts, deferredSearchQuery, healthFilter]);

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
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,_rgba(15,23,42,0.98),_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.32em] text-sky-100/70">Inventory operations</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Inventory health across your active Amazon catalog.
            </h1>
            <p className="mt-4 text-sm leading-7 text-slate-300 sm:text-base">
              Scan current stock levels, focus on risk states quickly, and move from inventory
              review to product actions without digging through dense rows.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-200">
              <div className="flex items-center gap-2">
                <Clock3 className="h-4 w-4 text-sky-300" />
                <span className="font-medium">Last synced {formatRelativeTimestamp(latestCapturedAt)}</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {latestCapturedAt ? formatAbsoluteTimestamp(latestCapturedAt) : "No inventory sync has run yet."}
              </p>
            </div>
            <button
              type="button"
              onClick={handleSync}
              disabled={isSyncing}
              className="inline-flex items-center justify-center gap-2 rounded-[1.25rem] bg-emerald-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <RefreshCcw className={["h-4 w-4", isSyncing ? "animate-spin" : ""].join(" ")} />
              {isSyncing ? "Syncing inventory..." : "Sync inventory"}
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            icon={Warehouse}
            label="Total products"
            value={inventoryItems.length}
            note={`${filteredItems.length} currently visible in the table.`}
          />
          <SummaryCard
            icon={AlertTriangle}
            label="Low stock items"
            value={lowStockCount}
            note="Products approaching the configured threshold."
            tone={lowStockCount > 0 ? "warning" : "success"}
          />
          <SummaryCard
            icon={ShieldAlert}
            label="Out of stock"
            value={outOfStockCount}
            note="Products that need immediate replenishment."
            tone={outOfStockCount > 0 ? "danger" : "success"}
          />
          <SummaryCard
            icon={RefreshCcw}
            label="Recently updated"
            value={recentlyUpdatedCount}
            note="Rows refreshed within the last 24 hours."
          />
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <article className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-slate-950/60">
          <div className="border-b border-white/10 px-5 py-5 sm:px-6 sm:py-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Inventory table</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Current stock snapshot</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Each row is interactive and leads back to product management for follow-up changes.
                </p>
              </div>
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-slate-300">
                <span className="h-2 w-2 rounded-full bg-sky-400" />
                {filteredItems.length} visible rows
              </div>
            </div>

            <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(0,1fr)_220px_220px]">
              <label className="flex w-full items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3">
                <Search className="h-4 w-4 text-slate-500" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search by product title, SKU, ASIN, or marketplace"
                  className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                />
              </label>
              <select
                value={marketplaceFilter}
                onChange={(event) => setMarketplaceFilter(event.target.value)}
                className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
              >
                <option value="all" className="bg-slate-950">
                  All marketplaces
                </option>
                {marketplaceOptions.map((marketplaceId) => (
                  <option key={marketplaceId} value={marketplaceId} className="bg-slate-950">
                    {formatMarketplaceLabel(marketplaceId)}
                  </option>
                ))}
              </select>
              <select
                value={healthFilter}
                onChange={(event) => setHealthFilter(event.target.value)}
                className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
              >
                <option value="all" className="bg-slate-950">
                  All stock states
                </option>
                <option value="healthy" className="bg-slate-950">
                  Healthy
                </option>
                <option value="low" className="bg-slate-950">
                  Low stock
                </option>
                <option value="out_of_stock" className="bg-slate-950">
                  Out of stock
                </option>
              </select>
            </div>
          </div>

          {syncMessage ? (
            <div className="mx-5 mt-5 rounded-[1.25rem] border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100 sm:mx-6">
              {syncMessage}
            </div>
          ) : null}

          <div className="p-5 sm:p-6">
            {isLoading ? (
              <div className="space-y-4">
                <div className="hidden overflow-hidden rounded-[1.5rem] border border-white/10 lg:block">
                  <div className="grid grid-cols-[minmax(0,2fr)_repeat(4,minmax(90px,1fr))_180px_140px] gap-4 border-b border-white/10 bg-white/[0.03] px-5 py-4">
                    {Array.from({ length: 7 }).map((_, index) => (
                      <div key={index} className="h-4 animate-pulse rounded bg-white/10" />
                    ))}
                  </div>
                  <div className="space-y-0">
                    {Array.from({ length: 5 }).map((_, index) => (
                      <div
                        key={index}
                        className="grid grid-cols-[minmax(0,2fr)_repeat(4,minmax(90px,1fr))_180px_140px] gap-4 border-b border-white/10 px-5 py-5"
                      >
                        {Array.from({ length: 7 }).map((__, cellIndex) => (
                          <div
                            key={cellIndex}
                            className="h-14 animate-pulse rounded-2xl bg-white/[0.06]"
                          />
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="space-y-4 lg:hidden">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <div
                      key={index}
                      className="h-44 animate-pulse rounded-[1.5rem] border border-white/10 bg-white/[0.04]"
                    />
                  ))}
                </div>
              </div>
            ) : error ? (
              <div className="flex items-start gap-3 rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 p-6 text-sm text-rose-100">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] px-6 py-12 text-center">
                <Warehouse className="mx-auto h-10 w-10 text-slate-500" />
                <h3 className="mt-4 text-lg font-medium text-white">No inventory rows match the current filters.</h3>
                <p className="mt-3 text-sm leading-6 text-slate-400">
                  Try a different keyword, reset the status filter, or change the selected marketplace.
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-4 lg:hidden">
                  {filteredItems.map((item) => (
                    <InventoryRow
                      key={item.product_id}
                      item={item}
                      variant="mobile"
                      onSelect={() => navigate("/products")}
                    />
                  ))}
                </div>

                <div className="hidden overflow-hidden rounded-[1.5rem] border border-white/10 lg:block">
                  <table className="min-w-full table-fixed border-collapse">
                    <thead className="bg-white/[0.04]">
                      <tr className="text-left text-xs uppercase tracking-[0.24em] text-slate-500">
                        <th className="w-[30%] px-5 py-4 font-medium">Product</th>
                        <th className="px-5 py-4 font-medium">Available</th>
                        <th className="px-5 py-4 font-medium">Reserved</th>
                        <th className="px-5 py-4 font-medium">Inbound</th>
                        <th className="px-5 py-4 font-medium">Threshold</th>
                        <th className="px-5 py-4 font-medium">Status</th>
                        <th className="px-5 py-4 font-medium">Last updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredItems.map((item) => (
                        <InventoryRow
                          key={item.product_id}
                          item={item}
                          variant="desktop"
                          onSelect={() => navigate("/products")}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </article>

        <aside className="rounded-[1.75rem] border border-white/10 bg-slate-950/60 p-5 sm:p-6">
          <div>
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-3 text-amber-100">
                    <ShieldAlert className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Alert queue</p>
                    <h2 className="mt-1 text-xl font-semibold text-white">Inventory alerts</h2>
                  </div>
                </div>
                <span className="inline-flex rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-300">
                  {filteredAlerts.length}
                </span>
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-400">
                Critical and warning alerts stay visible here so replenishment issues are easy to triage beside the table.
              </p>
            </div>
          <div className="mt-6 space-y-4">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-44 animate-pulse rounded-[1.5rem] border border-white/10 bg-white/[0.04]"
                />
              ))
            ) : error ? (
              <div className="rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 p-4 text-sm text-rose-100">
                Alerts are temporarily unavailable while inventory data is failing to load.
              </div>
            ) : filteredAlerts.length === 0 ? (
              <div className="rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-6 text-center">
                <ShieldAlert className="mx-auto h-9 w-9 text-slate-500" />
                <h3 className="mt-4 text-base font-medium text-white">No active alerts</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Inventory alerts will appear here when a SKU falls below its threshold.
                </p>
              </div>
            ) : (
              filteredAlerts.map((alert) => (
                <AlertCard
                  key={`${alert.product_id}-${alert.created_at}`}
                  alert={alert}
                  onViewProduct={() => navigate("/products")}
                />
              ))
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}
