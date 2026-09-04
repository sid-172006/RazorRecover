# RazorRecover ⚡
### An Explainable AI Agent for Safe Recurring-Payment Recovery
**Track 03: AI Revenue Recovery — Razorpay AI Buildathon**

> *"We don't blindly retry every failed payment. We determine the safest next action, execute it within strict limits, and show exactly how much revenue was recovered."*

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Frontend-Next.js%2014-black.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![Google Gemini](https://img.shields.io/badge/AI%20Engine-Google%20Gemini-4285F4.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Playwright](https://img.shields.io/badge/Testing-Playwright%20E2E-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev)

---

## 🚀 Key Highlights & Measured Results

From our [Ground-Truth Benchmark Report](GROUND_TRUTH_EVALUATION_REPORT.md) (16 realistic failure scenarios based on Razorpay's published error taxonomy):
- **Recovered Revenue:** **₹98,549.00** across subscriptions (`SIMULATED` outcome).
- **Retries Avoided:** **18 doomed attempts prevented** (expired cards, blocked accounts, cancelled mandates).
- **Classification Accuracy:** **100.0%** against labeled ground truth.
- **Safety Boundary Enforcement:** **100% Policy Adherence (0 violations)**.
- **Deterministic Efficiency:** **75% of failures** diagnosed in **<5ms** by deterministic rules with zero token cost; AI is invoked only when bank error reasons are genuinely ambiguous.

---

## 🌟 What's New & Core Features

### 1. Dual-Perspective Interactive Simulator (`/simulator`)
Experience payment failure and autonomous recovery in a visual, interactive dual viewport:
- **Merchant SaaS Checkout:** Interactive checkout card with editable subscription amounts (e.g. ₹1.5k, ₹18.5k, or custom), plan selection, and one-click payment triggering.
- **Customer Smartphone (Mock):** Live simulated mobile phone receiving WhatsApp recovery notifications with contextual 1-click recovery actions.
- **Live 5-Stage Autonomous Pipeline Visualizer:**
  1. **Webhook Ingested & Verified:** Validates Razorpay HMAC-SHA256 signature and idempotency.
  2. **Intelligent Diagnosis & Classification:** Visualizes Tier 1 (Deterministic Rule) vs. Tier 2 (Google Gemini live LLM reasoning).
  3. **Safety & Compliance Guardrails:** Verifies retry budgets, cooldown windows, and RBI auto-debit AFA limits.
  4. **Smart Recovery Action Dispatched:** Dispatches personalized WhatsApp notification with suppressive guardrails against retry fatigue.
  5. **Resolution & Merchant Ledger Update:** Simulates customer 1-click recovery and updates the SQLite financial ledger in real time.

### 2. Dynamic Ambiguous Decline Triage with Google Gemini
When bank decline messages are vague or lack sub-reasons, RazorRecover escalates to **Google Gemini** (`gemini-3.1-flash-lite`, `gemini-3.5-flash`, `gemini-3.6-flash` multi-model cascade):
- **Dynamic Confidence Scoring:** Confidence is never hardcoded. Gemini evaluates the specific nuance of the bank error message and assigns a calibrated confidence score (e.g., 70% to 90%).
- **Interactive Sub-Scenario Presets:**
  - **Transient Core Banking Glitch** (*"Payment was declined by customer bank"*) ➔ `retry_after_delay` (Confidence ~82%)
  - **Banking App 2FA Confirmation** (*"Customer confirmation required on mobile banking app"*) ➔ `customer_reapproval` (Confidence ~88%)
  - **Card Restriction / Channel Blocked** (*"Transaction not permitted for card type"*) ➔ `request_payment_method_update` (Confidence ~82%)
  - **Mandate Limit Exceeded** (*"Mandate execution failed: recurring debit limit exceeded"*) ➔ `request_reauthorisation` (Confidence ~86%)
- **Raw Bank Error Playground:** Type any custom bank decline text in the simulator textarea and watch Gemini analyze the root cause live!

### 3. Executive Recovery Ledger (`/`)
- Real-time auto-polling financial metrics: Total Failures, At-Risk Revenue, Recovered Revenue, Retries Avoided, Recovery Rate.
- Comprehensive incident inspection drawer with complete raw JSON payloads, policy decisions, and audit timeline.
- Honest `SIMULATED` provenance badge on every test record.

---

## 📐 Two-Tier Architecture

```
Razorpay Webhook (payment.failed)
        ↓
Webhook Security (HMAC-SHA256 signature verification & idempotency)
        ↓
Failure Normalizer (defensively extracts nested payment/subscription fields & masks PII)
        ↓
Tier 1: Deterministic Rules (app/classifier.py — handles clear-cut cases in <5ms, zero token cost)
        ↓ (if inconclusive / ambiguous)
Tier 2: AI Reasoning Agent (app/llm_classifier.py — Google Gemini multi-model cascade)
        ↓
Policy Validator (app/policy.py — whitelist, retry budgets, cooldowns, RBI AFA limits)
        ↓
Action Executor (app/executor.py — retry, notify, reauthorise, or manual review queue)
        ↓
Immutable Audit Log (AuditEvent & PaymentFailure SQLite tables)
        ↓
Live Next.js 14 Dashboard (Interactive dual-perspective simulator & ledger feed)
```

---

## 🛠️ Project Structure

- **`razorrecover/`**: FastAPI backend, database models, policy engine, and LLM classifier.
  - `app/classifier.py`: Tier 1 deterministic rules for clear failure categories.
  - `app/llm_classifier.py`: Tier 2 Google Gemini AI triage with model fallback.
  - `app/policy.py`: Deterministic safety gate & allowed-action whitelist.
  - `app/executor.py`: Action execution with explicit `SIMULATED` labeling.
  - `app/simulation.py`: Interactive simulation engine with dynamic amounts & error descriptions.
  - `scripts/ground_truth_dataset.json`: Labeled benchmark dataset (16 realistic scenarios).
  - `scripts/run_ground_truth_batch.py`: Automated batch evaluation runner.
  - `test_e2e_playwright.py`: Comprehensive Playwright browser and API test suite.
- **`razorrecover-dashboard/`**: Next.js 14 + Tailwind CSS dashboard.
  - `app/page.tsx`: Executive Recovery Ledger and live metrics strip.
  - `app/simulator/page.tsx`: Dual-perspective checkout & smartphone recovery simulator.
  - `lib/api.ts`: Typed API client for FastAPI backend communication.

---

## 🏃 Quickstart: Running Locally

### Prerequisites
- Python 3.9+
- Node.js 18+
- Google Gemini API Key (free tier available at [Google AI Studio](https://aistudio.google.com/))

### 1. Backend Setup (FastAPI)
```bash
cd razorrecover
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt

# Configure environment variables
# Copy .env.example to .env and set GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```
*Backend runs at `http://127.0.0.1:8000` with interactive API docs at `http://127.0.0.1:8000/docs`.*

### 2. Frontend Setup (Next.js)
```bash
cd razorrecover-dashboard
npm install
npm run dev
```
- Open **http://localhost:3000** for the **Executive Recovery Ledger**.
- Open **http://localhost:3000/simulator** for the **Live Dual-Perspective Simulator**.

### 3. Clear / Reset Database (Optional)
If you want to start with a fresh slate before recording a demo:
```bash
python -c "from app.database import Base, engine; Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)"
```

### 4. Run Benchmark & Tests
```bash
# Run the complete ground-truth benchmark suite:
python razorrecover/scripts/run_ground_truth_batch.py

# Run Playwright E2E browser & API test suite (optional):
# Requires: pip install playwright && playwright install chromium
python razorrecover/test_e2e_playwright.py
```

---

## 🎬 How to Demo in the Interactive Simulator

1. Navigate to **http://localhost:3000/simulator**.
2. **Test Clear-Cut Rule Failure (Tier 1):**
   - Choose Scenario 1 (*"Month-End Low Balance"*) or Scenario 2 (*"Expired Card"*).
   - Click **Simulate Customer Payment →**.
   - Notice Step 2 runs instantaneously via **Tier 1: Deterministic Rule** (<5ms, zero token cost).
3. **Test Ambiguous Bank Decline with Google Gemini (Tier 2):**
   - Choose Scenario 3 (*"Ambiguous Bank Decline"*).
   - Select one of the presets (e.g., **Banking App 2FA** or **Card Restrictions**) or type any custom bank error string into the textarea.
   - Adjust the **Amount Due** (e.g., ₹18,500).
   - Click **Simulate Customer Payment →**.
   - Watch Step 2 highlight **Google Gemini (Live AI Agent)** with calibrated confidence scores, dynamic category, and natural language diagnosis.
4. **Complete 1-Click Recovery:**
   - Look at the **Customer Mobile View** on the left.
   - Tap the WhatsApp resolution button (e.g. *"Authorize ₹18,500 in Banking App"*).
   - Watch Step 5 update to **RECOVERED (+₹18,500)** and verify the Ledger updates on the main page.

---

## ⚠️ Data Strategy: Why Simulated Webhooks

Razorpay's webhook configuration is **gated behind KYC completion, even in Test Mode**. While API keys are available immediately, the Dashboard → Webhooks settings page requires full KYC verification before a webhook endpoint URL can be registered. This means real `payment.failed` webhook events cannot be received without a fully verified business account.

**Our workaround** (documented in the [Project Spec's Data Strategy section](RazorRecover-Project-Spec.md#5-data-strategy-be-explicit-about-this-in-the-demo)):
- The simulator generates realistically structured, correctly HMAC-SHA256 signed payloads matching Razorpay's published webhook format — field names, error codes, error reasons, and nesting taken from Razorpay's official API documentation.
- The backend **cannot distinguish** these from a real Razorpay webhook call — the same signature verification, parsing, classification, policy, and execution pipeline runs identically.
- Every simulated fixture is **explicitly labeled** `SIMULATED` (via the `X-RazorRecover-Test-Source` header), and the dashboard renders a visible `SIMULATED` provenance tag on each record. We never present simulated outcomes as genuine recovered money.

---

## 📄 Documentation Links

- [Project Specification](RazorRecover-Project-Spec.md)
- [Project Documentation & Audit Trail](RazorRecover-Project-Documentation%20(1).md)
- [Ground-Truth Evaluation Report](GROUND_TRUTH_EVALUATION_REPORT.md)
