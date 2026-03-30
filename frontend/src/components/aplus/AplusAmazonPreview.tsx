import {
  Check,
  ImageIcon,
  ImageOff,
  Info,
  MessageSquareQuote,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import type {
  AplusAsset,
  AplusDraftPayload,
  AplusLanguage,
  AplusModulePayload,
} from "../../lib/api";
import { formatLanguageLabel } from "./languages";
import {
  moduleHasUnsupportedPublishImageConfig,
  moduleIsEditorialOnly,
  moduleIsRealPublishSupported,
  moduleSupportsPublishImage,
  moduleSupportsPublishOverlay,
  resolveModulePublishableImageUrl,
} from "./previewImage";

type AplusAmazonPreviewProps = {
  draft: AplusDraftPayload;
  language: AplusLanguage;
  assets?: AplusAsset[];
};

const twoLineClampStyle = {
  display: "-webkit-box",
  WebkitLineClamp: 2,
  WebkitBoxOrient: "vertical" as const,
  overflow: "hidden",
};

export function AplusAmazonPreview({ draft, language, assets = [] }: AplusAmazonPreviewProps) {
  const publishableModules = draft.modules.filter((module) => moduleIsRealPublishSupported(module.module_type));
  const editorialModules = draft.modules.filter((module) => moduleIsEditorialOnly(module.module_type));
  const heroModule =
    publishableModules.find((module) => module.module_type === "hero") ??
    publishableModules[0] ??
    draft.modules[0];
  const heroImageUrl = resolveModulePublishableImageUrl(heroModule, assets);
  const visibleModules = publishableModules.filter((module) => module.module_id !== heroModule?.module_id);

  return (
    <div className="rounded-[1.75rem] border border-white/10 bg-[radial-gradient(circle_at_top,_rgba(251,191,36,0.12),_transparent_32%),linear-gradient(180deg,rgba(15,23,42,0.9),rgba(2,6,23,0.95))] p-3 sm:p-4">
      <div className="mx-auto flex h-[640px] min-h-[560px] max-h-[72vh] w-full items-center justify-center">
        <div className="relative h-full w-full max-w-[760px] rounded-[2.1rem] border border-white/10 bg-[#cfd5da] p-3 shadow-[0_28px_90px_rgba(2,6,23,0.45)]">
          <div className="flex h-full flex-col overflow-hidden rounded-[1.7rem] bg-[#f6f4ee]">
            <div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-300" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
              </div>
              <div className="flex flex-wrap items-center justify-end gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-950 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] text-white">
                  <Sparkles className="h-3 w-3" />
                  A+ preview
                </span>
                <span className="rounded-full border border-slate-200 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">
                  {formatLanguageLabel(language)}
                </span>
              </div>
            </div>

            <div className="h-full overflow-y-auto overscroll-contain px-3 py-3 sm:px-4 sm:py-4">
              <div className="mx-auto max-w-[660px] space-y-3">
                <section className="rounded-[1.35rem] bg-[linear-gradient(135deg,#fff8e6,#ffffff_60%,#f8fafc)] p-4 shadow-sm shadow-slate-300/40">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[10px] font-medium uppercase tracking-[0.24em] text-slate-500">
                      Hero
                    </p>
                    <span className="rounded-full bg-slate-950 px-2 py-1 text-[10px] font-medium uppercase tracking-[0.18em] text-white">
                      Live subset
                    </span>
                    {editorialModules.length > 0 ? (
                      <span className="rounded-full border border-amber-300/30 bg-amber-100 px-2 py-1 text-[10px] font-medium uppercase tracking-[0.18em] text-amber-700">
                        {editorialModules.length} editorial module{editorialModules.length === 1 ? "" : "s"} omitted
                      </span>
                    ) : null}
                  </div>
                  <h4
                    className="mt-2 text-xl font-semibold leading-tight text-slate-950 sm:text-[1.45rem]"
                    style={twoLineClampStyle}
                  >
                    {draft.headline}
                  </h4>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{draft.subheadline}</p>

                  <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1.05fr)_minmax(220px,0.95fr)]">
                    <div className="rounded-[1rem] bg-white p-4 shadow-sm shadow-slate-200/70">
                      <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-slate-500">
                        Brand story
                      </p>
                      <p className="mt-2 text-[13px] leading-6 text-slate-600">{draft.brand_story}</p>
                    </div>

                    <div className="rounded-[1rem] border border-dashed border-slate-300 bg-slate-50 p-4">
                      <div className="flex items-center gap-2 text-slate-500">
                        <ImageIcon className="h-3.5 w-3.5" />
                        <p className="text-[10px] font-medium uppercase tracking-[0.22em]">
                          Creative direction
                        </p>
                      </div>
                      <PreviewImageCard
                        imageUrl={heroImageUrl}
                        imageBrief={
                          heroModule?.image_brief ?? "Add an image brief to preview the hero visual."
                        }
                      />
                      {heroImageUrl && heroModule && moduleSupportsPublishOverlay(heroModule.module_type) ? (
                        <div className="mt-3 inline-flex max-w-full rounded-full bg-slate-900 px-3 py-1.5 text-xs font-medium text-white">
                          <span className="truncate">
                            {heroModule.overlay_text ??
                              extractOverlayText(heroModule.image_brief) ??
                              "Overlay text preview"}
                          </span>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </section>

                <section className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                  {draft.key_features.map((feature) => (
                    <div
                      key={feature}
                      className="rounded-[1rem] border border-slate-200 bg-white px-3 py-3 shadow-sm shadow-slate-200/50"
                    >
                      <div className="flex items-start gap-2.5">
                        <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                        <p className="text-[13px] leading-5 text-slate-700">{feature}</p>
                      </div>
                    </div>
                  ))}
                </section>

                {visibleModules.length > 0 ? (
                  <section className="space-y-3">
                    {visibleModules.map((module) => (
                      <ModulePreviewCard key={module.module_id} module={module} assets={assets} />
                    ))}
                  </section>
                ) : null}

                {editorialModules.length > 0 ? (
                  <section className="rounded-[1rem] border border-amber-300/20 bg-amber-50 p-4 shadow-sm shadow-amber-200/40">
                    <div className="flex items-center gap-2 text-amber-700">
                      <Info className="h-3.5 w-3.5" />
                      <p className="text-[10px] font-medium uppercase tracking-[0.22em]">
                        Editorial-only modules
                      </p>
                    </div>
                    <p className="mt-2 text-[13px] leading-6 text-amber-800">
                      {editorialModules.length === 1
                        ? "One draft module is still editorial-only and stays outside the live Amazon request."
                        : `${editorialModules.length} draft modules are still editorial-only and stay outside the live Amazon request.`}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {editorialModules.map((module) => (
                        <span
                          key={module.module_id}
                          className="rounded-full border border-amber-300/30 bg-white px-3 py-1.5 text-[11px] font-medium text-amber-800"
                        >
                          {module.module_type}: {module.headline}
                        </span>
                      ))}
                    </div>
                  </section>
                ) : null}

                <section className="rounded-[1rem] border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/50">
                  <div className="flex items-center gap-2 text-slate-500">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <p className="text-[10px] font-medium uppercase tracking-[0.22em]">
                      Compliance checks
                    </p>
                  </div>
                  <div className="mt-3 grid gap-2">
                    {draft.compliance_notes.map((note) => (
                      <div
                        key={note}
                        className="rounded-[0.9rem] bg-slate-50 px-3 py-2.5 text-[13px] leading-5 text-slate-700"
                      >
                        {note}
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ModulePreviewCard({
  module,
  assets,
}: {
  module: AplusModulePayload;
  assets: AplusAsset[];
}) {
  const imageUrl = resolveModulePublishableImageUrl(module, assets);
  const supportsImage = moduleSupportsPublishImage(module.module_type);
  const unsupportedImageConfig = moduleHasUnsupportedPublishImageConfig(module);

  return (
    <article className="rounded-[1rem] border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/50">
      <div className="grid gap-3 md:grid-cols-[180px_minmax(0,1fr)]">
        <div className="rounded-[0.95rem] bg-[linear-gradient(135deg,#e2e8f0,#f8fafc)] p-3">
          <div className="flex items-center gap-2 text-slate-500">
            {module.module_type === "faq" ? (
              <MessageSquareQuote className="h-3.5 w-3.5" />
            ) : (
              <ImageIcon className="h-3.5 w-3.5" />
            )}
            <p className="text-[10px] font-medium uppercase tracking-[0.22em]">
              {module.module_type === "faq" ? "Trust section" : `${module.module_type} module`}
            </p>
          </div>
          {supportsImage ? (
            <>
              <PreviewImageCard imageUrl={imageUrl} imageBrief={module.image_brief} />
              {imageUrl && moduleSupportsPublishOverlay(module.module_type) ? (
                <div className="mt-3 inline-flex max-w-full rounded-full bg-slate-900 px-3 py-1.5 text-[11px] font-medium text-white">
                  <span className="truncate">
                    {module.overlay_text ?? extractOverlayText(module.image_brief) ?? "Overlay text preview"}
                  </span>
                </div>
              ) : null}
            </>
          ) : (
            <div className="mt-3 rounded-[0.95rem] border border-slate-200 bg-slate-50 px-3 py-3 text-[12px] leading-5 text-slate-600">
              {unsupportedImageConfig ? (
                <span className="inline-flex items-start gap-2">
                  <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                  This module publishes as text only in the real Amazon subset. Attached Studio images or overlays are omitted.
                </span>
              ) : (
                "This module publishes as text only."
              )}
            </div>
          )}
        </div>

        <div>
          <h5 className="text-lg font-semibold leading-snug text-slate-950">{module.headline}</h5>
          <p className="mt-2 text-[13px] leading-6 text-slate-600">{module.body}</p>
          {module.bullets.length > 0 ? (
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {module.bullets.map((bullet) => (
                <div
                  key={bullet}
                  className="rounded-[0.9rem] border border-slate-200 bg-slate-50 px-3 py-2.5 text-[12px] leading-5 text-slate-700"
                >
                  {bullet}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function PreviewImageCard({
  imageUrl,
  imageBrief,
}: {
  imageUrl: string | null;
  imageBrief: string;
}) {
  if (imageUrl) {
    return (
      <div className="mt-3 overflow-hidden rounded-[0.95rem] border border-slate-200 bg-white">
        <img src={imageUrl} alt={imageBrief} className="aspect-[4/3] h-full w-full object-cover" />
      </div>
    );
  }

  return (
    <div className="mt-3 rounded-[0.95rem] bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.22),_transparent_42%),linear-gradient(135deg,#e2e8f0,#f8fafc)] p-3">
      <div className="flex items-start gap-2">
        <ImageOff className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
        <p className="text-[13px] leading-5 text-slate-700">{imageBrief}</p>
      </div>
    </div>
  );
}

function extractOverlayText(imageBrief?: string): string | null {
  if (!imageBrief) {
    return null;
  }

  const match = imageBrief.match(/(?:Overlay-Text|overlay text):\s*['"]([^'"]+)['"]/i);
  return match?.[1] ?? null;
}
