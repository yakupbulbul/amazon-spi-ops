import {
  AlertTriangle,
  BellRing,
  CheckCheck,
  RefreshCcw,
  Send,
  ShieldCheck,
} from "lucide-react";
import { startTransition, useEffect, useEffectEvent, useState } from "react";

import { useAuth } from "../hooks/useAuth";
import {
  getEvents,
  sendSlackTestNotification,
  type EventLogItem,
  type SlackTestResponse,
} from "../lib/api";

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function SettingsPage() {
  const { token } = useAuth();
  const [events, setEvents] = useState<EventLogItem[]>([]);
  const [latestTestResult, setLatestTestResult] = useState<SlackTestResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const loadEvents = useEffectEvent(async ({ cancelled = false }: { cancelled?: boolean } = {}) => {
    if (!token) {
      return;
    }

    try {
      const response = await getEvents(token);
      if (!cancelled) {
        startTransition(() => {
          setEvents(response.items);
          setError(null);
        });
      }
    } catch (loadError) {
      if (!cancelled) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load settings activity.");
      }
    } finally {
      if (!cancelled) {
        setIsLoading(false);
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

  const recentNotifications = events.flatMap((event) => event.notifications).slice(0, 6);
  const latestSlackTest =
    events.find((event) => event.event_type === "slack_test")?.notifications[0] ?? null;

  async function handleSendTestNotification() {
    if (!token || isSending) {
      return;
    }

    setIsSending(true);
    setError(null);
    setStatusMessage(null);

    try {
      const response = await sendSlackTestNotification(token);
      setLatestTestResult(response);
      setStatusMessage(response.message);

      window.setTimeout(() => {
        void loadEvents();
      }, 2500);
    } catch (sendError) {
      setError(
        sendError instanceof Error ? sendError.message : "Unable to queue Slack test notification.",
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(245,158,11,0.18),_rgba(15,23,42,0.94)_38%,_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-xs uppercase tracking-[0.32em] text-amber-100/70">Operational settings</p>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
            Keep outbound integrations server-side and verify runtime behavior with controlled tests.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            Secrets remain on the backend. Use the test action below to validate Slack delivery from
            the live worker and inspect the stored delivery result without exposing the webhook in the browser.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Recent notifications</p>
            <p className="mt-4 text-4xl font-semibold text-white">{recentNotifications.length}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Latest worker delivery outcomes across all event types.</p>
          </article>
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Latest Slack test</p>
            <p className="mt-4 text-2xl font-semibold capitalize text-white">
              {latestSlackTest?.status ?? "Not run"}
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              {latestSlackTest?.error_message ?? "Queue a test notification to inspect the current runtime path."}
            </p>
          </article>
        </div>
      </section>

      {error ? (
        <section className="flex items-start gap-3 rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </section>
      ) : null}

      {statusMessage ? (
        <section className="flex items-start gap-3 rounded-[1.5rem] border border-emerald-400/20 bg-emerald-500/10 px-5 py-4 text-sm text-emerald-100">
          <CheckCheck className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{statusMessage}</span>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <BellRing className="h-5 w-5 text-amber-200" />
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Slack check</p>
              <h3 className="mt-1 text-xl font-semibold text-white">Send test notification</h3>
            </div>
          </div>

          <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
            <p className="text-sm leading-7 text-slate-300">
              The test action creates an event log row, queues a Slack notification through the
              worker, and then records the final delivery result. This is the safest way to confirm
              webhook runtime behavior from the admin UI.
            </p>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void handleSendTestNotification()}
              disabled={isSending}
              className="inline-flex items-center gap-2 rounded-[1.25rem] bg-amber-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <Send className="h-4 w-4" />
              <span>{isSending ? "Queueing test..." : "Send test Slack notification"}</span>
            </button>

            <button
              type="button"
              onClick={() => void loadEvents()}
              className="inline-flex items-center gap-2 rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-5 py-3 text-sm text-white transition hover:bg-white/[0.08]"
            >
              <RefreshCcw className="h-4 w-4" />
              <span>Refresh activity</span>
            </button>
          </div>

          {latestTestResult ? (
            <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Latest queued test</p>
              <p className="mt-3 text-sm text-slate-200">Event {latestTestResult.event_id}</p>
              <p className="mt-2 text-sm text-slate-400">Notification {latestTestResult.notification_id}</p>
            </div>
          ) : null}
        </article>

        <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-sky-200" />
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Recent outcomes</p>
              <h3 className="mt-1 text-xl font-semibold text-white">Delivery audit trail</h3>
            </div>
          </div>

          {isLoading ? (
            <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-6 text-sm text-slate-300">
              Loading delivery audit trail...
            </div>
          ) : recentNotifications.length === 0 ? (
            <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-6 text-sm leading-6 text-slate-400">
              No notification attempts have been recorded yet.
            </div>
          ) : (
            <div className="mt-6 space-y-3">
              {recentNotifications.map((notification) => (
                <article
                  key={notification.id}
                  className="rounded-[1.25rem] border border-white/10 bg-white/[0.03] p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs capitalize text-slate-300">
                      {notification.notification_type.replaceAll("_", " ")}
                    </span>
                    <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs capitalize text-slate-300">
                      {notification.status}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-200">{notification.message_preview}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.22em] text-slate-500">
                    {formatTimestamp(notification.created_at)}
                  </p>
                  {notification.error_message ? (
                    <p className="mt-3 rounded-[1rem] border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">
                      {notification.error_message}
                    </p>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
