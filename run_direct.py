"""
One-command pipeline runner for the Specialist Swarm, applying the
(user-approved) corporate-proxy bypass so the managed-agents calls reach
api.anthropic.com directly.

Usage:
    python run_direct.py setup   # 6 cheap steps (env, specialists, skills,
                                 #   coordinator, S2 critic, S4 fan-out)
    python run_direct.py run     # the COSTLY deal-desk run (reads setup state)

The API key is read from .env (gitignored). The approved proxy bypass sets
ANTHROPIC_BASE_URL to the real Anthropic API and drops ANTHROPIC_AUTH_TOKEN.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _apply_env() -> None:
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set in .env")
    # Approved corporate-proxy bypass: hit the real API, not the corporate
    # gateway that rejects this workspace key.
    os.environ["ANTHROPIC_BASE_URL"] = "https://api.anthropic.com"
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    # No docx skill exists in the workspace -> no DOCX_SKILL_ID (markdown fallback).
    os.environ.pop("DOCX_SKILL_ID", None)


def setup() -> None:
    import setup_environment
    import create_specialists
    import upload_skills
    import create_coordinator
    import stretch_critic_subagent
    import stretch_parallel_fanout

    _apply_env()
    modules = (
        setup_environment,
        create_specialists,
        upload_skills,
        create_coordinator,
        stretch_critic_subagent,
        stretch_parallel_fanout,
    )
    for mod in modules:
        print(f"\n########## STEP: {mod.__name__} ##########", flush=True)
        mod.main()
    print("\nSETUP COMPLETE. Next:  python run_direct.py run   (COSTLY)")


def run() -> None:
    import run_deal_desk

    _apply_env()
    run_deal_desk.main()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "setup":
        setup()
    elif mode == "run":
        run()
    else:
        raise SystemExit("Usage: python run_direct.py {setup|run}")
