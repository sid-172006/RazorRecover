import { StatusTone, TONE_CLASSES } from "@/lib/format";

export function StatusBadge({ tone, label }: { tone: StatusTone; label: string }) {
  const classes = TONE_CLASSES[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 text-[13px] ${classes.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${classes.dot}`} aria-hidden />
      {label}
    </span>
  );
}

export function ProvenanceTag({ mode }: { mode: string | null }) {
  if (!mode) return null;
  const isLive = mode === "LIVE_TEST_MODE";
  return (
    <span
      className={`font-mono text-[11px] px-1.5 py-0.5 rounded-sm border ${
        isLive ? "border-accent text-accent" : "border-rule-strong text-ink-muted"
      }`}
      title={
        isLive
          ? "This event came from a real Razorpay test-mode webhook."
          : "This outcome was simulated, not from a real customer/bank response."
      }
    >
      {mode}
    </span>
  );
}
