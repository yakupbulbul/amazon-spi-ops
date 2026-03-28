import { AlertTriangle, Lightbulb } from "lucide-react";

import type { AplusOptimizationSuggestion } from "../../lib/api";

type AplusSectionWarningsProps = {
  items: AplusOptimizationSuggestion[];
};

export function AplusSectionWarnings({ items }: AplusSectionWarningsProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {items.slice(0, 2).map((item) => (
        <div
          key={`${item.section}-${item.title}`}
          className={[
            "rounded-[1rem] border px-3 py-3",
            item.severity === "critical"
              ? "border-rose-400/15 bg-rose-500/10"
              : "border-amber-300/15 bg-amber-500/10",
          ].join(" ")}
        >
          <div className="flex items-start gap-3">
            {item.severity === "critical" ? (
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-200" />
            ) : (
              <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-200" />
            )}
            <div>
              <p className="text-sm font-medium text-white">{item.title}</p>
              <p className="mt-1 text-sm leading-6 text-slate-300">{item.message}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
