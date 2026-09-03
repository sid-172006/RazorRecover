"""
Pydantic response models for our own API (not for validating Razorpay's raw
payload — that's parsed defensively in webhook_parser.py since Razorpay's
schema has many optional/nested fields we don't want to hard-fail on).

Uses typing.Optional instead of the `X | None` syntax throughout — Pydantic
has to resolve these at runtime to build its validators, and Python 3.9
cannot evaluate `X | None` at runtime even with `from __future__ import
annotations` (that only defers evaluation, it doesn't add the syntax to
older Python). Optional[X] is the compatible equivalent.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PaymentFailureOut(BaseModel):
    id: str
    razorpay_event_id: str
    razorpay_payment_id: Optional[str]
    subscription_id: Optional[str]
    execution_mode: str
    amount: Optional[float]
    error_code: Optional[str]
    error_description: Optional[str]
    error_source: Optional[str]
    error_step: Optional[str]
    error_reason: Optional[str]
    category: Optional[str]
    confidence: Optional[float]
    decided_by: Optional[str]
    recommended_action: Optional[str]
    decision_reason: Optional[str]
    customer_message: Optional[str]
    policy_approved: Optional[str]
    policy_rejection_reason: Optional[str]
    executed_action: Optional[str]
    action_execution_mode: Optional[str]
    execution_result: Optional[str]
    customer_ref_masked: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditEventOut(BaseModel):
    id: str
    event_type: str
    detail: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
