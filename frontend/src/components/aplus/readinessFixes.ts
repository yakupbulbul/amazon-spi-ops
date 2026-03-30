import type { AplusReadinessIssue } from "../../lib/api";

export type AplusReadinessFixAction = {
  label: string;
  description: string;
};

export function getReadinessIssueKey(issue: AplusReadinessIssue): string {
  return `${issue.code}:${issue.field_label ?? issue.message}`;
}
