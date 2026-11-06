"""
Zero-cost verification for the P3 stretch scripts (S2 critic + S4 fan-out).

Makes NO Anthropic API calls and costs nothing. It stubs the `anthropic`
package with an in-memory fake workspace, then exercises the idempotency and
anti-clobber guarantees of:

  - stretch_critic_subagent.apply_critic            (S2)
  - stretch_parallel_fanout.apply_parallel_fanout   (S4)

Run:  python test_p3_stretch.py
Expect the final line:  ALL CHECKS PASSED (no API calls, no cost).
"""

import sys
import types
from types import SimpleNamespace


def _install_fake_anthropic() -> None:
    """Replace `anthropic` so importing the scripts makes no real API calls."""
    fake = types.ModuleType("anthropic")

    class _NoRealClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("tests must not construct the real Anthropic client")

    fake.Anthropic = _NoRealClient
    sys.modules["anthropic"] = fake


_install_fake_anthropic()

import create_coordinator  # noqa: E402  (real base coordinator system prompt)
import stretch_critic_subagent as scs  # noqa: E402
import stretch_parallel_fanout as spf  # noqa: E402

BASE = create_coordinator.COORDINATOR_SYSTEM
SPECIALIST_KEYS = ["pricing", "legal", "technical_fit", "competitive"]
EXPECTED_TOTAL_AGENTS = len(SPECIALIST_KEYS) + 1  # specialists + coordinator


class FakeAgent:
    def __init__(self, agent_id, name, system):
        self.id = agent_id
        self.name = name
        self.system = system
        self.version = 1
        self.multiagent = SimpleNamespace(agents=[])
        self.skills = []


class FakeAgents:
    def __init__(self):
        self._agents = {}
        self._seq = 0

    def _new_id(self, prefix):
        self._seq += 1
        return f"{prefix}_{self._seq:03d}"

    def create(self, name, **kwargs):
        aid = self._new_id("agent")
        agent = FakeAgent(aid, name, kwargs.get("system", ""))
        self._agents[aid] = agent
        return agent

    def retrieve(self, agent_id):
        return self._agents[agent_id]

    def update(self, agent_id, version=None, system=None, multiagent=None, **kwargs):
        agent = self._agents[agent_id]
        if system is not None:
            agent.system = system
        if multiagent is not None:
            agent.multiagent.agents = list(multiagent["agents"])
        agent.version = (version if version is not None else agent.version) + 1
        return agent


class FakeClient:
    def __init__(self):
        self.beta = SimpleNamespace(agents=FakeAgents())


def make_workspace():
    client = FakeClient()
    agents = client.beta.agents
    specialist_ids = {}
    roster = []
    for key in SPECIALIST_KEYS:
        agent = agents.create(name=key, system="")
        specialist_ids[key] = agent.id
        roster.append({"type": "agent", "id": agent.id})
    coordinator = agents.create(name="Deal Desk Senior Partner", system=BASE)
    coordinator.multiagent.agents = roster
    return client, coordinator.id, specialist_ids


def roster_ids(client, coordinator_id):
    coord = client.beta.agents.retrieve(coordinator_id)
    return [a["id"] for a in coord.multiagent.agents]


def check(label, condition):
    if not condition:
        print(f"FAIL: {label}")
        sys.exit(1)
    print(f"  ok: {label}")


def main() -> None:
    print("S2 — critic idempotency (run twice, no duplication)")
    client, coord, spec = make_workspace()
    roster_before = len(roster_ids(client, coord))
    scs.apply_critic(client, coord, spec)
    c = client.beta.agents.retrieve(coord)
    check("critic recorded in specialist_ids", "critic" in spec)
    check("exactly one # Critic block after run 1", c.system.count("# Critic") == 1)
    check("roster grew by exactly one", len(roster_ids(client, coord)) == roster_before + 1)
    check("critic in roster exactly once", roster_ids(client, coord).count(spec["critic"]) == 1)

    scs.apply_critic(client, coord, spec)  # second run must be a no-op
    c = client.beta.agents.retrieve(coord)
    check("no duplicated # Critic block after run 2", c.system.count("# Critic") == 1)
    check("no duplicated roster entry after run 2", roster_ids(client, coord).count(spec["critic"]) == 1)
    check("critic not re-created (agent count stable)",
          len(client.beta.agents._agents) == EXPECTED_TOTAL_AGENTS + 1)

    print("S2 + S4 — anti-clobber (S4 preserves critic roster entry and skills)")
    coord_agent = client.beta.agents.retrieve(coord)
    coord_agent.skills = [{"type": "custom", "skill_id": "s1_firm_voice"}]
    skills_before = list(coord_agent.skills)
    spf.apply_parallel_fanout(client, coord)
    c = client.beta.agents.retrieve(coord)
    check("exactly one # Parallel delegation block", c.system.count("# Parallel delegation") == 1)
    check("S2 # Critic block preserved by S4", c.system.count("# Critic") == 1)
    check("critic still in roster exactly once", roster_ids(client, coord).count(spec["critic"]) == 1)
    check("S4 did not touch coordinator skills", c.skills == skills_before)

    spf.apply_parallel_fanout(client, coord)  # second run must be a no-op
    c = client.beta.agents.retrieve(coord)
    check("no duplicated fan-out block after run 2", c.system.count("# Parallel delegation") == 1)

    print("S4 alone — idempotency on a fresh coordinator")
    client2, coord2, _ = make_workspace()
    spf.apply_parallel_fanout(client2, coord2)
    check("fan-out present after run 1", client2.beta.agents.retrieve(coord2).system.count("# Parallel delegation") == 1)
    spf.apply_parallel_fanout(client2, coord2)
    check("fan-out not duplicated after run 2", client2.beta.agents.retrieve(coord2).system.count("# Parallel delegation") == 1)

    print("Order independence — S4 then S2")
    client3, coord3, spec3 = make_workspace()
    spf.apply_parallel_fanout(client3, coord3)
    scs.apply_critic(client3, coord3, spec3)
    c3 = client3.beta.agents.retrieve(coord3)
    check("both blocks present exactly once each",
          c3.system.count("# Parallel delegation") == 1 and c3.system.count("# Critic") == 1)
    check("critic in roster exactly once", roster_ids(client3, coord3).count(spec3["critic"]) == 1)

    print("\nALL CHECKS PASSED (no API calls, no cost).")


if __name__ == "__main__":
    main()
