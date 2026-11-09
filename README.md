# Specialist Swarm — Deal Desk Swarm

**Ergebnis:** Multi-Agent-System aus dem Hackathon „Option 3 — Specialist Swarm" (Partner Basecamp 2026, **1. Preis**).
**Plattform:** [Claude Managed Agents](https://platform.claude.com/docs/en/managed-agents/multi-agent), Multi-Agent (Research Preview, Beta-Header `managed-agents-2026-04-01`) + [Custom Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview).
**Szenario:** Card A — Deal Desk: eine RFP fliegt rein, eine Proposal-Response fliegt raus.

## Was gebaut wurde

Ein Coordinator-Agent („Senior Partner") orchestriert den kompletten Deal-Desk-Prozess:

1. Liest die RFP (`synthetic-data/rfp-acme-corp.md`) selbst.
2. Delegt **allen vier Spezialisten in einer einzigen Nachricht** — explizites paralleles Fan-out (sichtbar im Event-Stream: vier Threads spawnen innerhalb von Sekunden und laufen parallel).
3. Synthesisiert die Antworten der Spezialisten zu einer Proposal-Response.
4. Schickt den Entwurf an den **Critic** (adversarial Review): `SHIP IT` → finalisieren; `REVISE` → Punkte adressieren (max. zwei Durchgänge); `STOP` → nicht liefern, Begründung melden.

### Roster

| Rolle | Modell | Skill / Wissensbasis |
| --- | --- | --- |
| Coordinator (Senior Partner) | `claude-opus-4-7` | `your-firm-voice` (Hausstimme als Skill) |
| Pricing Specialist | `claude-sonnet-4-6` | `pricing-playbook` |
| Legal Reviewer | `claude-sonnet-4-6` | `legal-checklist` |
| Technical Fit Specialist | `claude-sonnet-4-6` | `product-overview.md` (Kontext) |
| Competitive Intel Analyst | `claude-haiku-4-5-20251001` | `competitive-intel` |
| Critic (5. Agent, S2) | `claude-opus-4-7` | — (prüft: Zahlen, widersprüchliche Positionen, erfundene Referenzen) |

## Was der Live-Run gezeigt hat (verifiziert im Hackathon)

- **Paralleles Fan-out:** alle vier Spezialisten-Threads spawnen innerhalb von Sekunden (Event-Stream als Live-Demo).
- **Critic-Loop:** Synthese → Review → Verdict (`SHIP IT` / `REVISE` / `STOP`).
- **Spezialisten-Deliverables** in der Session (z. B. Pricing-Empfehlung, Legal-Review).
- **Finaler Output:** Markdown-Synthese. Im Workspace existierte keine docx-Skill, daher landet das Dokument als strukturiertes Markdown statt als branded Word-Doc — das Word-Format ist der bekannte, offene Feinschliff.

## Grenzen (bewusst: Proof-of-Concept, kein Produkt)

- **Research-Preview-API:** SDK- und API-Fläche haben sich während des Hackathons geändert. Notwendig gewordene Anpassungen: `display_title` → `display_name` (Skills-Objekte), pydantic-Objekte statt Dictionaries im Coordinator-Roster, UTF-8-Handling der Windows-Konsole.
- **Nur synthetische Daten** — keine echten Kunden- oder Projektdaten.
- **Keine echten Systemintegrationen** (CRM/ITSM/PSA) — als nächste Ausbaustufe vorgesehen (MCP, siehe `stretch-goals.md`).
- **Idempotenz:** `upload_skills.py`, `stretch_critic_subagent.py`, `stretch_parallel_fanout.py` sind re-run-sicher; `create_specialists.py` und `create_coordinator.py` erzeugen bei Wiederholung neue Agents (State-Dateien prüfen, nicht blind neu ausführen).

## Setup und Execution

```powershell
pip install -r requirements.txt
# API-Key NUR in .env (gitignored) — nie ins Repo, nie ins Chat-Log:
#   ANTHROPIC_API_KEY=sk-ant-...
```

**Ein-Befehl-Finalisierung:** `./finalize.ps1` (PowerShell) — prüft Python und Key (Wert wird nie ausgegeben), führt alle Setup-Schritte in korrekter Reihenfolge aus, startet den Deal-Run erst nach Bestätigung und prüft am Ende den Output.

**Alternativ Schritt für Schritt** (Reihenfolge ist wichtig: `upload_skills` vor `create_coordinator`):

```bash
python setup_environment.py
python create_specialists.py
python upload_skills.py
python create_coordinator.py
python stretch_critic_subagent.py     # S2: Critic (idempotent)
python stretch_parallel_fanout.py     # S4: explizites Fan-out (idempotent)
python run_deal_desk.py               # der kostenpflichtige Lauf
```

**Hinweise:**
- `NO_VOICE=1 python create_coordinator.py` erzeugt einen Baseline-Coordinator ohne Hausstimme (Vorher-/Nachher-Vergleich, `snapshot_run.py`).
- `DOCX_SKILL_ID=<id> python create_coordinator.py` hängt optional eine docx-Skill an den Coordinator, falls eine im Workspace existiert.
- Läuft der Event-Stream ab (längerer SSE-Stream), der Swarm weiter: `python poll_session.py` holt die Session über kurze Aufrufe ab und lädt alle Dateien nach `outputs/`.
- State-Dateien (`.environment_id`, `.specialist_ids.json`, `.skill_ids.json`, `.coordinator_id`, `.last_session_id`) und `outputs/` sind lokal und gitignored.

## Dateistruktur

```
├── README.md                    (dieses Dokument)
├── scenario-cards.md            (Szenario-Karten A/B/C)
├── stretch-goals.md             (Stretch-Ziele S1–S10)
├── finalize.ps1                 (Ein-Befehl-Finalisierung)
├── run_direct.py                (Pipeline-Runner: setup | run)
├── poll_session.py              (Session-Abfrage nach Stream-Abbruch)
├── setup_environment.py         (Cloud-Environment, idempotent)
├── create_specialists.py        (4 Spezialisten)
├── upload_skills.py             (Skills hochladen + anhängen, idempotent)
├── create_coordinator.py        (Coordinator + Voice-Skill + optional docx)
├── run_deal_desk.py             (der Deal-Run, streamed)
├── stretch_critic_subagent.py   (S2: Critic, idempotent)
├── stretch_parallel_fanout.py   (S4: explizites Fan-out, idempotent)
├── snapshot_run.py              (Vorher-/Nachher-Snapshots von outputs/)
├── download_deliverable.py      (Dateien einer Session laden)
├── skills/                      (Custom Skills)
│   ├── pricing-playbook/SKILL.md
│   ├── legal-checklist/SKILL.md
│   ├── competitive-intel/SKILL.md
│   └── your-firm-voice/SKILL.md
└── synthetic-data/
    ├── rfp-acme-corp.md         (RFP — der Auslöser)
    ├── past-wins.json           (Vergleichsdeals für Pricing)
    └── product-overview.md      (Capability Map für Technical Fit)
```
