"""The Strands agent: Bright Data tools + Cognee memory + a Bedrock model.

    python -m travel_companion.agent "I have a free day in SF. Plan it."

Everything happens inside the Bright Data MCP context manager. Tools pulled
from an MCPClient stop working the moment that block exits, so the agent is
constructed and run inside it.
"""

from __future__ import annotations

import sys

from strands import Agent
from strands.models import BedrockModel

from . import brightdata
from .config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL_ID,
    AWS_REGION,
    BEDROCK_MODEL_ID,
    MODEL_PROVIDER,
    WORLD_FRESHNESS_HOURS,
)
from .tools import MEMORY_TOOLS

SYSTEM_PROMPT = f"""\
You are a travel companion with a persistent memory of one specific traveler.

HOW TO THINK

1. Start with `recall_self`. Never plan from assumptions about this traveler —
   look up what they actually decided, and when.

2. People change their minds. Their memory contains decisions that were later
   reversed. Time-aware recall surfaces the current version; trust the recent
   decision over the older one it contradicts, and say so out loud when you
   notice a reversal ("you used to prefer X, but as of <date> Y").

3. Then check the world with `recall_world`. Stored world facts go stale in
   {WORLD_FRESHNESS_HOURS} hours. If what you get back is older than that — or
   if the plan depends on it being true right now — re-verify it live with the
   Bright Data search/scrape tools before you rely on it.

4. When the live web contradicts a stored fact, say so explicitly, fix the
   plan, and write the correction back with `remember`. This is the job, not a
   side quest: the brain should be more correct after this conversation.

5. Finish with a concrete plan, not a menu of options. Times, places, how they
   get between them. If a constraint rules something out, name the constraint.

Be specific and brief. No preamble.
"""


def model():
    """Bedrock by default — that's what the AWS credit pays for."""
    if MODEL_PROVIDER == "anthropic":
        from strands.models.anthropic import AnthropicModel

        # AnthropicModel requires max_tokens explicitly; Bedrock defaults it.
        return AnthropicModel(
            client_args={"api_key": ANTHROPIC_API_KEY},
            model_id=ANTHROPIC_MODEL_ID,
            max_tokens=4096,
        )
    return BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=AWS_REGION)


def build(bright) -> Agent:
    tools = bright.list_tools_sync() + MEMORY_TOOLS
    return Agent(model=model(), system_prompt=SYSTEM_PROMPT, tools=tools)


def ask(question: str) -> str:
    with brightdata.client() as bright:
        agent = build(bright)
        return str(agent(question))


def main() -> None:
    question = " ".join(sys.argv[1:]) or (
        "I have a free day in San Francisco before the hackathon. Plan it for me."
    )
    print(ask(question))


if __name__ == "__main__":
    main()
