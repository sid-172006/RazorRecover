# RazorRecover — Backend

Full pipeline: receive a Razorpay webhook → verify signature → dedupe →
classify (rule or Claude) → policy-check → execute (simulated) → audit log
→ metrics. All 5 build phases complete and tested.

## What's built

- `app/database.py` — SQLite (swappable to Postgres) via SQLAlchemy
- `app/models.py` — `PaymentFailure` + `AuditEvent` tables
- `app/webhook_security.py` — HMAC-SHA256 signature verification
- `app/webhook_parser.py` — pulls fields out of Razorpay's payload defensively
- `app/audit.py` — logs one audit row per pipeline step
- `app/classifier.py` — deterministic rules for 4 clear categories:
  insufficient balance, expired/blocked card, authentication/AFA required,
  mandate cancelled. Anything that doesn't confidently match is left as
  `unknown_bank_decline` — the handoff point to Claude.
- `app/policy.py` — the safety layer. Retry budget (max 3/subscription/7 days),
  notification cooldown (24h), confidence threshold (0.6), and rejects any
  action outside the allowed set outright.
- `app/llm_classifier.py` — Claude classification for ambiguous cases.
  Forces structured JSON output, validated with Pydantic against the same
  allowed-action list the policy validator uses. Falls back to manual review
  (never guesses) if the API call fails or returns something invalid.
- `app/pipeline.py` — orchestrates classify → policy-check → execute for
  each incoming failure. Same policy gate for rule-based and Claude-based
  decisions — no separate looser path for AI.
- `app/executor.py` — executes the policy-approved action. Every outcome
  labeled `SIMULATED`/`LIVE_TEST_MODE` honestly. Checks a `KILL_SWITCH` env
  var first. Outcomes seeded by `failure.id` for reproducible demos.
- `app/metrics.py` + `GET /metrics` — live-computed recovery numbers.
- `app/main.py` — the FastAPI app, all endpoints.
- `scripts/send_test_webhook.py` — generates realistic, correctly-signed,
  Razorpay-shaped test payloads (see below — this is the current way to
  generate test data, since Razorpay's real webhook setup turned out to be
  gated behind KYC even in Test Mode).

## Tested (not just written)

- Signature verification: valid accepted, invalid rejected (400), duplicate ignored
- All 4 rule categories classify correctly end-to-end, including a fix after
  testing caught the "blocked card" phrasing not matching the original rule
- Ambiguous cases correctly fall through to Claude / manual review
- All 5 policy rejection scenarios verified against a seeded DB
- Claude integration tested with a mocked API client (valid decision,
  malformed JSON, disallowed action — all handled correctly)
- Full batch runs via `send_test_webhook.py --all`, with `execution_mode`
  verified as correctly `SIMULATED` (not `LIVE_TEST_MODE`) for script-generated data

## Setup

```bash
cd razorrecover
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

**Windows + Python 3.9 note:** if `pip install` fails trying to build
`greenlet` from source, run this first to force the pre-built version:
```bash
pip install --only-binary=:all: greenlet==3.2.4
```

Fill in `.env`:
- `RAZORPAY_WEBHOOK_SECRET` — any string you make up yourself (used to sign
  test payloads via `send_test_webhook.py`; also needed if you later get
  real webhook access)
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` — from Razorpay Dashboard →
  API Keys, Test mode
- `ANTHROPIC_API_KEY` — needed for Claude classification of ambiguous
  cases; without it, ambiguous cases route straight to manual review

## Run locally

```bash
uvicorn app.main:app --reload --port 8000
```

Check it's up: `http://localhost:8000/health` → `{"status": "ok"}`
Interactive API docs: `http://localhost:8000/docs`

## Generating test failures

**Razorpay gates webhook configuration behind KYC completion, even in Test
Mode** — confirmed directly through their onboarding assistant. So instead
of a live webhook, use `scripts/send_test_webhook.py`: it builds realistic,
Razorpay-shaped `payment.failed` payloads (matching their real documented
field names and error codes), signs them with the same HMAC-SHA256 scheme
Razorpay uses, and POSTs them to your local server. The backend can't tell
the difference from a real webhook call — everything downstream runs
identically. These are correctly labeled `SIMULATED`, not `LIVE_TEST_MODE`.

```bash
# one random scenario
python scripts/send_test_webhook.py

# every scenario once (covers all 4 rule categories + 2 ambiguous cases)
python scripts/send_test_webhook.py --all

# a specific scenario, repeated
python scripts/send_test_webhook.py --scenario insufficient_balance --count 5

# test idempotency (resends the last event, should be ignored)
python scripts/send_test_webhook.py --duplicate
```

Each stored record shows its `category`, `confidence`, `recommended_action`,
`policy_approved`, `executed_action`, `execution_result`, and `status`.
Check `GET /metrics` for the aggregate numbers.

If KYC ever clears and real webhook access opens up, the setup is:
`ngrok http 8000` → Razorpay Dashboard → Webhooks → Add New Webhook →
URL = your ngrok URL + `/webhooks/razorpay` → set a secret matching
`RAZORPAY_WEBHOOK_SECRET` → select `payment.failed` at minimum. Real
webhook calls will correctly get labeled `LIVE_TEST_MODE` automatically
(no `X-RazorRecover-Test-Source` header, unlike the script).

## Next step

Run the backend and dashboard (`razorrecover-dashboard/`, Phase 5,
built separately) together and confirm the dashboard renders real data —
not yet done. Then: real Claude API key test, a labeled ground-truth
dataset for accuracy metrics, and the demo recording.
