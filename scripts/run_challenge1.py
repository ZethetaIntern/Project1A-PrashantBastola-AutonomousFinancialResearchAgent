
"""Run Challenge 1 and save the raw research result."""

import json
import logging
from pathlib import Path

from agent.core import create_agent

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"

QUERY = (
    "Create a comprehensive profile of Microsoft Corporation covering "
    "its business overview, financial summary, key executives, and recent "
    "developments. Use company_profile, financial_api, and web_search "
    "where appropriate. Distinguish sourced facts from unavailable "
    "information. Do not invent figures or citations."
)

ALLOWED_TOOLS = {
    "company_profile",
    "financial_api",
    "web_search",
}


def main() -> None:
    """Execute Challenge 1 and persist its result."""
    logging.basicConfig(level=logging.INFO)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    agent = create_agent(
        max_iterations=4,
        max_tokens=1000,
        allowed_tools=ALLOWED_TOOLS,
    )

    try:
        result = agent.run(QUERY)
    except Exception as exc:
        logging.exception("Challenge 1 failed")
        result = {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    output_path = RESULTS_DIR / "challenge_1_raw.json"
    output_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    print(f"\nResult saved to: {output_path}")
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Iterations: {result.get('iterations', 'unknown')}")
    print(f"Error: {result.get('error', 'none')}")

    tool_calls = result.get("tool_calls", [])
    print("Tools used:", [call.get("tool") for call in tool_calls])

    answer = result.get("answer", "")
    if answer:
        print("\nAnswer preview:\n")
        print(answer[:2500])


if __name__ == "__main__":
    main()
