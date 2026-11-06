"""
Create the coordinator agent that orchestrates the specialist swarm.

The coordinator's roster is the four specialists created by create_specialists.py.
The coordinator decides which specialists to consult, in what order, and how to
synthesise their outputs into the final deliverable.

Saves the coordinator's ID to .coordinator_id.

Usage:
    python create_coordinator.py
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic


COORDINATOR_SYSTEM = """\
You are the Senior Partner running the Deal Desk. An inbound RFP has just
arrived. Your job is to orchestrate the specialists, synthesise their work,
and produce a single branded proposal response document.

# Your roster

You can call these specialists:
- Pricing Specialist: commercial terms recommendation
- Legal Reviewer: contract flags and counter-positions
- Technical Fit Specialist: product capability fit
- Competitive Intel Analyst: who else is in the deal and how to position

# How to run a deal

1. Read the RFP yourself first. Note the customer, scope, and any obvious
   curveballs.

2. Delegate to ALL FOUR specialists in parallel. Each gets:
   - The full RFP text
   - A clear, narrow brief stating what you need from them
   - A deadline ("answer in one message, ~300 words")

3. Synthesise their outputs into a single proposal response. The response
   should cover:
   - Executive summary (3 bullets)
   - Our understanding of the customer's need
   - Why we're the right fit (drawing on Technical Fit + Competitive Intel)
   - Commercial proposal (drawing on Pricing)
   - Contract approach (drawing on Legal)
   - Risks and how we mitigate them

4. Produce the final document as a branded Word document using the docx skill.
   Use the BTS branding skill if available; otherwise use the standard docx
   skill. The deliverable is the docx itself, not a chat message.

# How to talk to specialists

When delegating, be direct: "Pricing Specialist: for this RFP, recommend
terms. Include discount band and red-line concessions. Cite past-wins.json
where relevant."

When you receive a specialist's reply, accept it. Don't second-guess. If
you genuinely disagree, send the specialist a follow-up — but only if it
matters.

# Tone

Senior partner running a real deal. Confident, terse, decisive. You move
fast because the RFP deadline is real.
"""


VOICE_SKILL = "your-firm-voice"
VOICE_PROMPT_ADDENDUM = """
# House voice

Write the final proposal in the firm's house voice. Apply the
your-firm-voice skill to the synthesis and to the final document (not to the
specialists' internal analysis).
"""


def load_coordinator_skills() -> list[dict]:
    """Attach the firm-voice skill if it was uploaded.

    Set NO_VOICE=1 to create a baseline coordinator without it
    (used for the before/after comparison).
    """
    if os.environ.get("NO_VOICE") == "1":
        print("NO_VOICE=1 -> coordinator without firm-voice skill (baseline)")
        return []
    skill_ids_path = Path(".skill_ids.json")
    if not skill_ids_path.exists():
        print("WARNING: .skill_ids.json missing - run upload_skills.py first. "
              "Creating coordinator without firm-voice skill.")
        return []
    skill_id = json.loads(skill_ids_path.read_text()).get(VOICE_SKILL)
    if not skill_id:
        print(f"WARNING: {VOICE_SKILL} not in .skill_ids.json - skipping.")
        return []
    return [{"type": "custom", "skill_id": skill_id, "version": "latest"}]


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY before running.")

    specialist_ids_path = Path(".specialist_ids.json")
    if not specialist_ids_path.exists():
        raise SystemExit("Run create_specialists.py first.")
    specialist_ids = json.loads(specialist_ids_path.read_text())

    client = Anthropic(
        api_key=api_key,
        default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
    )

    voice_skills = load_coordinator_skills()
    skills = list(voice_skills)
    # Optional docx skill: attach only when DOCX_SKILL_ID is set. Without it the
    # coordinator may fall back to markdown instead of a real .docx.
    docx_skill_id = os.environ.get("DOCX_SKILL_ID")
    if docx_skill_id:
        skills.append({"type": "custom", "skill_id": docx_skill_id, "version": "latest"})
        print(f"DOCX_SKILL_ID set -> attaching docx skill {docx_skill_id}")
    else:
        print("DOCX_SKILL_ID not set -> no docx skill (markdown fallback possible).")
    system = COORDINATOR_SYSTEM + (VOICE_PROMPT_ADDENDUM if voice_skills else "")

    coordinator = client.beta.agents.create(
        name="Deal Desk Senior Partner",
        model="claude-opus-4-7",  # Coordinator deserves the most capable model
        system=system,
        tools=[{"type": "agent_toolset_20260401"}],
        skills=skills,
        multiagent={
            "type": "coordinator",
            "agents": [
                {"type": "agent", "id": agent_id}
                for agent_id in specialist_ids.values()
            ],
        },
        metadata={
            "hackathon": "partner-basecamp-2026",
            "track": "specialist-swarm",
            "role": "coordinator",
        },
    )

    Path(".coordinator_id").write_text(coordinator.id)
    print(f"Coordinator created: {coordinator.id}")
    print(f"Roster: {list(specialist_ids.keys())}")
    print(f"\nNext: python upload_skills.py then python run_deal_desk.py")


if __name__ == "__main__":
    main()
