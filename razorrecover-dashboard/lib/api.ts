const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type PaymentFailure = {
  id: string;
  razorpay_event_id: string;
  razorpay_payment_id: string | null;
  subscription_id: string | null;
  execution_mode: string;
  amount: number | null;
  error_code: string | null;
  error_description: string | null;
  error_source: string | null;
  error_step: string | null;
  error_reason: string | null;
  category: string | null;
  confidence: number | null;
  decided_by: string | null;
  recommended_action: string | null;
  decision_reason: string | null;
  customer_message: string | null;
  policy_approved: string | null;
  policy_rejection_reason: string | null;
  executed_action: string | null;
  action_execution_mode: string | null;
  execution_result: string | null;
  customer_ref_masked: string | null;
  status: string;
  created_at: string;
};

export type AuditEvent = {
  id: string;
  event_type: string;
  detail: string | null;
  created_at: string;
};

export type Metrics = {
  total_failures: number;
  classified_by_rule: number;
  classified_by_claude: number;
  policy_rejected_count: number;
  policy_violations_count?: number;
  recovered_count: number;
  recovered_amount: number;
  unresolved_or_failed_count: number;
  manual_review_count: number;
  retries_avoided: number;
  total_amount_at_risk: number;
  recovery_rate: number | null;
  avg_time_to_recovery?: number;
  category_counts?: Record<string, number>;
  recovery_by_category?: Record<string, number>;
  note: string;
};

export type SimulationScenario = {
  title: string;
  story: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  default_amount: number;
  plan_name: string;
  error_code: string;
  error_description: string;
  error_source: string;
  error_step: string;
  error_reason: string;
  recovery_method: string;
  action_cta: string;
};

export type SimulationResponse = {
  payment_failure: PaymentFailure;
  scenario: SimulationScenario;
  raw_payload: any;
  signature: string;
};

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Request to ${path} failed with status ${res.status}`);
  }
  return res.json();
}

async function apiPost<T>(path: string, body: any): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Request to ${path} failed with status ${res.status}: ${errorText}`);
  }
  return res.json();
}

export function fetchFailures(limit = 50): Promise<PaymentFailure[]> {
  return apiGet<PaymentFailure[]>(`/payment-failures?limit=${limit}`);
}

export function fetchAuditTrail(failureId: string): Promise<AuditEvent[]> {
  return apiGet<AuditEvent[]>(`/payment-failures/${failureId}/audit-trail`);
}

export function fetchMetrics(): Promise<Metrics> {
  return apiGet<Metrics>(`/metrics`);
}

export function fetchScenarios(): Promise<Record<string, SimulationScenario>> {
  return apiGet<Record<string, SimulationScenario>>(`/simulation/scenarios`);
}

export function simulateFailure(
  scenario: string,
  amount?: number,
  errorDescription?: string
): Promise<SimulationResponse> {
  return apiPost<SimulationResponse>(`/simulate-failure`, {
    scenario,
    amount,
    error_description: errorDescription,
  });
}

export function resolveFailure(
  failureId: string,
  resolutionMethod: string = "upi_quickpay"
): Promise<{ status: string; payment_failure: PaymentFailure }> {
  return apiPost<{ status: string; payment_failure: PaymentFailure }>(
    `/payment-failures/${failureId}/resolve`,
    { resolution_method: resolutionMethod }
  );
}

