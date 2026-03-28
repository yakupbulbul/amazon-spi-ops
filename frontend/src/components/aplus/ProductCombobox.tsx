import { BadgeInfo, Check, ChevronsUpDown, Search } from "lucide-react";
import {
  Fragment,
  useDeferredValue,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";

import type { ProductListItem } from "../../lib/api";

type ProductComboboxProps = {
  products: ProductListItem[];
  selectedProduct: ProductListItem | null;
  onSelect: (product: ProductListItem) => void;
  disabled?: boolean;
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function HighlightedText({ text, query }: { text: string; query: string }) {
  if (!query.trim()) {
    return <>{text}</>;
  }

  const pattern = new RegExp(`(${escapeRegExp(query.trim())})`, "ig");
  return (
    <>
      {text.split(pattern).map((part, index) =>
        pattern.test(part) ? (
          <mark key={`${part}-${index}`} className="rounded bg-amber-300/30 px-0.5 text-amber-50">
            {part}
          </mark>
        ) : (
          <Fragment key={`${part}-${index}`}>{part}</Fragment>
        ),
      )}
    </>
  );
}

export function ProductCombobox({
  products,
  selectedProduct,
  onSelect,
  disabled = false,
}: ProductComboboxProps) {
  const inputId = useId();
  const listboxId = useId();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const deferredQuery = useDeferredValue(query);

  const filteredProducts = useMemo(() => {
    const normalizedQuery = deferredQuery.trim().toLowerCase();
    const results = !normalizedQuery
      ? products
      : products.filter((product) =>
          [
            product.sku,
            product.asin,
            product.title,
            product.brand ?? "",
            product.marketplace_id,
          ]
            .join(" ")
            .toLowerCase()
            .includes(normalizedQuery),
        );

    return results.slice(0, 80);
  }, [deferredQuery, products]);

  useEffect(() => {
    setActiveIndex(0);
  }, [deferredQuery]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, []);

  function handleSelect(product: ProductListItem) {
    onSelect(product);
    setQuery("");
    setIsOpen(false);
    inputRef.current?.blur();
  }

  return (
    <div ref={rootRef} className="space-y-3">
      <div className="space-y-1">
        <label htmlFor={inputId} className="block text-sm font-medium text-slate-200">
          Product
        </label>
        <p className="text-xs leading-5 text-slate-500">
          Search by SKU, ASIN, title, or brand to find the right listing quickly.
        </p>
      </div>

      <div className="relative">
        <div className="flex items-center gap-3 rounded-[1.25rem] border border-white/10 bg-slate-950/70 px-4 py-3 transition focus-within:border-sky-300/30 focus-within:bg-slate-950">
          <Search className="h-4 w-4 text-slate-500" />
          <input
            id={inputId}
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={isOpen}
            aria-controls={listboxId}
            aria-autocomplete="list"
            value={query}
            disabled={disabled}
            onFocus={() => setIsOpen(true)}
            onChange={(event) => {
              setQuery(event.target.value);
              setIsOpen(true);
            }}
            onKeyDown={(event) => {
              if (!filteredProducts.length) {
                if (event.key === "Escape") {
                  setIsOpen(false);
                }
                return;
              }

              if (event.key === "ArrowDown") {
                event.preventDefault();
                setIsOpen(true);
                setActiveIndex((currentIndex) => Math.min(currentIndex + 1, filteredProducts.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setIsOpen(true);
                setActiveIndex((currentIndex) => Math.max(currentIndex - 1, 0));
              } else if (event.key === "Enter" && isOpen) {
                event.preventDefault();
                handleSelect(filteredProducts[activeIndex] ?? filteredProducts[0]);
              } else if (event.key === "Escape") {
                setIsOpen(false);
              }
            }}
            placeholder="Search by SKU, ASIN, title, or brand"
            className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500 disabled:cursor-not-allowed"
          />
          <ChevronsUpDown className="h-4 w-4 text-slate-500" />
        </div>

        {isOpen ? (
          <div
            id={listboxId}
            role="listbox"
            className="absolute left-0 right-0 top-[calc(100%+0.5rem)] z-20 max-h-80 overflow-y-auto rounded-[1.5rem] border border-white/10 bg-slate-950/95 p-2 shadow-2xl shadow-black/40 backdrop-blur"
          >
            {filteredProducts.length === 0 ? (
              <div className="rounded-[1.25rem] px-4 py-5 text-sm text-slate-400">
                No products match that search.
              </div>
            ) : (
              filteredProducts.map((product, index) => {
                const isSelected = selectedProduct?.id === product.id;
                const isActive = index === activeIndex;

                return (
                  <button
                    key={product.id}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => handleSelect(product)}
                    className={[
                      "flex w-full items-start justify-between gap-3 rounded-[1.25rem] px-4 py-3 text-left transition",
                      isActive ? "bg-white/[0.08]" : "hover:bg-white/[0.05]",
                    ].join(" ")}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-white">
                        <HighlightedText text={product.title} query={query} />
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        <HighlightedText text={`SKU ${product.sku}`} query={query} />
                        <span className="mx-2">·</span>
                        <HighlightedText text={`ASIN ${product.asin}`} query={query} />
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        <HighlightedText
                          text={`${product.brand ?? "Unbranded"} · ${product.marketplace_id}`}
                          query={query}
                        />
                      </p>
                    </div>
                    {isSelected ? <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /> : null}
                  </button>
                );
              })
            )}
          </div>
        ) : null}
      </div>

      <div className="rounded-[1.5rem] bg-white/[0.03] px-4 py-4">
        <div className="flex items-center gap-2 text-slate-400">
          <BadgeInfo className="h-4 w-4" />
          <p className="text-xs uppercase tracking-[0.22em]">Selected product</p>
        </div>
        {selectedProduct ? (
          <>
            <p className="mt-3 text-sm font-medium leading-6 text-white">{selectedProduct.title}</p>
            <p className="mt-2 text-xs text-slate-500">
              {selectedProduct.brand ?? "Unbranded"} · {selectedProduct.marketplace_id}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              SKU {selectedProduct.sku} <span className="mx-2 text-slate-600">•</span> ASIN {selectedProduct.asin}
            </p>
          </>
        ) : (
          <p className="mt-2 text-sm text-slate-400">Choose a product from the catalog search.</p>
        )}
      </div>
    </div>
  );
}
