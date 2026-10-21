from demobank_qa.oracles import compare_money,inclusive_boundary,rejected_without_side_effects,aggregate
from demobank_qa.spec import clauses_from_prd
from demobank_qa.plan import compile_plan
from pathlib import Path


def test_money_oracle():
    assert compare_money('$4,369.75 USD','4369.75')=='PASSED'
    assert compare_money('$4,369.74 USD','4369.75')=='FAILED'
    assert compare_money('$4,369.7 USD','4369.75')=='FAILED'


def test_no_side_effects():
    base={'a':'100.00','b':'200.00'}
    assert rejected_without_side_effects(error_visible=True,success_visible=False,
        accounts_before=base,accounts_after=base,transactions_before={'x'},transactions_after={'x'})=='PASSED'
    assert rejected_without_side_effects(error_visible=True,success_visible=False,
        accounts_before=base,accounts_after={'a':'99.00','b':'201.00'},transactions_before={'x'},transactions_after={'x','y'})=='FAILED'


def test_inclusive():
    assert inclusive_boundary({'a','b'},{'a','b','c'})=='PASSED'
    assert inclusive_boundary({'a'},{'b'})=='FAILED'
    assert inclusive_boundary(set(),set())=='UNVERIFIED'


def test_no_false_failures():
    assert aggregate([])=='UNVERIFIED'
    assert aggregate(['PASSED','UNVERIFIED'])=='UNVERIFIED'
    assert aggregate(['PASSED','FAILED'])=='FAILED'


def test_live_prd_mapping():
    prd=Path(__file__).resolve().parents[2]/'test-website'/'PRD.md'
    if prd.exists():
        reqs=clauses_from_prd(prd)
        assert len(reqs)>=15
        scenarios=compile_plan(reqs)
        assert {s.id for s in scenarios}=={'login','dashboard','logout','single_day','zero','precision'}
        assert len({s.requirement_id for s in scenarios})==5
