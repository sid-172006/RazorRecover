"""
Phase 3 — LLM classification for genuinely ambiguous failures
(the ones app/classifier.py's rules couldn't confidently label).

Uses Google Gemini via direct REST API (no SDK needed — avoids Python 3.9
dependency conflicts with google-generativeai).

Design principle from the spec, enforced here: the LLM RECOMMENDS, it never
acts. This module only returns a structured, validated decision — the
caller (pipeline.py) still runs it through the exact same policy validator
that rule-based decisions go through. If the LLM's response is malformed,
uses an action outside the allowed set, or the API call fails outright,
this returns None and the caller routes the case to manual review instead
of guessing.
"""
from __future__ import annotations

import json
import os
import logging
from typing import Optional

import requests
from pydantic import BaseModel, field_validator

from app.policy import ACTION_METADATA

logger = logging.getLogger("razorrecover")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ALLOWED_ACTIONS = list(ACTION_METADATA.keys())

SYSTEM_PROMPT = f"""You are a payment-failure triage assistant for RazorRecover, an \
AI agent that helps merchants recover failed recurring payments on Razorpay.

You are given details of a failed payment that a deterministic rule engine \
could NOT confidently classify (the error was generic or ambiguous — for \
example, a bank decline with no specific reason given, which Razorpay's own \
data shows genuinely happens since banks don't always share why).

Your job is ONLY to recommend a classification and next action. You do NOT \
execute anything — a separate policy system will independently validate \
your recommendation against retry budgets, notification cooldowns, and \
other safety rules before anything happens. If you are unsure, say so with \
a low confidence score rather than guessing — that is the correct, safe \
answer, not a failure.

Respond with ONLY a single JSON object, no markdown fences, no preamble, \
no explanation outside the JSON. Use exactly this shape:

{{
  "category": "<short snake_case label for the failure reason>",
  "confidence": <float 0.0-1.0>,
  "recommended_action": "<one of: {', '.join(ALLOWED_ACTIONS)}>",
  "reason": "<one or two sentences explaining your reasoning>",
  "customer_message": "<a short, clear message to send the customer, or empty string if no customer contact is warranted>",
  "retry_after_hours": <integer hours to wait before a retry, or null if not applicable>
}}

If recommended_action is not clearly justified by the evidence, choose \
"escalate_manual_review" and set a low confidence rather than picking an \
action you're not confident about."""


class ClaudeDecision(BaseModel):
    """Structured LLM decision — name kept as ClaudeDecision to avoid
    cascading renames across pipeline.py, executor.py, and tests."""
    category: str
    confidence: float
    recommended_action: str
    reason: str
    customer_message: str = ""
    retry_after_hours: Optional[int] = None

    @field_validator("recommended_action")
    @classmethod
    def action_must_be_allowed(cls, v: str) -> str:
        if v not in ACTION_METADATA:
            raise ValueError(f"'{v}' is not an allowed action ({ALLOWED_ACTIONS})")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


def _build_user_prompt(fields: dict, history: dict | None) -> str:
    lines = [
        "Failed payment details:",
        f"- amount: ₹{fields.get('amount')}" if fields.get("amount") is not None else "- amount: unknown",
        f"- error_code: {fields.get('error_code')}",
        f"- error_description: {fields.get('error_description')}",
        f"- error_source: {fields.get('error_source')}",
        f"- error_step: {fields.get('error_step')}",
        f"- error_reason: {fields.get('error_reason')}",
    ]
    if history:
        lines.append("")
        lines.append("Recent history for this subscription:")
        lines.append(f"- prior failures in last 7 days: {history.get('recent_failure_count', 0)}")
        lines.append(f"- customer notified recently: {history.get('recently_notified', False)}")
    return "\n".join(lines)


def classify_with_claude(fields: dict, history: dict | None = None) -> ClaudeDecision | None:
    """Function name kept as classify_with_claude to avoid cascading renames.
    Now uses Google Gemini via REST API under the hood."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — cannot run LLM classification.")
        return None

    user_prompt = _build_user_prompt(fields, history)
    url = GEMINI_API_URL.format(model=GEMINI_MODEL)

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 1000,
            "temperature": 0.2,
        }
    }

    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return None

    # Defensive cleanup in case the model wraps the JSON in fences despite instructions
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (possibly with language tag like ```json)
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned.lstrip("`")
    if cleaned.endswith("```"):
        cleaned = cleaned[: cleaned.rfind("```")].strip()

    try:
        parsed = json.loads(cleaned)
        return ClaudeDecision(**parsed)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.error(f"LLM returned invalid/unparseable output, routing to manual review. Error: {e}. Raw: {raw_text[:300]}")
        return None
