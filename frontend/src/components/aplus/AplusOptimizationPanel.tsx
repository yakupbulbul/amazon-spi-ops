import { AlertTriangle, BarChart3, CheckCircle2, Image, Lightbulb } from "lucide-react";

import type {
  AplusDraftResponse,
  AplusImprovementCategory,
  AplusOptimizationSuggestion,
} from "../../lib/api";
import { AplusScoreBadge } from "./AplusScoreBadge";

type AplusOptimizationPanelProps = {
  draft: AplusDraftResponse | null;
  hasUnsavedChanges: boolean;
  onImprove: (category: AplusImprovementCategory) => void;
  improvingCategory: AplusImprovementCategory | null;
};

export function AplusOptimizationPanel({
  draft,
  hasUnsavedChanges,
  onImprove,
  improvingCategory,
}: AplusOptimizationPanelProps) {
  const optimization = draft?.optimization_report ?? null;

  if (!optimization) {
    return (
      <section className="rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] px-5 py-5">
        <div className="flex items-start gap-3">
          <BarChart3 className="mt-0.5 h-4 w-4 text-slate-500" />
          <div>
            <p className="text-sm font-medium text-white">A+ optimization</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Generate a draft to score structure, clarity, differentiation, completeness, and image quality.
            </p>
          </div>
        </div>
      </section>
    );
  }

  const allSuggestions = [...optimization.critical_issues, ...optimization.warnings];

  return (
    <section className="rounded-[1.5rem] bg-white/[0.03] px-5 py-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Optimization</p>
          <h4 className="mt-2 text-lg font-semibold text-white">Conversion-focused quality review</h4>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            This layer scores how well the draft educates, differentiates, and maps to Amazon A+ best practices.
          </p>
        </div>

        <AplusScoreBadge score={optimization.overall_score} />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
        <MetricCard label="Structure" value={optimization.structure_score} />
        <MetricCard label="Clarity" value={optimization.clarity_score} />
        <MetricCard label="Differentiation" value={optimization.differentiation_score} />
        <MetricCard label="Completeness" value={optimization.completeness_score} />
        <MetricCard
          label="Images"
          value={optimization.image_quality_score}
          emptyLabel="Not used"
          icon={Image}
        />
      </div>

      <div className="mt-5 grid gap-3 xl:grid-cols-2">
        {improvementCategories.map((category) => (
          <ImprovementActionCard
            key={category.key}
            category={category.key}
            label={category.label}
            score={optimization[category.scoreKey]}
            suggestions={getCategorySuggestions(optimization, category.key)}
            isImproving={improvingCategory === category.key}
            onImprove={onImprove}
          />
        ))}
      </div>

      <div className="mt-5 grid gap-5 2xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="space-y-4">
          <SuggestionList
            title="Critical issues"
            tone="critical"
            emptyMessage="No critical optimization issues detected."
            items={optimization.critical_issues}
          />
          <SuggestionList
            title="Suggestions"
            tone="warning"
            emptyMessage="No optimization warnings right now."
            items={optimization.warnings}
          />
        </div>

        <div className="space-y-4">
          <article className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Section watchlist</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {optimization.section_insights.length === 0 ? (
                <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  No active section warnings
                </span>
              ) : (
                optimization.section_insights.map((insight) => (
                  <span
                    key={`${insight.section}-${insight.summary}`}
                    className={[
                      "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs",
                      insight.severity === "critical"
                        ? "border-rose-400/20 bg-rose-500/10 text-rose-100"
                        : "border-amber-300/20 bg-amber-500/10 text-amber-100",
                    ].join(" ")}
                  >
                    <AlertTriangle className="h-3.5 w-3.5" />
                    {insight.summary}
                  </span>
                ))
              )}
            </div>
          </article>

          <article className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Structural gaps</p>
            {optimization.missing_sections.length === 0 ? (
              <div className="mt-4 rounded-[1rem] border border-emerald-400/20 bg-emerald-500/10 px-3 py-3 text-sm text-emerald-100">
                The draft covers the core A+ structure.
              </div>
            ) : (
              <div className="mt-4 space-y-2">
                {optimization.missing_sections.map((section) => (
                  <div
                    key={section}
                    className="rounded-[1rem] border border-amber-300/15 bg-amber-500/10 px-3 py-3 text-sm text-amber-100"
                  >
                    {section}
                  </div>
                ))}
              </div>
            )}
          </article>

          <article className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Next best action</p>
            <div className="mt-4 rounded-[1rem] border border-white/10 bg-white/[0.03] px-3 py-3 text-sm leading-6 text-slate-300">
              {allSuggestions[0]?.message ??
                "Validate the draft after editing to refresh the optimization score and section advice."}
            </div>
            {hasUnsavedChanges ? (
              <div className="mt-3 rounded-[1rem] border border-sky-300/20 bg-sky-500/10 px-3 py-3 text-sm text-sky-100">
                The optimization layer reflects the last saved draft. Validate again after edits to refresh the score.
              </div>
            ) : null}
          </article>
        </div>
      </div>
    </section>
  );
}

const improvementCategories: Array<{
  key: AplusImprovementCategory;
  label: string;
  scoreKey:
    | "structure_score"
    | "clarity_score"
    | "differentiation_score"
    | "completeness_score";
}> = [
  { key: "structure", label: "Improve structure", scoreKey: "structure_score" },
  { key: "clarity", label: "Improve clarity", scoreKey: "clarity_score" },
  { key: "differentiation", label: "Improve differentiation", scoreKey: "differentiation_score" },
  { key: "completeness", label: "Improve completeness", scoreKey: "completeness_score" },
];

function getCategorySuggestions(
  optimization: NonNullable<AplusDraftResponse["optimization_report"]>,
  category: AplusImprovementCategory,
): AplusOptimizationSuggestion[] {
  const keywords: Record<AplusImprovementCategory, string[]> = {
    structure: ["hero", "feature", "comparison", "usage", "structure", "brand story"],
    clarity: ["headline", "clarity", "benefit", "dense", "cross-section", "copy"],
    differentiation: ["differentiation", "generic", "comparison", "alternative"],
    completeness: ["technical", "customer education", "usage", "brand story", "complete"],
  };
  const matches = [...optimization.critical_issues, ...optimization.warnings].filter((item) => {
    const haystack = `${item.section} ${item.title} ${item.message}`.toLowerCase();
    return keywords[category].some((keyword) => haystack.includes(keyword));
  });
  return matches.slice(0, 3);
}

type MetricCardProps = {
  label: string;
  value: number | null;
  emptyLabel?: string;
  icon?: typeof Image;
};

function MetricCard({ label, value, emptyLabel = "Pending", icon: Icon = BarChart3 }: MetricCardProps) {
  const toneClass =
    value === null
      ? "border-white/10 bg-slate-950/60 text-slate-300"
      : value >= 82
        ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-100"
        : value >= 68
          ? "border-amber-300/20 bg-amber-500/10 text-amber-100"
          : "border-rose-400/20 bg-rose-500/10 text-rose-100";

  return (
    <article className={["rounded-[1.25rem] border px-4 py-4", toneClass].join(" ")}>
      <div className="flex items-center gap-2 opacity-80">
        <Icon className="h-3.5 w-3.5" />
        <p className="text-xs uppercase tracking-[0.2em]">{label}</p>
      </div>
      <p className="mt-3 text-2xl font-semibold">{value ?? emptyLabel}</p>
    </article>
  );
}

type ImprovementActionCardProps = {
  category: AplusImprovementCategory;
  label: string;
  score: number;
  suggestions: AplusOptimizationSuggestion[];
  isImproving: boolean;
  onImprove: (category: AplusImprovementCategory) => void;
};

function ImprovementActionCard({
  category,
  label,
  score,
  suggestions,
  isImproving,
  onImprove,
}: ImprovementActionCardProps) {
  const toneClass =
    score >= 82
      ? "border-emerald-400/15 bg-emerald-500/10"
      : score >= 68
        ? "border-amber-300/15 bg-amber-500/10"
        : "border-rose-400/15 bg-rose-500/10";

  return (
    <article className={["rounded-[1.25rem] border px-4 py-4", toneClass].join(" ")}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
          <p className="mt-3 text-2xl font-semibold text-white">{score}</p>
        </div>
        <button
          type="button"
          onClick={() => onImprove(category)}
          disabled={isImproving}
          className="rounded-full border border-white/10 bg-white/10 px-3 py-2 text-xs font-medium text-white transition hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isImproving ? "Fixing..." : "Fix this"}
        </button>
      </div>

      <div className="mt-4 space-y-2">
        {suggestions.length === 0 ? (
          <p className="text-sm leading-6 text-slate-300">
            No urgent issues detected in this category. You can still refine it selectively.
          </p>
        ) : (
          suggestions.map((suggestion) => (
            <div
              key={`${category}-${suggestion.section}-${suggestion.title}`}
              className="rounded-[1rem] border border-white/10 bg-slate-950/40 px-3 py-3 text-sm leading-6 text-slate-200"
            >
              <p className="font-medium text-white">{suggestion.title}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">
                {suggestion.section}
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-300">{suggestion.message}</p>
            </div>
          ))
        )}
      </div>
    </article>
  );
}

type SuggestionListProps = {
  title: string;
  tone: "critical" | "warning";
  emptyMessage: string;
  items: AplusDraftResponse["optimization_report"]["critical_issues"];
};

function SuggestionList({ title, tone, emptyMessage, items }: SuggestionListProps) {
  return (
    <article className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{title}</p>
      {items.length === 0 ? (
        <div className="mt-4 rounded-[1rem] border border-white/10 bg-white/[0.03] px-3 py-3 text-sm leading-6 text-slate-300">
          {emptyMessage}
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <div
              key={`${item.section}-${item.title}-${item.message}`}
              className={[
                "rounded-[1rem] border px-3 py-3",
                tone === "critical"
                  ? "border-rose-400/15 bg-rose-500/10"
                  : "border-amber-300/15 bg-amber-500/10",
              ].join(" ")}
            >
              <div className="flex items-start gap-3">
                {tone === "critical" ? (
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-200" />
                ) : (
                  <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-200" />
                )}
                <div>
                  <p className="text-sm font-medium text-white">{item.title}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                    {item.section}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{item.message}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
