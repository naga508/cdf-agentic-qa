# CDF Agentic QA — DemoBank Verification

**AI-powered specification-driven quality assurance using Gemini, Python, Playwright, and deterministic verification.**

Developed for the Community Dreams Foundation Agentic QA Hackathon, October 21, 2026.

## Overview

This project implements an AI-assisted QA system that reads the DemoBank Product Requirements Document (PRD), extracts traceable acceptance criteria, executes real browser scenarios, validates resulting application state, and produces evidence-backed **PASSED / FAILED / UNVERIFIED** verdicts.

The central design principle is simple: **a successful click is not proof that a requirement passed.**

## Demonstrated Results

| Metric | Result |
|---|---:|
| Traceable PRD requirements | 32 |
| Implemented test scenarios | 6 |
| Distinct requirements exercised | 5 |
| Passed scenarios | 4 |
| Failed scenarios | 2 |
| Passed requirements | 3 |
| Failed requirements | 2 |
| Unverified requirements | 27 |
| Blocked executions | 0 |

### Reproduced Defects

**PRD-023 — Inclusive Date Filtering**

A single-day transaction filter omitted a transaction on the selected boundary date, despite the PRD requiring inclusive dates.

**PRD-014 — Zero-Amount Transfer Validation**

DemoBank accepted a zero-value transfer, displayed success, and created a transaction record instead of rejecting the invalid request.

Both findings were reproduced against the live browser application using deterministic database resets.

## Architecture

```text
DemoBank PRD.md
       |
       v
Requirement Extraction
       |
       v
Gemini Acceptance-Criteria Enrichment
       |
       v
Traceable Scenario Plan
       |
       v
Playwright Browser Execution
       |
       v
Deterministic State Verification
       |
       v
Evidence Collection
       |
       v
QA Audit Report + Cost Breakdown
```

### Technology Stack

- **Python:** Agent implementation and orchestration
- **Gemini 3.5 Flash-Lite:** Requirement interpretation
- **Playwright:** Real browser automation
- **Pydantic:** Typed schemas and structured results
- **PostgreSQL / Docker:** Deterministic test-state reset
- **React / FastAPI:** Supplied DemoBank application
- **Pytest:** Deterministic oracle unit tests

### Verification Strategy

The system uses deterministic oracles to verify application behavior, including UI-to-API balance agreement, protected-route access, inclusive date filtering, and invalid-transfer rejection with no unintended state changes.

Execution errors are distinguished from application defects. Requirements without sufficient evidence receive an **UNVERIFIED** verdict.

## LLM Cost Breakdown

| Metric | Demonstrated Run |
|---|---:|
| Model | Gemini 3.5 Flash-Lite |
| LLM API calls | 1 |
| Input tokens | 1,378 |
| Output tokens | 2,522 |
| Estimated paid-tier equivalent | $0.0067184 |
| Deterministic replay LLM cost | $0 |

The dollar amount is a configured pricing estimate, not a confirmed billing charge.

## Run the Project

See [Agent Architecture and Setup](agent/README.md) for the complete installation instructions.

Start DemoBank's PostgreSQL database, FastAPI backend, and React frontend first.

From the `agent/` directory, install dependencies:

```powershell
py -m pip install -r requirements.txt
py -m playwright install chromium
```

Run without an LLM:

```powershell
py -m demobank_qa --no-llm --headed
```

Run with Gemini requirement enrichment:

```powershell
py -m demobank_qa --model gemini-3.5-flash-lite --headed --out qa_output_submission
```

Configure `GEMINI_API_KEY` locally in `agent/.env` for Gemini access. Never commit the API key.

## QA Audit and Evidence

- [Final QA Audit Report](agent/qa_output_submission/report.md)
- [JSON Results](agent/qa_output_submission/report.json)
- [HTML Report Source](agent/qa_output_submission/report.html)
- [Agent Source Code](agent/demobank_qa/)
- [Product Requirements](test-website/PRD.md)
- [Setup and Architecture](agent/README.md)

## Limitations

This hackathon MVP supports six predefined browser verification scenarios covering five distinct requirements. Other requirements remain UNVERIFIED.

Gemini enriches requirement interpretation, but the runnable scenario library is predefined rather than automatically generated for arbitrary websites.

The executor uses deterministic verification and does not implement a general-purpose LLM recovery or replanning loop.

## Acknowledgments

The DemoBank target application and hackathon specification originate from the [Community Dreams Foundation Agentic QA Hackathon Kit](https://github.com/Community-Dreams-Foundation/Agentic-QA-Hackathon-kit).

All banking data used for testing is synthetic.
