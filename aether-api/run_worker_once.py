#!/usr/bin/env python3
"""Run the evaluation worker once to process queued jobs"""
import asyncio
import sys

# Add the parent directory to the path
sys.path.insert(0, '/Users/antone.king/dev/Aether/aether-api')

from app.workers.evaluator import process_evaluation_queue

if __name__ == "__main__":
    print("Starting worker...")
    try:
        asyncio.run(process_evaluation_queue())
    except KeyboardInterrupt:
        print("\nStopped by user")
