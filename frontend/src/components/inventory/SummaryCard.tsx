import type { LucideIcon } from "lucide-react";

type SummaryCardProps = {
  icon: LucideIcon;
  label: string;
  value: string | number;
  note: string;
  tone?: "neutral" | "success" | "warning" | "danger";
};

const toneStyles: Record<NonNullable<SummaryCardProps["tone"]>, string> = {
  neutral: "border-white/10 bg-white/[0.04] text-white",
  success: "border-emerald-400/20 bg-emerald-500/10 text-emerald-100",
  warning: "border-amber-400/20 bg-amber-500/10 text-amber-100",
  danger: "border-rose-400/20 bg-rose-500/10 text-rose-100",
};

export function SummaryCard({
  icon: Icon,
  label,
  value,
  note,
  tone = "neutral",
}: SummaryCardProps) {
  return (
    <article
      className={[
        "rounded-[1.5rem] border p-5 shadow-lg shadow-black/10",
        toneStyles[tone],
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-slate-300">{label}</p>
          <p className="mt-4 text-4xl font-semibold text-white">{value}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-slate-950/40 p-3 text-current">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-400">{note}</p>
    </article>
  );
}
