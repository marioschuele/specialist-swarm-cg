# Specialist Swarm — Deal Desk

Eine Multi-Agent-Plattform auf Basis von [Claude Managed Agents](https://platform.claude.com/docs/en/managed-agents/multi-agent) und [Custom Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview). Das System liest eine eingehende RFP, verteilt die Facharbeit parallel auf vier Domänen-Spezialisten, synthetisiert deren Ergebnisse zu einer Proposal-Response und lässt den Entwurf vor der Finalisierung von einem Reviewer-Agenten prüfen.

**Plattform:** Claude Managed Agents (Multi-Agent, Beta-Header `managed-agents-2026-04-01`) und Custom Skills.

## Funktionen

- **Parallele Facharbeit:** Der Koordinator delegiert in einem einzigen Schritt an vier Domänen-Spezialisten, die gleichzeitig arbeiten.
- **Domänen-Skills:** Jeder Spezialist nutzt eine eigene, versionierte Wissensbasis — Pricing-Playbook, Legal-Checkliste, Wettbewerbsdaten, Produktdokumentation.
- **Adversarial Review:** Ein Reviewer-Agent prüft den Entwurf auf konsistente Kennzahlen, widersprüchliche Positionen zwischen den Fachbereichen und nicht belegbare Aussagen, bevor das Dokument finalisiert wird.
- **Konfigurierbare Unternehmensstimme:** Das finale Dokument wird in einer eigenen, als Skill hinterlegten Hausstimme verfasst.

## Architektur

Der Koordinator führt den Prozess in vier Schritten:

1. Liest die RFP selbst und erfasst Kundenprofil, Umfang und kritische Forderungen.
2. Delegt die Facharbeit allen vier Spezialisten in einer einzigen Nachricht; die Agent-Threads werden parallel gestartet und laufen gleichzeitig.
3. Synthetisiert die Ergebnisse der Spezialisten zu einer Proposal-Response.
4. Überlässt den Entwurf dem Reviewer-Agenten. Bei `SHIP IT` wird das Dokument finalisiert, bei `REVISE` werden die genannten Punkte adressiert (höchstens zwei Durchgänge), bei `STOP` wird nicht finalisiert und die Begründung gemeldet.

### Komponenten

| Rolle | Modell | Wissensbasis (Skill) |
| --- | --- | --- |
| Koordinator | `claude-opus-4-7` | `your-firm-voice` |
| Pricing-Spezialist | `claude-sonnet-4-6` | `pricing-playbook` |
| Rechtsprüfung | `claude-sonnet-4-6` | `legal-checklist` |
| Technische Passung | `claude-sonnet-4-6` | `product-overview.md` (Kontext) |
| Wettbewerbsanalyse | `claude-haiku-4-5-20251001` | `competitive-intel` |
| Reviewer | `claude-opus-4-7` | — |

## Voraussetzungen

- Python 3.10+
- Ein API-Key für den Zugriff auf Claude Managed Agents
- Ein Workspace mit Zugriff auf die Multi-Agent-Fähigkeit (Beta)

## Installation

```bash
pip install -r requirements.txt
```

Der API-Key wird über die Umgebungsvariable `ANTHROPIC_API_KEY` bereitgestellt.

## Ausführung

**Ein-Befehls-Ausführung (PowerShell):**

```powershell
./finalize.ps1
```

Der Aufruf prüft Python und API-Key, führt die Einrichtung in der korrekten Reihenfolge aus, startet den Lauf nach Bestätigung und meldet das Ergebnis.

**Schrittweise Ausführung** (Reihenfolge beachten — `upload_skills` vor `create_coordinator`):

```bash
python setup_environment.py
python create_specialists.py
python upload_skills.py
python create_coordinator.py
python stretch_critic_subagent.py
python stretch_parallel_fanout.py
python run_deal_desk.py
```

## Konfiguration

| Variable | Wirkung |
| --- | --- |
| `ANTHROPIC_API_KEY` | API-Key (erforderlich) |
| `NO_VOICE` | `=1` erzeugt den Koordinator ohne Unternehmensstimme (Vergleichslauf, `snapshot_run.py`) |
| `DOCX_SKILL_ID` | bindet eine docx-Skill an den Koordinator an, falls im Workspace vorhanden |

## Projektstruktur

```
├── finalize.ps1                 (Ein-Befehls-Ausführung)
├── run_direct.py                (Pipeline-Runner: setup | run)
├── poll_session.py              (Abfrage der Session nach Stream-Abbruch)
├── setup_environment.py         (Agent-Laufumgebung)
├── create_specialists.py        (vier Spezialisten)
├── upload_skills.py             (Skills hochladen und zuordnen)
├── create_coordinator.py        (Koordinator inkl. Unternehmensstimme und optionaler docx-Skill)
├── run_deal_desk.py             (Ausführung des Laufs)
├── stretch_critic_subagent.py   (Reviewer-Agent)
├── stretch_parallel_fanout.py   (explizite parallele Delegation)
├── snapshot_run.py              (Vergleichsläufe: Vorher-/Nachher-Snapshots)
├── download_deliverable.py      (Dokumente einer Session laden)
├── scenario-cards.md            (Szenario-Karten)
├── stretch-goals.md             (weitere Ausbaustufen)
├── skills/
│   ├── pricing-playbook/SKILL.md
│   ├── legal-checklist/SKILL.md
│   ├── competitive-intel/SKILL.md
│   └── your-firm-voice/SKILL.md
└── synthetic-data/
    ├── rfp-acme-corp.md         (eingehende RFP)
    ├── past-wins.json           (vergleichbare Aufträge)
    └── product-overview.md      (Produktübersicht / Capability Map)
```

## Hinweise

- Die Ausführung erzeugt die Dokumente als strukturiertes Markdown. Für eine Word-Ausgabe wird eine docx-Skill benötigt, die über `DOCX_SKILL_ID` an den Koordinator angebunden wird.
- `upload_skills.py`, `stretch_critic_subagent.py` und `stretch_parallel_fanout.py` sind für wiederholtes Ausführen idempotent. `create_specialists.py` und `create_coordinator.py` erzeugen bei Wiederholung neue Agenten-Instanzen; die gespeicherten IDs sollten vor einem Neuaufbau geprüft werden.
- Bricht der Live-Event-Stream während eines längeren Laufs ab, läuft der Prozess weiter: `python poll_session.py` lädt die fertiggestellten Dokumente der Session herunter.
- Beispielhafte Eingabedaten (RFP, Vergleichsdeals, Produktübersicht) sind im Verzeichnis `synthetic-data/` enthalten.
