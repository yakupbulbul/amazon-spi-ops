const summaryCards = [
  { label: "Tracked products", value: "0", note: "Products will appear after catalog sync" },
  { label: "Low stock products", value: "0", note: "Threshold engine starts in Phase 3" },
  { label: "Recent sales events", value: "0", note: "Slack and order signals land in Phase 6" },
  { label: "Pending A+ drafts", value: "0", note: "AI draft workflow lands in Phase 5" },
];

const recentActivity = [
  "Backend health status is connected to the dashboard shell.",
  "Route scaffolding is ready for product, inventory, and notification features.",
  "Docker, FastAPI, React, Redis, PostgreSQL, and Nginx are now part of the runtime shape.",
];

const alertCards = [
  {
    title: "Inventory alerts",
    description: "Threshold rules and SKU alert badges will surface here once inventory sync is live.",
  },
  {
    title: "Slack delivery status",
    description: "Webhook checks and notification history will be available in the next notification phase.",
  },
];

export function DashboardPage() {
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
            {recentActivity.map((item) => (
              <div key={item} className="rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4">
                <p className="text-sm leading-6 text-slate-200">{item}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => (
          <article
            key={card.label}
            className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5"
          >
            <p className="text-sm text-slate-400">{card.label}</p>
            <p className="mt-4 text-4xl font-semibold text-white">{card.value}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">{card.note}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        {alertCards.map((card) => (
          <article
            key={card.title}
            className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-6"
          >
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Coming online</p>
            <h3 className="mt-3 text-2xl font-semibold text-white">{card.title}</h3>
            <p className="mt-4 max-w-xl text-sm leading-7 text-slate-400">{card.description}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

