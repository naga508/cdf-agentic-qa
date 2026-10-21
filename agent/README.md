# DemoBank QA Agent — Architecture and Setup

## Overview

An AI-assisted, specification-driven QA agent built for the CDF Agentic QA Hackathon.

The system reads the DemoBank Product Requirements Document (PRD), extracts traceable requirements, executes browser-based verification scenarios, and generates evidence-backed **PASSED / FAILED / UNVERIFIED** verdicts.

The central principle is that successful browser actions do not prove requirements have passed. Verdicts must be supported by observed application state and reproducible evidence.

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| LLM | Google Gemini 3.5 Flash-Lite |
| Browser automation | Playwright / Chromium |
| API verification | HTTPX |
| Backend under test | FastAPI |
| Frontend under test | React |
| Database | PostgreSQL / Docker |
| Testing | Pytest |
| Reporting | JSON, Markdown, HTML |

## System Architecture

```text
PRD.md
   |
   v
Requirement Extraction (Gemini)
   |
   v
Structured Requirements
   |
   v
Predefined Scenario Planner
   |
   v
Playwright Browser Executor
   |
   v
Deterministic Verification Oracles
   |
   v
Evidence Collector
   |
   v
QA Audit Report + Token Cost Breakdown
```

### Main Components

- **Spec ingestion:** Extracts requirements from the PRD and optionally enriches acceptance criteria using Gemini.
- **Scenario planning:** Maps requirements to executable positive, negative, and edge-case scenarios.
- **Browser driver:** Operates DemoBank through a real Chromium browser.
- **API probe:** Corroborates browser observations using the supplied application's backend.
- **Verification oracles:** Compare expected and actual state, including balances, transaction records, and validation responses.
- **Evidence collector:** Captures screenshots, observed values, and reproduction steps.
- **Report generator:** Produces machine-readable and human-readable audit artifacts.
- **Cost meter:** Records LLM token usage and estimated API cost.

## Installation and Setup

### Prerequisites

- Windows with Python and Node.js
- Docker Desktop with a running Linux container engine
- Playwright Chromium
- Gemini API key (optional for deterministic runs)

### 1. Start PostgreSQL

From the repository root:

```powershell
cd .\test-website\database
docker compose up -d --wait
```

Verify the container:

```powershell
docker compose ps
```

### 2. Start the FastAPI Backend

Open a new terminal and navigate to `test-website/backend`.

Create a virtual environment if needed:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Configure the local environment:

```powershell
$env:DATABASE_URL = 'postgresql://demobank:demobank_local@localhost:5432/demobank'
$env:SESSION_SECRET = [guid]::NewGuid().ToString('N')
```

Start FastAPI with a Windows-compatible event loop:

```powershell
python -m uvicorn demobank.main:app --host 127.0.0.1 --port 8000 --loop asyncio:SelectorEventLoop
```

Backend health check: http://localhost:8000/health

### 3. Start the React Frontend

Open another terminal and navigate to `test-website/frontend`.

```powershell
npm.cmd ci
npm.cmd run dev
```

Frontend URL: http://localhost:5173

### 4. Set Up the QA Agent

Open another terminal and navigate to `agent`.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

For Gemini-enabled runs, create `agent/.env`:

```env
GEMINI_API_KEY=YOUR_API_KEY
```

Never commit the `.env` file.

## Running the Agent

### Deterministic QA Suite

Run all six implemented scenarios without an LLM call:

```powershell
python -m demobank_qa --no-llm --headed
```

### Gemini-Enabled QA Suite

```powershell
python -m demobank_qa --model gemini-3.5-flash-lite --headed --out qa_output_submission
```

### Run an Individual Scenario

```powershell
python -m demobank_qa --no-llm --only login --headed
```

### Unit Tests

```powershell
python -m pytest -q
```

## Verified Hackathon Results

| Metric | Result |
|---|---:|
| PRD requirements | 32 |
| Executed scenarios | 6 |
| Passed scenarios | 4 |
| Failed scenarios | 2 |
| Passed requirements | 3 |
| Failed requirements | 2 |
| Unverified requirements | 27 |
| Blocked executions | 0 |

### Defect 1: PRD-023 — Inclusive Date Filter

**Expected:** Transactions occurring on the selected end date must be included.

**Observed:** A valid transaction from June 15, 2025, was missing when the start and end date were both June 15, 2025.

**Verdict:** FAILED.

### Defect 2: PRD-014 — Zero-Amount Transfer

**Expected:** A zero-amount transfer must be rejected without creating a transaction.

**Observed:** DemoBank displayed success and created a transaction record for a zero-value transfer.

**Verdict:** FAILED.

These findings were reproduced in real-browser tests with deterministic PostgreSQL resets.

## LLM Cost Breakdown

| Metric | Demonstrated Run |
|---|---:|
| Model | Gemini 3.5 Flash-Lite |
| API calls | 1 |
| Input tokens | 1,378 |
| Output tokens | 2,522 |
| Estimated API cost | $0.0067184 |
| Deterministic verification LLM cost | $0 |

The estimated API cost is calculated using configured token prices and may differ from actual billing.

## QA Audit Reports

The final artifacts are available in `qa_output_submission/`:

- [Markdown QA Audit](qa_output_submission/report.md)
- [JSON QA Audit](qa_output_submission/report.json)
- [HTML QA Audit](qa_output_submission/report.html)
- [Extracted Requirements](qa_output_submission/requirements.json)
- [Scenario Plan](qa_output_submission/scenario_plan.json)
- `qa_output_submission/screenshots/` — Browser evidence

## Known Limitations

- The MVP contains six predefined scenarios covering five distinct requirements.
- Untested or insufficiently evidenced requirements remain UNVERIFIED.
- Gemini assists specification interpretation, but executable scenarios are not generated dynamically for arbitrary applications.
- Deterministic database resets require the local Docker/PostgreSQL environment.
- General-purpose LLM recovery and browser replanning are not implemented.
- On Windows, Psycopg requires a compatible asyncio event loop, and SQL reset input must preserve UTF-8 encoding.

## Safety

Testing is restricted to DemoBank and its synthetic financial data. The agent does not interact with actual banking systems or store real financial credentials.

---

**CDF Agentic QA Hackathon — October 21, 2026**
