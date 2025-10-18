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
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.redis_client import get_redis
from app.models import RAGTrace, Evaluation

# RAGAS imports
try:
    from ragas.metrics import faithfulness
    from ragas import evaluate
    from datasets import Dataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    print("⚠️  RAGAS not available. Faithfulness scoring will be skipped.")


async def process_evaluation_queue():
    """
    Main worker loop that processes evaluation jobs from Redis queue.

    Runs indefinitely, blocking on Redis queue for new jobs.
    """
    print("=" * 70)
    print("🚀 Aether Evaluation Worker Starting")
    print("=" * 70)
    print(f"Started at: {datetime.utcnow().isoformat()}")
    print(f"RAGAS Available: {'✅ Yes' if RAGAS_AVAILABLE else '❌ No'}")
    if RAGAS_AVAILABLE:
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key and openai_key != "your-openai-key":
            print(f"OpenAI API Key: ✅ Configured")
        else:
            print(f"OpenAI API Key: ⚠️  Not configured (faithfulness will be skipped)")
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

                if results.get('faithfulness') is not None:
                    print(f"      Faithfulness: {results.get('faithfulness'):.2f}")
                    if results.get('hallucination_detected'):
                        print(f"      ⚠️  HALLUCINATION DETECTED (score < 0.5)")
                    print(f"      Evaluation Cost: ${results.get('evaluation_cost_usd', 0):.4f}")

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
    - Faithfulness score (RAGAS, uses OpenAI)

    TODO (Next phase):
    - Answer relevancy, context precision/recall
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

    # 3. RAGAS Faithfulness Score (LLM-based, detects hallucinations)
    if trace.contexts and len(trace.contexts) > 0:
        try:
            faithfulness_result = await compute_faithfulness(
                query=trace.query,
                answer=trace.response,
                contexts=[ctx.get("text", "") for ctx in trace.contexts]
            )
            results["faithfulness"] = faithfulness_result["score"]
            results["evaluation_cost_usd"] = faithfulness_result["cost"]

            # Mark as hallucination if faithfulness < 0.5
            results["hallucination_detected"] = faithfulness_result["score"] < 0.5 if faithfulness_result["score"] is not None else False
        except Exception as e:
            print(f"   ⚠️  RAGAS faithfulness failed: {e}")
            results["faithfulness"] = None
            results["evaluation_cost_usd"] = 0.0
            results["hallucination_detected"] = False
    else:
        # No contexts, can't compute faithfulness
        results["faithfulness"] = None
        results["evaluation_cost_usd"] = 0.0
        results["hallucination_detected"] = False

    return results


async def compute_faithfulness(query: str, answer: str, contexts: List[str]) -> Dict[str, Any]:
    """
    Compute faithfulness score using RAGAS.

    Faithfulness measures whether the answer is grounded in the provided contexts.
    Score ranges from 0.0 (completely unfaithful/hallucinated) to 1.0 (perfectly faithful).

    Args:
        query: The user's question
        answer: The generated response
        contexts: List of retrieved context texts

    Returns:
        Dictionary with 'score' and 'cost' keys
    """
    if not RAGAS_AVAILABLE:
        return {"score": None, "cost": 0.0}

    if not contexts or not answer:
        return {"score": None, "cost": 0.0}

    try:
        # Prepare data in RAGAS format
        data = {
            "question": [query],
            "answer": [answer],
            "contexts": [contexts],  # RAGAS expects list of lists
        }

        # Create dataset
        dataset = Dataset.from_dict(data)

        # Run evaluation (this calls OpenAI API)
        # Note: RAGAS uses OpenAI by default, configured via OPENAI_API_KEY env var
        result = evaluate(dataset, metrics=[faithfulness])

        # Extract faithfulness score
        # RAGAS returns a dict with metric names as keys
        # The value might be a single score or a list (if evaluating multiple items)
        faithfulness_value = result["faithfulness"]
        if isinstance(faithfulness_value, list):
            faithfulness_score = float(faithfulness_value[0]) if faithfulness_value else None
        else:
            faithfulness_score = float(faithfulness_value)

        # Estimate cost (OpenAI gpt-3.5-turbo pricing)
        # Faithfulness typically uses ~500-1000 tokens per evaluation
        # At $0.001/1K tokens for gpt-3.5-turbo
        estimated_tokens = len(query.split()) + len(answer.split()) + sum(len(ctx.split()) for ctx in contexts)
        estimated_cost = Decimal(estimated_tokens / 1000 * 0.001)

        return {
            "score": faithfulness_score,
            "cost": float(estimated_cost)
        }

    except Exception as e:
        print(f"      RAGAS faithfulness error: {str(e)}")
        return {"score": None, "cost": 0.0}


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
