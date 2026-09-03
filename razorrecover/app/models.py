"""
MVP schema — deliberately a bit denormalized for phase 1 speed.
Split into separate decisions/recovery_actions tables later if there's time;
not worth losing a build day to schema perfectionism up front.
"""
import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionMode(str, enum.Enum):
    LIVE_TEST_MODE = "LIVE_TEST_MODE"   # real Razorpay test-mode webhook payload
    SIMULATED = "SIMULATED"             # constructed fixture, not from a real webhook
    DRY_RUN = "DRY_RUN"                 # decision made, action not yet executed


class FailureStatus(str, enum.Enum):
    RECEIVED = "received"
    CLASSIFIED = "classified"
    DECIDED = "decided"
    EXECUTED = "executed"
    MANUAL_REVIEW = "manual_review_required"
    RECOVERY_EXHAUSTED = "recovery_exhausted"


class PaymentFailure(Base):
    __tablename__ = "payment_failures"

    id = Column(String, primary_key=True, default=_uuid)

    # --- idempotency / source identity ---
    razorpay_event_id = Column(String, unique=True, index=True, nullable=False)
    razorpay_payment_id = Column(String, index=True, nullable=True)
    subscription_id = Column(String, index=True, nullable=True)

    # --- provenance (be honest about what's real vs simulated) ---
    execution_mode = Column(Enum(ExecutionMode), nullable=False, default=ExecutionMode.LIVE_TEST_MODE)

    # --- raw payload, kept separate from normalized fields ---
    raw_payload = Column(Text, nullable=False)  # JSON string, untouched

    # --- normalized failure fields (from Razorpay's error object) ---
    amount = Column(Float, nullable=True)
    error_code = Column(String, nullable=True)
    error_description = Column(Text, nullable=True)
    error_source = Column(String, nullable=True)
    error_step = Column(String, nullable=True)
    error_reason = Column(String, nullable=True)

    # --- classification + decision (populated by rules or Claude) ---
    category = Column(String, nullable=True)          # e.g. "insufficient_balance"
    confidence = Column(Float, nullable=True)          # null for deterministic rule matches
    decided_by = Column(String, nullable=True)         # "rule" | "claude"
    recommended_action = Column(String, nullable=True)
    decision_reason = Column(Text, nullable=True)
    customer_message = Column(Text, nullable=True)

    # --- policy validator outcome ---
    policy_approved = Column(String, nullable=True)    # "approved" | "rejected" | null
    policy_rejection_reason = Column(Text, nullable=True)

    # --- execution outcome ---
    executed_action = Column(String, nullable=True)
    action_execution_mode = Column(String, nullable=True)  # "SIMULATED" | "LIVE_TEST_MODE" | "DRY_RUN"
    execution_result = Column(String, nullable=True)   # "recovered" | "failed" | "pending" | "unresolved" | null

    status = Column(Enum(FailureStatus), nullable=False, default=FailureStatus.RECEIVED)

    # masked identifiers only — never store raw card/OTP data
    customer_ref_masked = Column(String, nullable=True)

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    audit_events = relationship("AuditEvent", back_populates="payment_failure", order_by="AuditEvent.created_at")


class AuditEvent(Base):
    """
    Immutable log: one row per meaningful step for a given payment_failure.
    This IS the audit trail the judges want to see — never update or delete rows here.
    """
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=_uuid)
    payment_failure_id = Column(String, ForeignKey("payment_failures.id"), nullable=False, index=True)

    event_type = Column(String, nullable=False)   # e.g. "webhook_received", "rule_classified",
                                                    # "claude_decision", "policy_rejected", "action_executed"
    detail = Column(Text, nullable=True)           # JSON string with the specifics of this step
    created_at = Column(DateTime, default=_now)

    payment_failure = relationship("PaymentFailure", back_populates="audit_events")
