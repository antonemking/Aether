#!/usr/bin/env python3
"""Test trace ingestion endpoint"""
import httpx
import asyncio
from datetime import datetime


async def test_ingestion():
    """Test the trace ingestion and retrieval flow."""

    # Test project ID from seed_data.py
    project_id = "2afd5cf5-0a7e-4859-b6ba-4c238f15539c"

    test_data = {
        "project_id": project_id,
        "query": "What is retrieval augmented generation?",
        "response": "RAG (Retrieval-Augmented Generation) is a technique that combines retrieval of relevant documents with LLM generation. It helps ground responses in factual information and reduces hallucinations by providing context from a knowledge base.",
        "contexts": [
            {
                "text": "Retrieval-Augmented Generation (RAG) improves LLM responses by first retrieving relevant documents from a knowledge base, then using those documents as context for generation.",
                "source": "doc_123",
                "score": 0.92
            },
            {
                "text": "RAG systems retrieve relevant documents before generating responses, which helps reduce hallucinations and provides more factual, grounded answers.",
                "source": "doc_456",
                "score": 0.85
            },
            {
                "text": "The retrieval step in RAG uses semantic search to find the most relevant passages from a document corpus based on the user's query.",
                "source": "doc_789",
                "score": 0.78
            }
        ],
        "metadata": {
            "model": "gpt-4",
            "user_id": "test_user_001",
            "session_id": "session_abc123"
        },
        "token_count": 1250,
        "latency_ms": 1850,
        "cost_usd": 0.025,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    async with httpx.AsyncClient() as client:
        print("=" * 70)
        print("🚀 Testing Trace Ingestion")
        print("=" * 70)
        print(f"Project ID: {project_id}")
        print(f"Query: {test_data['query']}")
        print(f"Contexts: {len(test_data['contexts'])} documents")
        print()

        # Test trace ingestion
        print("📤 Sending trace to API...")
        try:
            response = await client.post(
                "http://127.0.0.1:8000/api/v1/traces/",
                json=test_data,
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 202:
                result = response.json()
                trace_id = result["trace_id"]
                status = result["status"]

                print()
                print("=" * 70)
                print("✅ Trace Ingestion Successful")
                print("=" * 70)
                print(f"Trace ID: {trace_id}")
                print(f"Status: {status}")
                print()

                # Wait a moment for DB write
                await asyncio.sleep(0.5)

                # Test trace retrieval
                print("=" * 70)
                print("📥 Retrieving Trace")
                print("=" * 70)
                get_response = await client.get(
                    f"http://127.0.0.1:8000/api/v1/traces/{trace_id}",
                    timeout=5.0
                )

                if get_response.status_code == 200:
                    trace = get_response.json()
                    print(f"✅ Successfully retrieved trace")
                    print()
                    print(f"Query: {trace['query']}")
                    print(f"Response length: {len(trace['response'])} chars")
                    print(f"Contexts: {len(trace['contexts'])} documents")
                    print(f"Token count: {trace['token_count']}")
                    print(f"Latency: {trace['latency_ms']}ms")
                    print(f"Cost: ${trace['cost_usd']}")
                    print(f"Created: {trace['created_at']}")
                    print()

                    print("=" * 70)
                    print("🎯 Next Steps")
                    print("=" * 70)
                    print("1. Check database:")
                    print(f"   psql aether -c \"SELECT id, query FROM rag_traces WHERE id='{trace_id}';\"")
                    print()
                    print("2. Check Redis queue:")
                    print("   redis-cli")
                    print("   > LLEN evaluation_queue")
                    print("   > LRANGE evaluation_queue 0 -1")
                    print()
                else:
                    print(f"❌ Failed to retrieve trace: {get_response.status_code}")
                    print(f"Response: {get_response.text}")

            else:
                print()
                print(f"❌ Trace ingestion failed: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"❌ Error during test: {e}")
            raise


if __name__ == "__main__":
    print()
    asyncio.run(test_ingestion())
    print()
