import { useEffect, useState } from "react";

import { useAuth } from "../hooks/useAuth";
import {
  getDashboardSummary,
  type DashboardSummaryResponse,
} from "../lib/api";

export function DashboardPage() {
  const { token } = useAuth();
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSummary() {
      if (!token) {
        return;
      }

      try {
        const response = await getDashboardSummary(token);
        if (!cancelled) {
          setSummary(response);
          setError(null);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load dashboard");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadSummary();

    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="space-y-8">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,0.7fr)]">
        <div className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(251,191,36,0.18),_rgba(15,23,42,0.95)_42%,_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-xs uppercase tracking-[0.32em] text-amber-100/70">Operations cockpit</p>
          <h2 className="mt-4 max-w-2xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
            Responsive control plane for Amazon catalog, inventory, and A+ workflows.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            Phase 1 delivers the shell, health wiring, and production-ready foundations. The next
            phases will attach live SP-API, OpenAI, and Slack workflows to these modules.
          </p>
        </div>

        <div className="rounded-[2rem] border border-white/10 bg-slate-950/50 p-6">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Recent activity</p>
          <div className="mt-5 space-y-4">
            {isLoading ? (
              <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300">
                Loading dashboard activity...
              </div>
            ) : error ? (
              <div className="rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 p-4 text-sm text-rose-100">
                {error}
              </div>
            ) : (
              summary?.recent_activity.map((item) => (
                <div
                  key={`${item.title}-${item.occurred_at}`}
                  className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4"
                >
                  <p className="text-sm font-medium text-white">{item.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{item.detail}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {(summary?.metrics ?? []).map((card) => (
          <article
            key={card.label}
            className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5"
          >
            <p className="text-sm text-slate-400">{card.label}</p>
            <p className="mt-4 text-4xl font-semibold text-white">{card.value}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">{card.note}</p>
          </article>
        ))}
        {isLoading
          ? Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="h-40 animate-pulse rounded-[1.75rem] border border-white/10 bg-white/[0.04]"
              />
            ))
          : null}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-6">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Inventory alerts</p>
          <div className="mt-5 space-y-4">
            {summary?.inventory_alerts.map((item) => (
              <div key={`${item.title}-${item.occurred_at}`} className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4">
                <p className="text-sm font-medium text-white">{item.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-300">{item.detail}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-6">
          <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Slack delivery</p>
          <div className="mt-5 space-y-4">
            {summary?.slack_delivery.map((item) => (
              <div key={`${item.notification_type}-${item.created_at}`} className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4">
                <p className="text-sm font-medium capitalize text-white">
                  {item.notification_type.replaceAll("_", " ")}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-300">{item.message_preview}</p>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
