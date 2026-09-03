# RazorRecover ⚡
### An Explainable AI Agent for Safe Recurring-Payment Recovery
**Track 03: AI Revenue Recovery — Razorpay AI Buildathon**

> *"We don't blindly retry every failed payment. We determine the safest next action, execute it within strict limits, and show exactly how much revenue was recovered."*

---

## 🚀 Key Highlights & Measured Results

From our [Ground-Truth Benchmark Report](GROUND_TRUTH_EVALUATION_REPORT.md) (16 realistic failure scenarios based on Razorpay's published error taxonomy):
- **Recovered Revenue:** **₹97,250.00** across 8 subscription payments (`SIMULATED` outcome).
- **Retries Avoided:** **18 doomed attempts prevented** (expired cards, blocked accounts, cancelled mandates).
- **Classification Accuracy:** **100.0%** against labeled ground truth.
- **Safety Boundary Enforcement:** **100% Policy Adherence (0 violations)**.
- **Deterministic Efficiency:** **75% of failures** diagnosed in **<160ms** by deterministic rules with zero token cost; AI is invoked only when bank error reasons are genuinely ambiguous.

---

## 📐 Architecture

```
Razorpay Webhook (payment.failed)
        ↓
Webhook Security (HMAC-SHA256 verification & idempotency)
        ↓
Failure Normalizer (defensively extracts nested payment/subscription fields & masks customer identifiers)
        ↓
Deterministic Rules (app/classifier.py — handles clear-cut cases in <5ms)
        ↓
AI Reasoning Fallback (app/llm_classifier.py — Google Gemini / Claude for ambiguous bank declines)
        ↓
Policy Validator (app/policy.py — whitelist, retry budgets, cooldowns, confidence thresholds)
        ↓
Action Executor (app/executor.py — retry, notify, reauthorise, or escalate to manual review)
        ↓
Immutable Audit Log (AuditEvent SQLite table)
        ↓
Live Next.js 14 Dashboard (Ledger feed, metrics strip, interactive decision timelines)
```

---

## 🛠️ Project Structure

- **`razorrecover/`**: FastAPI backend, SQLAlchemy database, policy engine, and LLM classifier.
  - `app/classifier.py`: Deterministic rules for clear failure categories.
  - `app/policy.py`: Deterministic safety gate & allowed-action whitelist.
  - `app/llm_classifier.py`: Gemini / Claude AI triage for ambiguous failures.
  - `app/executor.py`: Action execution with explicit `SIMULATED` labeling.
  - `scripts/ground_truth_dataset.json`: Labeled benchmark dataset.
  - `scripts/run_ground_truth_batch.py`: Automated batch evaluation runner.
  - `test_e2e_playwright.py`: Comprehensive Playwright browser and API test suite.
- **`razorrecover-dashboard/`**: Next.js 14 + Tailwind CSS dashboard.
  - Two-pane layout: Live failure ledger on the left, interactive audit timeline on the right.
  - Live auto-polling metrics strip (Total failures, Recovered, Amount, Retries avoided, Recovery rate).

---

## 🏃 Quickstart: Running Locally

### 1. Backend (FastAPI)
```bash
cd razorrecover
python -m venv venv
venv\Scripts\activate      # On Windows
pip install -r requirements.txt
playwright install chromium

# Copy and fill your .env
cp .env.example .env
# Set GEMINI_API_KEY and RAZORPAY_WEBHOOK_SECRET

uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Dashboard (Next.js)
```bash
cd razorrecover-dashboard
npm install
npm run dev
```
Open **http://localhost:3000** in your browser.

### 3. Run Benchmark & Tests
```bash
# Run the complete ground-truth benchmark:
python razorrecover/scripts/run_ground_truth_batch.py

# Run Playwright automated E2E browser & API suite:
python razorrecover/test_e2e_playwright.py
```

---

## 📄 Documentation

- [Project Specification](RazorRecover-Project-Spec.md)
- [Project Documentation & Audit Trail](RazorRecover-Project-Documentation%20(1).md)
- [Ground-Truth Evaluation Report](GROUND_TRUTH_EVALUATION_REPORT.md)
