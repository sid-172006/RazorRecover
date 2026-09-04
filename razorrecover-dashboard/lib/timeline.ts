import { AuditEvent } from "./api";
import { formatAction, formatCategory } from "./format";

export type TimelineEntry = {
  title: string;
  description: string;
  tone: "neutral" | "positive" | "negative" | "caution";
};

function safeParse(detail: string | null): Record<string, unknown> {
  if (!detail) return {};
  try {
    return JSON.parse(detail);
  } catch {
    return {};
  }
}

export function toTimelineEntry(event: AuditEvent): TimelineEntry {
  const d = safeParse(event.detail);

  switch (event.event_type) {
    case "webhook_received":
      return {
        title: "Payment failed",
        description: `${d.error_code ?? "Unknown error"} — ${d.error_reason ?? "no specific reason given"}`,
        tone: "neutral",
      };

    case "rule_classified":
      return {
        title: `Classified by rule — ${formatCategory(String(d.category ?? ""))}`,
        description: String(d.reason ?? ""),
        tone: "neutral",
      };

    case "rule_classification_inconclusive":
      return {
        title: "Tier 1: No rule matched",
        description: "Error was too ambiguous for deterministic rules — escalated to Google Gemini AI agent.",
        tone: "caution",
      };

    case "gemini_classified":
    case "claude_classified": {
      const confidence = typeof d.confidence === "number" ? `${Math.round(d.confidence * 100)}%` : "?";
      const model = d.model ? String(d.model) : "Google Gemini";
      return {
        title: `Tier 2: Classified by ${model} — confidence ${confidence}`,
        description: `${formatAction(String(d.recommended_action ?? ""))} recommended. ${d.reason ?? ""}`,
        tone: "positive",
      };
    }

    case "claude_classification_failed":
      return {
        title: "AI classification unavailable",
        description: String(d.note ?? "Call failed or returned invalid output — routed to manual review rather than guessing."),
        tone: "caution",
      };

    case "policy_checked":
      return d.approved
        ? { title: "Policy: approved", description: "Recommendation cleared all safety checks.", tone: "positive" }
        : {
            title: "Policy: rejected",
            description: String(d.rejection_reason ?? "Rejected by policy."),
            tone: "negative",
          };

    case "customer_notified":
      return {
        title: `Customer notified — ${formatAction(String(d.action ?? ""))}`,
        description: String(d.message ?? ""),
        tone: "neutral",
      };

    case "action_executed": {
      const result = String(d.result ?? "");
      return {
        title: `Action executed — ${formatAction(String(d.action ?? ""))}`,
        description: `Result: ${result}${d.action_execution_mode ? ` (${d.action_execution_mode})` : ""}`,
        tone: result === "recovered" ? "positive" : "negative",
      };
    }

    case "kill_switch_active":
      return {
        title: "Kill switch active",
        description: "Execution was skipped and the case was sent to manual review.",
        tone: "caution",
      };

    default:
      return { title: event.event_type, description: event.detail ?? "", tone: "neutral" };
  }
}
