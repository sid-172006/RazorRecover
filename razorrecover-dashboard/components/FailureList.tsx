import { PaymentFailure } from "@/lib/api";
import { formatCategory, formatRupees, statusToneFor, statusLabel } from "@/lib/format";
import { StatusBadge, ProvenanceTag } from "./StatusBadge";

export function FailureList({
  failures,
  selectedId,
  onSelect,
}: {
  failures: PaymentFailure[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (failures.length === 0) {
    return (
      <div className="py-10 text-center text-ink-muted text-sm">
        No failures recorded yet. Once a webhook lands, it'll appear here.
      </div>
    );
  }

  return (
    <ul className="divide-y divide-rule">
      {failures.map((f) => {
        const tone = statusToneFor(f);
        const selected = f.id === selectedId;
        return (
          <li key={f.id}>
            <button
              onClick={() => onSelect(f.id)}
              className={`w-full text-left py-3 pr-3 pl-3 -ml-3 transition-colors ${
                selected ? "bg-accent-soft" : "hover:bg-rule/40"
              }`}
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-mono text-[13px] text-ink-muted truncate">
                  {f.razorpay_payment_id ?? f.id.slice(0, 8)}
                </span>
                <span className="font-mono text-[13px] text-ink tabular-nums shrink-0">
                  {formatRupees(f.amount)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3 mt-1">
                <span className="text-[14px] text-ink truncate">{formatCategory(f.category)}</span>
                <ProvenanceTag mode={f.execution_mode} />
              </div>
              <div className="mt-1.5 flex items-center justify-between gap-2">
                <StatusBadge tone={tone} label={statusLabel(f)} />
                {f.decided_by && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                      f.decided_by === "rule"
                        ? "bg-paper text-ink-muted border-rule"
                        : "bg-purple-50 text-purple-700 border-purple-200 font-semibold"
                    }`}
                  >
                    {f.decided_by === "rule" ? "⚡ Rule" : "🤖 Gemini"}
                  </span>
                )}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
