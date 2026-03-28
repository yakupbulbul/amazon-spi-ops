import {
  AlertTriangle,
  Boxes,
  PackageSearch,
  Search,
  X,
} from "lucide-react";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useEffectEvent,
  useMemo,
  useState,
} from "react";

import { useAuth } from "../hooks/useAuth";
import {
  getProducts,
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
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isMutating, setIsMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mutationMessage, setMutationMessage] = useState<string | null>(null);
  const [dialogState, setDialogState] = useState<MutationDialogState | null>(null);
  const [priceInput, setPriceInput] = useState("");
  const [currencyInput, setCurrencyInput] = useState("USD");
  const [stockInput, setStockInput] = useState("");
  const deferredSearchQuery = useDeferredValue(searchQuery);

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

  useEffect(() => {
    let cancelled = false;

    void loadProducts({ cancelled });

    return () => {
      cancelled = true;
    };
  }, [loadProducts, token]);

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

  function openPriceDialog(product: ProductListItem) {
    setMutationMessage(null);
    setDialogState({ type: "price", product });
    setPriceInput(product.price_amount ?? "");
    setCurrencyInput(product.price_currency ?? "USD");
  }

  function openStockDialog(product: ProductListItem) {
    setMutationMessage(null);
    setDialogState({ type: "stock", product });
    setStockInput(String(product.inventory?.available_quantity ?? 0));
  }

  function closeDialog() {
    if (isMutating) {
      return;
    }
    setDialogState(null);
    setPriceInput("");
    setCurrencyInput("USD");
    setStockInput("");
  }

  async function submitMutation() {
    if (!token || !dialogState) {
      return;
    }

    setIsMutating(true);
    setError(null);
    setMutationMessage(null);

    try {
      if (dialogState.type === "price") {
        if (!priceInput || Number(priceInput) <= 0) {
          throw new Error("Price must be greater than zero.");
        }
        const response = await updateProductPrice(token, dialogState.product.id, {
          price_amount: priceInput,
          price_currency: currencyInput.toUpperCase(),
        });
        await loadProducts();
        setMutationMessage(response.message);
      } else {
        const parsedQuantity = Number(stockInput);
        if (!Number.isInteger(parsedQuantity) || parsedQuantity < 0) {
          throw new Error("Quantity must be a whole number greater than or equal to zero.");
        }
        const response = await updateProductStock(token, dialogState.product.id, {
          quantity: parsedQuantity,
        });
        await loadProducts();
        setMutationMessage(response.message);
      }

      setDialogState(null);
    } catch (mutationError) {
      setError(mutationError instanceof Error ? mutationError.message : "Unable to update product.");
    } finally {
      setIsMutating(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(59,130,246,0.18),_rgba(15,23,42,0.95)_42%,_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-xs uppercase tracking-[0.32em] text-sky-100/70">Catalog workspace</p>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
            Seller catalog search with inventory posture and listing identifiers.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            The catalog view now supports price and stock changes with authenticated backend
            mutations, audit logging, and immediate refresh of the local product state.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Visible products</p>
            <p className="mt-4 text-4xl font-semibold text-white">{filteredProducts.length}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Filtered from the local product catalog.</p>
          </article>
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">At or below threshold</p>
            <p className="mt-4 text-4xl font-semibold text-white">{lowStockCount}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Products needing stock attention.</p>
          </article>
        </div>
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
                      className="rounded-full border border-sky-300/20 bg-sky-500/10 px-3 py-1.5 text-xs font-medium text-sky-100 transition hover:bg-sky-500/20"
                    >
                      Edit price
                    </button>
                    <button
                      type="button"
                      onClick={() => openStockDialog(product)}
                      className="rounded-full border border-amber-300/20 bg-amber-400/10 px-3 py-1.5 text-xs font-medium text-amber-100 transition hover:bg-amber-400/20"
                    >
                      Edit stock
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
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/85 backdrop-blur-sm"
            onClick={closeDialog}
            aria-label="Close dialog"
          />
          <section className="relative z-10 w-full max-w-lg rounded-[2rem] border border-white/10 bg-slate-950 p-6 shadow-2xl shadow-black/50">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-500">
                  {dialogState.type === "price" ? "Price update" : "Stock update"}
                </p>
                <h4 className="mt-2 text-2xl font-semibold text-white">{dialogState.product.title}</h4>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  Confirm the new {dialogState.type} for SKU {dialogState.product.sku}. This writes
                  an audit log entry and updates the local state after the backend mutation
                  succeeds.
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

            <div className="mt-6 space-y-5">
              {dialogState.type === "price" ? (
                <>
                  <label className="block space-y-2">
                    <span className="text-sm text-slate-300">Price amount</span>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={priceInput}
                      onChange={(event) => setPriceInput(event.target.value)}
                      className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
                    />
                  </label>
                  <label className="block space-y-2">
                    <span className="text-sm text-slate-300">Currency</span>
                    <input
                      type="text"
                      value={currencyInput}
                      onChange={(event) => setCurrencyInput(event.target.value)}
                      className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm uppercase text-white outline-none"
                    />
                  </label>
                </>
              ) : (
                <label className="block space-y-2">
                  <span className="text-sm text-slate-300">Available quantity</span>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={stockInput}
                    onChange={(event) => setStockInput(event.target.value)}
                    className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
                  />
                </label>
              )}
            </div>

            <div className="mt-6 rounded-[1.25rem] border border-amber-300/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
              Confirming this action will send the mutation through the backend workflow immediately.
            </div>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={closeDialog}
                className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-200 transition hover:bg-white/[0.08]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void submitMutation()}
                disabled={isMutating}
                className="rounded-[1.25rem] bg-amber-300 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isMutating ? "Applying..." : "Confirm update"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
