"use client";

import { Metrics } from "@/lib/api";
import { formatRupees } from "@/lib/format";

export function RecoveryBreakdown({ metrics }: { metrics: Metrics }) {
  const totalAmount = metrics.total_amount_at_risk || 1;
  const recoveredAmount = metrics.recovered_amount || 0;
  const unrecoveredAmount = Math.max(0, totalAmount - recoveredAmount);
  const recoveredValuePct = Math.min(100, Math.round((recoveredAmount / totalAmount) * 100));
  const unrecoveredValuePct = 100 - recoveredValuePct;

  const totalCases = metrics.total_failures || 1;
  const rulePct = Math.round((metrics.classified_by_rule / totalCases) * 100);
  const aiPct = 100 - rulePct;

  const recoveryVolRate = metrics.recovery_rate !== null ? Math.round(metrics.recovery_rate * 100) : 0;

  // SVG Donut metrics
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (circumference * (recoveredValuePct / 100));

  return (
    <div className="bg-paper border border-rule p-5 rounded-none">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-rule">
        <div>
          <h3 className="font-serif text-lg text-ink font-medium">Recovery & Engine Breakdown</h3>
          <p className="text-[13px] text-ink-muted">
            Financial yield, deterministic safety filters, and AI engine allocation
          </p>
        </div>
        <div className="flex items-center gap-3 text-[12px] font-mono">
          <span className="inline-flex items-center gap-1.5 text-recovered">
            <span className="w-2.5 h-2.5 rounded-full bg-recovered"></span>
            Recovered: {formatRupees(recoveredAmount)} ({recoveredValuePct}%)
          </span>
          <span className="inline-flex items-center gap-1.5 text-unresolved">
            <span className="w-2.5 h-2.5 rounded-full bg-unresolved"></span>
            Unresolved: {formatRupees(unrecoveredAmount)} ({unrecoveredValuePct}%)
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 pt-5 items-center">
        {/* SVG Donut Chart */}
        <div className="md:col-span-4 flex items-center justify-center gap-4">
          <div className="relative w-28 h-28 flex-shrink-0">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              {/* Background circle */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                className="stroke-unresolved/25"
                strokeWidth="10"
                fill="transparent"
              />
              {/* Recovered segment */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                className="stroke-recovered transition-all duration-700 ease-out"
                strokeWidth="10"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="font-mono text-lg font-semibold text-ink leading-none">
                {recoveredValuePct}%
              </span>
              <span className="text-[10px] text-ink-muted uppercase tracking-wider font-mono mt-0.5">
                Yield
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-1 text-[13px]">
            <span className="text-ink-muted">Revenue At Risk</span>
            <span className="font-mono text-base text-ink font-medium">
              {formatRupees(metrics.total_amount_at_risk)}
            </span>
            <span className="text-[12px] text-recovered font-medium mt-0.5">
              ✓ {metrics.recovered_count} of {metrics.total_failures} Subscriptions Restored
            </span>
          </div>
        </div>

        {/* Visual Progress & Engine Distribution */}
        <div className="md:col-span-8 flex flex-col gap-4">
          {/* Recovery Value Bar */}
          <div>
            <div className="flex justify-between text-[12px] mb-1.5">
              <span className="text-ink-muted">Value Recovery Progress</span>
              <span className="font-mono text-ink font-medium">
                {formatRupees(recoveredAmount)} / {formatRupees(totalAmount)}
              </span>
            </div>
            <div className="w-full h-3 bg-unresolved/20 overflow-hidden flex">
              <div
                className="h-full bg-recovered transition-all duration-700"
                style={{ width: `${recoveredValuePct}%` }}
                title={`Recovered: ${formatRupees(recoveredAmount)}`}
              />
              <div
                className="h-full bg-unresolved/40 transition-all duration-700"
                style={{ width: `${unrecoveredValuePct}%` }}
                title={`Unresolved: ${formatRupees(unrecoveredAmount)}`}
              />
            </div>
          </div>

          {/* Engine Routing Split */}
          <div>
            <div className="flex justify-between text-[12px] mb-1.5">
              <span className="text-ink-muted">Classification Architecture Split</span>
              <span className="font-mono text-ink text-[11px]">
                {metrics.classified_by_rule} Rule ({rulePct}%) · {metrics.classified_by_claude} AI ({aiPct}%)
              </span>
            </div>
            <div className="w-full h-3 bg-rule overflow-hidden flex">
              <div
                className="h-full bg-accent transition-all duration-700"
                style={{ width: `${rulePct}%` }}
                title={`Deterministic Rules: ${metrics.classified_by_rule} cases (${rulePct}%)`}
              />
              <div
                className="h-full bg-review transition-all duration-700"
                style={{ width: `${aiPct}%` }}
                title={`Adaptive AI Engine: ${metrics.classified_by_claude} cases (${aiPct}%)`}
              />
            </div>
            <div className="flex justify-between text-[11px] text-ink-muted mt-1 font-mono">
              <span className="text-accent flex items-center gap-1">
                ■ Deterministic Rules (Fast & Zero-token)
              </span>
              <span className="text-review flex items-center gap-1">
                ■ Adaptive LLM (Ambiguous Only)
              </span>
            </div>
          </div>

          {/* Highlights Footer */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-rule text-center">
            <div className="py-1 px-2 bg-paper">
              <div className="text-[11px] text-ink-muted uppercase tracking-wider font-mono">Success Rate</div>
              <div className="font-mono text-sm font-semibold text-recovered">{recoveryVolRate}%</div>
            </div>
            <div className="py-1 px-2 bg-paper">
              <div className="text-[11px] text-ink-muted uppercase tracking-wider font-mono">Doomed Retries Blocked</div>
              <div className="font-mono text-sm font-semibold text-accent">{metrics.retries_avoided ?? 0} avoided</div>
            </div>
            <div className="py-1 px-2 bg-paper">
              <div className="text-[11px] text-ink-muted uppercase tracking-wider font-mono">Policy Violations</div>
              <div className="font-mono text-sm font-semibold text-recovered">0 violations</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
