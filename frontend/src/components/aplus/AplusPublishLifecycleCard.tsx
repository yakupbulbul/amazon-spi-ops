import { AlertTriangle, CheckCircle2, Clock3, LoaderCircle, ShieldAlert, UploadCloud } from "lucide-react";

import type { AplusPublishJobResponse } from "../../lib/api";

const lifecycleSteps = [
  { key: "draft", label: "Draft" },
  { key: "assets_prepared", label: "Assets prepared" },
  { key: "validated", label: "Validated" },
  { key: "submitted", label: "Submitted" },
  { key: "in_review", label: "In review" },
  { key: "approved", label: "Approved" },
] as const;

function formatStatusLabel(status: string): string {
  return status.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function getStepIndex(status: string): number {
  const index = lifecycleSteps.findIndex((step) => step.key === status);
  if (index >= 0) {
    return index;
  }

  if (status === "rejected" || status === "failed") {
    return lifecycleSteps.findIndex((step) => step.key === "submitted");
  }

  return 0;
}

function getStatusAccent(status: string): string {
  if (status === "approved") {
    return "border-emerald-400/20 bg-emerald-500/10 text-emerald-100";
  }
  if (status === "rejected" || status === "failed") {
    return "border-rose-400/20 bg-rose-500/10 text-rose-100";
  }
  if (status === "in_review" || status === "submitted" || status === "validated" || status === "assets_prepared") {
    return "border-sky-300/20 bg-sky-500/10 text-sky-100";
  }
  return "border-white/10 bg-white/[0.03] text-slate-200";
}

function getStatusIcon(status: string) {
  if (status === "approved") {
    return <CheckCircle2 className="h-4 w-4" />;
  }
  if (status === "rejected" || status === "failed") {
    return <ShieldAlert className="h-4 w-4" />;
  }
  if (status === "in_review") {
    return <LoaderCircle className="h-4 w-4 animate-spin" />;
  }
  if (status === "submitted" || status === "validated" || status === "assets_prepared") {
    return <UploadCloud className="h-4 w-4" />;
  }
  return <Clock3 className="h-4 w-4" />;
}

type AplusPublishLifecycleCardProps = {
  publishJob: AplusPublishJobResponse | null;
  formatTimestamp: (value: string) => string;
};

export function AplusPublishLifecycleCard({
  publishJob,
  formatTimestamp,
}: AplusPublishLifecycleCardProps) {
  if (!publishJob) {
    return (
      <div className="rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-5 text-sm leading-6 text-slate-400">
        No Amazon submit job yet. Validate a supported draft, then submit it to start asset preparation,
        contract validation, and Amazon review tracking.
      </div>
    );
  }

  const currentStepIndex = getStepIndex(publishJob.status);
  const isRejected = publishJob.status === "rejected" || publishJob.status === "failed";

  return (
    <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Amazon review lifecycle</p>
          <h4 className="mt-2 text-lg font-semibold text-white">Live publish status</h4>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Track asset preparation, request submission, and Amazon review without leaving the Studio.
          </p>
        </div>
        <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm ${getStatusAccent(publishJob.status)}`}>
          {getStatusIcon(publishJob.status)}
          <span>{formatStatusLabel(publishJob.status)}</span>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
        <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Reference key</p>
          <p className="mt-2 break-all text-sm text-slate-200">
            {publishJob.content_reference_key ?? "Pending Amazon reference"}
          </p>
        </div>
        <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Submitted</p>
          <p className="mt-2 text-sm text-slate-200">
            {publishJob.submitted_at ? formatTimestamp(publishJob.submitted_at) : "Not submitted yet"}
          </p>
        </div>
        <div className="rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Latest update</p>
          <p className="mt-2 text-sm text-slate-200">
            {publishJob.completed_at
              ? formatTimestamp(publishJob.completed_at)
              : formatTimestamp(publishJob.created_at)}
          </p>
        </div>
      </div>

      <ol className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {lifecycleSteps.map((step, index) => {
          const isComplete = index < currentStepIndex || (publishJob.status === "approved" && index <= currentStepIndex);
          const isCurrent = !isRejected && index === currentStepIndex;
          return (
            <li
              key={step.key}
              className={[
                "rounded-[1.25rem] border px-4 py-3 text-sm",
                isComplete
                  ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-100"
                  : isCurrent
                    ? "border-sky-300/20 bg-sky-500/10 text-sky-100"
                    : "border-white/10 bg-slate-950/40 text-slate-500",
              ].join(" ")}
            >
              <p className="text-xs uppercase tracking-[0.2em] opacity-70">Step {index + 1}</p>
              <p className="mt-2 font-medium">{step.label}</p>
            </li>
          );
        })}
      </ol>

      {publishJob.rejection_reasons.length > 0 ? (
        <div className="mt-5 rounded-[1.25rem] border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">Amazon rejected this submission</p>
              <ul className="mt-2 space-y-2 text-sm leading-6">
                {publishJob.rejection_reasons.map((reason: string) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : null}

      {publishJob.warnings.length > 0 ? (
        <div className="mt-4 rounded-[1.25rem] border border-amber-300/15 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          <p className="font-medium">Amazon warnings</p>
          <ul className="mt-2 space-y-2 leading-6">
            {publishJob.warnings.map((warning: string) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {publishJob.error_message && publishJob.rejection_reasons.length === 0 ? (
        <div className="mt-4 rounded-[1.25rem] border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          <p className="font-medium">Latest publish issue</p>
          <p className="mt-2 leading-6">{publishJob.error_message}</p>
        </div>
      ) : null}
    </div>
  );
}
