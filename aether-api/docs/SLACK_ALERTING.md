# Slack Alerting System

Aether provides real-time Slack notifications for production RAG monitoring.

## Features

### Alert Types

1. **Hallucination Detection** 🤥
   - Triggered when faithfulness score falls below threshold (default: 0.5)
   - Severity: CRITICAL
   - Includes query, response preview, and faithfulness score

2. **Cost Spike** 💰
   - Triggered when daily evaluation costs exceed budget
   - Severity: WARNING
   - Includes current cost, budget, and overage percentage
   - De-duplicated: max 1 alert per day

3. **High Latency** ⏱️
   - Triggered when P95 latency exceeds threshold
   - Severity: WARNING
   - Includes current P95 and threshold
   - De-duplicated: max 1 alert per hour

## Setup

### 1. Create Slack Webhook

1. Go to https://api.slack.com/messaging/webhooks
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Aether Monitoring")
4. Select your workspace
5. Under "Incoming Webhooks", toggle "Activate Incoming Webhooks"
6. Click "Add New Webhook to Workspace"
7. Select a channel and authorize
8. Copy the webhook URL

### 2. Configure Alert Settings

Use the API to configure alert settings for your project:

```bash
# Create alert configuration
curl -X POST http://localhost:8000/api/v1/alert-config/{project_id} \
  -H "Content-Type: application/json" \
  -d '{
    "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "slack_enabled": true,
    "hallucination_threshold": 0.5,
    "hallucination_alerts_enabled": true,
    "daily_cost_budget_usd": 10.0,
    "cost_spike_alerts_enabled": true,
    "latency_p95_threshold_ms": 3000,
    "latency_alerts_enabled": true
  }'
```

### 3. Update Alert Configuration

```bash
# Update specific fields
curl -X PUT http://localhost:8000/api/v1/alert-config/{project_id} \
  -H "Content-Type: application/json" \
  -d '{
    "slack_webhook_url": "https://hooks.slack.com/services/NEW/WEBHOOK/URL",
    "daily_cost_budget_usd": 20.0
  }'
```

### 4. Get Alert Configuration

```bash
curl http://localhost:8000/api/v1/alert-config/{project_id}
```

## Alert Management

### List Alerts

```bash
# Get all unresolved alerts
curl http://localhost:8000/api/v1/alerts/{project_id}?resolved=false

# Filter by alert type
curl http://localhost:8000/api/v1/alerts/{project_id}?alert_type=hallucination

# Filter by severity
curl http://localhost:8000/api/v1/alerts/{project_id}?severity=critical

# Pagination
curl http://localhost:8000/api/v1/alerts/{project_id}?limit=20&offset=0
```

### Get Specific Alert

```bash
curl http://localhost:8000/api/v1/alerts/{project_id}/{alert_id}
```

### Resolve Alert

```bash
curl -X PUT http://localhost:8000/api/v1/alerts/{project_id}/{alert_id}/resolve
```

### Delete Alert

```bash
curl -X DELETE http://localhost:8000/api/v1/alerts/{project_id}/{alert_id}
```

## Configuration Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `slack_webhook_url` | string | null | Slack webhook URL |
| `slack_enabled` | boolean | false | Enable/disable Slack notifications |
| `hallucination_threshold` | float | 0.5 | Faithfulness score below this triggers alert |
| `hallucination_alerts_enabled` | boolean | true | Enable hallucination alerts |
| `daily_cost_budget_usd` | float | null | Daily evaluation cost budget |
| `cost_spike_alerts_enabled` | boolean | false | Enable cost spike alerts |
| `latency_p95_threshold_ms` | integer | null | P95 latency threshold in milliseconds |
| `latency_alerts_enabled` | boolean | false | Enable latency alerts |

## Alert Deduplication

To prevent alert spam, Aether automatically deduplicates certain alerts:

- **Hallucination alerts**: Sent for every hallucination (no deduplication)
- **Cost spike alerts**: Max 1 per day
- **Latency alerts**: Max 1 per hour

## Slack Message Format

Alerts are sent as rich Slack messages with:

- Color-coded attachments (green/orange/red based on severity)
- Alert type emoji
- Project name
- Timestamp
- Relevant metrics and metadata
- Trace ID for investigation

## Testing

Run the end-to-end test:

```bash
cd aether-api
python test_slack_integration.py
```

This will:
1. Configure alert settings
2. Ingest a trace with hallucination
3. Wait for worker to process
4. Verify alert was created
5. Send test notification to Slack

## Architecture

```
Trace Ingestion
  ↓
Evaluation Worker (evaluator.py)
  ↓
Compute Metrics (faithfulness, cost, latency)
  ↓
Check Alert Conditions (check_and_send_alerts)
  ↓
Create Alert Record (alerts table)
  ↓
Send to Slack (SlackService)
```

## Production Best Practices

1. **Secure webhook URLs**: Store in environment variables, not code
2. **Set appropriate thresholds**: Start conservative, tune based on data
3. **Monitor alert volume**: If receiving too many alerts, adjust thresholds
4. **Use different channels**: Separate channels for different severity levels
5. **Alert fatigue**: Implement resolution workflows to acknowledge and resolve alerts

## Metrics Service

The `MetricsService` provides aggregate metrics for alerting:

- `get_daily_cost(project_id)` - Total evaluation cost for today
- `get_p95_latency(project_id, hours=1)` - P95 latency over time window
- `get_hourly_trace_count(project_id)` - Trace volume
- `get_hallucination_rate(project_id, hours=24)` - Hallucination rate

These can be used for custom alerting logic or dashboards.

## Future Enhancements

- PagerDuty integration
- Email notifications
- Custom alert rules (e.g., "alert if hallucination rate > 5% in last hour")
- Alert acknowledgment workflow
- Alert aggregation (daily/weekly summaries)
- Webhook retry logic with exponential backoff
