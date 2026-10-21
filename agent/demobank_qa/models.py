from typing import Literal
from pydantic import BaseModel, Field

Verdict = Literal['PASSED','FAILED','UNVERIFIED']
ExecutionStatus = Literal['ok','recovered','blocked']

class Requirement(BaseModel):
    id: str
    section: str
    source_quote: str
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)

class Scenario(BaseModel):
    id: str
    requirement_id: str
    kind: Literal['normal','negative','edge']
    description: str
    oracle: str
    steps: list[str]

class CheckResult(BaseModel):
    scenario_id: str
    requirement_id: str
    verdict: Verdict
    execution_status: ExecutionStatus = 'ok'
    expected: str
    observed: str
    rationale: str
    screenshot: str | None = None
    dom_snapshot: str | None = None
    reproduction_steps: list[str] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)
