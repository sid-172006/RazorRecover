import { Metrics } from "@/lib/api";
import { formatRupees } from "@/lib/format";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 py-4 px-5 first:pl-0">
      <span className="text-[13px] text-ink-muted">{label}</span>
      <span className="font-mono text-2xl text-ink tabular-nums">{value}</span>
    </div>
  );
}

export function MetricsStrip({ metrics }: { metrics: Metrics }) {
  const recoveryRate =
    metrics.recovery_rate === null ? "—" : `${Math.round(metrics.recovery_rate * 100)}%`;

  return (
    <div>
      <div className="flex flex-wrap divide-x divide-rule">
        <Stat label="Total failures" value={String(metrics.total_failures)} />
        <Stat label="Recovered" value={String(metrics.recovered_count)} />
        <Stat label="Amount recovered" value={formatRupees(metrics.recovered_amount)} />
        <Stat label="Retries avoided" value={String(metrics.retries_avoided ?? 0)} />
        <Stat label="Unresolved / failed" value={String(metrics.unresolved_or_failed_count)} />
        <Stat label="Manual review" value={String(metrics.manual_review_count)} />
        <Stat label="Recovery rate" value={recoveryRate} />
        <Stat label="Avg recovery time" value={metrics.avg_time_to_recovery !== undefined ? `${metrics.avg_time_to_recovery}s` : "—"} />
        <Stat label="Policy violations" value={String(metrics.policy_violations_count ?? 0)} />
      </div>
      <p className="text-[13px] text-ink-faint pt-2 border-t border-rule">{metrics.note}</p>
    </div>
  );
}
