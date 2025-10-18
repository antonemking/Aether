#!/usr/bin/env python3
"""
Evaluation Worker - Processes traces from Redis queue and computes metrics.

This worker:
1. Polls the evaluation_queue in Redis
2. Fetches trace data from the database
3. Computes evaluation metrics
4. Saves results to the evaluations table
"""
import json
import asyncio
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from app.core.database import SessionLocal
from app.core.redis_client import get_redis
from app.models import RAGTrace, Evaluation


async def process_evaluation_queue():
    """
    Main worker loop that processes evaluation jobs from Redis queue.

    Runs indefinitely, blocking on Redis queue for new jobs.
    """
    print("=" * 70)
    print("🚀 Aether Evaluation Worker Starting")
    print("=" * 70)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print("Waiting for evaluation jobs...")
    print()

    redis_conn = await get_redis()

    processed_count = 0
    error_count = 0

    while True:
        db = SessionLocal()

        try:
            # Block on Redis queue for up to 5 seconds
            job_data = await redis_conn.brpop("evaluation_queue", timeout=5)

            if job_data:
                _, job_json = job_data
                job = json.loads(job_json)

                trace_id = job["trace_id"]
                job_id = job["job_id"]

                print(f"📥 Processing evaluation job: {job_id}")
                print(f"   Trace ID: {trace_id}")

                # Load trace from database
                trace = db.query(RAGTrace).filter(
                    RAGTrace.id == UUID(trace_id)
                ).first()

                if not trace:
                    print(f"   ❌ Trace not found: {trace_id}")
                    error_count += 1
                    continue

                # Check if evaluation already exists
                existing_eval = db.query(Evaluation).filter(
                    Evaluation.trace_id == trace.id
                ).first()

                if existing_eval:
                    print(f"   ⚠️  Evaluation already exists, skipping")
                    continue

                print(f"   🔄 Running evaluations...")

                # Compute evaluation metrics
                results = await run_evaluations(trace)

                # Create evaluation record
                evaluation = Evaluation(
                    trace_id=trace.id,
                    context_precision=results.get("context_precision"),
                    context_recall=results.get("context_recall"),
                    answer_relevancy=results.get("answer_relevancy"),
                    faithfulness=results.get("faithfulness"),
                    hallucination_detected=results.get("hallucination_detected", False),
                    toxicity_score=results.get("toxicity_score"),
                    pii_detected=results.get("pii_detected", False),
                    token_overlap_ratio=results.get("token_overlap_ratio"),
                    answer_length=results.get("answer_length"),
                    evaluation_cost_usd=results.get("evaluation_cost_usd"),
                    evaluated_at=datetime.utcnow()
                )

                db.add(evaluation)
                db.commit()
                db.refresh(evaluation)

                processed_count += 1

                print(f"   ✅ Evaluation complete!")
                print(f"      Token Overlap: {results.get('token_overlap_ratio', 0):.2%}")
                print(f"      Answer Length: {results.get('answer_length')} words")
                print(f"   📊 Total processed: {processed_count} | Errors: {error_count}")
                print()

        except KeyboardInterrupt:
            print("\n🛑 Shutting down worker...")
            break

        except Exception as e:
            error_count += 1
            print(f"   ❌ Error processing evaluation: {e}")
            print(f"   📊 Total processed: {processed_count} | Errors: {error_count}")
            print()
            db.rollback()
            await asyncio.sleep(1)

        finally:
            db.close()

    print()
    print("=" * 70)
    print("👋 Evaluation Worker Stopped")
    print("=" * 70)
    print(f"Total processed: {processed_count}")
    print(f"Total errors: {error_count}")
    print()


async def run_evaluations(trace: RAGTrace) -> Dict[str, Any]:
    """
    Run all evaluation metrics on a trace.

    Currently implements:
    - Token overlap ratio (fast, no LLM needed)
    - Answer length (fast)

    TODO (Day 4-5):
    - RAGAS metrics (faithfulness, answer_relevancy, context_precision/recall)
    - Hallucination detection
    - PII detection
    - Toxicity scoring

    Args:
        trace: RAGTrace model instance

    Returns:
        Dictionary of metric scores
    """
    results = {}

    # Fast metrics (no LLM calls needed)

    # 1. Token overlap ratio - measures how much of the answer comes from contexts
    if trace.contexts:
        context_texts = [ctx.get("text", "") for ctx in trace.contexts]
        results["token_overlap_ratio"] = calculate_token_overlap(
            trace.response,
            context_texts
        )
    else:
        results["token_overlap_ratio"] = 0.0

    # 2. Answer length - simple word count
    results["answer_length"] = len(trace.response.split())

    # 3. No evaluation cost yet (will add when using LLM-based metrics)
    results["evaluation_cost_usd"] = 0.0

    # TODO: Add RAGAS metrics
    # from ragas.metrics import faithfulness, answer_relevancy
    # from ragas import evaluate
    # from datasets import Dataset
    #
    # data = {
    #     "question": [trace.query],
    #     "answer": [trace.response],
    #     "contexts": [[c["text"] for c in trace.contexts]],
    # }
    # dataset = Dataset.from_dict(data)
    # ragas_results = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
    # results["faithfulness"] = ragas_results["faithfulness"]
    # results["answer_relevancy"] = ragas_results["answer_relevancy"]

    return results


def calculate_token_overlap(response: str, contexts: List[str]) -> float:
    """
    Calculate what percentage of response tokens appear in contexts.

    This is a simple but useful metric for RAG systems:
    - High overlap (>0.7) = answer is well-grounded in retrieved docs
    - Low overlap (<0.3) = answer may be hallucinated or uses outside knowledge

    Args:
        response: The generated answer text
        contexts: List of retrieved context texts

    Returns:
        Float between 0.0 and 1.0 representing overlap ratio
    """
    if not response or not contexts:
        return 0.0

    # Tokenize (simple whitespace split, lowercase)
    response_tokens = set(response.lower().split())

    # Combine all contexts
    combined_context = " ".join(contexts)
    context_tokens = set(combined_context.lower().split())

    if not response_tokens:
        return 0.0

    # Count overlap
    overlap = len(response_tokens & context_tokens)

    return overlap / len(response_tokens)


if __name__ == "__main__":
    """Run the worker as a standalone process."""
    try:
        asyncio.run(process_evaluation_queue())
    except KeyboardInterrupt:
        print("\n👋 Worker stopped by user")
        sys.exit(0)
