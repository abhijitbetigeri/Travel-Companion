"""Environment config. Everything reads from .env — nothing is hardcoded."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        raise RuntimeError(f"{name} is not set — copy .env.example to .env and fill it in")
    return val


COGNEE_BASE_URL = _require("COGNEE_BASE_URL").rstrip("/")
COGNEE_API_KEY = _require("COGNEE_API_KEY")

BRIGHTDATA_API_TOKEN = os.getenv("BRIGHTDATA_API_TOKEN", "").strip()
BRIGHTDATA_MCP_URL = f"https://mcp.brightdata.com/mcp?token={BRIGHTDATA_API_TOKEN}"

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)

# Strands is model-agnostic. Bedrock is the target (it's what the AWS credit
# pays for), but an unconfigured AWS account shouldn't block building the rest
# of the agent — set MODEL_PROVIDER=anthropic to keep moving, then switch back.
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "bedrock").lower()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL_ID = os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-5-20250929")

# The two memory lifecycles. See ARCHITECTURE.md.
DATASET_SELF = os.getenv("COGNEE_DATASET_SELF", "self")
DATASET_WORLD = os.getenv("COGNEE_DATASET_WORLD", "world")

WORLD_FRESHNESS_HOURS = int(os.getenv("WORLD_FRESHNESS_HOURS", "24"))

DATA_DIR = ROOT / "data"
