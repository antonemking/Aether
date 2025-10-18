"""
Metrics Service

Aggregates and computes metrics for alerting (cost spikes, latency, etc.)
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import RAGTrace, Evaluation


class MetricsService:
    """Service for computing aggregate metrics."""

    @staticmethod
    def get_daily_cost(db: Session, project_id: str, date: Optional[datetime] = None) -> float:
        """
        Calculate total evaluation cost for a project on a given day.

        Args:
            db: Database session
            project_id: Project UUID
            date: Date to calculate cost for (defaults to today)

        Returns:
            Total cost in USD
        """
        if date is None:
            date = datetime.utcnow()

        # Start and end of the day
        start_of_day = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_of_day = start_of_day + timedelta(days=1)

        # Sum all evaluation costs for traces in this project on this day
        result = db.query(func.sum(Evaluation.evaluation_cost_usd)).join(
            RAGTrace, Evaluation.trace_id == RAGTrace.id
        ).filter(
            RAGTrace.project_id == project_id,
            Evaluation.evaluated_at >= start_of_day,
            Evaluation.evaluated_at < end_of_day
        ).scalar()

        return float(result) if result else 0.0


    @staticmethod
    def get_p95_latency(db: Session, project_id: str, hours: int = 1) -> Optional[float]:
        """
        Calculate P95 latency for a project over the last N hours.

        Args:
            db: Database session
            project_id: Project UUID
            hours: Number of hours to look back

        Returns:
            P95 latency in milliseconds, or None if no data
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Get all latencies for this project in the time window
        latencies = db.query(RAGTrace.latency_ms).filter(
            RAGTrace.project_id == project_id,
            RAGTrace.created_at >= cutoff_time,
            RAGTrace.latency_ms.isnot(None)
        ).order_by(RAGTrace.latency_ms).all()

        if not latencies:
            return None

        # Calculate P95
        latency_values = [l[0] for l in latencies]
        p95_index = int(len(latency_values) * 0.95)
        return float(latency_values[p95_index])


    @staticmethod
    def get_hourly_trace_count(db: Session, project_id: str, hours: int = 1) -> int:
        """
        Count traces for a project in the last N hours.

        Args:
            db: Database session
            project_id: Project UUID
            hours: Number of hours to look back

        Returns:
            Number of traces
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        count = db.query(func.count(RAGTrace.id)).filter(
            RAGTrace.project_id == project_id,
            RAGTrace.created_at >= cutoff_time
        ).scalar()

        return int(count) if count else 0


    @staticmethod
    def get_hallucination_rate(db: Session, project_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate hallucination rate for a project over the last N hours.

        Args:
            db: Database session
            project_id: Project UUID
            hours: Number of hours to look back

        Returns:
            Dictionary with total_evaluations, hallucinations, and rate
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Count total evaluations
        total = db.query(func.count(Evaluation.id)).join(
            RAGTrace, Evaluation.trace_id == RAGTrace.id
        ).filter(
            RAGTrace.project_id == project_id,
            Evaluation.evaluated_at >= cutoff_time
        ).scalar()

        # Count hallucinations
        hallucinations = db.query(func.count(Evaluation.id)).join(
            RAGTrace, Evaluation.trace_id == RAGTrace.id
        ).filter(
            RAGTrace.project_id == project_id,
            Evaluation.evaluated_at >= cutoff_time,
            Evaluation.hallucination_detected == True
        ).scalar()

        total = int(total) if total else 0
        hallucinations = int(hallucinations) if hallucinations else 0

        rate = (hallucinations / total) if total > 0 else 0.0

        return {
            "total_evaluations": total,
            "hallucinations": hallucinations,
            "rate": rate
        }
