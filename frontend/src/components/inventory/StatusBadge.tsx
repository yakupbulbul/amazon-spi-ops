import { AlertTriangle, CheckCircle2, TriangleAlert, XCircle } from "lucide-react";

import { formatStatusLabel } from "./formatters";

const badgeStyles: Record<string, string> = {
  healthy: "border-emerald-400/25 bg-emerald-500/10 text-emerald-100",
  low: "border-amber-400/25 bg-amber-500/10 text-amber-100",
  out_of_stock: "border-rose-400/25 bg-rose-500/10 text-rose-100",
  critical: "border-rose-400/25 bg-rose-500/10 text-rose-100",
};

const badgeIcons = {
  healthy: CheckCircle2,
  low: TriangleAlert,
  out_of_stock: XCircle,
  critical: AlertTriangle,
} as const;

type StatusBadgeProps = {
  status: string;
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const Icon = badgeIcons[status as keyof typeof badgeIcons] ?? AlertTriangle;

  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold capitalize",
        badgeStyles[status] ?? badgeStyles.critical,
      ].join(" ")}
    >
      <Icon className="h-3.5 w-3.5" />
      {formatStatusLabel(status)}
    </span>
  );
}
