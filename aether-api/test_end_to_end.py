#!/usr/bin/env python3
"""
End-to-end test for Aether evaluation pipeline.

Tests the complete flow:
1. Ingest trace via API
2. Worker processes evaluation queue
3. Evaluation results saved to database
"""
import httpx
import asyncio
import time
from datetime import datetime
from app.core.database import SessionLocal
from app.models import Evaluation
from uuid import UUID


async def test_end_to_end():
    """Test complete trace ingestion and evaluation flow."""

    project_id = "2afd5cf5-0a7e-4859-b6ba-4c238f15539c"

    print("=" * 70)
    print("🧪 Aether End-to-End Test")
    print("=" * 70)
    print()

    # Step 1: Ingest a new trace
    print("Step 1: Ingesting trace...")
    trace_data = {
        "project_id": project_id,
        "query": "How does vector search work in RAG systems?",
        "response": "Vector search in RAG systems uses embeddings to find semantically similar documents. The query is converted to a vector embedding, then compared against stored document embeddings using similarity metrics like cosine similarity.",
        "contexts": [
            {
                "text": "Vector search uses embeddings to represent text as numerical vectors in high-dimensional space.",
                "source": "doc_101",
                "score": 0.88
            },
            {
                "text": "RAG systems convert queries to embeddings and use cosine similarity to find relevant documents.",
                "source": "doc_102",
                "score": 0.82
            }
        ],
        "metadata": {
            "model": "gpt-4",
            "test": "end_to_end"
        },
        "token_count": 850,
        "latency_ms": 1200,
        "cost_usd": 0.015,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/traces/",
            json=trace_data,
            timeout=10.0
        )

        if response.status_code != 202:
            print(f"❌ Failed to ingest trace: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        result = response.json()
        trace_id = result["trace_id"]
        print(f"✅ Trace ingested: {trace_id}")
        print()

        # Step 2: Wait for worker to process (in real scenario, worker runs in background)
        print("Step 2: Waiting for evaluation worker to process...")
        print("   (Note: Make sure worker is running with: python -m app.workers.evaluator)")
        print()

        # Poll database for evaluation (timeout after 30 seconds)
        db = SessionLocal()
        evaluation = None
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            evaluation = db.query(Evaluation).filter(
                Evaluation.trace_id == UUID(trace_id)
            ).first()

            if evaluation:
                break

            attempt += 1
            print(f"   Waiting... ({attempt}/{max_attempts})")
            await asyncio.sleep(1)

        db.close()

        if not evaluation:
            print()
            print(f"⚠️  Evaluation not found after {max_attempts} seconds")
            print("   This is expected if the worker is not running.")
            print("   To complete the test, run the worker in another terminal:")
            print("   python -m app.workers.evaluator")
            return False

        # Step 3: Verify evaluation results
        print()
        print("=" * 70)
        print("✅ Evaluation Complete")
        print("=" * 70)
        print(f"Evaluation ID: {evaluation.id}")
        print(f"Trace ID: {evaluation.trace_id}")
        print()
        print("Metrics:")
        print(f"  Token Overlap Ratio: {evaluation.token_overlap_ratio:.2%}")
        print(f"  Answer Length: {evaluation.answer_length:.0f} words")
        print(f"  Hallucination Detected: {evaluation.hallucination_detected}")
        print(f"  PII Detected: {evaluation.pii_detected}")
        print(f"  Evaluation Cost: ${evaluation.evaluation_cost_usd:.4f}")
        print(f"  Evaluated At: {evaluation.evaluated_at}")
        print()

        # Step 4: Verify data integrity
        print("=" * 70)
        print("🔍 Data Integrity Check")
        print("=" * 70)

        checks_passed = 0
        total_checks = 4

        if evaluation.token_overlap_ratio is not None:
            print(f"✅ Token overlap calculated: {evaluation.token_overlap_ratio:.2%}")
            checks_passed += 1
        else:
            print("❌ Token overlap missing")

        if evaluation.answer_length is not None and evaluation.answer_length > 0:
            print(f"✅ Answer length calculated: {evaluation.answer_length} words")
            checks_passed += 1
        else:
            print("❌ Answer length invalid")

        if evaluation.hallucination_detected is not None:
            print(f"✅ Hallucination check complete: {evaluation.hallucination_detected}")
            checks_passed += 1
        else:
            print("❌ Hallucination check missing")

        if evaluation.evaluated_at is not None:
            print(f"✅ Timestamp recorded: {evaluation.evaluated_at}")
            checks_passed += 1
        else:
            print("❌ Timestamp missing")

        print()
        print("=" * 70)
        if checks_passed == total_checks:
            print(f"🎉 All checks passed! ({checks_passed}/{total_checks})")
            print("=" * 70)
            print()
            print("✅ End-to-end test SUCCESSFUL")
            return True
        else:
            print(f"⚠️  Some checks failed ({checks_passed}/{total_checks})")
            print("=" * 70)
            return False


if __name__ == "__main__":
    print()
    success = asyncio.run(test_end_to_end())
    print()

    if success:
        exit(0)
    else:
        exit(1)
