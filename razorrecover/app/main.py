"""
RazorRecover — Phase 1: payment event pipeline.

What this file does right now (Phase 1 scope only):
  1. Receive a Razorpay webhook (payment.failed, subscription.pending, subscription.halted)
  2. Verify its signature
  3. Deduplicate (idempotency)
  4. Store the raw payload + normalized fields
  5. Log an audit event
  6. Expose simple read endpoints so you can see what's landed in the DB

NOT built yet (next phases): the rule classifier, Claude integration,
policy validator, action executor. Those hook in after step 4 above —
see the TODO marker in handle_webhook().
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.database import Base, engine, get_db
from app.models import PaymentFailure, ExecutionMode, FailureStatus
from app.webhook_security import verify_signature
from app.webhook_parser import extract_failure_fields
from app.audit import log_event
from app.pipeline import process_failure
from app.metrics import compute_metrics
from app.schemas import PaymentFailureOut, AuditEventOut
from app.simulation import SIMULATION_SCENARIOS, build_simulated_webhook

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("razorrecover")

RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

# Events we care about for the MVP. Extend later (e.g. payment.captured to
# detect a successful recovery) once phase 4 (action execution) exists.
HANDLED_EVENTS = {"payment.failed", "subscription.pending", "subscription.halted"}

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RazorRecover", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhooks/razorpay")
async def handle_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=None, alias="X-Razorpay-Signature"),
    x_test_source: str = Header(default=None, alias="X-RazorRecover-Test-Source"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    # --- 1. Verify signature BEFORE trusting anything in the body ---
    if not RAZORPAY_WEBHOOK_SECRET:
        logger.warning("RAZORPAY_WEBHOOK_SECRET is not set — refusing to process webhook.")
        raise HTTPException(status_code=500, detail="Webhook secret not configured on server")

    if not verify_signature(raw_body, x_razorpay_signature, RAZORPAY_WEBHOOK_SECRET):
        logger.warning("Rejected webhook with invalid signature.")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed JSON body")

    event_type = payload.get("event")
    if event_type not in HANDLED_EVENTS:
        # Acknowledge receipt so Razorpay doesn't retry, but don't process it.
        logger.info(f"Ignoring unhandled event type: {event_type}")
        return {"status": "ignored", "event": event_type}

    # --- 2. Idempotency key ---
    # Razorpay doesn't always guarantee a top-level unique id across all event
    # types/versions, so build a stable fallback from what's always present.
    razorpay_event_id = (
        payload.get("id")
        or f"{event_type}:{payload.get('payload', {}).get('payment', {}).get('entity', {}).get('id', '')}:{payload.get('created_at', '')}"
    )

    existing = db.query(PaymentFailure).filter_by(razorpay_event_id=razorpay_event_id).first()
    if existing:
        logger.info(f"Duplicate webhook received for {razorpay_event_id}, ignoring.")
        return {"status": "duplicate_ignored", "payment_failure_id": existing.id}

    # --- 3. Parse + normalize ---
    fields = extract_failure_fields(payload)

    # Honesty check: only mark as LIVE_TEST_MODE if this genuinely wasn't
    # flagged as coming from our own simulated test-data script. Real Razorpay
    # webhook calls never send this header, so they default to LIVE_TEST_MODE.
    execution_mode = ExecutionMode.SIMULATED if x_test_source else ExecutionMode.LIVE_TEST_MODE

    failure = PaymentFailure(
        razorpay_event_id=razorpay_event_id,
        razorpay_payment_id=fields["razorpay_payment_id"],
        subscription_id=fields["subscription_id"],
        execution_mode=execution_mode,
        raw_payload=json.dumps(payload),
        amount=fields["amount"],
        error_code=fields["error_code"],
        error_description=fields["error_description"],
        error_source=fields["error_source"],
        error_step=fields["error_step"],
        error_reason=fields["error_reason"],
        customer_ref_masked=fields["customer_ref_masked"],
        status=FailureStatus.RECEIVED,
    )
    db.add(failure)
    db.commit()
    db.refresh(failure)

    log_event(db, failure.id, "webhook_received", {
        "event_type": event_type,
        "error_code": fields["error_code"],
        "error_reason": fields["error_reason"],
    })

    # --- 4. Classify + policy-check (Phase 2) ---
    # Rule match -> classified + policy-checked immediately.
    # No rule match -> left as category="unknown_bank_decline" for Phase 3 (Claude) to pick up.
    failure = process_failure(db, failure)

    logger.info(f"Processed payment failure {failure.id} (event={event_type}, category={failure.category}, status={failure.status})")
    return {
        "status": "received",
        "payment_failure_id": failure.id,
        "category": failure.category,
        "processing_status": failure.status,
    }


@app.get("/payment-failures", response_model=list[PaymentFailureOut])
def list_payment_failures(db: Session = Depends(get_db), limit: int = 50):
    return (
        db.query(PaymentFailure)
        .order_by(PaymentFailure.created_at.desc())
        .limit(limit)
        .all()
    )


@app.get("/payment-failures/{failure_id}", response_model=PaymentFailureOut)
def get_payment_failure(failure_id: str, db: Session = Depends(get_db)):
    failure = db.query(PaymentFailure).filter_by(id=failure_id).first()
    if not failure:
        raise HTTPException(status_code=404, detail="Not found")
    return failure


@app.get("/payment-failures/{failure_id}/audit-trail", response_model=list[AuditEventOut])
def get_audit_trail(failure_id: str, db: Session = Depends(get_db)):
    failure = db.query(PaymentFailure).filter_by(id=failure_id).first()
    if not failure:
        raise HTTPException(status_code=404, detail="Not found")
    return failure.audit_events


@app.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    return compute_metrics(db)


class SimulateFailureRequest(BaseModel):
    scenario: str = "insufficient_balance"
    amount: Optional[float] = None
    error_description: Optional[str] = None


class ResolveFailureRequest(BaseModel):
    resolution_method: str = "upi_quickpay"


@app.get("/simulation/scenarios")
def get_simulation_scenarios():
    """Returns metadata for all available customer demo scenarios."""
    return SIMULATION_SCENARIOS


@app.post("/simulate-failure")
def simulate_failure(req: SimulateFailureRequest, db: Session = Depends(get_db)):
    """
    Ingests an authentic Razorpay payment.failed event for the chosen scenario,
    runs it through classification, policy checks, and execution.
    """
    if req.scenario not in SIMULATION_SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {req.scenario}")

    payload, raw_bytes, signature = build_simulated_webhook(
        req.scenario,
        req.amount,
        req.error_description,
    )
    event_type = payload.get("event")
    razorpay_event_id = payload.get("id")
    fields = extract_failure_fields(payload)

    failure = PaymentFailure(
        razorpay_event_id=razorpay_event_id,
        razorpay_payment_id=fields["razorpay_payment_id"],
        subscription_id=fields["subscription_id"],
        execution_mode=ExecutionMode.SIMULATED,
        raw_payload=json.dumps(payload),
        amount=fields["amount"],
        error_code=fields["error_code"],
        error_description=fields["error_description"],
        error_source=fields["error_source"],
        error_step=fields["error_step"],
        error_reason=fields["error_reason"],
        customer_ref_masked=fields["customer_ref_masked"],
        status=FailureStatus.RECEIVED,
    )
    db.add(failure)
    db.commit()
    db.refresh(failure)

    log_event(db, failure.id, "webhook_received", {
        "event_type": event_type,
        "error_code": fields["error_code"],
        "error_reason": fields["error_reason"],
        "simulated_scenario": req.scenario,
    })

    failure = process_failure(db, failure)

    scenario_info = SIMULATION_SCENARIOS[req.scenario]
    if not failure.customer_message:
        failure.customer_message = f"Hi {scenario_info['customer_name'].split()[0]}, your payment of ₹{failure.amount:,.2f} for {scenario_info['plan_name']} was declined. Please resolve: {scenario_info['action_cta']}."
        db.commit()
        db.refresh(failure)

    return {
        "payment_failure": PaymentFailureOut.model_validate(failure),
        "scenario": scenario_info,
        "raw_payload": payload,
        "signature": signature,
    }


@app.post("/payment-failures/{failure_id}/resolve")
def resolve_failure(failure_id: str, req: ResolveFailureRequest, db: Session = Depends(get_db)):
    """
    Simulates the customer clicking the recovery action (e.g. WhatsApp UPI link or Card update),
    marking the transaction successfully recovered and updating recovery metrics.
    """
    failure = db.query(PaymentFailure).filter_by(id=failure_id).first()
    if not failure:
        raise HTTPException(status_code=404, detail="Payment failure not found")

    failure.execution_result = "recovered"
    failure.status = FailureStatus.EXECUTED
    failure.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(failure)

    log_event(db, failure.id, "customer_recovered_interactive", {
        "resolution_method": req.resolution_method,
        "recovered_amount": failure.amount,
        "status": "recovered",
    })

    return {
        "status": "recovered",
        "payment_failure": PaymentFailureOut.model_validate(failure),
    }

