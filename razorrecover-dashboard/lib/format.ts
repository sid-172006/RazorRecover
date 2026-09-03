export function formatRupees(amount: number | null): string {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

export function formatCategory(category: string | null): string {
  if (!category) return "Unclassified";
  return category
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export function formatAction(action: string | null): string {
  if (!action) return "—";
  return action
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}

export type StatusTone = "recovered" | "unresolved" | "review" | "rejected" | "pending";

export function statusToneFor(failure: {
  status: string;
  execution_result: string | null;
  policy_approved: string | null;
}): StatusTone {
  if (failure.execution_result === "recovered") return "recovered";
  if (failure.status === "manual_review_required") return "review";
  if (failure.policy_approved === "rejected") return "rejected";
  if (failure.execution_result === "unresolved" || failure.execution_result === "failed") return "unresolved";
  return "pending";
}

export function statusLabel(failure: { status: string }): string {
  const map: Record<string, string> = {
    received: "Received",
    classified: "Classified",
    decided: "Decided",
    executed: "Recovered",
    manual_review_required: "Manual review",
    recovery_exhausted: "Unresolved",
  };
  return map[failure.status] ?? failure.status;
}

export const TONE_CLASSES: Record<StatusTone, { dot: string; text: string; bg: string }> = {
  recovered: { dot: "bg-recovered", text: "text-recovered", bg: "bg-recovered-soft" },
  unresolved: { dot: "bg-unresolved", text: "text-unresolved", bg: "bg-unresolved-soft" },
  review: { dot: "bg-review", text: "text-review", bg: "bg-review-soft" },
  rejected: { dot: "bg-rejected", text: "text-rejected", bg: "bg-rejected-soft" },
  pending: { dot: "bg-ink-faint", text: "text-ink-muted", bg: "bg-rule" },
};
