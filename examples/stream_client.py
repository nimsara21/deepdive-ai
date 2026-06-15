#!/usr/bin/env python
"""
Example client for the streaming research endpoint.
Demonstrates how to consume newline-delimited JSON responses.
"""
import json
import sys
import httpx


async def stream_research(query: str, base_url: str = "http://localhost:8000"):
    """Stream research results and print them in real-time."""
    print(f"🔍 Researching: {query}\n")

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{base_url}/research/stream",
            json={"query": query},
        ) as response:
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}")
                return

            full_answer = ""
            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                event = json.loads(line)
                event_type = event.get("event")

                if event_type == "planning":
                    print("⏳ Planning query decomposition...")

                elif event_type == "searching":
                    sub_q = event.get("sub_questions", [])
                    num_results = event.get("num_results", 0)
                    print(f"✅ Generated {len(sub_q)} sub-questions")
                    print(f"✅ Found {num_results} search results\n")

                elif event_type == "summarizing":
                    print("📝 Synthesizing answer...\n")

                elif event_type == "token":
                    # Stream tokens as they arrive
                    token = event.get("data", "")
                    full_answer += token
                    sys.stdout.write(token)
                    sys.stdout.flush()

                elif event_type == "complete":
                    sources = event.get("sources", [])
                    print("\n\n" + "=" * 60)
                    print("📚 Sources:")
                    for i, src in enumerate(sources, 1):
                        print(f"  [{i}] {src}")

                elif event_type == "cached":
                    print("⚡ Cached result\n")
                    print(event.get("final_answer", ""))
                    print("\n" + "=" * 60)
                    print("📚 Sources:")
                    for i, src in enumerate(event.get("sources", []), 1):
                        print(f"  [{i}] {src}")

                elif event_type == "error":
                    print(f"❌ Error: {event.get('message')}")


if __name__ == "__main__":
    import asyncio

    query = sys.argv[1] if len(sys.argv) > 1 else "What is machine learning?"
    asyncio.run(stream_research(query))
