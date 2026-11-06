# finalize.ps1 — one-command finalization for the Specialist Swarm (Card A).
#
# Run from the repo root, in PowerShell. It reads the API key from the
# ENVIRONMENT only — it never stores, prints, or commits the value.
#
# Before running, set these in YOUR shell (never in a file or in chat):
#   $env:ANTHROPIC_API_KEY = "sk-ant-..."      # required
#   $env:DOCX_SKILL_ID     = "skill_..."       # optional: needed for a real .docx
#
# Then:  ./finalize.ps1

$ErrorActionPreference = "Stop"

function Step($n, $name) {
    Write-Host "`n=== [$n] $name ===" -ForegroundColor Cyan
}

# 0. Python check (a working interpreter is required; none is installed by default here).
Step 0 "Python"
$py = $null
foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    Write-Host "No Python found. Install first:  winget install Python.Python.3.12" -ForegroundColor Red
    exit 1
}
Write-Host "Using: $py"
& $py --version

# 1. Key check (value is never echoed).
Step 1 "ANTHROPIC_API_KEY"
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Host "ANTHROPIC_API_KEY is not set. Set it in your shell first." -ForegroundColor Red
    exit 1
}
Write-Host "ANTHROPIC_API_KEY is set (value hidden)."

# 2. Dependencies.
Step 2 "pip install -r requirements.txt"
& $py -m pip install -r requirements.txt

# 3. Fresh build with your key (in the documented order).
# NOTE: upload_skills MUST run before create_coordinator (needs .skill_ids.json).
Step 3 "setup_environment.py"
& $py setup_environment.py
Step 4 "create_specialists.py"
& $py create_specialists.py
Step 5 "upload_skills.py"
& $py upload_skills.py
Step 6 "create_coordinator.py  (voice + optional docx skill)"
& $py create_coordinator.py
Step 7 "S2 critic (idempotent)"
& $py stretch_critic_subagent.py
Step 8 "S4 parallel fan-out (idempotent)"
& $py stretch_parallel_fanout.py

# 9. THE COSTLY RUN — confirm before it proceeds.
Step 9 "run_deal_desk.py  (COSTLY)"
Write-Host "This starts the full swarm: Opus coordinator + 4 specialists + critic + docx." -ForegroundColor Yellow
Write-Host "A spend cap should be in place. Press ENTER to run, or Ctrl+C to abort."
$null = Read-Host

& $py run_deal_desk.py

# 10. Deliverable check — the whole demo hinges on a real .docx landing here.
Step 10 "Check outputs/"
$docx = Get-ChildItem -Path outputs -Filter *.docx -ErrorAction SilentlyContinue
if ($docx) {
    Write-Host "OK: .docx present in outputs/ ->" -ForegroundColor Green
    $docx | ForEach-Object { Write-Host ("   " + $_.Name) -ForegroundColor Green }
    Write-Host "If the text does not sound like your house voice, re-check the firm-voice skill wiring." -ForegroundColor Green
} else {
    Write-Host "NO .docx in outputs/ — markdown-only output." -ForegroundColor Red
    Write-Host "The coordinator likely has no docx skill. Set DOCX_SKILL_ID, then re-run create_coordinator.py + run_deal_desk.py (or accept markdown)." -ForegroundColor Red
}

Write-Host "`nDone. Monitor 1 = the event stream above; Monitor 2 = outputs/*.docx." -ForegroundColor Cyan
