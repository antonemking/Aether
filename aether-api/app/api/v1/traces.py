from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import json
import uuid

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models import RAGTrace
from app.schemas.trace import TraceCreate, TraceIngestResponse
import redis.asyncio as redis

router = APIRouter()


async def queue_evaluation(trace_id: str, redis_conn: redis.Redis):
    """Queue a trace for evaluation."""
    job_data = {
        "job_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
    }
    # Push to Redis list (simple queue)
    await redis_conn.lpush("evaluation_queue", json.dumps(job_data))


@router.post("/", response_model=TraceIngestResponse, status_code=202)
async def ingest_trace(
    trace: TraceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    redis_conn: redis.Redis = Depends(get_redis),
):
    """
    Ingest a RAG trace for evaluation.

    Returns 202 Accepted - trace is queued for async processing.
    """
    try:
        # Create trace record
        db_trace = RAGTrace(
            project_id=trace.project_id,
            query=trace.query,
            response=trace.response,
            contexts=[ctx.model_dump() for ctx in trace.contexts] if trace.contexts else None,
            trace_metadata=trace.metadata,
            token_count=trace.token_count,
            latency_ms=trace.latency_ms,
            cost_usd=trace.cost_usd,
            created_at=trace.timestamp or datetime.utcnow(),
        )

        db.add(db_trace)
        db.commit()
        db.refresh(db_trace)

        # Queue for evaluation (async)
        background_tasks.add_task(queue_evaluation, str(db_trace.id), redis_conn)

        return TraceIngestResponse(
            trace_id=db_trace.id,
            status="queued",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to ingest trace: {str(e)}")


@router.get("/{trace_id}")
async def get_trace(trace_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific trace by ID."""
    trace = db.query(RAGTrace).filter(RAGTrace.id == trace_id).first()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
