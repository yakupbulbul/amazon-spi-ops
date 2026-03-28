import { AlertTriangle, RefreshCcw, Search, Warehouse } from "lucide-react";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { AlertCard } from "../components/inventory/AlertCard";
import {
  formatAbsoluteTimestamp,
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

  const lowOrCriticalCount = filteredItems.filter(
    (item) => item.alert_status !== "healthy",
  ).length;
  const outOfStockCount = filteredItems.filter((item) => item.alert_status === "out_of_stock").length;

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
          <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-4 py-2 text-xs text-slate-200">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Last synced {formatRelativeTimestamp(latestCapturedAt)}
            {latestCapturedAt ? (
              <span className="text-slate-400">({formatAbsoluteTimestamp(latestCapturedAt)})</span>
            ) : null}
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <SummaryCard
            icon={Warehouse}
            label="Visible inventory rows"
            value={filteredItems.length}
            note="Filtered from the latest snapshot set."
          />
          <SummaryCard
            icon={AlertTriangle}
            label="Rows needing attention"
            value={lowOrCriticalCount}
            note={`${outOfStockCount} are currently out of stock.`}
            tone={lowOrCriticalCount > 0 ? "warning" : "success"}
          />
          <SummaryCard
            icon={RefreshCcw}
            label="Recently updated"
            value={recentlyUpdatedCount}
            note="Rows refreshed in the last 24 hours."
          />
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
                    {marketplaceId}
                  </option>
                ))}
              </select>
              <select
                value={healthFilter}
                onChange={(event) => setHealthFilter(event.target.value)}
                className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
              >
                <option value="all" className="bg-slate-950">
                  All health states
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
            <>
              <div className="mt-6 space-y-4 lg:hidden">
                {filteredItems.map((item) => (
                  <InventoryRow
                    key={item.product_id}
                    item={item}
                    variant="mobile"
                    onSelect={() => navigate("/products")}
                  />
                ))}
              </div>

              <div className="mt-6 hidden overflow-hidden rounded-[1.5rem] border border-white/10 lg:block">
                <table className="min-w-full table-fixed border-collapse">
                  <thead className="bg-white/[0.04]">
                    <tr className="text-left text-xs uppercase tracking-[0.24em] text-slate-500">
                      <th className="px-5 py-4 font-medium">Product</th>
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
                <AlertCard
                  key={`${alert.product_id}-${alert.created_at}`}
                  alert={alert}
                  onViewProduct={() => navigate("/products")}
                />
              ))
            )}
          </div>
        </article>
      </section>
    </div>
  );
}
