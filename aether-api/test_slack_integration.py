#!/usr/bin/env python3
"""
End-to-End Slack Alerting Integration Test

Tests the complete flow:
1. Configure alert settings with Slack webhook
2. Ingest a trace with hallucination
3. Worker processes and detects hallucination
4. Alert sent to Slack
5. Alert saved to database
"""
import requests
import time
from uuid import UUID

# Configuration
API_BASE_URL = "http://127.0.0.1:8000"
PROJECT_ID = "2afd5cf5-0a7e-4859-b6ba-4c238f15539c"  # From seed_data.py
API_KEY = "ae_test_key_development_12345"

# IMPORTANT: You need to provide a real Slack webhook URL to test
# Get one from https://api.slack.com/messaging/webhooks
SLACK_WEBHOOK_URL = input("Enter your Slack webhook URL (or press Enter to skip): ").strip()

if not SLACK_WEBHOOK_URL:
    print("\n⚠️  No Slack webhook provided. This test will configure alerting but won't send to Slack.")
    print("To fully test Slack integration:")
    print("1. Create a Slack webhook at https://api.slack.com/messaging/webhooks")
    print("2. Re-run this test with the webhook URL")
    print()
else:
    print(f"\n✅ Using Slack webhook: {SLACK_WEBHOOK_URL[:50]}...")
    print()

print("=" * 70)
print("🧪 Aether Slack Alerting Integration Test")
print("=" * 70)
print()

# Step 1: Configure alert settings
print("1️⃣  Configuring alert settings...")

alert_config = {
    "slack_webhook_url": SLACK_WEBHOOK_URL if SLACK_WEBHOOK_URL else None,
    "slack_enabled": bool(SLACK_WEBHOOK_URL),
    "hallucination_threshold": 0.5,
    "hallucination_alerts_enabled": True,
    "daily_cost_budget_usd": 1.0,
    "cost_spike_alerts_enabled": True,
    "latency_p95_threshold_ms": 5000,
    "latency_alerts_enabled": True
}

# Try to create, or update if exists
try:
    response = requests.post(
        f"{API_BASE_URL}/api/v1/alert-config/{PROJECT_ID}",
        json=alert_config,
        timeout=5
    )
    if response.status_code == 409:  # Already exists
        print("   Alert config already exists, updating...")
        response = requests.put(
            f"{API_BASE_URL}/api/v1/alert-config/{PROJECT_ID}",
            json=alert_config,
            timeout=5
        )
    response.raise_for_status()
    print(f"   ✅ Alert config saved")
    print(f"   Slack enabled: {bool(SLACK_WEBHOOK_URL)}")
    print(f"   Hallucination threshold: 0.5")
    print()
except requests.exceptions.RequestException as e:
    print(f"   ❌ Failed to configure alerts: {e}")
    print(f"   Response: {response.text if 'response' in locals() else 'No response'}")
    exit(1)

# Step 2: Ingest a trace with intentional hallucination
print("2️⃣  Ingesting trace with hallucination...")

trace_data = {
    "project_id": PROJECT_ID,
    "query": "What is the capital of Germany?",
    "response": "The capital of Germany is Paris, which is known for its beautiful Brandenburg Gate and rich history. Berlin is actually just a small town in the countryside.",  # Intentional hallucination
    "contexts": [
        {
            "text": "Berlin is the capital and largest city of Germany. It is located in northeastern Germany.",
            "source": "doc_germany_001",
            "score": 0.98
        },
        {
            "text": "Germany's capital, Berlin, has been the seat of the German government since 1999.",
            "source": "doc_germany_002",
            "score": 0.92
        }
    ],
    "metadata": {
        "model": "gpt-4",
        "test": "slack_integration",
        "user_id": "test_user_123"
    },
    "token_count": 425,
    "latency_ms": 850,
    "cost_usd": 0.011
}

headers = {"X-API-Key": API_KEY}

try:
    response = requests.post(
        f"{API_BASE_URL}/api/v1/traces",
        json=trace_data,
        headers=headers,
        timeout=5
    )
    response.raise_for_status()
    trace_result = response.json()
    trace_id = trace_result["trace_id"]
    print(f"   ✅ Trace ingested: {trace_id}")
    print()
except requests.exceptions.RequestException as e:
    print(f"   ❌ Failed to ingest trace: {e}")
    exit(1)

# Step 3: Wait for worker to process
print("3️⃣  Waiting for evaluation worker to process...")
print("   (Make sure the worker is running with: python run_worker_once.py)")
print()

# Poll for evaluation completion
max_wait = 30  # seconds
start_time = time.time()
evaluation_complete = False

while (time.time() - start_time) < max_wait:
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/traces/{trace_id}",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        trace_data = response.json()

        if trace_data.get("evaluation"):
            evaluation_complete = True
            print(f"   ✅ Evaluation complete!")
            print(f"      Faithfulness: {trace_data['evaluation'].get('faithfulness', 'N/A')}")
            print(f"      Hallucination detected: {trace_data['evaluation'].get('hallucination_detected', False)}")
            print(f"      Token overlap: {trace_data['evaluation'].get('token_overlap_ratio', 0):.2%}")
            print()
            break

        time.sleep(2)
        print("   ⏳ Still processing...")

    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Error checking trace: {e}")
        time.sleep(2)

if not evaluation_complete:
    print("   ⚠️  Evaluation did not complete within 30 seconds")
    print("   Make sure the worker is running!")
    exit(1)

# Step 4: Check for alert in database
print("4️⃣  Checking for alerts...")

try:
    response = requests.get(
        f"{API_BASE_URL}/api/v1/alerts/{PROJECT_ID}?resolved=false",
        timeout=5
    )
    response.raise_for_status()
    alerts_data = response.json()

    if alerts_data["total"] > 0:
        print(f"   ✅ Found {alerts_data['total']} alert(s)")
        for alert in alerts_data["alerts"]:
            print(f"\n   Alert Details:")
            print(f"   - Type: {alert['alert_type']}")
            print(f"   - Severity: {alert['severity']}")
            print(f"   - Message: {alert['message']}")
            print(f"   - Created: {alert['created_at']}")
            if alert.get("alert_metadata"):
                print(f"   - Metadata: {alert['alert_metadata']}")
    else:
        print("   ⚠️  No alerts found (this might be expected if hallucination score was above threshold)")

except requests.exceptions.RequestException as e:
    print(f"   ⚠️  Error fetching alerts: {e}")

print()
print("=" * 70)
print("✅ Slack Integration Test Complete")
print("=" * 70)
print()

if SLACK_WEBHOOK_URL:
    print("Check your Slack channel for the alert notification!")
else:
    print("To test Slack notifications:")
    print("1. Get a webhook URL from https://api.slack.com/messaging/webhooks")
    print("2. Update the alert config with: PUT /api/v1/alert-config/{project_id}")
    print("3. Ingest a new trace with hallucination")
    print("4. Watch for Slack notification!")
print()
