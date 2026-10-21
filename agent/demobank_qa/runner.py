import argparse
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

from .checks import execute
from .costs import CostMeter
from .driver import Driver
from .models import CheckResult
from .plan import compile_plan
from .report import render
from .reset import reset_seed
from .spec import clauses_from_prd,enrich_with_llm


def main(argv=None):
    parser=argparse.ArgumentParser(description='Spec-driven, evidence-backed DemoBank QA')
    parser.add_argument('--prd',default='../test-website/PRD.md')
    parser.add_argument('--base-url',default='http://localhost:5173')
    parser.add_argument('--api-url',default='http://localhost:8000',help='Or "none" to disable API corroboration')
    parser.add_argument('--database-dir',default='../test-website/database')
    parser.add_argument('--out',default='qa_output')
    parser.add_argument('--model',default='gemini-3.5-flash-lite')
    parser.add_argument('--no-llm',action='store_true',help='Use only deterministic PRD parser')
    parser.add_argument('--headed',action='store_true',help='Show live Chromium UI')
    parser.add_argument('--skip-reset',action='store_true',help='Skip local DB reset (not fully reproducible)')
    parser.add_argument('--dry-run',action='store_true',help='Compile PRD and scenario plan without browser')
    parser.add_argument('--only',default='',help='Comma-separated IDs: login,dashboard,logout,single_day,zero,precision')
    args=parser.parse_args(argv)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    out=Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    meter=CostMeter()
    reqs=clauses_from_prd(Path(args.prd))
    if args.no_llm:
        mode='deterministic PRD parser (--no-llm)'
    else:
        reqs,mode=enrich_with_llm(reqs,args.model,meter)
    (out/'requirements.json').write_text(json.dumps([r.model_dump() for r in reqs],indent=2),encoding='utf-8')
    plan=compile_plan(reqs)
    if args.only:
        selected={i.strip() for i in args.only.split(',')}
        plan=[s for s in plan if s.id in selected]
        if not plan:
            raise SystemExit('No matching scenario IDs. Options: login,dashboard,logout,single_day,zero,precision')
    (out/'scenario_plan.json').write_text(json.dumps([s.model_dump() for s in plan],indent=2),encoding='utf-8')
    results=[]
    resets=[]
    if args.dry_run:
        print(f'PRD: {len(reqs)} clauses; planned scenarios: {len(plan)}; extraction: {mode}')
        print('Plan:',', '.join(s.id for s in plan))
        print('Saved:',out/'requirements.json',out/'scenario_plan.json')
        return 0
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=not args.headed)
        try:
            for s in plan:
                print(f'RUN {s.id} ({s.kind}) — {s.requirement_id}',flush=True)
                if not args.skip_reset:
                    try:
                        reset_seed(Path(args.database_dir))
                        resets.append(f'{s.id}: migrations+seed reset OK')
                    except Exception as exc:
                        msg=f'Cannot reliably execute without deterministic DB reset: {type(exc).__name__}: {str(exc)[:200]}'
                        resets.append(f'{s.id}: RESET BLOCKED — {msg}')
                        results.append(CheckResult(scenario_id=s.id,requirement_id=s.requirement_id,
                            verdict='UNVERIFIED', execution_status='blocked', expected=s.description,
                            observed='Reset unavailable',rationale=msg,reproduction_steps=s.steps))
                        continue
                else:
                    resets.append(f'{s.id}: reset skipped by operator; initial data not guaranteed')
                context=browser.new_context(viewport={'width':1280,'height':800})
                page=context.new_page()
                driver=Driver(page,args.base_url,None if args.api_url.lower()=='none' else args.api_url)
                try:
                    result=execute(s,driver)
                except Exception as exc:
                    result=CheckResult(scenario_id=s.id,requirement_id=s.requirement_id,
                        verdict='UNVERIFIED',execution_status='blocked',expected=s.description,
                        observed=f'{type(exc).__name__}: {str(exc)[:500]}',
                        rationale='Execution/infrastructure failure is not evidence of a product defect.',
                        reproduction_steps=s.steps,console_errors=driver.logs[-8:])
                try:
                    result.screenshot=driver.screenshot(out,s.id)
                    result.dom_snapshot=driver.dom()
                except Exception:
                    pass
                results.append(result)
                context.close()
                print(f'  => {result.verdict} ({result.execution_status})',flush=True)
        finally:
            browser.close()
    report=render(reqs,results,meter,out,mode,resets)
    print('RESULTS',report['summary'])
    print('FILES',out/'report.html',out/'report.md',out/'report.json')
    print('COST',report['cost'])
    return 0
