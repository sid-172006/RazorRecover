"""
Phase 4 addendum — a simple metrics summary over what's in the DB so far.
This is what Phase 5's dashboard will render; exposing it as an endpoint
now means it's already testable and usable even before the frontend exists.

All numbers here are computed live from the payment_failures table —
nothing cached, nothing cherry-picked.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import PaymentFailure, FailureStatus


def compute_metrics(db: Session) -> dict:
    total = db.query(func.count(PaymentFailure.id)).scalar() or 0

    recovered = db.query(PaymentFailure).filter(PaymentFailure.execution_result == "recovered").all()
    recovered_count = len(recovered)
    recovered_amount = sum(f.amount or 0 for f in recovered)

    unresolved = db.query(func.count(PaymentFailure.id)).filter(
        PaymentFailure.execution_result.in_(["unresolved", "failed"])
    ).scalar() or 0

    manual_review = db.query(func.count(PaymentFailure.id)).filter(
        PaymentFailure.status == FailureStatus.MANUAL_REVIEW
    ).scalar() or 0

    ambiguous_routed_to_claude = db.query(func.count(PaymentFailure.id)).filter(
        PaymentFailure.decided_by == "claude"
    ).scalar() or 0

    rule_classified = db.query(func.count(PaymentFailure.id)).filter(
        PaymentFailure.decided_by == "rule"
    ).scalar() or 0

    policy_rejected = db.query(func.count(PaymentFailure.id)).filter(
        PaymentFailure.policy_approved == "rejected"
    ).scalar() or 0

    at_risk_amount = db.query(func.sum(PaymentFailure.amount)).scalar() or 0

    # Unnecessary retries avoided:
    # 1. Permanent/unfixable payment methods (expired/blocked cards) avoid standard 3 retries
    card_updates = db.query(func.count(PaymentFailure.id)).filter(
        PaymentFailure.recommended_action == "request_payment_method_update"
    ).scalar() or 0
    # 2. Cancelled mandates avoid standard 3 retries
    mandate_updates = db.query(func.count(PaymentFailure.id)).filter(
        PaymentFailure.recommended_action == "request_reauthorisation"
    ).scalar() or 0
    # 3. Policy rejections directly prevent repeated attempts
    retries_avoided = (card_updates * 3) + (mandate_updates * 3) + policy_rejected

    return {
        "total_failures": total,
        "classified_by_rule": rule_classified,
        "classified_by_claude": ambiguous_routed_to_claude,
        "policy_rejected_count": policy_rejected,
        "recovered_count": recovered_count,
        "recovered_amount": round(recovered_amount, 2),
        "unresolved_or_failed_count": unresolved,
        "manual_review_count": manual_review,
        "retries_avoided": retries_avoided,
        "total_amount_at_risk": round(at_risk_amount, 2),
        "recovery_rate": round(recovered_count / total, 4) if total else None,
        "note": "recovered_amount reflects SIMULATED recovery outcomes — see action_execution_mode on each record.",
    }
