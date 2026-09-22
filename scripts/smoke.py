"""Three credential checks. Run this first — each can fail in a boring way.

    python scripts/smoke.py          # all three
    python scripts/smoke.py bedrock  # just one

Bedrock is the one that bites: model access is per-region opt-in and an
un-enabled model returns AccessDenied, not "not found".
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from travel_companion import cognee_client as cog  # noqa: E402
from travel_companion.config import (  # noqa: E402
    AWS_REGION,
    BEDROCK_MODEL_ID,
    BRIGHTDATA_API_TOKEN,
    COGNEE_BASE_URL,
)


def check_cognee() -> None:
    print(f"  tenant: {COGNEE_BASE_URL}")
    datasets = cog.list_datasets()
    print(f"  datasets: {[d['name'] for d in datasets] or '(none)'}")
    print(f"  quota: {cog.quota()}")


def check_model() -> None:
    """Whichever provider MODEL_PROVIDER selects — this is what the agent runs on."""
    from strands import Agent

    from travel_companion.agent import model
    from travel_companion.config import MODEL_PROVIDER

    agent = Agent(model=model(), system_prompt="Reply with one word.")
    said = str(agent("Say: ready")).strip()
    print(f"  provider: {MODEL_PROVIDER}")
    print(f"  said:     {said[:60]!r}")


def check_bedrock() -> None:
    import boto3

    if not BEDROCK_MODEL_ID:
        raise RuntimeError("BEDROCK_MODEL_ID is empty")
    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    resp = client.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": "Reply with the word: ready"}]}],
        inferenceConfig={"maxTokens": 16},
    )
    text = resp["output"]["message"]["content"][0]["text"].strip()
    print(f"  region: {AWS_REGION}")
    print(f"  model:  {BEDROCK_MODEL_ID}")
    print(f"  said:   {text!r}")


def check_brightdata() -> None:
    from travel_companion import brightdata

    if not BRIGHTDATA_API_TOKEN:
        raise RuntimeError("BRIGHTDATA_API_TOKEN is empty")
    with brightdata.client() as bright:
        names = [t.tool_name for t in bright.list_tools_sync()]
    print(f"  {len(names)} tools: {', '.join(names[:8])}{' ...' if len(names) > 8 else ''}")


CHECKS = {
    "cognee": check_cognee,
    "model": check_model,
    "brightdata": check_brightdata,
    "bedrock": check_bedrock,  # not in the default run while Bedrock is blocked
}

DEFAULT = ["cognee", "model", "brightdata"]


def main() -> None:
    wanted = sys.argv[1:] or DEFAULT
    failed = []
    for name in wanted:
        print(f"\n=== {name} ===")
        try:
            CHECKS[name]()
            print("  OK")
        except Exception as exc:  # noqa: BLE001 - smoke test, report everything
            failed.append(name)
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc(limit=2)

    print()
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)
    print(f"all {len(wanted)} checks passed")


if __name__ == "__main__":
    main()
