"""
Phase 2 — policy validator.

This is the safety boundary described in the spec: recommendations (whether
from a rule or, from Phase 3 onward, from Claude) do NOT execute directly.
They pass through here first. This module has no AI in it at all —
deterministic checks only, on purpose.

Reads audit_events/payment_failures history to check retry budgets and
notification cooldowns. Phase 4 (action executor) will be the thing that
actually WRITES the "action_executed" audit events this reads — until then,
these checks will mostly pass since there's no history yet, but the logic
is in place and ready.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import PaymentFailure, AuditEvent, FailureStatus

# --- tunable policy limits ---
MAX_RETRIES_PER_SUBSCRIPTION = 3
RETRY_LOOKBACK_DAYS = 7
NOTIFICATION_COOLDOWN_HOURS = 24
MIN_CONFIDENCE_TO_ACT = 0.6

# Which actions consume retry budget vs. just notify vs. are terminal.
# Phase 3 (Claude) must only ever recommend an action from this map —
# anything else gets rejected automatically (see validate_action).
ACTION_METADATA = {
    "wait_and_notify":                 {"type": "notify"},
    "request_payment_method_update":   {"type": "notify"},
    "customer_reapproval":             {"type": "notify"},
    "request_reauthorisation":         {"type": "notify"},
    "retry_now":                       {"type": "retry"},
    "retry_after_delay":               {"type": "retry"},
    "stop_retrying":                   {"type": "terminal"},
    "escalate_manual_review":          {"type": "terminal"},
}


@dataclass
class PolicyResult:
    approved: bool
    rejection_reason: str | None = None


def validate_action(db: Session, failure: PaymentFailure, recommended_action: str, confidence: float) -> PolicyResult:
    # --- 0. Unknown action — reject outright. This is what stops a
    # malformed or hallucinated Claude response from ever reaching execution. ---
    if recommended_action not in ACTION_METADATA:
        return PolicyResult(False, f"Unrecognized action '{recommended_action}' — not in the allowed action set.")

    action_type = ACTION_METADATA[recommended_action]["type"]

    # --- 1. Confidence threshold ---
    if confidence < MIN_CONFIDENCE_TO_ACT:
        return PolicyResult(False, f"Confidence {confidence:.2f} is below the minimum threshold ({MIN_CONFIDENCE_TO_ACT}).")

    # --- 2. Subscription already exhausted / in manual review ---
    if failure.subscription_id and _subscription_already_exhausted(db, failure.subscription_id):
        return PolicyResult(False, "This subscription already has a recovery_exhausted or manual_review outcome on record.")

    # --- 3. Retry budget ---
    if action_type == "retry" and failure.subscription_id:
        recent_retries = _count_recent_retry_actions(db, failure.subscription_id)
        if recent_retries >= MAX_RETRIES_PER_SUBSCRIPTION:
            return PolicyResult(False, f"Retry budget exhausted ({recent_retries}/{MAX_RETRIES_PER_SUBSCRIPTION} in the last {RETRY_LOOKBACK_DAYS} days).")

    # --- 4. Notification cooldown ---
    if action_type == "notify" and failure.subscription_id:
        last_notified = _last_notification_time(db, failure.subscription_id)
        if last_notified and (datetime.now(timezone.utc) - last_notified) < timedelta(hours=NOTIFICATION_COOLDOWN_HOURS):
            return PolicyResult(False, f"Customer was already notified within the last {NOTIFICATION_COOLDOWN_HOURS}h cooldown window.")

    return PolicyResult(True, None)


def get_subscription_history(db: Session, subscription_id: str) -> dict:
    """
    Small public summary used to give Claude context in Phase 3 — deliberately
    just a count + boolean, not raw records, to keep the prompt lean.
    """
    since = datetime.now(timezone.utc) - timedelta(days=RETRY_LOOKBACK_DAYS)
    recent_failure_count = (
        db.query(func.count(PaymentFailure.id))
        .filter(
            PaymentFailure.subscription_id == subscription_id,
            PaymentFailure.created_at >= since,
        )
        .scalar()
        or 0
    )
    last_notified = _last_notification_time(db, subscription_id)
    recently_notified = bool(
        last_notified and (datetime.now(timezone.utc) - last_notified) < timedelta(hours=NOTIFICATION_COOLDOWN_HOURS)
    )
    return {"recent_failure_count": recent_failure_count, "recently_notified": recently_notified}


def _subscription_already_exhausted(db: Session, subscription_id: str) -> bool:
    return (
        db.query(PaymentFailure)
        .filter(
            PaymentFailure.subscription_id == subscription_id,
            PaymentFailure.status == FailureStatus.RECOVERY_EXHAUSTED,
        )
        .first()
        is not None
    )


def _count_recent_retry_actions(db: Session, subscription_id: str) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=RETRY_LOOKBACK_DAYS)
    return (
        db.query(func.count(AuditEvent.id))
        .join(PaymentFailure, AuditEvent.payment_failure_id == PaymentFailure.id)
        .filter(
            PaymentFailure.subscription_id == subscription_id,
            AuditEvent.event_type == "action_executed",
            AuditEvent.created_at >= since,
        )
        .scalar()
        or 0
    )


def _last_notification_time(db: Session, subscription_id: str) -> datetime | None:
    event = (
        db.query(AuditEvent)
        .join(PaymentFailure, AuditEvent.payment_failure_id == PaymentFailure.id)
        .filter(
            PaymentFailure.subscription_id == subscription_id,
            AuditEvent.event_type == "customer_notified",
        )
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    return event.created_at.replace(tzinfo=timezone.utc) if event else None
