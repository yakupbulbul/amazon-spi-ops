import { FileStack, Layers3, MonitorSmartphone, Package2, X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import type { AplusAsset, AplusDraftPayload, AplusLanguage, AplusModulePayload } from "../../lib/api";
import { AplusAmazonPreview } from "./AplusAmazonPreview";
import { formatLanguageLabel } from "./languages";
import {
  moduleHasUnsupportedPublishImageConfig,
  moduleIsEditorialOnly,
  moduleIsRealPublishSupported,
  moduleSupportsPublishOverlay,
  resolveModulePublishableImageUrl,
} from "./previewImage";

type AplusPreviewModalProps = {
  draft: AplusDraftPayload;
  language: AplusLanguage;
  assets: AplusAsset[];
  variantLabel?: string;
  productTitle?: string | null;
  onClose: () => void;
  returnFocusTo: HTMLElement | null;
};

type PreviewMode = "device" | "stack";

export function AplusPreviewModal({
  draft,
  language,
  assets,
  variantLabel,
  productTitle,
  onClose,
  returnFocusTo,
}: AplusPreviewModalProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const [mode, setMode] = useState<PreviewMode>("device");

  const publishableModules = draft.modules.filter((module) => moduleIsRealPublishSupported(module.module_type));
  const editorialModules = draft.modules.filter((module) => moduleIsEditorialOnly(module.module_type));

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const previousPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;

    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }

    const focusFrame = window.requestAnimationFrame(() => {
      closeButtonRef.current?.focus();
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab" || !dialogRef.current) {
        return;
      }

      const focusableElements = dialogRef.current.querySelectorAll<HTMLElement>(
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
    <div className="fixed inset-0 z-[120]">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/85 backdrop-blur-sm"
        onClick={onClose}
        aria-label="Close preview"
      />

      <div className="absolute inset-0 flex items-end justify-center p-0 sm:items-center sm:p-6">
        <section
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="aplus-preview-title"
          className="relative z-10 flex h-[100dvh] w-full flex-col overflow-hidden border-white/10 bg-slate-950 shadow-2xl shadow-black/50 sm:h-[92vh] sm:max-h-[980px] sm:max-w-[1400px] sm:rounded-[2rem] sm:border"
        >
          <div className="border-b border-white/10 bg-[linear-gradient(135deg,_rgba(245,158,11,0.14),_rgba(15,23,42,0.98)_28%,_rgba(2,6,23,1)_100%)] px-5 py-5 sm:px-6">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
              <div className="min-w-0 flex-1">
                <p className="text-xs uppercase tracking-[0.28em] text-slate-400">A+ preview</p>
                <h3 id="aplus-preview-title" className="mt-2 text-2xl font-semibold text-white">
                  Preview A+ layout
                </h3>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                  This preview now follows the active draft variant and the real publish subset already
                  supported by the backend. Publishable modules stay centered, while editorial-only modules
                  are clearly separated instead of mixed into the live layout.
                </p>

                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <PreviewStatCard
                    icon={<Package2 className="h-4 w-4" />}
                    label="Product"
                    value={productTitle ?? "Current draft"}
                  />
                  <PreviewStatCard
                    icon={<Layers3 className="h-4 w-4" />}
                    label="Active variant"
                    value={variantLabel ?? `Current (${formatLanguageLabel(language)})`}
                  />
                  <PreviewStatCard
                    icon={<MonitorSmartphone className="h-4 w-4" />}
                    label="Live publish subset"
                    value={`${publishableModules.length} module${publishableModules.length === 1 ? "" : "s"}`}
                  />
                  <PreviewStatCard
                    icon={<FileStack className="h-4 w-4" />}
                    label="Editorial only"
                    value={`${editorialModules.length} module${editorialModules.length === 1 ? "" : "s"}`}
                    tone={editorialModules.length > 0 ? "warning" : "default"}
                  />
                </div>

                <div className="mt-4 rounded-[1rem] border border-amber-300/15 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-amber-100">
                  The device mock and module stack now prioritize the real Amazon request shape: hero,
                  feature, and faq modules. Unsupported editorial modules stay visible in a separate
                  section so the preview no longer overstates live publish fidelity.
                </div>
              </div>

              <div className="flex items-center gap-3 self-start">
                <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-300">
                  {formatLanguageLabel(language)}
                </span>
                <button
                  ref={closeButtonRef}
                  type="button"
                  onClick={onClose}
                  className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-slate-100 transition hover:bg-white/10"
                  aria-label="Close preview"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              <PreviewModeButton
                active={mode === "device"}
                label="Device mock"
                icon={<MonitorSmartphone className="h-4 w-4" />}
                onClick={() => setMode("device")}
              />
              <PreviewModeButton
                active={mode === "stack"}
                label="Module stack"
                icon={<FileStack className="h-4 w-4" />}
                onClick={() => setMode("stack")}
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-6">
            {mode === "device" ? (
              <AplusAmazonPreview draft={draft} language={language} assets={assets} />
            ) : (
              <AplusModuleStackPreview draft={draft} language={language} assets={assets} />
            )}
          </div>
        </section>
      </div>
    </div>,
    document.body,
  );
}

function PreviewModeButton({
  active,
  label,
  icon,
  onClick,
}: {
  active: boolean;
  label: string;
  icon: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition",
        active
          ? "border-amber-300/20 bg-amber-300 text-slate-950"
          : "border-white/10 bg-white/[0.04] text-slate-200 hover:bg-white/[0.08]",
      ].join(" ")}
    >
      {icon}
      {label}
    </button>
  );
}

function PreviewStatCard({
  icon,
  label,
  value,
  tone = "default",
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone?: "default" | "warning";
}) {
  return (
    <div
      className={[
        "rounded-[1rem] border px-4 py-3",
        tone === "warning"
          ? "border-amber-300/15 bg-amber-500/10"
          : "border-white/10 bg-white/[0.04]",
      ].join(" ")}
    >
      <div className="flex items-center gap-2 text-slate-400">
        {icon}
        <span className="text-xs uppercase tracking-[0.18em]">{label}</span>
      </div>
      <p className="mt-2 text-sm font-medium text-white">{value}</p>
    </div>
  );
}

function AplusModuleStackPreview({
  draft,
  language,
  assets,
}: {
  draft: AplusDraftPayload;
  language: AplusLanguage;
  assets: AplusAsset[];
}) {
  const publishableModules = draft.modules.filter((module) => moduleIsRealPublishSupported(module.module_type));
  const editorialModules = draft.modules.filter((module) => moduleIsEditorialOnly(module.module_type));

  return (
    <div className="mx-auto max-w-5xl space-y-4 rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.84),rgba(2,6,23,0.96))] p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-900">
          Amazon module stack
        </span>
        <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-300">
          {formatLanguageLabel(language)}
        </span>
        <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-100">
          {publishableModules.length} publishable
        </span>
        {editorialModules.length > 0 ? (
          <span className="rounded-full border border-amber-300/20 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-100">
            {editorialModules.length} editorial only
          </span>
        ) : null}
      </div>

      <section className="rounded-[1.5rem] bg-white p-5 text-slate-900 shadow-lg shadow-black/10 sm:p-6">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Hero</p>
        <h4 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight">{draft.headline}</h4>
        <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">{draft.subheadline}</p>
      </section>

      <section className="grid gap-3 lg:grid-cols-3">
        {draft.key_features.map((feature) => (
          <div
            key={feature}
            className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-4 text-sm leading-6 text-slate-200"
          >
            {feature}
          </div>
        ))}
      </section>

      <section className="space-y-4">
        {publishableModules.map((module) => (
          <article
            key={module.module_id}
            className="grid gap-4 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4 lg:grid-cols-[220px_minmax(0,1fr)]"
          >
            <div className="rounded-[1.1rem] bg-[linear-gradient(135deg,rgba(226,232,240,0.2),rgba(248,250,252,0.06))] p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">{module.module_type}</p>
              <div className="mt-3 overflow-hidden rounded-[1rem] border border-white/10 bg-slate-950/60">
                {resolveModulePublishableImageUrl(module, assets) ? (
                  <img
                    src={resolveModulePublishableImageUrl(module, assets) ?? undefined}
                    alt={module.image_brief}
                    className="aspect-[4/3] h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex aspect-[4/3] items-center justify-center px-4 text-center text-sm leading-6 text-slate-500">
                    {moduleHasUnsupportedPublishImageConfig(module)
                      ? "This module publishes without the selected Studio image."
                      : module.image_brief}
                  </div>
                )}
              </div>
              {module.overlay_text &&
              resolveModulePublishableImageUrl(module, assets) &&
              moduleSupportsPublishOverlay(module.module_type) ? (
                <div className="mt-3 rounded-full bg-white/[0.06] px-3 py-2 text-xs text-slate-200">
                  Overlay: {module.overlay_text}
                </div>
              ) : null}
            </div>

            <div>
              <h5 className="text-xl font-semibold text-white">{module.headline}</h5>
              <p className="mt-3 text-sm leading-7 text-slate-300">{module.body}</p>
              {module.bullets.length > 0 ? (
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {module.bullets.map((bullet) => (
                    <div
                      key={bullet}
                      className="rounded-[1rem] border border-white/10 bg-slate-950/60 px-3 py-3 text-sm leading-6 text-slate-200"
                    >
                      {bullet}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </article>
        ))}
      </section>

      {editorialModules.length > 0 ? (
        <section className="rounded-[1.5rem] border border-amber-300/15 bg-amber-500/10 p-4 sm:p-5">
          <p className="text-xs uppercase tracking-[0.22em] text-amber-100/80">Editorial-only modules</p>
          <p className="mt-2 text-sm leading-6 text-amber-100">
            These modules are kept in the working draft for editing, but they are not part of the live Amazon publish subset yet.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {editorialModules.map((module) => (
              <EditorialModuleCard key={module.module_id} module={module} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

function EditorialModuleCard({ module }: { module: AplusModulePayload }) {
  return (
    <article className="rounded-[1rem] border border-amber-300/15 bg-slate-950/35 p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-amber-100/70">{module.module_type}</p>
      <h5 className="mt-2 text-base font-semibold text-white">{module.headline}</h5>
      <p className="mt-2 text-sm leading-6 text-slate-300">{module.body}</p>
    </article>
  );
}
