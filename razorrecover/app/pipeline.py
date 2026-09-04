"""
Phase 2 orchestration: run rule classification, then (if a rule matched)
run the policy validator, updating the record and audit trail at each step.

If no rule confidently matches, the failure is left in CLASSIFIED status
with category=None — that's the explicit handoff point for Phase 3 (Claude)
to pick up. Nothing here forces a guess.
"""
from sqlalchemy.orm import Session

from app.models import PaymentFailure, FailureStatus
from app.classifier import classify_by_rules
from app.policy import validate_action, get_subscription_history
from app.llm_classifier import classify_with_claude, GEMINI_MODEL
from app.executor import execute_action
from app.audit import log_event

AMBIGUOUS_CATEGORY = "unknown_bank_decline"


def process_failure(db: Session, failure: PaymentFailure) -> PaymentFailure:
    fields = {
        "amount": failure.amount,
        "error_code": failure.error_code,
        "error_description": failure.error_description,
        "error_reason": failure.error_reason,
        "error_step": failure.error_step,
    }

    rule_result = classify_by_rules(fields)

    if rule_result is None:
        return _handle_ambiguous_case(db, failure, fields)

    # --- rule matched: record the classification ---
    failure.category = rule_result.category
    failure.confidence = rule_result.confidence
    failure.decided_by = rule_result.decided_by
    failure.recommended_action = rule_result.recommended_action
    failure.decision_reason = rule_result.decision_reason
    failure.status = FailureStatus.CLASSIFIED
    db.commit()
    db.refresh(failure)

    log_event(db, failure.id, "rule_classified", {
        "category": rule_result.category,
        "recommended_action": rule_result.recommended_action,
        "confidence": rule_result.confidence,
        "reason": rule_result.decision_reason,
    })

    return _apply_policy_and_finalize(db, failure, rule_result.recommended_action, rule_result.confidence)


def _handle_ambiguous_case(db: Session, failure: PaymentFailure, fields: dict) -> PaymentFailure:
    """No deterministic rule matched — hand off to Claude (Phase 3)."""
    failure.category = AMBIGUOUS_CATEGORY
    failure.status = FailureStatus.CLASSIFIED
    db.commit()
    db.refresh(failure)
    log_event(db, failure.id, "rule_classification_inconclusive", {
        "note": "No deterministic rule matched — routing to Claude (Phase 3).",
    })

    history = get_subscription_history(db, failure.subscription_id) if failure.subscription_id else None
    decision = classify_with_claude(fields, history)

    if decision is None:
        # Claude call failed, or returned something invalid — do NOT guess.
        # Route straight to manual review, same as a policy rejection would.
        failure.status = FailureStatus.MANUAL_REVIEW
        failure.decision_reason = "Claude classification unavailable or invalid — routed to manual review."
        db.commit()
        db.refresh(failure)
        log_event(db, failure.id, "claude_classification_failed", {
            "note": "Claude call failed or returned invalid/unparseable output.",
        })
        return failure

    failure.category = decision.category
    failure.confidence = decision.confidence
    failure.decided_by = "claude"
    failure.recommended_action = decision.recommended_action
    failure.decision_reason = decision.reason
    failure.customer_message = decision.customer_message
    db.commit()
    db.refresh(failure)

    log_event(db, failure.id, "claude_classified", {
        "category": decision.category,
        "recommended_action": decision.recommended_action,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "retry_after_hours": decision.retry_after_hours,
        "model": GEMINI_MODEL,
    })

    return _apply_policy_and_finalize(db, failure, decision.recommended_action, decision.confidence)


def _apply_policy_and_finalize(db: Session, failure: PaymentFailure, recommended_action: str, confidence: float) -> PaymentFailure:
    """Shared by both the rule path and the Claude path — same policy gate for both."""
    policy_result = validate_action(db, failure, recommended_action, confidence)

    failure.policy_approved = "approved" if policy_result.approved else "rejected"
    failure.policy_rejection_reason = policy_result.rejection_reason
    failure.status = FailureStatus.DECIDED if policy_result.approved else FailureStatus.MANUAL_REVIEW
    db.commit()
    db.refresh(failure)

    log_event(db, failure.id, "policy_checked", {
        "approved": policy_result.approved,
        "rejection_reason": policy_result.rejection_reason,
    })

    if policy_result.approved:
        failure = execute_action(db, failure)

    return failure
