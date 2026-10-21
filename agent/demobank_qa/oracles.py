"""Pure, deterministic checks; browser actions alone cannot yield PASSED."""
from decimal import Decimal, InvalidOperation
from .models import Verdict


def compare_money(displayed: str, expected: str) -> Verdict:
    import re
    match = re.search(r'\$\s*(-?[\d,]+\.\d{2})(?!\d)', displayed)
    if not match:
        return 'FAILED'
    try:
        actual = Decimal(match.group(1).replace(',', ''))
        return 'PASSED' if actual == Decimal(expected) else 'FAILED'
    except (InvalidOperation, TypeError):
        return 'UNVERIFIED'


def rejected_without_side_effects(
    *, error_visible: bool, success_visible: bool,
    accounts_before: dict[str, str], accounts_after: dict[str, str],
    transactions_before: set[str], transactions_after: set[str],
) -> Verdict:
    if accounts_before.keys() != accounts_after.keys():
        return 'UNVERIFIED'
    if success_visible or accounts_before != accounts_after or transactions_before != transactions_after:
        return 'FAILED'
    return 'PASSED' if error_visible else 'FAILED'


def inclusive_boundary(expected_ids: set[str], observed_ids: set[str]) -> Verdict:
    if not expected_ids:
        return 'UNVERIFIED'
    return 'PASSED' if expected_ids <= observed_ids else 'FAILED'


def aggregate(verdicts: list[Verdict]) -> Verdict:
    if not verdicts:
        return 'UNVERIFIED'
    if 'FAILED' in verdicts:
        return 'FAILED'
    if 'UNVERIFIED' in verdicts:
        return 'UNVERIFIED'
    return 'PASSED'
