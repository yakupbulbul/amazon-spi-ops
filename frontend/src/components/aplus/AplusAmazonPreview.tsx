import {
  Check,
  Columns3,
  ImageIcon,
  MessageSquareQuote,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import type { AplusDraftPayload, AplusLanguage, AplusModulePayload } from "../../lib/api";
import { formatLanguageLabel } from "./languages";

type AplusAmazonPreviewProps = {
  draft: AplusDraftPayload;
  language: AplusLanguage;
};

export function AplusAmazonPreview({ draft, language }: AplusAmazonPreviewProps) {
  return (
    <div className="rounded-[2rem] bg-[#f7f7f3] p-4 text-slate-900 shadow-[0_30px_80px_rgba(2,6,23,0.35)] sm:p-5">
      <div className="rounded-[1.5rem] border border-slate-200 bg-white p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-4">
          <span className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white">
            <Sparkles className="h-3.5 w-3.5" />
            Amazon A+ layout preview
          </span>
          <span className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600">
            {formatLanguageLabel(language)}
          </span>
          <span className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600">
            {draft.modules.length} modules
          </span>
        </div>

        <section className="mt-6 rounded-[1.5rem] bg-[linear-gradient(135deg,#fff8e6,#ffffff_55%,#f8fafc)] p-5 sm:p-6">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Hero</p>
          <h4 className="mt-3 max-w-2xl text-3xl font-semibold leading-tight text-slate-950">
            {draft.headline}
          </h4>
          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">{draft.subheadline}</p>
          <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
            <div className="rounded-[1.25rem] bg-white p-5 shadow-sm shadow-slate-200/70">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Brand story</p>
              <p className="mt-3 text-sm leading-7 text-slate-600">{draft.brand_story}</p>
            </div>
            <div className="rounded-[1.25rem] border border-dashed border-slate-300 bg-slate-50 p-5">
              <div className="flex items-center gap-2 text-slate-500">
                <ImageIcon className="h-4 w-4" />
                <p className="text-xs uppercase tracking-[0.22em]">Creative direction</p>
              </div>
              <div className="mt-4 rounded-[1rem] bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.25),_transparent_44%),linear-gradient(135deg,#e2e8f0,#f8fafc)] p-4">
                <p className="text-sm leading-6 text-slate-700">
                  {draft.modules[0]?.image_brief ?? "Add an image brief to preview the first hero visual."}
                </p>
              </div>
              <div className="mt-4 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white">
                {extractOverlayText(draft.modules[0]?.image_brief) ?? "Overlay text preview"}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-4 lg:grid-cols-3">
          {draft.key_features.map((feature) => (
            <div
              key={feature}
              className="rounded-[1.25rem] border border-slate-200 bg-slate-50 px-4 py-4"
            >
              <div className="flex items-start gap-3">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <p className="text-sm leading-6 text-slate-700">{feature}</p>
              </div>
            </div>
          ))}
        </section>

        <section className="mt-6 space-y-4">
          {draft.modules.map((module, index) => (
            <ModulePreviewCard key={`${module.module_type}-${index}`} module={module} />
          ))}
        </section>

        <section className="mt-6 rounded-[1.25rem] border border-slate-200 bg-slate-50 p-5">
          <div className="flex items-center gap-2 text-slate-500">
            <ShieldCheck className="h-4 w-4" />
            <p className="text-xs uppercase tracking-[0.22em]">Compliance checks</p>
          </div>
          <div className="mt-4 grid gap-3">
            {draft.compliance_notes.map((note) => (
              <div
                key={note}
                className="rounded-[1rem] bg-white px-4 py-3 text-sm leading-6 text-slate-700 shadow-sm shadow-slate-200/60"
              >
                {note}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function ModulePreviewCard({ module }: { module: AplusModulePayload }) {
  if (module.module_type === "comparison") {
    return (
      <article className="rounded-[1.5rem] border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 text-slate-500">
          <Columns3 className="h-4 w-4" />
          <p className="text-xs uppercase tracking-[0.22em]">Comparison module</p>
        </div>
        <h5 className="mt-3 text-xl font-semibold text-slate-950">{module.headline}</h5>
        <p className="mt-3 text-sm leading-6 text-slate-600">{module.body}</p>
        <div className="mt-5 overflow-hidden rounded-[1rem] border border-slate-200">
          <div className="grid grid-cols-[1.2fr_1fr_1fr] bg-slate-100 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
            <div className="px-4 py-3">Criteria</div>
            <div className="border-l border-slate-200 px-4 py-3">This product</div>
            <div className="border-l border-slate-200 px-4 py-3">Generic alternative</div>
          </div>
          {module.bullets.map((bullet) => (
            <div
              key={bullet}
              className="grid grid-cols-[1.2fr_1fr_1fr] border-t border-slate-200 text-sm text-slate-700"
            >
              <div className="px-4 py-3">{bullet}</div>
              <div className="border-l border-slate-200 px-4 py-3 text-emerald-700">Highlighted benefit</div>
              <div className="border-l border-slate-200 px-4 py-3 text-slate-500">Basic alternative</div>
            </div>
          ))}
        </div>
      </article>
    );
  }

  return (
    <article className="rounded-[1.5rem] border border-slate-200 bg-white p-5">
      <div className="grid gap-5 lg:grid-cols-[minmax(220px,0.8fr)_minmax(0,1.2fr)]">
        <div className="rounded-[1.25rem] bg-[linear-gradient(135deg,#e2e8f0,#f8fafc)] p-4">
          <div className="flex items-center gap-2 text-slate-500">
            {module.module_type === "faq" ? (
              <MessageSquareQuote className="h-4 w-4" />
            ) : (
              <ImageIcon className="h-4 w-4" />
            )}
            <p className="text-xs uppercase tracking-[0.22em]">
              {module.module_type === "faq" ? "Trust section" : `${module.module_type} module`}
            </p>
          </div>
          <div className="mt-4 rounded-[1rem] bg-white/90 px-4 py-3 text-sm leading-6 text-slate-700 shadow-sm">
            {module.image_brief}
          </div>
          <div className="mt-4 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white">
            {extractOverlayText(module.image_brief) ?? "Overlay text preview"}
          </div>
        </div>

        <div>
          <h5 className="text-xl font-semibold text-slate-950">{module.headline}</h5>
          <p className="mt-3 text-sm leading-7 text-slate-600">{module.body}</p>
          {module.bullets.length > 0 ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {module.bullets.map((bullet) => (
                <div
                  key={bullet}
                  className="rounded-[1rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700"
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

function extractOverlayText(imageBrief?: string): string | null {
  if (!imageBrief) {
    return null;
  }

  const match = imageBrief.match(/(?:Overlay-Text|overlay text):\s*['"]([^'"]+)['"]/i);
  return match?.[1] ?? null;
}
