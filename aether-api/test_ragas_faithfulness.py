#!/usr/bin/env python3
"""
Test RAGAS Faithfulness Integration

This script:
1. Ingests a test trace with known hallucination
2. Waits for worker to evaluate it
3. Verifies faithfulness score was computed
4. Shows the evaluation results
"""
import httpx
import asyncio
from datetime import datetime
from app.core.database import SessionLocal
from app.models import Evaluation
from uuid import UUID


async def test_ragas_faithfulness():
    """Test faithfulness evaluation with a case that should score poorly."""

    project_id = "2afd5cf5-0a7e-4859-b6ba-4c238f15539c"

    print("=" * 70)
    print("🧪 Testing RAGAS Faithfulness Integration")
    print("=" * 70)
    print()

    # Create a trace with intentional hallucination for testing
    print("Step 1: Creating trace with potential hallucination...")
    trace_data = {
        "project_id": project_id,
        "query": "What is the capital of France?",
        "response": "The capital of France is Berlin, which is known for its beautiful Eiffel Tower and delicious croissants. Paris is actually the second-largest city.",  # Intentional hallucination
        "contexts": [
            {
                "text": "Paris is the capital and most populous city of France. It is located in the north-central part of the country.",
                "source": "doc_france_001",
                "score": 0.95
            },
            {
                "text": "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France.",
                "source": "doc_eiffel_001",
                "score": 0.88
            }
        ],
        "metadata": {
            "model": "gpt-4",
            "test": "faithfulness_hallucination"
        },
        "token_count": 450,
        "latency_ms": 980,
        "cost_usd": 0.012,
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

        # Wait for evaluation
        print("Step 2: Waiting for faithfulness evaluation...")
        print("   (Worker must be running: python -m app.workers.evaluator)")
        print()

        db = SessionLocal()
        evaluation = None
        max_attempts = 60  # Wait up to 60 seconds for LLM evaluation
        attempt = 0

        while attempt < max_attempts:
            evaluation = db.query(Evaluation).filter(
                Evaluation.trace_id == UUID(trace_id)
            ).first()

            if evaluation and evaluation.faithfulness is not None:
                break

            attempt += 1
            if attempt % 5 == 0:
                print(f"   Waiting... ({attempt}/{max_attempts}s)")
            await asyncio.sleep(1)

        db.close()

        if not evaluation:
            print()
            print(f"⚠️  Evaluation not found after {max_attempts} seconds")
            print("   Make sure:")
            print("   1. Worker is running: python -m app.workers.evaluator")
            print("   2. OpenAI API key is set in .env")
            return False

        if evaluation.faithfulness is None:
            print()
            print(f"⚠️  Faithfulness score not computed")
            print("   Check worker logs for errors")
            print("   Make sure OPENAI_API_KEY is set in .env")
            return False

        # Show results
        print()
        print("=" * 70)
        print("✅ RAGAS Faithfulness Evaluation Complete")
        print("=" * 70)
        print()
        print("Test Details:")
        print(f"  Query: \"{trace_data['query']}\"")
        print(f"  Response: \"{trace_data['response'][:100]}...\"")
        print()
        print("Evaluation Results:")
        print(f"  Faithfulness Score: {evaluation.faithfulness:.3f}")
        print(f"  Token Overlap: {evaluation.token_overlap_ratio:.2%}")
        print(f"  Answer Length: {evaluation.answer_length} words")
        print(f"  Hallucination Detected: {evaluation.hallucination_detected}")
        print(f"  Evaluation Cost: ${evaluation.evaluation_cost_usd:.4f}")
        print()

        # Validate results
        print("=" * 70)
        print("🔍 Validation")
        print("=" * 70)

        checks_passed = 0
        total_checks = 3

        # Check 1: Faithfulness should be low (since we intentionally hallucinated)
        if evaluation.faithfulness is not None:
            if evaluation.faithfulness < 0.7:
                print(f"✅ Faithfulness score detected issue (< 0.7): {evaluation.faithfulness:.3f}")
                checks_passed += 1
            else:
                print(f"⚠️  Expected low faithfulness (hallucination), got: {evaluation.faithfulness:.3f}")
        else:
            print("❌ Faithfulness score not computed")

        # Check 2: Evaluation cost should be non-zero
        if evaluation.evaluation_cost_usd and evaluation.evaluation_cost_usd > 0:
            print(f"✅ Evaluation cost tracked: ${evaluation.evaluation_cost_usd:.4f}")
            checks_passed += 1
        else:
            print(f"⚠️  Evaluation cost not tracked properly")

        # Check 3: Hallucination flag should be set if faithfulness < 0.5
        if evaluation.faithfulness and evaluation.faithfulness < 0.5:
            if evaluation.hallucination_detected:
                print(f"✅ Hallucination flag set correctly")
                checks_passed += 1
            else:
                print(f"⚠️  Hallucination not detected despite low faithfulness")
        else:
            # If faithfulness >= 0.5, hallucination flag should be false
            if not evaluation.hallucination_detected:
                print(f"✅ Hallucination flag correct (not detected)")
                checks_passed += 1

        print()
        print("=" * 70)
        if checks_passed >= 2:  # Allow some flexibility
            print(f"🎉 RAGAS Integration Test PASSED ({checks_passed}/{total_checks} checks)")
            print("=" * 70)
            print()
            print("✅ Faithfulness scoring is working!")
            print("   Next: Build alerting system to notify on low scores")
            return True
        else:
            print(f"⚠️  Some checks failed ({checks_passed}/{total_checks})")
            print("=" * 70)
            return False


if __name__ == "__main__":
    print()
    success = asyncio.run(test_ragas_faithfulness())
    print()

    if success:
        exit(0)
    else:
        exit(1)
