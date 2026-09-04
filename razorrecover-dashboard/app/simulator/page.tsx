"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  SimulationScenario,
  SimulationResponse,
  fetchScenarios,
  simulateFailure,
  resolveFailure,
  PaymentFailure,
} from "@/lib/api";

type CheckoutState = "idle" | "processing" | "failed" | "resolving" | "recovered";

export default function SimulatorPage() {
  const [scenarios, setScenarios] = useState<Record<string, SimulationScenario>>({});
  const [selectedScenarioKey, setSelectedScenarioKey] = useState<string>("insufficient_balance");
  const [checkoutState, setCheckoutState] = useState<CheckoutState>("idle");
  const [simulationData, setSimulationData] = useState<SimulationResponse | null>(null);
  const [currentFailure, setCurrentFailure] = useState<PaymentFailure | null>(null);
  const [showJson, setShowJson] = useState<boolean>(false);
  const [loadingScenarios, setLoadingScenarios] = useState<boolean>(true);
  const [pipelineStep, setPipelineStep] = useState<number>(0);
  const [amountInput, setAmountInput] = useState<number>(1499);

  useEffect(() => {
    fetchScenarios()
      .then((data) => {
        setScenarios(data);
        if (Object.keys(data).length > 0 && !data[selectedScenarioKey]) {
          const firstKey = Object.keys(data)[0];
          setSelectedScenarioKey(firstKey);
          setAmountInput(data[firstKey].default_amount);
        } else if (data[selectedScenarioKey]) {
          setAmountInput(data[selectedScenarioKey].default_amount);
        }
      })
      .catch((err) => {
        console.error("Failed to load scenarios:", err);
      })
      .finally(() => setLoadingScenarios(false));
  }, []);

  const currentScenario = scenarios[selectedScenarioKey] || {
    title: "Month-End Low Balance",
    story: "Rahul's debit card has low balance on month-end.",
    customer_name: "Rahul Verma",
    customer_email: "rahul.verma@example.com",
    customer_phone: "+91 98765 43210",
    default_amount: 1499.0,
    plan_name: "Apex Cloud Pro (Monthly)",
    error_code: "GATEWAY_ERROR",
    error_description: "Your payment could not be completed due to insufficient account balance.",
    error_reason: "insufficient_funds",
    recovery_method: "UPI QuickPay",
    action_cta: "Pay ₹1,499 via UPI QuickPay",
  };

  const handleSelectScenario = (key: string) => {
    setSelectedScenarioKey(key);
    setCheckoutState("idle");
    setSimulationData(null);
    setCurrentFailure(null);
    setPipelineStep(0);
    if (scenarios[key]) {
      setAmountInput(scenarios[key].default_amount);
    }
  };

  const handleTriggerPayment = async () => {
    setCheckoutState("processing");
    setPipelineStep(1);

    try {
      // Simulate network gateway trip for realism
      await new Promise((r) => setTimeout(r, 900));

      const res = await simulateFailure(selectedScenarioKey, amountInput);
      setSimulationData(res);
      setCurrentFailure(res.payment_failure);
      setCheckoutState("failed");

      // Animate pipeline stages sequentially
      setPipelineStep(2);
      await new Promise((r) => setTimeout(r, 450));
      setPipelineStep(3);
      await new Promise((r) => setTimeout(r, 450));
      setPipelineStep(4);
    } catch (err) {
      console.error("Simulation failed:", err);
      alert("Failed to reach backend simulation endpoint. Is uvicorn running on port 8000?");
      setCheckoutState("idle");
      setPipelineStep(0);
    }
  };

  const handleCustomerResolve = async () => {
    if (!currentFailure) return;
    setCheckoutState("resolving");

    try {
      await new Promise((r) => setTimeout(r, 800));
      const res = await resolveFailure(currentFailure.id, "upi_quickpay");
      setCurrentFailure(res.payment_failure);
      setCheckoutState("recovered");
      setPipelineStep(5);
    } catch (err) {
      console.error("Resolution failed:", err);
      alert("Failed to resolve payment via backend.");
      setCheckoutState("failed");
    }
  };

  const handleReset = () => {
    setCheckoutState("idle");
    setSimulationData(null);
    setCurrentFailure(null);
    setPipelineStep(0);
    setAmountInput(currentScenario.default_amount);
  };

  const activeAmount = currentFailure?.amount ?? amountInput;

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 border-b border-rule pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-mono uppercase tracking-wider text-accent bg-accent-soft px-2 py-0.5 rounded font-semibold">
              Live Product Demo
            </span>
            <span className="text-[12px] text-ink-muted">Dual-Perspective Experience</span>
          </div>
          <h1 className="font-serif text-2xl text-ink font-semibold">
            Interactive Payment Failure & Recovery Simulator
          </h1>
          <p className="text-[13px] text-ink-muted mt-1 max-w-2xl">
            Simulate realistic Razorpay payment declines without terminal commands. Experience how
            RazorRecover diagnoses the root cause, applies policy guardrails, and autonomously recovers
            the revenue.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleReset}
            className="px-3.5 py-1.5 text-[13px] border border-rule hover:border-ink-muted text-ink rounded bg-paper transition-colors font-medium"
          >
            ↺ Reset Canvas
          </button>
          <Link
            href="/"
            className="px-3.5 py-1.5 text-[13px] bg-ink hover:bg-ink/90 text-paper rounded font-medium transition-colors"
          >
            View Main Ledger →
          </Link>
        </div>
      </div>

      {/* Scenario Story Cards */}
      <section className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[12px] font-mono uppercase tracking-wider text-ink-muted font-medium">
            1. Select a Payment Failure Scenario
          </h2>
          <span className="text-[12px] text-ink-faint">Matches Razorpay published error taxonomy</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {Object.entries(scenarios).map(([key, item]) => {
            const isSelected = selectedScenarioKey === key;
            const isGemini = key === "generic_bank_decline";
            return (
              <button
                key={key}
                onClick={() => handleSelectScenario(key)}
                className={`text-left p-3.5 rounded-lg border transition-all relative overflow-hidden flex flex-col justify-between ${
                  isSelected
                    ? isGemini
                      ? "border-purple-500 bg-purple-50/50 shadow-sm ring-1 ring-purple-500"
                      : "border-accent bg-accent-soft/40 shadow-sm ring-1 ring-accent"
                    : "border-rule bg-paper hover:border-rule-strong hover:bg-white"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px] font-mono text-ink-faint">
                      ₹{item.default_amount.toLocaleString("en-IN")}
                    </span>
                    {isGemini ? (
                      <span className="text-[10px] font-mono bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-bold border border-purple-200 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-600 animate-pulse" />
                        GEMINI
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono bg-paper text-ink-muted px-1.5 py-0.5 rounded border border-rule">
                        RULE
                      </span>
                    )}
                  </div>
                  <div className="text-[13px] font-semibold text-ink leading-snug mb-1">
                    {item.title}
                  </div>
                  <p className="text-[11px] text-ink-muted line-clamp-2 leading-relaxed">
                    {item.story}
                  </p>
                </div>
                <div className="mt-2.5 pt-2 border-t border-rule/60 flex items-center justify-between text-[11px] text-ink-faint font-mono">
                  <span>{item.customer_name.split(" ")[0]}</span>
                  <span className={isGemini ? "text-purple-700 font-semibold" : "text-accent font-medium"}>
                    {isGemini ? "Gemini Fallback" : item.error_reason}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* Dual Perspective Split View */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* LEFT COLUMN: Customer Experience & Smartphone Mockup (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <h2 className="text-[12px] font-mono uppercase tracking-wider text-ink-muted font-medium flex items-center gap-1.5">
              <span>📱</span> Customer Experience
            </h2>
            <span className="text-[11px] text-ink-faint">Buyer Viewport</span>
          </div>

          {/* SaaS Checkout Card */}
          <div className="border border-rule rounded-xl bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between pb-4 border-b border-rule mb-4">
              <div>
                <div className="text-[11px] font-mono text-ink-faint uppercase">Checkout Order</div>
                <div className="font-semibold text-ink text-[16px]">{currentScenario.plan_name}</div>
              </div>
              <div className="text-right">
                <label htmlFor="custom-amount" className="text-[11px] font-mono text-ink-faint flex items-center justify-end gap-1">
                  <span>Amount Due</span>
                  {checkoutState === "idle" && (
                    <span className="text-[10px] text-accent font-semibold">(Editable ✎)</span>
                  )}
                </label>
                <div className="flex items-center justify-end gap-1 mt-0.5">
                  <span className="font-mono font-semibold text-ink text-[16px]">₹</span>
                  <input
                    id="custom-amount"
                    type="number"
                    min="1"
                    step="100"
                    disabled={checkoutState !== "idle"}
                    value={amountInput}
                    onChange={(e) => setAmountInput(Math.max(1, Number(e.target.value)))}
                    className="w-28 font-mono font-semibold text-ink text-[16px] text-right bg-paper border border-rule focus:border-accent focus:ring-1 focus:ring-accent rounded px-1.5 py-0.5 outline-none disabled:bg-white disabled:border-transparent transition-colors"
                  />
                </div>
                {checkoutState === "idle" && (
                  <div className="flex items-center justify-end gap-1.5 mt-1 text-[11px] font-mono">
                    <button
                      type="button"
                      onClick={() => setAmountInput(currentScenario.default_amount)}
                      className="text-ink-faint hover:text-ink underline"
                    >
                      Default
                    </button>
                    <span className="text-rule">•</span>
                    <button
                      type="button"
                      onClick={() => setAmountInput(1499)}
                      className="text-ink-faint hover:text-accent"
                    >
                      ₹1.5k
                    </button>
                    <span className="text-rule">•</span>
                    <button
                      type="button"
                      onClick={() => setAmountInput(18500)}
                      className="text-ink-faint hover:text-accent"
                    >
                      ₹18.5k
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-3 mb-5 text-[13px]">
              <div className="flex justify-between text-ink-muted">
                <span>Customer</span>
                <span className="font-medium text-ink">{currentScenario.customer_name}</span>
              </div>
              <div className="flex justify-between text-ink-muted">
                <span>Phone / WhatsApp</span>
                <span className="font-mono text-ink">{currentScenario.customer_phone}</span>
              </div>
              <div className="flex justify-between text-ink-muted">
                <span>Payment Method</span>
                <span className="font-mono text-ink flex items-center gap-1.5">
                  <span className="w-3 h-2 rounded-sm bg-accent inline-block" />
                  HDFC Visa •••• 4821
                </span>
              </div>
            </div>

            {/* Action Buttons based on state */}
            {checkoutState === "idle" && (
              <button
                onClick={handleTriggerPayment}
                className="w-full py-3 bg-ink hover:bg-ink/90 text-paper font-semibold rounded-lg text-[14px] transition-all flex items-center justify-center gap-2 shadow hover:shadow-md"
              >
                <span>Simulate Customer Payment</span>
                <span>→</span>
              </button>
            )}

            {checkoutState === "processing" && (
              <div className="w-full py-3 bg-paper border border-rule text-ink-muted rounded-lg text-[13px] flex items-center justify-center gap-2.5">
                <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                <span>Contacting Issuing Bank via Razorpay...</span>
              </div>
            )}

            {checkoutState !== "idle" && checkoutState !== "processing" && (
              <div className="p-3.5 rounded-lg border border-unresolved/30 bg-unresolved-soft/40 text-unresolved text-[13px]">
                <div className="flex items-center gap-2 font-semibold mb-1">
                  <span>❌</span>
                  <span>Payment Declined ({currentScenario.error_code})</span>
                </div>
                <p className="text-[12px] text-ink-muted leading-relaxed">
                  {currentScenario.error_description}
                </p>
                <div className="mt-2 text-[11px] font-mono text-ink-faint">
                  Transaction Ref: {currentFailure?.razorpay_payment_id || "pay_sim_pending"}
                </div>
              </div>
            )}
          </div>

          {/* Smartphone Simulator Viewport */}
          <div className="border border-rule rounded-2xl bg-paper p-4 shadow-sm relative overflow-hidden">
            <div className="flex items-center justify-between pb-3 border-b border-rule mb-3 text-[11px] font-mono text-ink-faint">
              <span>Customer Mobile (Mock)</span>
              <span>12:45 PM • 5G</span>
            </div>

            {/* If still idle */}
            {checkoutState === "idle" && (
              <div className="py-12 text-center text-ink-faint text-[13px]">
                <p>Click &ldquo;Simulate Customer Payment&rdquo; above to watch the autonomous recovery alert arrive on the customer&rsquo;s phone.</p>
              </div>
            )}

            {/* Incoming WhatsApp Banner */}
            {(checkoutState === "failed" || checkoutState === "resolving") && (
              <div className="animate-fadeIn">
                <div className="bg-[#128C7E] text-white px-3.5 py-2 rounded-t-xl flex items-center justify-between text-[12px]">
                  <div className="flex items-center gap-2">
                    <span className="font-bold">WhatsApp Business</span>
                    <span className="text-[11px] opacity-80">• RazorRecover Bot</span>
                  </div>
                  <span className="text-[10px] opacity-75">Just now</span>
                </div>

                <div className="bg-white border-x border-b border-rule p-4 rounded-b-xl shadow-sm">
                  <div className="bg-[#DCF8C6] p-3.5 rounded-lg text-ink text-[13px] mb-3 leading-relaxed shadow-sm">
                    <p className="font-medium text-[#075E54] text-[12px] mb-1">
                      Apex Cloud Notification
                    </p>
                    <p>
                      {currentFailure?.customer_message ||
                        `Hi ${currentScenario.customer_name.split(" ")[0]}, your payment for ${currentScenario.plan_name} of ₹${activeAmount.toLocaleString("en-IN")} was declined. Click below to resolve seamlessly:`}
                    </p>
                    <div className="text-[10px] text-right text-ink-faint mt-1.5 font-mono">
                      Sent via WhatsApp Cloud API
                    </div>
                  </div>

                  {/* Interactive Resolution CTA */}
                  <button
                    onClick={handleCustomerResolve}
                    disabled={checkoutState === "resolving"}
                    className="w-full py-2.5 bg-[#25D366] hover:bg-[#20bd5a] text-white font-semibold rounded-lg text-[13px] transition-all flex items-center justify-center gap-2 shadow hover:shadow-md"
                  >
                    {checkoutState === "resolving" ? (
                      <>
                        <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>Authorizing 1-Click Recovery...</span>
                      </>
                    ) : (
                      <>
                        <span>⚡</span>
                        <span>{currentScenario.action_cta}</span>
                      </>
                    )}
                  </button>
                  <p className="text-[11px] text-center text-ink-faint mt-2">
                    Clicking simulates customer tapping the link on WhatsApp.
                  </p>
                </div>
              </div>
            )}

            {/* Recovered State */}
            {checkoutState === "recovered" && (
              <div className="bg-recovered-soft border border-recovered/40 rounded-xl p-5 text-center animate-fadeIn">
                <div className="w-10 h-10 rounded-full bg-recovered text-white flex items-center justify-center mx-auto mb-2 text-lg">
                  ✓
                </div>
                <div className="font-serif font-semibold text-recovered text-[18px]">
                  Payment Successfully Recovered!
                </div>
                <p className="text-[12px] text-ink-muted mt-1 max-w-sm mx-auto">
                  ₹{activeAmount.toLocaleString("en-IN")} secured into merchant
                  account via {currentScenario.recovery_method}. Involuntary churn averted.
                </p>
                <div className="mt-4 pt-3 border-t border-recovered/20 flex items-center justify-center gap-2 text-[12px] font-mono text-recovered font-medium">
                  <span>Status: EXECUTED</span>
                  <span>•</span>
                  <span>Outcome: RECOVERED</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: RazorRecover Autonomous Engine Brain (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <h2 className="text-[12px] font-mono uppercase tracking-wider text-ink-muted font-medium flex items-center gap-1.5">
              <span>🧠</span> RazorRecover Autonomous Engine
            </h2>
            <span className="text-[11px] font-mono text-accent font-medium">
              Decision Latency: &lt;15ms
            </span>
          </div>

          {/* Real-time Pipeline Visualizer */}
          <div className="border border-rule rounded-xl bg-white p-5 shadow-sm">
            <div className="text-[13px] font-semibold text-ink mb-4 pb-3 border-b border-rule flex items-center justify-between">
              <span>Autonomous Decision Pipeline</span>
              <span className="text-[11px] font-mono text-ink-faint">
                {pipelineStep === 0 && "Standby"}
                {pipelineStep === 1 && "Ingesting Event..."}
                {pipelineStep >= 2 && pipelineStep < 5 && "Action Dispatched"}
                {pipelineStep === 5 && "Complete • Ledger Updated"}
              </span>
            </div>

            <div className="space-y-4">
              {/* Step 1: Webhook Ingestion */}
              <div
                className={`p-3 rounded-lg border transition-all ${
                  pipelineStep >= 1
                    ? "border-accent/40 bg-accent-soft/20 text-ink"
                    : "border-rule/60 bg-paper/60 text-ink-faint opacity-60"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 font-medium text-[13px]">
                    <span className="w-5 h-5 rounded-full bg-accent/10 text-accent flex items-center justify-center text-[11px] font-mono font-bold">
                      1
                    </span>
                    <span>Webhook Ingested &amp; Verified</span>
                  </div>
                  {pipelineStep >= 1 && (
                    <span className="text-[11px] font-mono bg-recovered-soft text-recovered px-2 py-0.5 rounded font-medium">
                      HMAC-SHA256 Valid
                    </span>
                  )}
                </div>
                <p className="text-[12px] text-ink-muted ml-7">
                  Parsed Razorpay <code className="font-mono text-[11px] bg-paper px-1 py-0.5 border border-rule rounded">payment.failed</code> event. Idempotency key verified against replay attacks.
                </p>
              </div>

              {/* Step 2: AI Classification */}
              {(() => {
                const isGeminiDecided =
                  currentFailure?.decided_by === "gemini" ||
                  currentFailure?.decided_by === "claude" ||
                  selectedScenarioKey === "generic_bank_decline";

                return (
                  <div
                    className={`p-3.5 rounded-lg border transition-all ${
                      pipelineStep >= 2
                        ? isGeminiDecided
                          ? "border-purple-300 bg-gradient-to-br from-purple-50/70 to-indigo-50/30 text-ink shadow-sm"
                          : "border-accent/40 bg-accent-soft/20 text-ink"
                        : "border-rule/60 bg-paper/60 text-ink-faint opacity-60"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2 font-medium text-[13px]">
                        <span
                          className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-mono font-bold ${
                            isGeminiDecided && pipelineStep >= 2
                              ? "bg-purple-600 text-white"
                              : "bg-accent/10 text-accent"
                          }`}
                        >
                          2
                        </span>
                        <span>Intelligent Diagnosis &amp; Classification</span>
                      </div>
                      {pipelineStep >= 2 && (
                        <span
                          className={`text-[11px] font-mono px-2 py-0.5 rounded font-semibold flex items-center gap-1.5 ${
                            isGeminiDecided
                              ? "bg-purple-100 text-purple-800 border border-purple-200"
                              : "bg-accent-soft text-accent"
                          }`}
                        >
                          {isGeminiDecided ? (
                            <>
                              <span className="w-1.5 h-1.5 rounded-full bg-purple-600 animate-pulse" />
                              <span>🤖 Google Gemini (Live AI Agent)</span>
                            </>
                          ) : (
                            "⚡ Tier 1: Deterministic Rule"
                          )}
                        </span>
                      )}
                    </div>

                    {pipelineStep >= 2 && isGeminiDecided ? (
                      <div className="text-[12px] text-ink ml-7 space-y-2 mt-2">
                        <div className="flex items-center gap-2 text-[11px] font-mono bg-white/90 border border-purple-200/80 p-2 rounded">
                          <span className="text-amber-700 font-semibold">Tier 1 (Rule Engine):</span>
                          <span className="text-ink-muted">Inconclusive — Vague decline with no specific reason code.</span>
                        </div>
                        <div className="bg-purple-50/80 border border-purple-200 p-2.5 rounded-lg">
                          <div className="flex items-center justify-between text-[11px] font-mono text-purple-900 font-semibold mb-1">
                            <span className="flex items-center gap-1">
                              <span>Tier 2: Escalated to Google Gemini</span>
                            </span>
                            <span>Confidence: {currentFailure?.confidence ? `${Math.round(currentFailure.confidence * 100)}%` : "70%"}</span>
                          </div>
                          <div className="text-[12px] text-purple-950 font-sans leading-relaxed">
                            &ldquo;{currentFailure?.decision_reason || "The customer's bank declined the payment without giving a specific reason. Recommending smart delayed retry."}&rdquo;
                          </div>
                          <div className="mt-1.5 pt-1.5 border-t border-purple-200/60 flex items-center justify-between text-[11px] font-mono text-purple-800">
                            <span>Category: <strong>{currentFailure?.category || "bank_decline_unspecified"}</strong></span>
                            <span>Action: <strong>{currentFailure?.recommended_action || "retry_after_delay"}</strong></span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-[12px] text-ink-muted ml-7 space-y-1">
                        <div>
                          Category:{" "}
                          <strong className="text-ink font-mono">
                            {currentFailure?.category || currentScenario.error_reason}
                          </strong>{" "}
                          (Confidence: {currentFailure?.confidence ? `${Math.round(currentFailure.confidence * 100)}%` : "100%"})
                        </div>
                        <div className="text-[11px] text-ink-faint">
                          Diagnosis: {currentFailure?.decision_reason || "Identified root cause from Razorpay gateway error taxonomy."}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Step 3: Policy Guardrails */}
              <div
                className={`p-3 rounded-lg border transition-all ${
                  pipelineStep >= 3
                    ? "border-accent/40 bg-accent-soft/20 text-ink"
                    : "border-rule/60 bg-paper/60 text-ink-faint opacity-60"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 font-medium text-[13px]">
                    <span className="w-5 h-5 rounded-full bg-accent/10 text-accent flex items-center justify-center text-[11px] font-mono font-bold">
                      3
                    </span>
                    <span>Safety &amp; Compliance Guardrails</span>
                  </div>
                  {pipelineStep >= 3 && (
                    <span className="text-[11px] font-mono bg-recovered-soft text-recovered px-2 py-0.5 rounded font-medium">
                      Policy Approved
                    </span>
                  )}
                </div>
                <p className="text-[12px] text-ink-muted ml-7">
                  Verified RBI auto-debit AFA limits, 24-hour customer communication rate limits, and idempotency budget.
                </p>
              </div>

              {/* Step 4: Autonomous Action Dispatched */}
              <div
                className={`p-3 rounded-lg border transition-all ${
                  pipelineStep >= 4
                    ? "border-accent/40 bg-accent-soft/20 text-ink"
                    : "border-rule/60 bg-paper/60 text-ink-faint opacity-60"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 font-medium text-[13px]">
                    <span className="w-5 h-5 rounded-full bg-accent/10 text-accent flex items-center justify-center text-[11px] font-mono font-bold">
                      4
                    </span>
                    <span>Smart Recovery Action Dispatched</span>
                  </div>
                  {pipelineStep >= 4 && (
                    <span className="text-[11px] font-mono bg-accent-soft text-accent px-2 py-0.5 rounded font-medium">
                      {currentFailure?.recommended_action || "customer_recovery"}
                    </span>
                  )}
                </div>
                <p className="text-[12px] text-ink-muted ml-7">
                  Personalized WhatsApp recovery dispatch generated with 1-click fallback link. Unnecessary spam retries suppressed.
                </p>
              </div>

              {/* Step 5: Resolution Loop */}
              <div
                className={`p-3 rounded-lg border transition-all ${
                  pipelineStep === 5
                    ? "border-recovered/40 bg-recovered-soft/50 text-ink"
                    : "border-rule/60 bg-paper/60 text-ink-faint opacity-60"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2 font-medium text-[13px]">
                    <span
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-mono font-bold ${
                        pipelineStep === 5
                          ? "bg-recovered text-white"
                          : "bg-rule text-ink-muted"
                      }`}
                    >
                      5
                    </span>
                    <span>Resolution &amp; Merchant Ledger Update</span>
                  </div>
                  {pipelineStep === 5 && (
                    <span className="text-[11px] font-mono bg-recovered text-white px-2 py-0.5 rounded font-medium">
                      RECOVERED (+₹{activeAmount.toLocaleString("en-IN")})
                    </span>
                  )}
                </div>
                <p className="text-[12px] text-ink-muted ml-7">
                  {pipelineStep === 5
                    ? "Customer completed recovery. Transaction status updated to RECOVERED in SQLite database. Main ledger metrics refreshed."
                    : "Awaiting customer interaction or scheduled retry window..."}
                </p>
              </div>
            </div>
          </div>

          {/* Quick Actions & Inspection */}
          <div className="border border-rule rounded-xl bg-paper p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-[12px] text-ink-muted">
              {currentFailure ? (
                <span>
                  Incident ID:{" "}
                  <code className="font-mono text-ink font-semibold">
                    {currentFailure.id.slice(0, 18)}…
                  </code>
                </span>
              ) : (
                <span>Run a simulation to generate an incident record.</span>
              )}
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                onClick={() => setShowJson(!showJson)}
                disabled={!simulationData}
                className="px-3 py-1.5 text-[12px] font-mono border border-rule hover:border-ink-muted rounded text-ink bg-white disabled:opacity-40 transition-colors"
              >
                {showJson ? "Hide JSON" : "Inspect Webhook JSON"}
              </button>

              <Link
                href="/"
                className="px-3 py-1.5 text-[12px] font-medium bg-ink text-paper rounded hover:bg-ink/90 transition-colors inline-flex items-center gap-1"
              >
                <span>Check Ledger</span>
                <span>↗</span>
              </Link>
            </div>
          </div>

          {/* Collapsible JSON Inspector */}
          {showJson && simulationData && (
            <div className="border border-rule rounded-xl bg-ink text-paper p-4 font-mono text-[11px] max-h-72 overflow-y-auto animate-fadeIn">
              <div className="flex items-center justify-between pb-2 border-b border-rule/20 mb-2 text-ink-faint text-[10px]">
                <span>X-Razorpay-Signature: {simulationData.signature}</span>
                <span>Verified by Backend</span>
              </div>
              <pre className="whitespace-pre-wrap leading-relaxed text-rule">
                {JSON.stringify(simulationData.raw_payload, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
