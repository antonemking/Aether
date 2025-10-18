from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.redis_client import get_redis
import redis.asyncio as redis

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db), redis_conn: redis.Redis = Depends(get_redis)):
    """Health check endpoint - verifies database and Redis connections."""
    try:
        # Check database
        db.execute(text("SELECT 1"))

        # Check Redis
        await redis_conn.ping()

        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
