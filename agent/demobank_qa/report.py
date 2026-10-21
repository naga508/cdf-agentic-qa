"""Evidence-backed report in JSON, Markdown and HTML."""
import html
import json
from collections import defaultdict,Counter
from datetime import datetime, timezone
from pathlib import Path
from .models import Requirement,CheckResult
from .oracles import aggregate


def requirement_verdicts(requirements: list[Requirement],results: list[CheckResult]):
    by_req=defaultdict(list)
    for result in results: by_req[result.requirement_id].append(result)
    output=[]
    for req in requirements:
        group=by_req[req.id]
        verdict=aggregate([r.verdict for r in group]) if group else 'UNVERIFIED'
        output.append({'id':req.id,'section':req.section,'source_quote':req.source_quote,
                       'verdict':verdict,'scenario_ids':[r.scenario_id for r in group],
                       'note':'No implemented verification scenario yet.' if not group else ''})
    return output


def render(requirements: list[Requirement],results: list[CheckResult],cost, out: Path,extraction_mode: str, reset_log: list[str]):
    out.mkdir(parents=True,exist_ok=True)
    req_rows=requirement_verdicts(requirements,results)
    counts=dict(Counter(row['verdict'] for row in req_rows))
    payload={
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'extraction_mode':extraction_mode,
        'summary':{'total_requirements':len(requirements),'checked_scenarios':len(results),
                   'passed_requirements':counts.get('PASSED',0),'failed_requirements':counts.get('FAILED',0),
                   'unverified_requirements':counts.get('UNVERIFIED',0)},
        'requirements':[r.model_dump() for r in requirements],
        'traceability':req_rows,
        'results':[r.model_dump() for r in results],
        'reset_log':reset_log,
        'cost':cost.summary(),
    }
    (out/'report.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    lines=['# DemoBank QA Audit','',f"Generated: {payload['generated_at']}",'',
           f"**Verdicts:** {payload['summary']['passed_requirements']} PASSED / {payload['summary']['failed_requirements']} FAILED / {payload['summary']['unverified_requirements']} UNVERIFIED across {len(requirements)} traceable PRD clauses.",
           '',f"**Ingestion:** {extraction_mode}",'',
           'Execution blocked ≠ application failed. Unexecuted requirements stay UNVERIFIED.','',
           '## Requirement traceability','',
           '| PRD ID | Section | Verdict | Scenario(s) |', '|---|---|---|---|']
    for r in req_rows:
        lines.append(f"| {r['id']} | {r['section']} | **{r['verdict']}** | {', '.join(r['scenario_ids']) or 'not yet implemented'} |")
    lines+=['','## Scenario-level evidence','']
    by_id={r.id:r for r in requirements}
    for r in results:
        req=by_id[r.requirement_id]
        lines.extend([
            f'### {r.scenario_id} — {r.verdict}',
            f'- **Requirement:** {req.id} ({req.section})',
            f'- **PRD quote:** {req.source_quote}',
            f'- **Execution:** {r.execution_status}',
            f'- **Expected:** {r.expected}',
            f'- **Observed:** {r.observed}',
            f'- **Rationale:** {r.rationale}',
            '- **Reproduction steps:**',
        ])
        lines.extend([f'  {i}. {s}' for i,s in enumerate(r.reproduction_steps,1)])
        if r.screenshot:
            lines.append(f'- **Screenshot (at assertion):** ![Evidence {r.scenario_id}]({r.screenshot})')
        if r.dom_snapshot:
            lines += [f'- **DOM excerpt:** `{r.dom_snapshot[:800].replace(chr(10)," ")}`']
        lines.append('')
    c=payload['cost']
    lines+=['## API / token cost','',f"- LLM calls: {c['calls']}",f"- Input tokens: {c['input_tokens']}",
            f"- Output tokens: {c['output_tokens']}",
            f"- Estimated API spend (USD): {c['estimated_api_usd'] if c['estimated_api_usd'] is not None else 'unavailable — configure pricing'}",
            '- Replay/verification LLM calls: 0',f"- Note: {c['pricing_note']}",'','## Reset log','']
    lines.extend([f'- {x}' for x in reset_log] or ['- No reset information'])
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # Self-contained readable HTML, no extra markdown package needed.
    rows=[]
    for r in req_rows:
        rows.append(f"<tr><td>{html.escape(r['id'])}</td><td>{html.escape(r['section'])}</td><td><strong>{html.escape(r['verdict'])}</strong></td><td>{html.escape(r['source_quote'])}</td></tr>")
    details=[]
    for r in results:
        req=by_id[r.requirement_id]
        shot=f'<img style="max-width:100%;border:1px solid #ddd" src="{html.escape(r.screenshot)}" />' if r.screenshot else ''
        details.append(f'<section><h3>{html.escape(r.scenario_id)} — {r.verdict}</h3><blockquote>{html.escape(req.source_quote)}</blockquote>'
                      f'<p><b>Expected:</b> {html.escape(r.expected)}</p><p><b>Observed:</b> {html.escape(r.observed)}</p>'
                      f'<p><b>Rationale:</b> {html.escape(r.rationale)}</p>'
                      f'<ol>{"".join("<li>"+html.escape(s)+"</li>" for s in r.reproduction_steps)}</ol>{shot}</section>')
    document=f'''<!doctype html><html lang="en"><meta charset="UTF-8"/><title>DemoBank QA Audit</title>
    <style>body{{font:15px system-ui,sans-serif;max-width:1100px;margin:30px auto;padding:0 20px;line-height:1.5;color:#1b2533}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d4d9e0;padding:8px;text-align:left;vertical-align:top}}th{{background:#f2f5f9}}section{{border-bottom:1px solid #ccd;margin:28px 0;padding-bottom:22px}}blockquote{{background:#f7f9fb;padding:12px}}</style>
    <h1>DemoBank — Evidence-backed QA Audit</h1><p>{html.escape(str(payload['summary']))}</p>
    <p>PRD source preserved. Unexecuted checks are UNVERIFIED, not failed.</p>
    <h2>Traceability matrix</h2><table><tr><th>PRD ID</th><th>Section</th><th>Verdict</th><th>Source quote</th></tr>{''.join(rows)}</table>
    <h2>Evidence and reproduction</h2>{''.join(details)}<h2>Token / cost</h2><pre>{html.escape(json.dumps(c,indent=2))}</pre></html>'''
    (out/'report.html').write_text(document,encoding='utf-8')
    return payload
