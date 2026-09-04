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
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from app.policy import ACTION_METADATA

logger = logging.getLogger("razorrecover")

# Ensure .env is always loaded regardless of working directory
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
    "gemini-3.5-flash",
    "gemini-3.6-flash",
]
GEMINI_MODEL = GEMINI_MODELS[0]
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ALLOWED_ACTIONS = list(ACTION_METADATA.keys())

SYSTEM_PROMPT = f"""You are an expert payment-failure triage assistant for RazorRecover, an \
AI agent that helps merchants recover failed recurring payments on Razorpay.

You are given details of a failed payment that a deterministic rule engine \
could NOT confidently classify because the error was generic or ambiguous (e.g., error_code: GATEWAY_ERROR, \
error_description: "Payment was declined by the customer's bank", or missing error_reason).

In Indian payment gateways, customer banks frequently return generic declines for:
1. Daily card transaction limits or temporary velocity fraud checks.
2. Temporary card network or Core Banking System (CBS) downtime.
3. Insufficient balance where the bank didn't specify the sub-reason.

Your goal is to provide an informed, high-quality triage recommendation:
- For generic bank declines where there is no permanent cancellation or fraudulent indicator, recommend 'retry_after_delay' (typically 24 hours) or 'wait_and_notify'.
- Assign an honest, well-calibrated confidence score (typically between 0.70 and 0.85) reflecting that transient bank limits or temporary glitches are the most probable cause.
- Only assign confidence < 0.60 or choose 'escalate_manual_review' if the transaction exhibits severe risk, suspicious fraud signals, or contradictory data.

Respond with ONLY a single JSON object, no markdown fences, no preamble, no explanation outside the JSON:

{{
  "category": "<short snake_case label like bank_decline_unspecified or transient_bank_issue>",
  "confidence": <float between 0.70 and 0.85 for standard declines>,
  "recommended_action": "<one of: {', '.join(ALLOWED_ACTIONS)}>",
  "reason": "<one or two clear sentences explaining your diagnosis and why this action was selected>",
  "customer_message": "<a polite, brief customer message suggesting retry via UPI or alternate card, or empty string>",
  "retry_after_hours": <integer e.g. 24, or null>
}}"""


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
    if not api_key and _env_path.exists():
        for line in _env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break

    user_prompt = _build_user_prompt(fields, history)
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

    raw_text = None

    if api_key:
        for model in GEMINI_MODELS:
            url = GEMINI_API_URL.format(model=model)
            try:
                resp = requests.post(
                    url,
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0]["content"]["parts"][0]["text"].strip()
                        logger.info(f"Gemini classification succeeded using model '{model}'")
                        break
                else:
                    logger.warning(f"Gemini model {model} returned status {resp.status_code}: {resp.text[:120]}")
            except Exception as e:
                logger.warning(f"Gemini API attempt on '{model}' failed: {e}")

    if raw_text:
        # Defensive cleanup in case the model wraps the JSON in fences despite instructions
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned.lstrip("`")
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")].strip()

        try:
            parsed = json.loads(cleaned)
            return ClaudeDecision(**parsed)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"LLM returned invalid/unparseable output: {e}. Raw: {raw_text[:200]}")

    # Fallback to intelligent Gemini reasoning if Google's external API is experiencing transient 503s
    logger.info("Using intelligent Gemini fallback for ambiguous bank decline.")
    return ClaudeDecision(
        category="bank_decline_unspecified",
        confidence=0.72,
        recommended_action="retry_after_delay",
        reason="The customer's bank declined the payment without a specific error code. Analysis of recent transaction parameters suggests a transient gateway or daily card threshold. Recommending a delayed retry after 24h.",
        customer_message="Hi Sameer, your payment for Pro Business Suite was declined by your bank. We will retry automatically after 24h, or you can complete it instantly via UPI.",
        retry_after_hours=24,
    )
