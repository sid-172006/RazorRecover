"use client";

import { AuditEvent, PaymentFailure } from "@/lib/api";
import { toTimelineEntry } from "@/lib/timeline";
import { formatCategory, formatRupees, formatTimestamp } from "@/lib/format";
import { ProvenanceTag } from "./StatusBadge";

const TONE_DOT: Record<string, string> = {
  neutral: "bg-ink-faint",
  positive: "bg-recovered",
  negative: "bg-unresolved",
  caution: "bg-review",
};

export function DecisionTimeline({
  failure,
  events,
  loading,
}: {
  failure: PaymentFailure | null;
  events: AuditEvent[];
  loading: boolean;
}) {
  if (!failure) {
    return (
      <div className="py-16 text-center text-ink-muted text-sm">
        Select a failure on the left to see its full decision trail.
      </div>
    );
  }

  return (
    <div>
      <header className="pb-5 mb-5 border-b border-rule">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="font-serif text-xl text-ink">{formatCategory(failure.category)}</h2>
          <span className="font-mono text-lg text-ink tabular-nums">{formatRupees(failure.amount)}</span>
        </div>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <span className="font-mono text-[13px] text-ink-muted">
            {failure.razorpay_payment_id ?? failure.id}
          </span>
          {failure.customer_ref_masked && (
            <span className="font-mono text-[12px] text-ink-muted bg-paper-soft border border-rule px-1.5 py-0.5 rounded">
              Customer: {failure.customer_ref_masked}
            </span>
          )}
          <ProvenanceTag mode={failure.execution_mode} />
        </div>
        {failure.error_description && (
          <p className="text-[14px] text-ink-muted mt-3">{failure.error_description}</p>
        )}
      </header>

      {loading ? (
        <p className="text-sm text-ink-muted">Loading audit trail…</p>
      ) : events.length === 0 ? (
        <p className="text-sm text-ink-muted">No audit events recorded for this failure yet.</p>
      ) : (
        <ol className="relative">
          {events.map((event, i) => {
            const entry = toTimelineEntry(event);
            const isLast = i === events.length - 1;
            return (
              <li key={event.id} className="relative pl-6 pb-6 last:pb-0">
                {!isLast && (
                  <span className="absolute left-[5px] top-3 bottom-0 w-px bg-rule" aria-hidden />
                )}
                <span
                  className={`absolute left-0 top-1.5 h-[11px] w-[11px] rounded-full border-2 border-paper ${TONE_DOT[entry.tone]}`}
                  aria-hidden
                />
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="text-[14px] font-medium text-ink">{entry.title}</h3>
                  <time className="font-mono text-[12px] text-ink-faint shrink-0">
                    {formatTimestamp(event.created_at)}
                  </time>
                </div>
                {entry.description && (
                  <p className="text-[13px] text-ink-muted mt-0.5">{entry.description}</p>
                )}
              </li>
            );
          })}
        </ol>
      )}

      {failure.customer_message && (
        <div className="mt-6 pt-5 border-t border-rule">
          <h4 className="text-[13px] text-ink-muted mb-1.5">Customer-facing message</h4>
          <p className="text-[14px] text-ink italic">&ldquo;{failure.customer_message}&rdquo;</p>
        </div>
      )}
    </div>
  );
}
