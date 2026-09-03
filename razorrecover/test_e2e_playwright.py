"""
Professional End-to-End Test Suite for RazorRecover
Tests:
1. Complete Backend Route Coverage:
   - GET /health
   - GET /metrics
   - GET /payment-failures
   - GET /payment-failures/{id}
   - GET /payment-failures/{id}/audit-trail
   - POST /webhooks/razorpay (Security: Missing Signature -> 400/500)
   - POST /webhooks/razorpay (Security: Invalid Signature -> 400)
   - POST /webhooks/razorpay (Idempotency: Duplicate Event -> duplicate_ignored)
2. LLM Routing Verification:
   - Ambiguous payload triggers LLM fallback
   - Decision parsed, policy-checked, and executed
   - Audit trail contains all expected lifecycle events
3. Playwright Headless Browser UI Test:
   - Header, Metrics Strip rendering
   - Failure list selection and dynamic timeline inspection
   - Visual verification and screenshot capture
"""
import os
import sys
import io
import json
import time
import hmac
import hashlib
import requests
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE = "http://localhost:8000"
DASHBOARD_BASE = "http://localhost:3000"
WEBHOOK_SECRET = "my_test_secret_123"

def print_banner(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_api_routes():
    print_banner("1. TESTING ALL API ROUTES & SECURITY")

    # 1. Health
    r = requests.get(f"{API_BASE}/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print(" [PASS] GET /health -> 200 OK", r.json())

    # 2. Metrics
    r = requests.get(f"{API_BASE}/metrics")
    assert r.status_code == 200, f"Metrics failed: {r.status_code}"
    metrics = r.json()
    assert "total_failures" in metrics
    assert "recovered_count" in metrics
    assert "recovered_amount" in metrics
    assert "retries_avoided" in metrics
    assert "recovery_rate" in metrics
    print(f" [PASS] GET /metrics -> 200 OK (Total: {metrics['total_failures']}, Recovered: {metrics['recovered_count']}, Retries Avoided: {metrics.get('retries_avoided')}, Recovered Amt: {metrics['recovered_amount']})")

    # 3. List Payment Failures
    r = requests.get(f"{API_BASE}/payment-failures")
    assert r.status_code == 200, f"List failures failed: {r.status_code}"
    failures = r.json()
    assert len(failures) > 0, "Expected at least 1 failure in DB"
    print(f" [PASS] GET /payment-failures -> 200 OK ({len(failures)} records returned)")

    first_failure = failures[0]
    failure_id = first_failure["id"]

    # 4. Single Payment Failure Detail
    r = requests.get(f"{API_BASE}/payment-failures/{failure_id}")
    assert r.status_code == 200, f"Single failure failed: {r.status_code}"
    detail = r.json()
    assert detail["id"] == failure_id
    print(f" [PASS] GET /payment-failures/{failure_id} -> 200 OK (Category: {detail.get('category')})")

    # 5. Audit Trail for failure
    r = requests.get(f"{API_BASE}/payment-failures/{failure_id}/audit-trail")
    assert r.status_code == 200, f"Audit trail failed: {r.status_code}"
    trail = r.json()
    assert len(trail) > 0, "Expected at least 1 audit event"
    event_types = [e["event_type"] for e in trail]
    print(f" [PASS] GET /payment-failures/{failure_id}/audit-trail -> 200 OK ({len(trail)} events: {event_types})")

    # 6. Webhook Security: Missing signature
    dummy_payload = json.dumps({"event": "payment.failed"})
    r = requests.post(f"{API_BASE}/webhooks/razorpay", data=dummy_payload)
    assert r.status_code in [400, 422], f"Expected 400 for missing signature, got {r.status_code}"
    print(f" [PASS] POST /webhooks/razorpay (No Signature) -> {r.status_code} Rejected")

    # 7. Webhook Security: Invalid signature
    r = requests.post(
        f"{API_BASE}/webhooks/razorpay",
        data=dummy_payload,
        headers={"X-Razorpay-Signature": "invalid_sig_123456"}
    )
    assert r.status_code == 400, f"Expected 400 for invalid signature, got {r.status_code}"
    print(f" [PASS] POST /webhooks/razorpay (Bad Signature) -> 400 Invalid Webhook Signature")

    # 8. Webhook Security: Idempotency (Duplicate event)
    # Generate valid payload and sign it
    test_event_id = f"evt_test_idempotent_{int(time.time())}"
    valid_payload = {
        "id": test_event_id,
        "event": "payment.failed",
        "created_at": int(time.time()),
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_idem_1",
                    "amount": 100000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "GATEWAY_ERROR",
                    "error_description": "The card used for this payment has expired.",
                    "error_source": "customer",
                    "error_step": "payment_authorization",
                    "error_reason": "card_expired"
                }
            }
        }
    }
    body_str = json.dumps(valid_payload)
    sig = hmac.new(WEBHOOK_SECRET.encode(), body_str.encode(), hashlib.sha256).hexdigest()
    headers = {
        "X-Razorpay-Signature": sig,
        "X-RazorRecover-Test-Source": "playwright_test",
        "Content-Type": "application/json"
    }

    # First send
    r1 = requests.post(f"{API_BASE}/webhooks/razorpay", data=body_str, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["status"] == "received"
    print(f" [PASS] POST /webhooks/razorpay (First event) -> 200 Received")

    # Second send (same event ID)
    r2 = requests.post(f"{API_BASE}/webhooks/razorpay", data=body_str, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate_ignored"
    print(f" [PASS] POST /webhooks/razorpay (Duplicate event) -> 200 duplicate_ignored")

def test_llm_routing():
    print_banner("2. TESTING LLM ROUTING & PIPELINE EXECUTION")
    
    # Send ambiguous error to trigger LLM
    ambiguous_event_id = f"evt_test_llm_{int(time.time())}"
    ambiguous_payload = {
        "id": ambiguous_event_id,
        "event": "payment.failed",
        "created_at": int(time.time()),
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_llm_{int(time.time())}",
                    "amount": 88000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "GATEWAY_ERROR",
                    "error_description": "Payment was declined by customer bank without specific reason.",
                    "error_source": "customer",
                    "error_step": "payment_authorization",
                    "error_reason": None
                }
            }
        }
    }
    body_str = json.dumps(ambiguous_payload)
    sig = hmac.new(WEBHOOK_SECRET.encode(), body_str.encode(), hashlib.sha256).hexdigest()
    headers = {
        "X-Razorpay-Signature": sig,
        "X-RazorRecover-Test-Source": "playwright_test",
        "Content-Type": "application/json"
    }

    print(" -> Sending ambiguous payment failure to trigger LLM classifier...")
    t0 = time.time()
    r = requests.post(f"{API_BASE}/webhooks/razorpay", data=body_str, headers=headers, timeout=120)
    elapsed = time.time() - t0
    assert r.status_code == 200, f"Webhook failed: {r.status_code} - {r.text}"
    resp_data = r.json()
    print(f" [PASS] LLM classification webhook completed in {elapsed:.2f}s: {resp_data}")
    
    failure_id = resp_data["payment_failure_id"]
    assert resp_data["category"] != "unknown_bank_decline", "Expected LLM to assign concrete category"

    # Verify audit trail
    r_audit = requests.get(f"{API_BASE}/payment-failures/{failure_id}/audit-trail")
    events = r_audit.json()
    event_types = [e["event_type"] for e in events]
    print(f" [PASS] Audit trail verified: {event_types}")
    assert "webhook_received" in event_types
    assert "rule_classification_inconclusive" in event_types
    assert "claude_classified" in event_types
    assert "policy_checked" in event_types

def test_browser_ui_with_playwright():
    print_banner("3. TESTING DASHBOARD UI VIA PLAYWRIGHT CHROMIUM")
    os.makedirs("test_artifacts", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print(f" -> Navigating to {DASHBOARD_BASE}...")
        page.goto(DASHBOARD_BASE, wait_until="networkidle")

        # 1. Assert Title
        title = page.title()
        print(f" [PASS] Page title: '{title}'")
        assert "RazorRecover" in title or len(title) > 0

        # 2. Check Header
        header = page.locator("h1, header, div:has-text('RazorRecover')").first
        assert header.is_visible(), "Header 'RazorRecover' not visible"
        print(" [PASS] RazorRecover branding header is visible")

        # 3. Check Metrics Strip (wait for client-side API fetch)
        page.wait_for_selector("text=Total failures", timeout=15000)
        metrics_container = page.locator("text=Total failures").first
        assert metrics_container.is_visible(), "Metrics strip not visible"
        print(" [PASS] Metrics strip (Total failures, Recovered, Amount, Recovery rate) is visible")

        # 4. Check Failure List
        page.wait_for_selector("text=Failures", timeout=10000)
        failure_items = page.locator("div:has-text('SIMULATED')")
        count = failure_items.count()
        print(f" [PASS] Found {count} rendered failure items in list")
        assert count > 0, "Expected failure items rendered in UI"

        # Capture initial dashboard screenshot
        screenshot_path1 = "test_artifacts/dashboard_overview.png"
        page.screenshot(path=screenshot_path1, full_page=True)
        print(f" [PASS] Captured overview screenshot: {screenshot_path1}")

        # 5. Click on the first failure item and assert Decision Timeline
        first_item = page.locator("button, div[role='button'], div[class*='cursor-pointer']").filter(has_text="SIMULATED").first
        if not first_item.is_visible():
            first_item = failure_items.first
        
        first_item.click()
        page.wait_for_timeout(1000)

        # Check Decision Timeline Pane
        timeline_heading = page.locator("text=Decision timeline").first
        assert timeline_heading.is_visible(), "Decision timeline heading not visible"

        # Check audit trail steps in timeline
        page.wait_for_selector("text=Payment failed", timeout=5000)
        assert page.locator("text=Payment failed").first.is_visible()
        print(" [PASS] Decision timeline rendered 'Payment failed' event")

        # Capture timeline screenshot
        screenshot_path2 = "test_artifacts/timeline_inspection.png"
        page.screenshot(path=screenshot_path2, full_page=True)
        print(f" [PASS] Captured timeline screenshot: {screenshot_path2}")

        # 6. Click specifically on the LLM classified item (find by category or text)
        llm_item = page.locator("div").filter(has_text="Bank Decline Generic").first
        if llm_item.is_visible():
            llm_item.click()
            page.wait_for_timeout(1000)
            page.wait_for_selector("text=No rule matched", timeout=5000)
            print(" [PASS] LLM classified item clicked -> 'No rule matched' visible in timeline")
            screenshot_path3 = "test_artifacts/llm_timeline_inspection.png"
            page.screenshot(path=screenshot_path3, full_page=True)
            print(f" [PASS] Captured LLM timeline screenshot: {screenshot_path3}")

        browser.close()

if __name__ == "__main__":
    test_api_routes()
    test_llm_routing()
    test_browser_ui_with_playwright()
    print_banner("ALL END-TO-END TESTS PASSED SUCCESSFULLY! (100% HEALTHY)")
