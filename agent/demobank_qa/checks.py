"""Scenarios: UI is the primary surface, API state corroborates claims."""
import re
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from .models import CheckResult, Scenario, Verdict
from .driver import Driver
from .oracles import compare_money, rejected_without_side_effects, inclusive_boundary


def balances_and_transactions(driver: Driver):
    accounts=driver.api('/api/accounts')['accounts']
    txns=driver.api('/api/transactions')['transactions']
    return ({a['id']:a['balance'] for a in accounts}, {t['id'] for t in txns},accounts,txns)


def execute(scenario: Scenario, driver: Driver) -> CheckResult:
    method=CHECKS[scenario.id]
    verdict,expected,observed,rationale=method(driver)
    return CheckResult(
        scenario_id=scenario.id,requirement_id=scenario.requirement_id,
        verdict=verdict, execution_status='ok', expected=expected,
        observed=observed,rationale=rationale,
        reproduction_steps=scenario.steps, console_errors=driver.logs[-8:]
    )


def login(driver: Driver):
    driver.enter_demo()
    signed=driver.page.get_by_test_id('active-customer').inner_text().strip()
    present=driver.page.locator('[data-testid="account-card"]').count()
    ok=driver.page.url.endswith('/dashboard') and signed and present==2
    return ('PASSED' if ok else 'FAILED',
            'Dashboard with active customer and two account cards, no password',
            f'URL={driver.page.url}, active={signed}, cards={present}',
            'Verified resulting dashboard state after Enter Demo.' if ok else 'Observed dashboard state differs from PRD.')


def dashboard(driver: Driver):
    driver.enter_demo()
    accounts=driver.api('/api/accounts')['accounts']
    cards=driver.page.locator('[data-testid="account-card"]')
    cards.first.wait_for(timeout=12000)
    comparisons=[]
    if len(accounts)!=2:
        return ('UNVERIFIED','One checking + one savings in API',str(accounts),'Unexpected seed data; cannot establish baseline.')
    for account in accounts:
        card=cards.filter(has=driver.page.get_by_role('heading',name=account['name']))
        if card.count()!=1:
            comparisons.append({'name':account['name'],'match':False,'observed':'account card missing'})
            continue
        c=card.first
        visible_money=c.locator('[data-testid="account-balance"]').inner_text()
        visible_mask = c.locator(".account-card__number").evaluate(
           """element => Array.from(element.childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE)
                .map(node => node.textContent)
                .join("")
                .trim()"""
        )

        comparisons.append({
            'name':account['name'],'expected_balance':account['balance'],
            'shown_balance':visible_money,'expected_mask':account['masked_number'],
            'shown_mask':visible_mask,
            'match':compare_money(visible_money,account['balance'])=='PASSED'
                    and visible_mask.strip()==account['masked_number']
                    and account['currency']=='USD',
        })
    ok=len(comparisons)==2 and all(x['match'] for x in comparisons)
    return ('PASSED' if ok else 'FAILED',
            'Both account names, masked identifiers, and two-decimal USD balances match authenticated API',
            str(comparisons),
            'UI values checked against live API values; mismatched or missing card constitutes defect.')


def logout(driver: Driver):
    driver.enter_demo()
    driver.page.get_by_role('button',name='Log out').click(timeout=8000)
    driver.page.wait_for_url(driver.base_url+'/',timeout=10000)
    driver.visit('/dashboard')
    driver.page.get_by_role('button',name='Enter Demo').wait_for(timeout=10000)
    blocked=driver.page.url.rstrip('/')==driver.base_url
    return ('PASSED' if blocked else 'FAILED',
            'After logout, direct /dashboard navigation is blocked',
            f'Final URL={driver.page.url}, Enter Demo visible={blocked}',
            'Direct protected-route navigation checked after logout, not just logout click.')


def single_day(driver: Driver):
    driver.enter_demo()
    _,_,_,txs=balances_and_transactions(driver)
    if not txs:
        return ('UNVERIFIED','Seed has at least one dated transaction','No transactions from API','No usable baseline for date boundary.')
    # One seeded completed transaction is enough. We derive date from actual timestamp.
    chosen=next((t for t in txs if t.get('status')=='completed'),txs[0])
    local_date=datetime.fromisoformat(chosen['occurred_at'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat()
    expected={t['id'] for t in txs if datetime.fromisoformat(t['occurred_at'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat()==local_date}
    driver.page.get_by_role('link',name='Transactions',exact=True).click()
    driver.page.get_by_role('heading',name='Transactions',exact=True).wait_for()
    driver.page.get_by_label('Start date').fill(local_date)
    driver.page.get_by_label('End date').fill(local_date)
    # Wait specifically for the filtered API response, so stale pre-filter rows
    # cannot produce a false PASSED verdict.
    with driver.page.expect_response(
        lambda response: '/api/transactions?' in response.url
        and 'start_date=' in response.url and 'end_date=' in response.url,
        timeout=15000,
    ):
        driver.page.get_by_role('button',name='Apply filters').click()
    driver.page.wait_for_url(re.compile(r'start_date='),timeout=10000)
    # Observe the post-response UI results/empty state (no fixed sleeps).
    driver.page.locator('[data-testid="transaction-row"], .state--empty, .state--error, [data-testid="result-count"]').first.wait_for(timeout=12000)
    visible=set(driver.page.locator('[data-testid="transaction-row"]').evaluate_all('(nodes) => nodes.map(n => n.getAttribute("data-transaction-id"))'))
    verdict=inclusive_boundary(expected,visible)
    return (verdict,
            f'For inclusive date {local_date}, visible transaction IDs include {sorted(expected)}',
            f'Visible IDs={sorted(visible)}; missing={sorted(expected-visible)}',
            'Expected IDs taken from unfiltered authenticated transaction data, not the broken date-filter response.')


def invalid_amount(driver: Driver,amount: str):
    driver.enter_demo()
    before,tx_before,accounts,_=balances_and_transactions(driver)
    if len(accounts)!=2:
        return ('UNVERIFIED','Two owned accounts','Unexpected account count','No reliable before snapshot.')
    driver.page.get_by_role('link',name='Transfer',exact=True).click()
    driver.page.get_by_role('heading',name='Transfer between your accounts').wait_for()
    driver.page.get_by_label('Amount (USD)').fill(amount)
    driver.page.get_by_role('button',name='Transfer funds',exact=True).click()
    # Let validation/fetch finish via state-based UI observation; no blind delay.
    feedback=driver.page.locator('.feedback-anchor [role="alert"], #amount-error, [role="alert"]')
    try:
        feedback.first.wait_for(state='visible',timeout=6000)
    except Exception:
        try: driver.page.wait_for_load_state('networkidle',timeout=3000)
        except Exception: pass
    before_submission_still_pending=driver.page.get_by_role('button',name='Submitting transfer…').count()>0
    if before_submission_still_pending:
        return ('UNVERIFIED','Rejected transfer settled','Submission still pending','Cannot assert no side effects before request completes.')
    after,tx_after,_,_=balances_and_transactions(driver)
    error_visible=driver.page.locator('#amount-error').count()>0 or driver.page.get_by_text('Transfer not completed').count()>0
    success_visible=driver.page.get_by_text('Transfer complete',exact=False).count()>0
    verdict=rejected_without_side_effects(
        error_visible=error_visible,success_visible=success_visible,
        accounts_before=before,accounts_after=after,
        transactions_before=tx_before,transactions_after=tx_after)
    return (verdict,
            f'Amount {amount!r} rejected with visible error; no balance change; no added transaction',
            f'error_visible={error_visible}, success_visible={success_visible}, '
            f'before_balances={before}, after_balances={after}, '
            f'added_txns={sorted(tx_after-tx_before)}, removed_txns={sorted(tx_before-tx_after)}',
            'Invalid transfer judged on UI feedback AND actual account/transaction state.')


def zero(driver: Driver): return invalid_amount(driver,'0')
def precision(driver: Driver): return invalid_amount(driver,'1.234')

CHECKS={'login':login,'dashboard':dashboard,'logout':logout,'single_day':single_day,'zero':zero,'precision':precision}
