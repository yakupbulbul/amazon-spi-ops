import { BarChart3 } from "lucide-react";

type AplusScoreBadgeProps = {
  score: number | null;
};

export function AplusScoreBadge({ score }: AplusScoreBadgeProps) {
  if (score === null) {
    return (
      <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-slate-300">
        <BarChart3 className="h-3.5 w-3.5 text-slate-400" />
        Score pending
      </div>
    );
  }

  const toneClass =
    score >= 82
      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-100"
      : score >= 68
        ? "border-amber-300/20 bg-amber-500/10 text-amber-100"
        : "border-rose-400/20 bg-rose-500/10 text-rose-100";

  const label = score >= 82 ? "Strong draft" : score >= 68 ? "Needs refinement" : "Needs work";

  return (
    <div className={["inline-flex items-center gap-3 rounded-full border px-3 py-2", toneClass].join(" ")}>
      <BarChart3 className="h-3.5 w-3.5" />
      <span className="text-xs uppercase tracking-[0.2em] opacity-80">A+ score</span>
      <span className="text-sm font-semibold">{score}</span>
      <span className="text-xs opacity-80">{label}</span>
    </div>
  );
}
