import { Activity, BellRing, Search } from "lucide-react";
import type { ReactNode } from "react";

import { useBackendHealth } from "../../hooks/useBackendHealth";

type TopBarProps = {
  leftSlot?: ReactNode;
};

export function TopBar({ leftSlot }: TopBarProps) {
  const { status, message } = useBackendHealth();

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/50 backdrop-blur-xl">
      <div className="flex flex-wrap items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex flex-1 items-center gap-3">
          {leftSlot}
          <div className="hidden min-w-0 flex-1 items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/5 px-4 py-3 md:flex">
            <Search className="h-4 w-4 text-slate-400" />
            <span className="truncate text-sm text-slate-400">
              Search products, ASINs, listings, alerts, or A+ drafts
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/5 px-4 py-3">
            <span
              className={[
                "inline-flex h-2.5 w-2.5 rounded-full",
                status === "healthy"
                  ? "bg-emerald-400"
                  : status === "loading"
                    ? "bg-amber-300"
                    : "bg-rose-400",
              ].join(" ")}
            />
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">API status</p>
              <p className="text-sm font-medium text-white">{message}</p>
            </div>
            <Activity className="h-4 w-4 text-slate-400" />
          </div>

          <button
            type="button"
            className="inline-flex h-12 w-12 items-center justify-center rounded-[1.25rem] border border-white/10 bg-white/5 text-slate-200 transition hover:bg-white/10"
            aria-label="Notifications"
          >
            <BellRing className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}

