import {
  AlertTriangle,
  Boxes,
  CloudDownload,
  PencilLine,
  RefreshCcw,
  PackageSearch,
  Search,
  ShoppingBag,
  X,
} from "lucide-react";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useEffectEvent,
  useMemo,
  useRef,
  useState,
} from "react";

import { useAuth } from "../hooks/useAuth";
import {
  createCatalogImportJob,
  getLatestCatalogImportJob,
  getProducts,
  type CatalogImportJob,
  updateProductPrice,
  updateProductStock,
  type ProductListItem,
} from "../lib/api";

const healthBadgeStyles: Record<string, string> = {
  healthy: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200",
  low: "border-amber-400/20 bg-amber-500/10 text-amber-100",
  critical: "border-rose-400/20 bg-rose-500/10 text-rose-100",
  out_of_stock: "border-rose-400/20 bg-rose-500/10 text-rose-100",
};

const marketplaceCurrencyDefaults: Record<string, string> = {
  A1PA6795UKMFR9: "EUR",
  A1F83G8C2ARO7P: "GBP",
  ATVPDKIKX0DER: "USD",
};

function formatCurrency(amount: string | null, currency: string | null): string {
  if (!amount || !currency) {
    return "Unavailable";
  }

  const parsedAmount = Number(amount);
  if (Number.isNaN(parsedAmount)) {
    return `${amount} ${currency}`;
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(parsedAmount);
}

function getAlertLabel(product: ProductListItem): string {
  const status = product.inventory?.alert_status ?? "unknown";
  return status.replaceAll("_", " ");
}

function formatImportStatus(status: string): string {
  return status.replaceAll("_", " ");
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "Not started";
  }

  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getDefaultCurrency(product: ProductListItem): string {
  return product.price_currency ?? marketplaceCurrencyDefaults[product.marketplace_id] ?? "USD";
}

function getDialogTitle(dialogState: MutationDialogState): string {
  return dialogState.type === "price" ? "Change listing price" : "Change available stock";
}

function getDialogIntro(dialogState: MutationDialogState): string {
  return dialogState.type === "price"
    ? "Review the current price, enter the new marketplace price, and save the update to Amazon."
    : "Review the current available quantity, enter the new stock number, and save the update to Amazon.";
}

function getCurrentValueLabel(dialogState: MutationDialogState): string {
  return dialogState.type === "price"
    ? formatCurrency(dialogState.product.price_amount, dialogState.product.price_currency)
    : `${dialogState.product.inventory?.available_quantity ?? 0} units`;
}

function getPendingValueLabel(
  dialogState: MutationDialogState,
  priceInput: string,
  currencyInput: string,
  stockInput: string,
): string {
  if (dialogState.type === "price") {
    return priceInput ? `${currencyInput.trim().toUpperCase()} ${priceInput}` : "Enter a new price";
  }

  return stockInput ? `${stockInput} units` : "Enter a new quantity";
}

type MutationDialogState =
  | {
      type: "price";
      product: ProductListItem;
    }
  | {
      type: "stock";
      product: ProductListItem;
    };

export function ProductsPage() {
  const { token } = useAuth();
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [latestImportJob, setLatestImportJob] = useState<CatalogImportJob | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mutationMessage, setMutationMessage] = useState<string | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [dialogState, setDialogState] = useState<MutationDialogState | null>(null);
  const [priceInput, setPriceInput] = useState("");
  const [currencyInput, setCurrencyInput] = useState("USD");
  const [stockInput, setStockInput] = useState("");
  const deferredSearchQuery = useDeferredValue(searchQuery);
  const latestImportJobRef = useRef<CatalogImportJob | null>(null);

  const loadProducts = useEffectEvent(async ({ cancelled = false }: { cancelled?: boolean } = {}) => {
    if (!token) {
      return;
    }

    try {
      const response = await getProducts(token);
      if (!cancelled) {
        startTransition(() => {
          setProducts(response.items);
          setError(null);
        });
      }
    } catch (loadError) {
      if (!cancelled) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load products.");
      }
    } finally {
      if (!cancelled) {
        setIsLoading(false);
      }
    }
  });

  const loadLatestImportJob = useEffectEvent(
    async ({ cancelled = false }: { cancelled?: boolean } = {}) => {
      if (!token) {
        return;
      }

      try {
        const response = await getLatestCatalogImportJob(token);
        if (!cancelled) {
          const previousJob = latestImportJobRef.current;
          latestImportJobRef.current = response;
          startTransition(() => {
            setLatestImportJob(response);
          });

          if (
            response &&
            response.status === "succeeded" &&
            (previousJob?.id !== response.id || previousJob.status !== "succeeded")
          ) {
            await loadProducts();
          }
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load import status.");
        }
      }
    },
  );

  useEffect(() => {
    let cancelled = false;

    void loadProducts({ cancelled });
    void loadLatestImportJob({ cancelled });

    return () => {
      cancelled = true;
    };
  }, [loadLatestImportJob, loadProducts, token]);

  useEffect(() => {
    if (!token || !latestImportJob || !["pending", "running"].includes(latestImportJob.status)) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void loadLatestImportJob();
    }, 4000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [latestImportJob, loadLatestImportJob, token]);

  const filteredProducts = useMemo(() => {
    const normalizedQuery = deferredSearchQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return products;
    }

    return products.filter((product) =>
      [
        product.title,
        product.sku,
        product.asin,
        product.brand ?? "",
        product.marketplace_id,
      ]
        .join(" ")
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [deferredSearchQuery, products]);

  const lowStockCount = filteredProducts.filter((product) => {
    const availableQuantity = product.inventory?.available_quantity ?? 0;
    return availableQuantity <= product.low_stock_threshold;
  }).length;

  const importButtonLabel = latestImportJob
    ? latestImportJob.status === "pending" || latestImportJob.status === "running"
      ? "Import running..."
      : "Refresh Amazon Catalog"
    : "Import from Amazon";

  const isImportActive = latestImportJob
    ? latestImportJob.status === "pending" || latestImportJob.status === "running"
    : false;

  function openPriceDialog(product: ProductListItem) {
    setMutationMessage(null);
    setDialogError(null);
    setDialogState({ type: "price", product });
    setPriceInput(product.price_amount ?? "");
    setCurrencyInput(getDefaultCurrency(product));
  }

  function openStockDialog(product: ProductListItem) {
    setMutationMessage(null);
    setDialogError(null);
    setDialogState({ type: "stock", product });
    setStockInput(String(product.inventory?.available_quantity ?? 0));
  }

  function closeDialog() {
    if (isMutating) {
      return;
    }
    setDialogState(null);
    setDialogError(null);
    setPriceInput("");
    setCurrencyInput("USD");
    setStockInput("");
  }

  async function triggerCatalogImport() {
    if (!token || isImporting || isImportActive) {
      return;
    }

    setIsImporting(true);
    setError(null);
    setMutationMessage(null);

    try {
      const job = await createCatalogImportJob(token);
      latestImportJobRef.current = job;
      setLatestImportJob(job);
      setMutationMessage("Amazon catalog import started. The page will refresh when the job completes.");
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Unable to start Amazon import.");
    } finally {
      setIsImporting(false);
    }
  }

  async function submitMutation() {
    if (!token || !dialogState) {
      return;
    }

    setIsMutating(true);
    setError(null);
    setDialogError(null);
    setMutationMessage(null);

    try {
      if (dialogState.type === "price") {
        const normalizedAmount = Number(priceInput);
        const normalizedCurrency = currencyInput.trim().toUpperCase();

        if (!priceInput || Number.isNaN(normalizedAmount) || normalizedAmount <= 0) {
          throw new Error("Price must be greater than zero.");
        }
        if (!/^[A-Z]{3}$/.test(normalizedCurrency)) {
          throw new Error("Currency must be a 3-letter ISO code such as EUR or USD.");
        }
        if (
          dialogState.product.price_amount === priceInput &&
          dialogState.product.price_currency === normalizedCurrency
        ) {
          setMutationMessage(`No price change was applied for ${dialogState.product.sku}.`);
          setDialogState(null);
          return;
        }

        const response = await updateProductPrice(token, dialogState.product.id, {
          price_amount: priceInput,
          price_currency: normalizedCurrency,
        });
        await loadProducts();
        setMutationMessage(response.message);
      } else {
        const parsedQuantity = Number(stockInput);
        if (!Number.isInteger(parsedQuantity) || parsedQuantity < 0) {
          throw new Error("Quantity must be a whole number greater than or equal to zero.");
        }
        if ((dialogState.product.inventory?.available_quantity ?? 0) === parsedQuantity) {
          setMutationMessage(`No stock change was applied for ${dialogState.product.sku}.`);
          setDialogState(null);
          return;
        }

        const response = await updateProductStock(token, dialogState.product.id, {
          quantity: parsedQuantity,
        });
        await loadProducts();
        setMutationMessage(response.message);
      }

      setDialogState(null);
    } catch (mutationError) {
      setDialogError(
        mutationError instanceof Error ? mutationError.message : "Unable to update product.",
      );
    } finally {
      setIsMutating(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(59,130,246,0.18),_rgba(15,23,42,0.95)_42%,_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-xs uppercase tracking-[0.32em] text-sky-100/70">Amazon catalog mirror</p>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
            Import live seller listings and manage the mirrored catalog from one workspace.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            The products view now imports real Amazon listings, tracks the latest import job, and
            keeps price and stock mutations available for mirrored catalog items.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Visible products</p>
            <p className="mt-4 text-4xl font-semibold text-white">{filteredProducts.length}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Filtered from the mirrored Amazon catalog.</p>
          </article>
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Latest import status</p>
            <p className="mt-4 text-2xl font-semibold capitalize text-white">
              {latestImportJob ? formatImportStatus(latestImportJob.status) : "Not started"}
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              {latestImportJob
                ? `${latestImportJob.processed_count} processed${latestImportJob.total_expected ? ` of ${latestImportJob.total_expected}` : ""}.`
                : "Run the first Amazon import to replace the sample catalog."}
            </p>
          </article>
        </div>
      </section>

      <section className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Import control</p>
            <h3 className="mt-2 text-xl font-semibold text-white">Amazon listings sync</h3>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Import all seller listings for marketplace {latestImportJob?.marketplace_id ?? "A1PA6795UKMFR9"}.
              The job runs in the background and the catalog refreshes automatically when it finishes.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void triggerCatalogImport()}
            disabled={isImporting || isImportActive}
            className="inline-flex items-center justify-center gap-2 rounded-[1.25rem] bg-amber-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isImportActive ? <RefreshCcw className="h-4 w-4 animate-spin" /> : <CloudDownload className="h-4 w-4" />}
            <span>{isImporting ? "Queueing import..." : importButtonLabel}</span>
          </button>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <article className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Job</p>
            <p className="mt-3 text-base font-medium capitalize text-white">
              {latestImportJob ? formatImportStatus(latestImportJob.status) : "Awaiting first import"}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Started {formatTimestamp(latestImportJob?.started_at ?? latestImportJob?.created_at ?? null)}
            </p>
          </article>
          <article className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Processed</p>
            <p className="mt-3 text-3xl font-semibold text-white">
              {latestImportJob?.processed_count ?? 0}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              {latestImportJob?.total_expected
                ? `Target ${latestImportJob.total_expected} listings`
                : "Total estimate available after the first page"}
            </p>
          </article>
          <article className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Created / Updated</p>
            <p className="mt-3 text-3xl font-semibold text-white">
              {(latestImportJob?.created_count ?? 0) + (latestImportJob?.updated_count ?? 0)}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              {latestImportJob?.created_count ?? 0} created, {latestImportJob?.updated_count ?? 0} updated
            </p>
          </article>
          <article className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Low stock</p>
            <p className="mt-3 text-3xl font-semibold text-white">{lowStockCount}</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">Products at or below threshold.</p>
          </article>
        </div>

        {latestImportJob?.error_message ? (
          <div className="mt-4 flex items-start gap-3 rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 p-4 text-sm text-rose-100">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{latestImportJob.error_message}</span>
          </div>
        ) : null}
      </section>

      <section className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Catalog query</p>
            <h3 className="mt-2 text-xl font-semibold text-white">Products</h3>
          </div>
          <label className="flex w-full items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 lg:max-w-md">
            <Search className="h-4 w-4 text-slate-500" />
            <input
              type="search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search by SKU, ASIN, brand, or title"
              className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
            />
          </label>
        </div>

        {isLoading ? (
          <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-6 text-sm text-slate-300">
            Loading product catalog...
          </div>
        ) : error ? (
          <div className="mt-6 flex items-start gap-3 rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 p-6 text-sm text-rose-100">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] px-6 py-12 text-center">
            <PackageSearch className="mx-auto h-10 w-10 text-slate-500" />
            <h4 className="mt-4 text-lg font-medium text-white">No products match this search.</h4>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Try a SKU, ASIN, brand name, or clear the filter to see the full catalog.
            </p>
          </div>
        ) : (
          <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-white/10">
            <div className="hidden grid-cols-[minmax(0,2fr)_minmax(0,1fr)_120px_120px_140px_150px_180px] gap-4 border-b border-white/10 bg-white/[0.04] px-5 py-4 text-xs uppercase tracking-[0.24em] text-slate-500 lg:grid">
              <span>Product</span>
              <span>Identifiers</span>
              <span>Price</span>
              <span>Available</span>
              <span>Inbound</span>
              <span>Stock health</span>
              <span>Actions</span>
            </div>

            <div className="divide-y divide-white/10">
              {filteredProducts.map((product) => (
                <article
                  key={product.id}
                  className="grid gap-5 px-5 py-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_120px_120px_140px_150px_180px] lg:items-center"
                >
                  <div className="min-w-0">
                    <p className="truncate text-base font-medium text-white">{product.title}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span className="rounded-full border border-white/10 px-2.5 py-1">
                        {product.brand ?? "Unbranded"}
                      </span>
                      <span className="rounded-full border border-white/10 px-2.5 py-1 capitalize">
                        {product.source.replaceAll("_", " ")}
                      </span>
                      <span className="rounded-full border border-white/10 px-2.5 py-1">
                        Threshold {product.low_stock_threshold}
                      </span>
                      <span className="rounded-full border border-white/10 px-2.5 py-1">
                        {product.marketplace_id}
                      </span>
                    </div>
                  </div>

                  <div className="grid gap-2 text-sm text-slate-300">
                    <div>
                      <span className="text-slate-500">SKU</span>
                      <p className="font-mono text-xs text-slate-100">{product.sku}</p>
                    </div>
                    <div>
                      <span className="text-slate-500">ASIN</span>
                      <p className="font-mono text-xs text-slate-100">{product.asin}</p>
                    </div>
                  </div>

                  <div className="text-sm text-slate-100">
                    {formatCurrency(product.price_amount, product.price_currency)}
                  </div>

                  <div className="flex items-center gap-2 text-sm text-slate-100">
                    <Boxes className="h-4 w-4 text-slate-500" />
                    <span>{product.inventory?.available_quantity ?? 0}</span>
                  </div>

                  <div className="text-sm text-slate-100">
                    {product.inventory?.inbound_quantity ?? 0}
                    <span className="ml-2 text-xs text-slate-500">
                      reserved {product.inventory?.reserved_quantity ?? 0}
                    </span>
                  </div>

                  <div>
                    <span
                      className={[
                        "inline-flex rounded-full border px-3 py-1 text-xs font-medium capitalize",
                        healthBadgeStyles[product.inventory?.alert_status ?? "critical"] ??
                          healthBadgeStyles.critical,
                      ].join(" ")}
                    >
                      {getAlertLabel(product)}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => openPriceDialog(product)}
                      className="inline-flex items-center gap-2 rounded-full border border-sky-300/20 bg-sky-500/10 px-3 py-1.5 text-xs font-medium text-sky-100 transition hover:bg-sky-500/20"
                    >
                      <PencilLine className="h-3.5 w-3.5" />
                      Change price
                    </button>
                    <button
                      type="button"
                      onClick={() => openStockDialog(product)}
                      className="inline-flex items-center gap-2 rounded-full border border-amber-300/20 bg-amber-400/10 px-3 py-1.5 text-xs font-medium text-amber-100 transition hover:bg-amber-400/20"
                    >
                      <ShoppingBag className="h-3.5 w-3.5" />
                      Change stock
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}
      </section>

      {mutationMessage ? (
        <section className="rounded-[1.5rem] border border-emerald-400/20 bg-emerald-500/10 px-5 py-4 text-sm text-emerald-100">
          {mutationMessage}
        </section>
      ) : null}

      {dialogState ? (
        <div className="fixed inset-0 z-50 flex justify-end">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/85 backdrop-blur-sm"
            onClick={closeDialog}
            aria-label="Close dialog"
          />
          <section className="relative z-10 flex h-full w-full max-w-2xl flex-col border-l border-white/10 bg-slate-950 shadow-2xl shadow-black/50">
            <div className="border-b border-white/10 bg-[linear-gradient(135deg,_rgba(245,158,11,0.14),_rgba(15,23,42,0.96)_35%,_rgba(2,6,23,1)_100%)] px-5 py-5 sm:px-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-slate-400">
                    {dialogState.type === "price" ? "Listing price editor" : "Available stock editor"}
                  </p>
                  <h4 className="mt-2 text-2xl font-semibold text-white">
                    {getDialogTitle(dialogState)}
                  </h4>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    {getDialogIntro(dialogState)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={closeDialog}
                  className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10"
                  aria-label="Close dialog"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-6">
              <div className="grid gap-3 rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4 sm:grid-cols-2">
                <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Product</p>
                  <p className="mt-2 text-sm font-medium text-white">{dialogState.product.title}</p>
                  <p className="mt-2 text-xs text-slate-400">
                    SKU {dialogState.product.sku}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    ASIN {dialogState.product.asin}
                  </p>
                </div>
                <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Marketplace</p>
                  <p className="mt-2 text-sm font-medium text-white">
                    {dialogState.product.marketplace_id}
                  </p>
                  <p className="mt-2 text-xs text-slate-400">
                    Current value
                  </p>
                  <p className="mt-1 text-lg font-semibold text-white">
                    {getCurrentValueLabel(dialogState)}
                  </p>
                </div>
              </div>

              <form
                className="mt-6"
                onSubmit={(event) => {
                  event.preventDefault();
                  void submitMutation();
                }}
              >
                <div className="rounded-[1.25rem] border border-sky-300/15 bg-sky-500/10 px-4 py-3 text-sm leading-6 text-sky-100">
                  Step 1: update the value below.
                  <br />
                  Step 2: review the "New value to save" box.
                  <br />
                  Step 3: click the save button at the bottom of this panel.
                </div>

                <div className="mt-6 space-y-5">
                  {dialogState.type === "price" ? (
                    <>
                      <label className="block space-y-2">
                        <span className="text-sm text-slate-300">New price amount</span>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={priceInput}
                          onChange={(event) => setPriceInput(event.target.value)}
                          className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-base text-white outline-none"
                        />
                      </label>
                      <label className="block space-y-2">
                        <span className="text-sm text-slate-300">Currency code</span>
                        <input
                          type="text"
                          value={currencyInput}
                          onChange={(event) => setCurrencyInput(event.target.value)}
                          maxLength={3}
                          className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-base uppercase text-white outline-none"
                        />
                        <p className="text-xs text-slate-500">
                          Defaults from the product marketplace when no saved currency exists yet.
                        </p>
                      </label>
                    </>
                  ) : (
                    <label className="block space-y-2">
                      <span className="text-sm text-slate-300">New available quantity</span>
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={stockInput}
                        onChange={(event) => setStockInput(event.target.value)}
                        className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-base text-white outline-none"
                      />
                    </label>
                  )}
                </div>

                <div className="mt-6 rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">New value to save</p>
                  <p className="mt-2 text-xl font-semibold text-white">
                    {getPendingValueLabel(dialogState, priceInput, currencyInput, stockInput)}
                  </p>
                </div>

                {dialogError ? (
                  <div className="mt-6 flex items-start gap-3 rounded-[1.25rem] border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{dialogError}</span>
                  </div>
                ) : null}

                <div className="mt-6 rounded-[1.25rem] border border-amber-300/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
                  Save will send this change to the backend immediately and record an audit log.
                </div>

                <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                  <button
                    type="button"
                    onClick={closeDialog}
                    className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-200 transition hover:bg-white/[0.08]"
                  >
                    Close panel
                  </button>
                  <button
                    type="submit"
                    disabled={isMutating}
                    className="rounded-[1.25rem] bg-amber-300 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {isMutating
                      ? "Saving..."
                      : dialogState.type === "price"
                        ? "Save price change"
                        : "Save stock change"}
                  </button>
                </div>
              </form>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
