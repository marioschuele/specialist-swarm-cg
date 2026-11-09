"""
Poll a managed-agents session until the swarm finishes, then download all
session files to outputs/. Uses SHORT file-list calls (which are stable in
this environment) instead of holding a long SSE stream (which drops).

Usage:  python poll_session.py [session_id]
        (defaults to .last_session_id)
"""
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv


def _apply_env() -> None:
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set in .env")
    os.environ["ANTHROPIC_BASE_URL"] = "https://api.anthropic.com"
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)


DONE_PATTERNS = re.compile(r"(proposal|response|final|synthesis|executive)", re.I)


def list_files(client, sid):
    files = client.beta.files.list(scope_id=sid, betas=["managed-agents-2026-04-01"])
    return list(files.data)


def looks_done(names):
    # done if we have 5+ files (4 specialists + final synthesis) OR a file
    # whose name signals the final proposal.
    if len(names) >= 5:
        return True
    return any(DONE_PATTERNS.search(n) for n in names)


def main() -> None:
    _apply_env()
    import sys
    from anthropic import Anthropic

    sid = sys.argv[1].strip() if len(sys.argv) > 1 else Path(".last_session_id").read_text().strip()
    client = Anthropic()
    print(f"Polling session {sid} (short file-list calls, no long stream)...", flush=True)

    seen = set()
    for i in range(1, 37):  # up to ~15 min at 25s cadence
        try:
            files = list_files(client, sid)
            names = [getattr(f, "filename", getattr(f, "name", str(f.id))) for f in files]
            new = [n for n in names if n not in seen]
            seen |= set(names)
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] poll {i:02d}: {len(names)} file(s)"
                  + (f"  NEW: {new}" if new else ""), flush=True)
            if looks_done(names):
                print(f"[{ts}] -> looks DONE. Downloading all session files to outputs/.", flush=True)
                out = Path("outputs")
                out.mkdir(exist_ok=True)
                count = 0
                for f in files:
                    fn = getattr(f, "filename", getattr(f, "name", str(f.id)))
                    dest = out / fn
                    content = client.beta.files.download(f.id)
                    content.write_to_file(str(dest))
                    print(f"   saved {fn} -> {dest}", flush=True)
                    count += 1
                print(f"\nPOLL DONE: {count} file(s) in outputs/.", flush=True)
                # Final listing for the caller
                for p in sorted(out.iterdir()):
                    print(f"   outputs/{p.name}  ({p.stat().st_size} bytes)", flush=True)
                return
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] poll {i:02d} error (retrying): {type(e).__name__} {str(e)[:120]}", flush=True)
        time.sleep(25)

    print("\nPOLL TIMEOUT (~15 min) without clear completion. Session may still be running.", flush=True)
    try:
        names = [getattr(f, "filename", getattr(f, "name", str(f.id))) for f in list_files(client, sid)]
        print("Current files:", names, flush=True)
    except Exception as e:
        print("final list error:", type(e).__name__, str(e)[:120], flush=True)


if __name__ == "__main__":
    main()
