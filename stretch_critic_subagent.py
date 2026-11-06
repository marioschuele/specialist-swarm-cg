"""
Stretch: add a Critic sub-agent to the coordinator's roster (S2).

The critic's job is to review the coordinator's draft before it goes out.
It must produce one of three verdicts:
- "ship it" (with a brief why)
- "revise" (with specific revisions)
- "stop" (with reason — e.g., we shouldn't pursue this deal)

This script is IDEMPOTENT: safe to run multiple times.
- It reuses the existing critic (recorded in .specialist_ids.json) instead
  of creating a duplicate on re-run.
- It only appends the critic to the coordinator roster when it's missing.
- It only appends the "# Critic" guidance to the system prompt when missing.
So re-running never duplicates the roster entry or the prompt block.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python stretch_critic_subagent.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic


CRITIC_SYSTEM = """\
You are the Deal Desk Critic. You don't write proposals. You review them.

When the coordinator asks for your review, you'll receive:
- The draft proposal
- The RFP (for context)

Your job: deliver one of three verdicts.

1. **SHIP IT** — the proposal is solid, with at most cosmetic suggestions.
2. **REVISE** — specific issues that need fixing. List them tersely. No more
   than 5 issues; if there are more, the proposal isn't ready.
3. **STOP** — we shouldn't pursue this deal. Reasons might include: terms
   we can't deliver, mismatched scale, regulatory issues, strategic conflict.

# Consistency checks (run every time, before the verdict)

Check the draft against itself and flag anything that doesn't hold up:

- **Numbers add up.** Every quoted price must reconcile with the stated
  tier and discount (list price minus discount). If a figure doesn't
  reconcile, flag it and name the section it appears in.
- **Positions agree across sections.** The commercial section and the
  contract section must not give two different positions on the same term —
  the liability-cap figure, for example, must be the same wherever it
  appears. Flag any contradiction between the specialists' outputs.
- **Claims are sourced.** Any customer reference, benchmark, or past-deal
  citation must be one we can actually point to. If a reference looks
  invented (no supporting data behind it), flag it as an
  "unsubstantiated reference."

Be sceptical. Your value to the coordinator is that you push back. A senior
partner who never gets pushback gets sloppy.

Lead your reply with: VERDICT: SHIP IT / REVISE / STOP.
"""

CRITIC_MARKER = "# Critic"

CRITIC_PROMPT_BLOCK = """

# Critic

Before producing the final document, send your draft to the Deal Desk
Critic. The Critic will reply with one of: SHIP IT, REVISE, or STOP.
- If SHIP IT: produce the final docx.
- If REVISE: address the issues and re-submit to the Critic. Repeat at most
  twice.
- If STOP: report to the user with the Critic's reasoning. Do NOT produce
  the final docx.
"""


def apply_critic(client, coordinator_id, specialist_ids):
    """Idempotently add the critic to the coordinator. Returns (critic_id, changed)."""
    # 1. Reuse or create the critic.
    critic_id = specialist_ids.get("critic")
    if critic_id:
        print(f"Reusing existing critic: {critic_id}")
    else:
        critic = client.beta.agents.create(
            name="Deal Desk Critic",
            model="claude-opus-4-7",  # The critic needs to be sharp
            system=CRITIC_SYSTEM,
            tools=[{"type": "agent_toolset_20260401"}],
            metadata={
                "hackathon": "partner-basecamp-2026",
                "track": "specialist-swarm",
                "role": "critic",
            },
        )
        critic_id = critic.id
        specialist_ids["critic"] = critic_id
        print(f"Critic created: {critic_id}")

    coordinator = client.beta.agents.retrieve(coordinator_id)
    roster = list(coordinator.multiagent.agents or [])
    prompt = coordinator.system
    current_ids = {a["id"] for a in roster}
    changed = False

    # 2. Add to roster only if missing.
    if critic_id not in current_ids:
        roster.append({"type": "agent", "id": critic_id})
        changed = True
        print("Critic added to coordinator roster.")
    else:
        print("Critic already in roster (skipped).")

    # 3. Append guidance only if missing.
    if CRITIC_MARKER not in prompt:
        prompt = prompt + CRITIC_PROMPT_BLOCK
        changed = True
        print("Critic guidance appended to coordinator prompt.")
    else:
        print("Critic guidance already present (skipped).")

    # 4. Persist only when something actually changed.
    if changed:
        client.beta.agents.update(
            coordinator_id,
            version=coordinator.version,
            system=prompt,
            multiagent={"type": "coordinator", "agents": roster},
        )
        print("Coordinator updated.")
    else:
        print("No changes needed — coordinator already has the critic (no-op).")

    return critic_id, changed


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    coordinator_id = Path(".coordinator_id").read_text().strip()
    specialist_ids = json.loads(Path(".specialist_ids.json").read_text())

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    critic_id, _changed = apply_critic(client, coordinator_id, specialist_ids)
    Path(".specialist_ids.json").write_text(json.dumps(specialist_ids, indent=2))

    print(f"Coordinator roster now includes the critic ({critic_id}).")
    print("Re-run run_deal_desk.py to see the critic in action.")


if __name__ == "__main__":
    main()
