# RazorRecover
### An Explainable AI Agent for Safe Recurring-Payment Recovery
**Track:** 03 — AI Revenue Recovery | **Razorpay AI Buildathon**

---

## 1. Problem Statement

Recurring payments (subscriptions, auto-debits) on Razorpay sometimes fail. Some failures are simple and self-explanatory (expired card, insufficient balance). Others are genuinely ambiguous — Razorpay's own error documentation confirms that certain bank declines come back with no specific reason, because the customer's bank doesn't share one.

Razorpay already provides subscription retry and notification functionality — but existing retry workflows are generally predefined (fixed schedules, fixed rules). Merchants need a more adaptive system that can distinguish recoverable failures from failures requiring customer action, while explaining every decision and measuring the resulting revenue recovery. That adaptive diagnosis, controlled decision-making, explainability, and measured outcome layer — on top of the existing payment workflow — is what this project adds.

One well-documented, real contributing cause: recurring payments above ₹15,000 require additional factor authentication (AFA) after mandate setup (some categories — insurance, mutual funds, card bills — have different limits). Failures happen when that authentication step is incomplete, rejected, or mishandled — not automatically just because of the amount. This is real and current, but it is *one* failure context among several the agent should handle — not the whole product.

---

## 2. What We're Building

An agent that:
1. Detects a failed recurring payment (via Razorpay test-mode webhook)
2. Diagnoses the likely cause — deterministic rules for clear cases, an LLM for genuinely ambiguous ones
3. Recommends a bounded next action (never acts unilaterally)
4. Passes that recommendation through a policy validator that enforces hard safety limits
5. Executes (or simulates) the approved action
6. Logs everything to an immutable audit trail
7. Reports recovered revenue, unresolved cases, and honest accuracy metrics

**Core pitch line:** *"We don't retry every failed payment. We determine the safest next action, execute it within strict limits, and show exactly how much revenue was recovered."*

---

## 3. Architecture

```
Razorpay webhook (payment.failed / subscription.pending / subscription.halted)
        ↓
Failure normalizer (verify signature, dedupe, structure the payload)
        ↓
Deterministic rules (handles clear-cut cases fast & explainably)
        ↓
LLM layer — ONLY for ambiguous cases (Claude API)
   → outputs structured JSON: classification, confidence,
     recommended_action, reason, customer_message, retry_after_hours
        ↓
Policy validator (deterministic — the LLM never acts directly)
   → checks: action allowed for this category? retry budget left?
     customer contacted recently? subscription already halted?
     another attempt in progress? is this idempotent/safe?
        ↓
Action executor (retry / notify / escalate — simulated where needed)
        ↓
Webhook/result monitor (did the retry succeed?)
        ↓
Audit log + dashboard
```

**Key design principle:** *AI recommends. Deterministic policy controls execution.* This is the main differentiator — it directly answers "is this safe to let near real money."

---

## 4. Action Policy Table

| Failure Category | Action |
|---|---|
| Temporary bank/network issue | Retry after a delay |
| Insufficient balance | Wait and notify customer |
| Expired or blocked card | Request payment-method update |
| Mandate cancelled | Ask customer to re-authorise |
| Authentication/AFA required | Send approval or re-approval link |
| Permanent invalid payment method | Stop retrying |
| Unknown/generic bank decline | LLM analysis → cautious retry or notification |
| Repeated unresolved failure | Escalate to `manual_review_required` |

Note: avoid framing "give up" as deletion/cancellation — use a safe terminal state like `manual_review_required` or `recovery_exhausted`.

---

## 5. Data Strategy (be explicit about this in the demo)

Two clearly labeled sources, never blended without disclosure:
- **Live-captured**: real Razorpay test-mode webhook payloads, from failures you actually trigger in a sandbox
- **Simulated fixtures**: constructed payloads for failure types that are hard to reliably reproduce in test mode (clearly labeled as such)

This honesty is a strength, not a weakness — it shows judges you understand the limits of test-mode data instead of overclaiming.

---

## 6. MVP Scope (build this first, not the full spec at once)

With a 9-day window, build one working vertical slice before expanding. A smaller, fully-working project beats a larger, partially-implemented one.

**MVP failure categories (four only):**
1. Insufficient balance
2. Expired or blocked card
3. Authentication/AFA required
4. Generic or unknown bank decline (routes to Claude)

**MVP vertical slice (in order):**
1. Receive a `payment.failed` webhook
2. Verify the webhook signature
3. Deduplicate and store the event
4. Classify the 3 clear categories with deterministic rules
5. Send only the unknown/ambiguous case to Claude
6. Return structured JSON from Claude
7. Validate the proposed action against the policy engine
8. Execute or simulate the action
9. Display the complete audit trail in the dashboard

**Recommended build order (backend before frontend):**
- **Phase 1 — Payment event pipeline:** FastAPI webhook endpoint, signature verification, event storage, idempotency (unique constraint on event ID/payment ID), normalized failure schema. Store the original raw payload separately from normalized fields; mask sensitive values before display. Rough tables: `payment_failures`, `decisions`, `recovery_actions`, `audit_events`, `subscriptions` — fine to start denormalized and split later if time allows.
- **Phase 2 — Rules + policy engine:** deterministic logic first (`clear failure → category → allowed action`; `ambiguous failure → Claude → policy validator → allowed action`). Policy validator is independent of Claude and can reject its recommendation — e.g. retry budget exhausted, subscription halted, retry already running, customer recently notified, confidence below threshold, category is permanent.
- **Phase 3 — Claude integration:** only for genuinely ambiguous cases. Validate the structured response with Pydantic; invalid JSON, unsupported action, or low confidence → route to `manual_review_required`.
- **Phase 4 — Action execution:** simulate what test mode can't reliably reproduce. Label every action visibly as `LIVE_TEST_MODE`, `SIMULATED`, or `DRY_RUN` — never present simulated recovery as genuine recovered money.
- **Phase 5 — Dashboard:** only screens that strengthen the story — live failure feed, payment detail page, AI decision + confidence, policy approval/rejection, action timeline, recovered amount, unresolved amount, retries avoided, manual-review queue.

**The single most useful screen to build:** a decision timeline like —
`Payment failed → classified as generic bank decline → Claude confidence: 0.68 → retry recommended → policy rejected: retry budget exhausted → sent to manual review`
This one example proves the system isn't blindly obeying the model.

---

## 7. Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python + FastAPI |
| Database | PostgreSQL (or SQLite if time-constrained) |
| Payments | Razorpay Python SDK, test mode + webhooks |
| Background jobs | Simple queue/worker for retries & LLM calls (avoid blocking webhook responses) |
| AI | Claude API — structured JSON output for classification & decisions |
| Frontend | Next.js dashboard — live feed, audit trail, metrics |
| Demo recording | OBS |

---

## 8. Metrics to Report (honest, not cherry-picked)

- Classification accuracy (against a labeled ground-truth set you build)
- Precision/recall for high-risk categories
- Abstention rate (cases the agent declined to guess on)
- Recovery rate = recovered payments / eligible failed payments
- Amount recovered
- Average time to recovery
- Retries avoided (unnecessary retries prevented)
- Manual-review rate
- Policy-violation count (target: zero)

**Headline number for the pitch:** *"The agent recovered ₹X while avoiding Y unnecessary retry attempts."*

---

## 9. Implementation Hygiene Checklist

- [ ] Verify Razorpay webhook signatures
- [ ] Idempotent webhook processing (unique constraints on event ID / payment ID)
- [ ] Never store raw card numbers, CVV, OTPs, or auth data
- [ ] Mask customer/payment identifiers on the dashboard
- [ ] Exponential backoff + hard maximum retry budget
- [ ] Prevent duplicate customer notifications (cooldown)
- [ ] Immutable audit record: input → model output → policy decision → execution result
- [ ] Log model version + prompt version
- [ ] Emergency kill switch for automated actions
- [ ] Require human approval for high-value or low-confidence actions

---

## 10. What Makes This Different

1. Not a payment-status dashboard — it acts (within limits)
2. Doesn't blindly retry every failure
3. Uses AI specifically where ambiguity is real and documented — not everywhere
4. Every decision is explainable and auditable
5. Has an explicit abstention / manual-review path, not forced guesses
6. Measures recovered money and avoided harm, not just model accuracy

---

## 11. Demo Checklist (5-min pitch should show)

1. A real Razorpay test-mode recurring payment failing (raw webhook payload)
2. The normalized failure record in the database
3. The AI's structured decision (classification, confidence, reasoning, action)
4. The policy validator approving/rejecting that action
5. The executed (or simulated) recovery action
6. The updated dashboard: audit trail + final metrics (recovered ₹, avoided retries, unresolved cases)
