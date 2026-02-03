from __future__ import annotations

"""Simple smoke-test script for local API checks.

Usage examples:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --skip-chat
    python scripts/smoke_test.py --base-url http://127.0.0.1:9000
"""

import argparse
import json

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Quick smoke test for the FastAPI service.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument(
        "--prompt",
        default="What's the weather forecast for Tokyo?",
        help="Prompt for /chat endpoint",
    )
    parser.add_argument(
        "--skip-chat",
        action="store_true",
        help="Run only /health check",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    print(f"[INFO] Smoke test started for {base}")

    # Step 1: health endpoint must be alive.
    try:
        health = requests.get(f"{base}/health", timeout=10)
        health.raise_for_status()
    except requests.RequestException as exc:
        print(f"[FAIL] GET /health: {exc}")
        return 1

    print("[OK] GET /health")
    print(json.dumps(health.json(), ensure_ascii=False, indent=2))

    if args.skip_chat:
        print("[INFO] Chat step skipped by --skip-chat")
        return 0

    # Step 2: chat endpoint should return agent response.
    try:
        chat = requests.post(
            f"{base}/chat",
            json={"prompt": args.prompt},
            timeout=120,
        )
        chat.raise_for_status()
    except requests.RequestException as exc:
        print(f"[FAIL] POST /chat: {exc}")
        return 1

    print("[OK] POST /chat")
    print(json.dumps(chat.json(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
