"""Explicit, inspectable scenario plan. Unimplemented PRD clauses stay UNVERIFIED."""
from .models import Requirement, Scenario

SCENARIOS = [
    ('login','normal','The landing page provides a clearly labeled',
     'Demo session begins without password; dashboard and active user visible.',
     'authenticated_dashboard', ['Navigate to landing','Click Enter Demo','Assert dashboard and active customer']),
    ('dashboard','normal','Each account displays a readable account name',
     'Both displayed account balances/identities agree with authenticated API and use USD format.',
     'account_values', ['Enter Demo','Read two account cards','Compare rendered balances with API']),
    ('logout','negative','Logging out returns the user to the landing page',
     'Protected route after logout redirects to landing/access-required.',
     'session_gate', ['Enter Demo','Click Log out','Navigate directly to /dashboard','Assert access blocked']),
    ('single_day','edge','The start and end dates are inclusive',
     'History filtered to a one-day range includes a known transaction on that day.',
     'inclusive_date', ['Enter Demo','Get an existing transaction and its Pacific date','Apply same-day start/end filters','Assert transaction is present']),
    ('zero','negative','Amount must be a positive number greater than zero',
     'Zero transfer rejected with clear feedback; balances and transaction IDs unchanged.',
     'reject_no_side_effect', ['Enter Demo','Read balances/transactions','Submit transfer amount 0','Assert rejection and no state change']),
    ('precision','edge','Amount must be a positive number greater than zero',
     'Three-decimal transfer rejected; balances and transaction IDs unchanged.',
     'reject_no_side_effect', ['Enter Demo','Read balances/transactions','Submit transfer amount 1.234','Assert rejection and no state change']),
]

def compile_plan(requirements: list[Requirement]) -> list[Scenario]:
    scenarios=[]
    for name,kind,anchor,desc,oracle,steps in SCENARIOS:
        matches=[r for r in requirements if r.source_quote.startswith(anchor)]
        if len(matches) != 1:
            raise ValueError(f'PRD clause missing/ambiguous: {anchor!r}')
        scenarios.append(Scenario(id=name,requirement_id=matches[0].id,kind=kind,description=desc,oracle=oracle,steps=steps))
    return scenarios
