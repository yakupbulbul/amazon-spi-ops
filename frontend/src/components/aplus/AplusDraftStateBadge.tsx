import { CheckCheck, CircleEllipsis, ShieldAlert, ShieldCheck } from "lucide-react";

type AplusDraftStateBadgeProps = {
  status: string | null | undefined;
};

const stateConfig: Record<
  string,
  { label: string; className: string; icon: typeof CircleEllipsis }
> = {
  draft: {
    label: "Draft only",
    className: "border-white/10 bg-white/[0.04] text-slate-200",
    icon: CircleEllipsis,
  },
  validated: {
    label: "Validated",
    className: "border-sky-300/20 bg-sky-500/10 text-sky-100",
    icon: CheckCheck,
  },
  ready_to_publish: {
    label: "Publish-ready",
    className: "border-emerald-400/20 bg-emerald-500/10 text-emerald-100",
    icon: ShieldCheck,
  },
  published: {
    label: "Published",
    className: "border-emerald-400/20 bg-emerald-500/10 text-emerald-100",
    icon: ShieldCheck,
  },
  failed: {
    label: "Needs attention",
    className: "border-rose-400/20 bg-rose-500/10 text-rose-100",
    icon: ShieldAlert,
  },
};

export function AplusDraftStateBadge({ status }: AplusDraftStateBadgeProps) {
  const config = stateConfig[status ?? "draft"] ?? stateConfig.draft;
  const Icon = config.icon;

  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium",
        config.className,
      ].join(" ")}
    >
      <Icon className="h-3.5 w-3.5" />
      {config.label}
    </span>
  );
}
