"""
Small helper so every step of the pipeline logs itself the same way.
Call this at every meaningful transition — received, classified, decided,
policy-checked, executed — so the dashboard can render a full timeline
per payment failure later.
"""
from __future__ import annotations

import json
from sqlalchemy.orm import Session

from app.models import AuditEvent


def log_event(db: Session, payment_failure_id: str, event_type: str, detail: dict | None = None) -> AuditEvent:
    event = AuditEvent(
        payment_failure_id=payment_failure_id,
        event_type=event_type,
        detail=json.dumps(detail) if detail is not None else None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
