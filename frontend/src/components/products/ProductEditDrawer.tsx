import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, X } from "lucide-react";

import type { ProductListItem } from "../../lib/api";

type ProductEditDrawerProps = {
  product: ProductListItem;
  type: "price" | "stock";
  isMutating: boolean;
  dialogError: string | null;
  title: string;
  intro: string;
  currentValueLabel: string;
  pendingValueLabel: string;
  priceInput: string;
  currencyInput: string;
  stockInput: string;
  onPriceChange: (value: string) => void;
  onCurrencyChange: (value: string) => void;
  onStockChange: (value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
  returnFocusTo: HTMLElement | null;
};

export function ProductEditDrawer({
  product,
  type,
  isMutating,
  dialogError,
  title,
  intro,
  currentValueLabel,
  pendingValueLabel,
  priceInput,
  currencyInput,
  stockInput,
  onPriceChange,
  onCurrencyChange,
  onStockChange,
  onClose,
  onSubmit,
  returnFocusTo,
}: ProductEditDrawerProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const firstInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const previousPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;

    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }

    const focusFrame = window.requestAnimationFrame(() => {
      firstInputRef.current?.focus();
      firstInputRef.current?.select();
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab" || !panelRef.current) {
        return;
      }

      const focusableElements = panelRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );

      if (focusableElements.length === 0) {
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      document.body.style.paddingRight = previousPaddingRight;
      returnFocusTo?.focus();
    };
  }, [onClose, returnFocusTo]);

  return createPortal(
    <div className="fixed inset-0 z-[100]">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Close dialog"
      />

      <div className="absolute inset-0 flex items-end justify-end sm:items-stretch">
        <section
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="product-edit-drawer-title"
          className="relative z-10 flex h-[100dvh] w-full flex-col overflow-hidden border-white/10 bg-slate-950 shadow-2xl shadow-black/50 sm:max-w-2xl sm:border-l"
        >
          <div className="border-b border-white/10 bg-[linear-gradient(135deg,_rgba(245,158,11,0.14),_rgba(15,23,42,0.96)_35%,_rgba(2,6,23,1)_100%)] px-5 py-5 sm:px-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-400">
                  {type === "price" ? "Listing price editor" : "Available stock editor"}
                </p>
                <h4 id="product-edit-drawer-title" className="mt-2 text-2xl font-semibold text-white">
                  {title}
                </h4>
                <p className="mt-2 text-sm leading-6 text-slate-300">{intro}</p>
              </div>
              <button
                type="button"
                onClick={onClose}
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
                <p className="mt-2 text-sm font-medium text-white">{product.title}</p>
                <p className="mt-2 text-xs text-slate-400">SKU {product.sku}</p>
                <p className="mt-1 text-xs text-slate-400">ASIN {product.asin}</p>
              </div>
              <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Marketplace</p>
                <p className="mt-2 text-sm font-medium text-white">{product.marketplace_id}</p>
                <p className="mt-2 text-xs text-slate-400">Current value</p>
                <p className="mt-1 text-lg font-semibold text-white">{currentValueLabel}</p>
              </div>
            </div>

            <form
              className="mt-6"
              onSubmit={(event) => {
                event.preventDefault();
                onSubmit();
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
                {type === "price" ? (
                  <>
                    <label className="block space-y-2">
                      <span className="text-sm text-slate-300">New price amount</span>
                      <input
                        ref={firstInputRef}
                        type="number"
                        min="0"
                        step="0.01"
                        value={priceInput}
                        onChange={(event) => onPriceChange(event.target.value)}
                        className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-base text-white outline-none"
                      />
                    </label>
                    <label className="block space-y-2">
                      <span className="text-sm text-slate-300">Currency code</span>
                      <input
                        type="text"
                        value={currencyInput}
                        onChange={(event) => onCurrencyChange(event.target.value)}
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
                      ref={firstInputRef}
                      type="number"
                      min="0"
                      step="1"
                      value={stockInput}
                      onChange={(event) => onStockChange(event.target.value)}
                      className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-base text-white outline-none"
                    />
                  </label>
                )}
              </div>

              <div className="mt-6 rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">New value to save</p>
                <p className="mt-2 text-xl font-semibold text-white">{pendingValueLabel}</p>
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
                  onClick={onClose}
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
                    : type === "price"
                      ? "Save price change"
                      : "Save stock change"}
                </button>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>,
    document.body,
  );
}
