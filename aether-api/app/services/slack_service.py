"""
Slack Integration Service

Handles sending alerts to Slack via webhooks.
"""
import httpx
from typing import Dict, Any, Optional
from datetime import datetime

from app.models.alert import AlertType, Severity


class SlackService:
    """Service for sending alerts to Slack."""

    @staticmethod
    async def send_alert(
        webhook_url: str,
        alert_type: AlertType,
        severity: Severity,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        project_name: str = "Unknown Project"
    ) -> bool:
        """
        Send an alert to Slack via webhook.

        Args:
            webhook_url: Slack webhook URL
            alert_type: Type of alert
            severity: Alert severity level
            message: Alert message
            metadata: Additional alert metadata
            project_name: Name of the project

        Returns:
            True if successful, False otherwise
        """
        if not webhook_url:
            return False

        # Choose emoji and color based on severity
        severity_config = {
            Severity.INFO: {"emoji": "ℹ️", "color": "#36a64f"},  # Green
            Severity.WARNING: {"emoji": "⚠️", "color": "#ff9900"},  # Orange
            Severity.CRITICAL: {"emoji": "🚨", "color": "#ff0000"},  # Red
        }

        config = severity_config.get(severity, {"emoji": "ℹ️", "color": "#36a64f"})

        # Choose alert type emoji
        type_emoji = {
            AlertType.HALLUCINATION: "🤥",
            AlertType.COST_SPIKE: "💰",
            AlertType.HIGH_LATENCY: "⏱️",
            AlertType.QUALITY_DROP: "📉",
            AlertType.ERROR_RATE: "❌",
        }

        alert_emoji = type_emoji.get(alert_type, "⚡")

        # Build Slack message
        slack_message = {
            "text": f"{config['emoji']} {alert_emoji} **{alert_type.value.replace('_', ' ').title()}** Alert",
            "attachments": [
                {
                    "color": config["color"],
                    "title": f"{severity.value.upper()}: {alert_type.value.replace('_', ' ').title()}",
                    "text": message,
                    "fields": [
                        {
                            "title": "Project",
                            "value": project_name,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": False
                        }
                    ],
                    "footer": "Aether RAG Monitoring",
                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png"
                }
            ]
        }

        # Add metadata fields if available
        if metadata:
            for key, value in metadata.items():
                if key not in ["trace_id", "evaluation_id"]:  # Skip IDs in main display
                    slack_message["attachments"][0]["fields"].append({
                        "title": key.replace("_", " ").title(),
                        "value": str(value),
                        "short": True
                    })

            # Add trace link if available
            if "trace_id" in metadata:
                slack_message["attachments"][0]["fields"].append({
                    "title": "Trace ID",
                    "value": f"`{metadata['trace_id']}`",
                    "short": False
                })

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=slack_message,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"   ⚠️  Failed to send Slack alert: {e}")
            return False


    @staticmethod
    async def send_hallucination_alert(
        webhook_url: str,
        project_name: str,
        trace_id: str,
        query: str,
        response: str,
        faithfulness_score: float,
        threshold: float
    ) -> bool:
        """
        Send a hallucination detection alert to Slack.

        Args:
            webhook_url: Slack webhook URL
            project_name: Name of the project
            trace_id: ID of the trace
            query: User query
            response: Generated response
            faithfulness_score: Faithfulness score
            threshold: Configured threshold

        Returns:
            True if successful, False otherwise
        """
        # Truncate long text for Slack
        query_preview = query[:200] + "..." if len(query) > 200 else query
        response_preview = response[:300] + "..." if len(response) > 300 else response

        message = f"Hallucination detected in RAG response!\n\n"
        message += f"*Query:* {query_preview}\n\n"
        message += f"*Response:* {response_preview}\n\n"
        message += f"*Faithfulness Score:* {faithfulness_score:.2f} (threshold: {threshold})"

        metadata = {
            "trace_id": trace_id,
            "faithfulness_score": f"{faithfulness_score:.2f}",
            "threshold": f"{threshold:.2f}"
        }

        return await SlackService.send_alert(
            webhook_url=webhook_url,
            alert_type=AlertType.HALLUCINATION,
            severity=Severity.CRITICAL,
            message=message,
            metadata=metadata,
            project_name=project_name
        )


    @staticmethod
    async def send_cost_spike_alert(
        webhook_url: str,
        project_name: str,
        current_cost: float,
        budget: float,
        time_period: str = "daily"
    ) -> bool:
        """
        Send a cost spike alert to Slack.

        Args:
            webhook_url: Slack webhook URL
            project_name: Name of the project
            current_cost: Current cost
            budget: Budget threshold
            time_period: Time period for the budget

        Returns:
            True if successful, False otherwise
        """
        overage_pct = ((current_cost - budget) / budget) * 100

        message = f"Cost spike detected!\n\n"
        message += f"Your {time_period} spend has exceeded the budget.\n\n"
        message += f"*Current Cost:* ${current_cost:.4f}\n"
        message += f"*Budget:* ${budget:.4f}\n"
        message += f"*Overage:* {overage_pct:.1f}%"

        metadata = {
            "current_cost": f"${current_cost:.4f}",
            "budget": f"${budget:.4f}",
            "overage": f"{overage_pct:.1f}%"
        }

        return await SlackService.send_alert(
            webhook_url=webhook_url,
            alert_type=AlertType.COST_SPIKE,
            severity=Severity.WARNING,
            message=message,
            metadata=metadata,
            project_name=project_name
        )


    @staticmethod
    async def send_latency_alert(
        webhook_url: str,
        project_name: str,
        p95_latency: float,
        threshold: float
    ) -> bool:
        """
        Send a high latency alert to Slack.

        Args:
            webhook_url: Slack webhook URL
            project_name: Name of the project
            p95_latency: Current P95 latency in milliseconds
            threshold: Threshold in milliseconds

        Returns:
            True if successful, False otherwise
        """
        message = f"High latency detected!\n\n"
        message += f"P95 latency has exceeded the configured threshold.\n\n"
        message += f"*Current P95:* {p95_latency:.0f}ms\n"
        message += f"*Threshold:* {threshold:.0f}ms"

        metadata = {
            "p95_latency": f"{p95_latency:.0f}ms",
            "threshold": f"{threshold:.0f}ms"
        }

        return await SlackService.send_alert(
            webhook_url=webhook_url,
            alert_type=AlertType.HIGH_LATENCY,
            severity=Severity.WARNING,
            message=message,
            metadata=metadata,
            project_name=project_name
        )
