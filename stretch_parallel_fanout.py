"""
Stretch S4: force the coordinator to delegate to ALL specialists in a
SINGLE message (explicit parallel fan-out) — the visible-parallelism story.

Idempotent and anti-clobber:
- Reads the CURRENT coordinator state before updating.
- Appends the "# Parallel delegation" instruction only if it's missing.
- Re-sends the roster unchanged, so the Critic (S2) and any specialist
  skills (S1) attached to the coordinator are preserved.
- Touches only `system` + `multiagent`. It never writes `skills`, so it
  won't clobber S1 (firm-voice skill). Run order vs. S1/S2 doesn't matter.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python stretch_parallel_fanout.py
"""

import os
from pathlib import Path

from anthropic import Anthropic


PARALLEL_MARKER = "# Parallel delegation"

PARALLEL_BLOCK = """

# Parallel delegation

When you delegate, send ALL specialist briefs in a SINGLE message — do not
wait between them. Spawn the specialist threads in parallel so the fan-out
is visible on the events stream (all of them spawning within seconds of
each other, then their replies flowing back together).
"""


def apply_parallel_fanout(client, coordinator_id):
    """Idempotently append the single-message fan-out instruction. Returns changed."""
    coordinator = client.beta.agents.retrieve(coordinator_id)
    prompt = coordinator.system
    roster = list(coordinator.multiagent.agents or [])

    if PARALLEL_MARKER in prompt:
        print("Parallel fan-out instruction already present (no-op).")
        return False

    prompt = prompt + PARALLEL_BLOCK
    print("Parallel fan-out instruction appended to coordinator prompt.")

    # Re-send the roster unchanged (normalised to dict form) — the critic and
    # any skills stay intact.
    agents = [
        (a if isinstance(a, dict) else {"type": "agent", "id": getattr(a, "id", None)})
        for a in roster
    ]
    client.beta.agents.update(
        coordinator_id,
        version=coordinator.version,
        system=prompt,
        multiagent={"type": "coordinator", "agents": agents},
    )
    print("Coordinator updated.")
    return True


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    coordinator_id = Path(".coordinator_id").read_text().strip()

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    apply_parallel_fanout(client, coordinator_id)
    print(
        "Re-run run_deal_desk.py — all four specialists should spawn within "
        "seconds of each other on the events stream."
    )


if __name__ == "__main__":
    main()
