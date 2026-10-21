# DemoBank — Autonomous Spec-Driven QA Agent (MVP)

**Goal:** PRD clauses → traceable scenario plan → real Playwright browser → deterministic oracle → `PASSED`/`FAILED`/`UNVERIFIED`, with evidence and reproducible steps. **A successful click is not a pass.**

## What is implemented

- Reads the supplied `../test-website/PRD.md` and extracts **every bullet under the behavioral sections** into `qa_output/requirements.json` with verbatim PRD quotes and stable IDs. Optional one-shot Gemini extraction enriches acceptance criteria; the PRD quote remains authoritative. If Gemini is unavailable, the report states that deterministic fallback was used.
- Compiles six replayable **normal/negative/edge** verification scenarios into `qa_output/scenario_plan.json`: `login`, `dashboard`, `logout`, `single_day`, `zero`, `precision`.
- Controls the **real DemoBank UI** with Playwright at 1280×800; calls the supplied backend API *only to corroborate state*, never to replace the UI test.
- Uses **numeric and state-based oracles**, including rejection + **no balance change and no new transaction** for invalid transfer values.
- Resets the local DemoBank PostgreSQL seed **before each scenario**. If reset fails, that scenario is **UNVERIFIED**, never a false product failure.
- Reports **all PRD clauses** in a traceability matrix. Unimplemented clauses are honestly **UNVERIFIED**. Failed checks include expected/observed, screenshot at assertion, DOM excerpt, and reproduction steps.
- Emits `qa_output/report.json`, `report.md`, `report.html`, and `screenshots/`.
- Tracks actual token counts from the optional Gemini call. Dollar estimates require pricing supplied through `.env`; the report does not claim an unknown price is $0.

**Important scope limitation:** This is a focused hard-coded deterministic scenario library tied to six checks, not a general-purpose autonomous scenario compiler. The LLM enhances specification interpretation; verification and replay require no model calls. No automatic recover/replan loop is included in this deadline-oriented MVP.

## Repository layout

Place this `agent/` folder alongside the *supplied* `test-website/` folder:

```text
Agentic-QA-Hackathon-kit-main/
├── test-website/
│   ├── PRD.md
│   ├── LOCAL_SETUP.md
│   ├── database/
│   ├── backend/
│   └── frontend/
└── agent/
    ├── demobank_qa/
    │   ├── __main__.py
    │   ├── models.py
    │   ├── spec.py
    │   ├── plan.py
    │   ├── driver.py
    │   ├── checks.py
    │   ├── oracles.py
    │   ├── reset.py
    │   ├── costs.py
    │   ├── report.py
    │   └── runner.py
    ├── tests/
    ├── requirements.txt
    └── .env.example
```

## Windows PowerShell — start DemoBank locally

Requires **Docker Desktop**, **Node 20+**, **Python 3.11+**. Open four PowerShell terminals.

**Terminal 1: DB**

```powershell
cd test-website\database
docker compose up -d --wait
```

Run from the repository root in each *new* terminal as needed.

**Terminal 2: API**

```powershell
cd test-website\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:DATABASE_URL = 'postgresql://demobank:demobank_local@localhost:5432/demobank'
$env:SESSION_SECRET = [guid]::NewGuid().ToString('N')
python -m uvicorn demobank.main:app --host 127.0.0.1 --port 8000
```

**Terminal 3: UI**

```powershell
cd test-website\frontend
npm ci
npm run dev
```

Visit http://localhost:5173 and make sure **Enter Demo** works.

**Terminal 4: agent**

```powershell
cd agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m pytest -q
python -m demobank_qa --no-llm --dry-run
```

> Keep the app base URL as **`http://localhost:5173`** (not `127.0.0.1`) to match DemoBank's credentialed CORS configuration.

## Fastest first end-to-end verification

Run the simplest actual browser scenario first:

```powershell
python -m demobank_qa --no-llm --only login --headed
```

It resets the synthetic database, launches Chromium, clicks **Enter Demo**, and checks the dashboard state. Review `qa_output/report.html` and its screenshot. If no live app/reset is available it reports **UNVERIFIED** instead of claiming a false defect.

Then run the full implemented suite:

```powershell
python -m demobank_qa --no-llm --headed
```

The six scenarios are: `login`, `dashboard`, `logout`, `single_day`, `zero`, `precision`. The **single-day inclusive-date** scenario is particularly useful because it derives expected transaction IDs from *unfiltered* transaction state and checks the visible filtered rows. It does **not** assume a defect unless the real UI evidence supports it.

## Run with real LLM spec ingestion

Add an optional `agent/.env` (never commit it):

```env
GEMINI_API_KEY=YOUR_KEY
INPUT_USD_PER_M_TOKENS=YOUR_CONFIRMED_INPUT_PRICE
OUTPUT_USD_PER_M_TOKENS=YOUR_CONFIRMED_OUTPUT_PRICE
```

Then run:

```powershell
python -m demobank_qa --only login --headed
python -m demobank_qa --headed
```

The first command makes one model call to interpret acceptance criteria if the key is valid. It records input/output token usage, and **explicitly logs when an API call fell back to deterministic extraction**. Re-run with `--no-llm` to demonstrate zero model calls for replay.

## Commands and flags

```text
python -m demobank_qa --prd ../test-website/PRD.md --base-url http://localhost:5173 --api-url http://localhost:8000 --headed
python -m demobank_qa --only single_day --no-llm
python -m demobank_qa --no-llm --dry-run
python -m demobank_qa --no-llm --skip-reset       # less reproducible; hosted-only fallback
python -m demobank_qa --no-llm --api-url none      # API-backed oracles may be UNVERIFIED
```

Test suite: `python -m pytest -q`.

### Deterministic database reset

The runner pipes the kit's **`migrations/001_create_schema.sql` and `seed.sql`** into only the supplied DemoBank PostgreSQL service via `docker compose exec -T postgres psql`. It uses the participant kit's own local compose stack. No external targets are touched. Always use synthetic data.

### Evidence and verdict rules

- `PASSED`: typed oracle confirms expected state with screenshot.
- `FAILED`: typed oracle confirms contradictory state; include observed vs expected and reproduction steps.
- `UNVERIFIED`: browser/API/reset unavailable, ambiguous baseline, scenario not implemented, or insufficient evidence. **An agent exception is not automatically a product defect.**

Two separate dimensions appear in output: `execution_status` (`ok`/`blocked`) and requirement verdict (`PASSED`/`FAILED`/`UNVERIFIED`).

## Known limitations and tradeoffs

- A subset of the PRD has executable scenarios. All other clauses remain visible as `UNVERIFIED` in the report. No fabricated coverage.
- API corroboration is only available locally when the backend is reachable and the browser holds the synthetic demo session.
- Browser selectors assume supplied DemoBank's labeled controls; unexpected states become `UNVERIFIED`. No LLM recover/replan during execution.
- Deterministic reset requires Docker Compose and the supplied local DB; hosted runs should use `--skip-reset` and may lack reliable mutation baselines.
- Some requirements need more scenarios than the six included; do not present the MVP as complete regression coverage.
- Prices are intentionally not hard-coded; USD estimate is `null` unless operator supplies current model prices.

## Video — 3–5 minute honest walkthrough

1. Show `PRD.md` clause and `qa_output/requirements.json` (spec ingestion).
2. Show `qa_output/scenario_plan.json` with negative + edge cases.
3. Run `python -m demobank_qa --no-llm --only single_day --headed` (live browser) and optionally invalid transfer.
4. Open `qa_output/report.html`, inspect a verdict, expected vs actual, screenshot, and reproduction steps.
5. Show `qa_output/report.json` cost fields; if Gemini was used on an earlier run, show recorded token totals and confirmed pricing assumptions.

**Do not** submit a dry run as evidence of a successful live run; verify the report came from a connected DemoBank instance.
