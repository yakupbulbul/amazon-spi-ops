import {
  AlertTriangle,
  CheckCheck,
  Clock3,
  Filter,
  RefreshCcw,
  Search,
} from "lucide-react";
import { startTransition, useEffect, useEffectEvent, useMemo, useState } from "react";

import { useAuth } from "../hooks/useAuth";
import { getEvents, type EventLogItem } from "../lib/api";

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function countNotificationStatus(events: EventLogItem[], status: string): number {
  return events.flatMap((event) => event.notifications).filter((item) => item.status === status).length;
}

export function NotificationsPage() {
  const { token } = useAuth();
  const [events, setEvents] = useState<EventLogItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEvents = useEffectEvent(async ({ cancelled = false }: { cancelled?: boolean } = {}) => {
    if (!token) {
      return;
    }

    try {
      const response = await getEvents(token);
      if (cancelled) {
        return;
      }
      startTransition(() => {
        setEvents(response.items);
        setError(null);
      });
    } catch (loadError) {
      if (!cancelled) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load events.");
      }
    } finally {
      if (!cancelled) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  });

  useEffect(() => {
    let cancelled = false;
    void loadEvents({ cancelled });
    return () => {
      cancelled = true;
    };
  }, [loadEvents, token]);

  const filteredEvents = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();
    return events.filter((event) => {
      const matchesStatus =
        statusFilter === "all" ||
        event.status === statusFilter ||
        event.notifications.some((notification) => notification.status === statusFilter);
      const matchesQuery =
        !normalizedQuery ||
        JSON.stringify({
          event_type: event.event_type,
          source: event.source,
          status: event.status,
          payload: event.payload,
          notifications: event.notifications.map((notification) => notification.message_preview),
        })
          .toLowerCase()
          .includes(normalizedQuery);

      return matchesStatus && matchesQuery;
    });
  }, [events, searchQuery, statusFilter]);

  const deliveredCount = countNotificationStatus(events, "succeeded");
  const failedCount = countNotificationStatus(events, "failed");
  const pendingCount = countNotificationStatus(events, "pending");

  return (
    <div className="space-y-8">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(16,185,129,0.18),_rgba(15,23,42,0.94)_36%,_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-xs uppercase tracking-[0.32em] text-emerald-100/70">Notification history</p>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
            Review operational events, Slack delivery outcomes, and failure reasons from one timeline.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            Every queued Slack notification is tied back to its event record, so price, stock, A+
            publish, and test delivery activity stays audit-friendly.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Tracked events</p>
            <p className="mt-4 text-4xl font-semibold text-white">{events.length}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Latest event timeline entries stored in PostgreSQL.</p>
          </article>
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Slack deliveries</p>
            <p className="mt-4 text-2xl font-semibold text-white">
              {deliveredCount} sent / {failedCount} failed
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              {pendingCount} notifications are still waiting on worker delivery.
            </p>
          </article>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        <article className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Delivered</p>
          <p className="mt-4 text-3xl font-semibold text-white">{deliveredCount}</p>
        </article>
        <article className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Failed</p>
          <p className="mt-4 text-3xl font-semibold text-white">{failedCount}</p>
        </article>
        <article className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Pending</p>
          <p className="mt-4 text-3xl font-semibold text-white">{pendingCount}</p>
        </article>
        <article className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Filtered events</p>
          <p className="mt-4 text-3xl font-semibold text-white">{filteredEvents.length}</p>
        </article>
      </section>

      <section className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Timeline controls</p>
            <h3 className="mt-2 text-xl font-semibold text-white">Filter notification history</h3>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row">
            <label className="flex min-w-0 items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 lg:min-w-[320px]">
              <Search className="h-4 w-4 text-slate-500" />
              <input
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search event type, source, payload, or message"
                className="w-full bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
              />
            </label>

            <label className="flex items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3">
              <Filter className="h-4 w-4 text-slate-500" />
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="bg-transparent text-sm text-white outline-none"
              >
                <option value="all" className="bg-slate-950">
                  All statuses
                </option>
                <option value="succeeded" className="bg-slate-950">
                  Succeeded
                </option>
                <option value="failed" className="bg-slate-950">
                  Failed
                </option>
                <option value="pending" className="bg-slate-950">
                  Pending
                </option>
                <option value="warning" className="bg-slate-950">
                  Warning
                </option>
                <option value="critical" className="bg-slate-950">
                  Critical
                </option>
              </select>
            </label>

            <button
              type="button"
              onClick={() => {
                setIsRefreshing(true);
                void loadEvents();
              }}
              disabled={isRefreshing}
              className="inline-flex items-center justify-center gap-2 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-70"
            >
              <RefreshCcw className={["h-4 w-4", isRefreshing ? "animate-spin" : ""].join(" ")} />
              <span>{isRefreshing ? "Refreshing..." : "Refresh"}</span>
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-6 text-sm text-slate-300">
            Loading notification history...
          </div>
        ) : error ? (
          <div className="mt-6 flex items-start gap-3 rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 p-6 text-sm text-rose-100">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-6 text-sm leading-6 text-slate-400">
            No events match the current filters.
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            {filteredEvents.map((event) => {
              const latestNotification = event.notifications[0] ?? null;

              return (
                <article
                  key={event.id}
                  className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5"
                >
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.22em] text-slate-500">
                        <span>{formatLabel(event.event_type)}</span>
                        <span className="text-slate-700">/</span>
                        <span>{formatLabel(event.source)}</span>
                      </div>
                      <h4 className="mt-3 text-lg font-semibold text-white">{latestNotification?.message_preview ?? "Event recorded"}</h4>
                      <p className="mt-3 text-sm leading-6 text-slate-400">
                        Occurred {formatTimestamp(event.occurred_at)}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <span className="rounded-full border border-white/10 px-3 py-1 text-xs font-medium capitalize text-slate-200">
                        event {formatLabel(event.status)}
                      </span>
                      {latestNotification ? (
                        <span className="rounded-full border border-white/10 px-3 py-1 text-xs font-medium capitalize text-slate-200">
                          slack {formatLabel(latestNotification.status)}
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                    <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/50 p-4">
                      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Payload</p>
                      <pre className="mt-3 overflow-x-auto text-xs leading-6 text-slate-300">
                        {JSON.stringify(event.payload, null, 2)}
                      </pre>
                    </div>

                    <div className="space-y-3">
                      {event.notifications.length === 0 ? (
                        <div className="rounded-[1.25rem] border border-dashed border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">
                          No Slack notification was attached to this event.
                        </div>
                      ) : (
                        event.notifications.map((notification) => (
                          <div
                            key={notification.id}
                            className="rounded-[1.25rem] border border-white/10 bg-slate-950/50 p-4"
                          >
                            <div className="flex flex-wrap items-center gap-2">
                              {notification.status === "succeeded" ? (
                                <CheckCheck className="h-4 w-4 text-emerald-300" />
                              ) : notification.status === "pending" ? (
                                <Clock3 className="h-4 w-4 text-amber-200" />
                              ) : (
                                <AlertTriangle className="h-4 w-4 text-rose-300" />
                              )}
                              <p className="text-sm font-medium text-white">
                                {formatLabel(notification.notification_type)}
                              </p>
                              <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs capitalize text-slate-300">
                                {formatLabel(notification.status)}
                              </span>
                            </div>
                            <p className="mt-3 text-sm leading-6 text-slate-300">
                              {notification.message_preview}
                            </p>
                            <p className="mt-2 text-xs uppercase tracking-[0.22em] text-slate-500">
                              {notification.channel_label ?? "Webhook"} · {formatTimestamp(notification.created_at)}
                            </p>
                            {notification.error_message ? (
                              <p className="mt-3 rounded-[1rem] border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">
                                {notification.error_message}
                              </p>
                            ) : null}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
