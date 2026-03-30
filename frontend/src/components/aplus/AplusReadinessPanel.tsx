import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Languages,
  LoaderCircle,
  Package2,
  ShieldAlert,
  WandSparkles,
} from "lucide-react";

import type { AplusDraftResponse, AplusReadinessIssue, ProductListItem } from "../../lib/api";
import { getReadinessIssueKey, type AplusReadinessFixAction } from "./readinessFixes";
import { AplusDraftStateBadge } from "./AplusDraftStateBadge";
import { formatLanguageLabel } from "./languages";


type AplusReadinessPanelProps = {
  draft: AplusDraftResponse | null;
  product: ProductListItem | null;
  hasUnsavedChanges: boolean;
  getBlockingIssueFixAction?: (issue: AplusReadinessIssue) => AplusReadinessFixAction | null;
  onApplyBlockingIssueFix?: (issue: AplusReadinessIssue) => void;
  blockingIssueFixInFlightKey?: string | null;
};


export function AplusReadinessPanel({
  draft,
  product,
  hasUnsavedChanges,
  getBlockingIssueFixAction,
  onApplyBlockingIssueFix,
  blockingIssueFixInFlightKey,
}: AplusReadinessPanelProps) {
  const readiness = draft?.readiness_report ?? null;

  if (!draft || !readiness) {
    return (
      <section className="rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] px-5 py-5">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-4 w-4 text-slate-500" />
          <div>
            <p className="text-sm font-medium text-white">Publish readiness</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Generate and validate a draft to see the Amazon-focused publish checklist.
            </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-[1.5rem] bg-white/[0.03] px-5 py-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Publish readiness</p>
          <h4 className="mt-2 text-lg font-semibold text-white">
            {readiness.is_publish_ready ? "Ready for Amazon submit" : "Needs review before publish"}
          </h4>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Amazon-facing checks look for blocking copy issues, weak sections, missing structure, and
            verbose modules before the real SP-API submit flow.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <AplusDraftStateBadge status={draft.status} />
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-200">
            <Package2 className="h-3.5 w-3.5 text-slate-400" />
            {product?.sku ?? draft.product_sku}
          </span>
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-200">
            <Languages className="h-3.5 w-3.5 text-slate-400" />
            {formatLanguageLabel(draft.source_language)}
            {draft.auto_translate ? ` -> ${formatLanguageLabel(draft.target_language)}` : ""}
          </span>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <SummaryPill
          tone={readiness.is_publish_ready ? "success" : "danger"}
          label="Blocking issues"
          value={String(readiness.blocking_errors.length)}
        />
        <SummaryPill
          tone={readiness.warnings.length > 0 ? "warning" : "neutral"}
          label="Warnings"
          value={String(readiness.warnings.length)}
        />
        <SummaryPill
          tone={readiness.missing_sections.length > 0 ? "warning" : "neutral"}
          label="Missing sections"
          value={String(readiness.missing_sections.length)}
        />
      </div>

      <div className="mt-5 grid gap-5 2xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <div className="space-y-4">
          <IssueList
            title="Blocking issues"
            emptyMessage="No blocking issues found. This validated draft is safe to submit in the current Amazon subset."
            icon={AlertTriangle}
            tone="danger"
            items={readiness.blocking_errors.map((issue) => {
              const action = getBlockingIssueFixAction?.(issue) ?? null;
              return {
                key: getReadinessIssueKey(issue),
                title: issue.field_label ?? "Draft issue",
                message: issue.message,
                action:
                  action && onApplyBlockingIssueFix
                    ? {
                        ...action,
                        pending: blockingIssueFixInFlightKey === getReadinessIssueKey(issue),
                        onClick: () => onApplyBlockingIssueFix(issue),
                      }
                    : null,
              };
            })}
          />
          <IssueList
            title="Warnings"
            emptyMessage="No warnings. The draft is concise and differentiated enough for review."
            icon={Info}
            tone="warning"
            items={readiness.warnings.map((issue) => ({
              key: getReadinessIssueKey(issue),
              title: issue.field_label ?? "Editorial warning",
              message: issue.message,
              action: null,
            }))}
          />
        </div>

        <div className="space-y-4">
          <article className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Checklist context</p>
            <dl className="mt-4 space-y-3">
              <MetaRow label="Product" value={draft.product_title} />
              <MetaRow label="Marketplace" value={draft.marketplace_id} />
              <MetaRow label="Checked payload" value={readiness.checked_payload} />
              <MetaRow
                label="Draft mode"
                value={draft.variant_role === "translated" ? "Translated variant" : "Original draft"}
              />
            </dl>
          </article>

          <article className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Missing or recommended sections</p>
            {readiness.missing_sections.length === 0 ? (
              <div className="mt-4 flex items-start gap-3 rounded-[1rem] bg-emerald-500/10 px-3 py-3 text-sm text-emerald-100">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                <span>Core publish structure is present for this draft.</span>
              </div>
            ) : (
              <div className="mt-4 space-y-2">
                {readiness.missing_sections.map((section) => (
                  <div
                    key={section}
                    className="rounded-[1rem] border border-amber-300/15 bg-amber-500/10 px-3 py-3 text-sm text-amber-100"
                  >
                    {section}
                  </div>
                ))}
              </div>
            )}
          </article>

          {hasUnsavedChanges ? (
            <div className="rounded-[1.25rem] border border-sky-300/20 bg-sky-500/10 px-4 py-4 text-sm leading-6 text-sky-100">
              The checklist reflects the last saved draft. Validate again after editing to refresh publish
              readiness.
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

type SummaryPillProps = {
  label: string;
  value: string;
  tone: "success" | "warning" | "danger" | "neutral";
};

function SummaryPill({ label, value, tone }: SummaryPillProps) {
  const toneClass =
    tone === "success"
      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-100"
      : tone === "warning"
        ? "border-amber-300/20 bg-amber-500/10 text-amber-100"
        : tone === "danger"
          ? "border-rose-400/20 bg-rose-500/10 text-rose-100"
          : "border-white/10 bg-slate-950/60 text-slate-200";

  return (
    <article className={["rounded-[1.25rem] border px-4 py-4", toneClass].join(" ")}>
      <p className="text-xs uppercase tracking-[0.2em] opacity-80">{label}</p>
      <p className="mt-3 text-2xl font-semibold">{value}</p>
    </article>
  );
}

type IssueListItem = {
  key: string;
  title: string;
  message: string;
  action: {
    label: string;
    description: string;
    pending: boolean;
    onClick: () => void;
  } | null;
};

type IssueListProps = {
  title: string;
  emptyMessage: string;
  icon: typeof AlertTriangle;
  tone: "warning" | "danger";
  items: IssueListItem[];
};

function IssueList({ title, emptyMessage, icon: Icon, tone, items }: IssueListProps) {
  const emptyTone =
    tone === "danger"
      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-100"
      : "border-white/10 bg-slate-950/60 text-slate-300";

  return (
    <article className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{title}</p>
      {items.length === 0 ? (
        <div className={["mt-4 rounded-[1rem] border px-3 py-3 text-sm leading-6", emptyTone].join(" ")}>
          {emptyMessage}
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <div
              key={item.key}
              className={[
                "rounded-[1rem] border px-3 py-3",
                tone === "danger"
                  ? "border-rose-400/15 bg-rose-500/10"
                  : "border-amber-300/15 bg-amber-500/10",
              ].join(" ")}
            >
              <div className="flex items-start gap-3">
                <Icon
                  className={[
                    "mt-0.5 h-4 w-4 shrink-0",
                    tone === "danger" ? "text-rose-200" : "text-amber-200",
                  ].join(" ")}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-white">{item.title}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-300">{item.message}</p>
                  {item.action ? (
                    <div className="mt-3 rounded-[0.95rem] border border-white/10 bg-black/20 px-3 py-3">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-sm font-medium text-white">Recommended fix</p>
                          <p className="mt-1 text-sm leading-6 text-slate-400">{item.action.description}</p>
                        </div>
                        <button
                          type="button"
                          onClick={item.action.onClick}
                          disabled={item.action.pending}
                          className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          {item.action.pending ? (
                            <>
                              <LoaderCircle className="h-4 w-4 animate-spin" />
                              Applying...
                            </>
                          ) : (
                            <>
                              <WandSparkles className="h-4 w-4" />
                              {item.action.label}
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

type MetaRowProps = {
  label: string;
  value: string;
};

function MetaRow({ label, value }: MetaRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-white/5 pb-3 last:border-b-0 last:pb-0">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-right text-sm text-slate-200">{value}</dd>
    </div>
  );
}
