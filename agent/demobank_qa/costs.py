"""Record observed tokens and transparent estimated API spend."""
import os
from pydantic import BaseModel, Field

class CostEntry(BaseModel):
    phase: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_usd: float | None = None

class CostMeter(BaseModel):
    entries: list[CostEntry] = Field(default_factory=list)
    def add(self,phase: str,model: str,input_tokens: int,output_tokens: int):
        input_rate = os.getenv('INPUT_USD_PER_M_TOKENS')
        output_rate = os.getenv('OUTPUT_USD_PER_M_TOKENS')
        cost = None
        if input_rate is not None and output_rate is not None:
            cost = round((input_tokens*float(input_rate) + output_tokens*float(output_rate))/1_000_000,8)
        self.entries.append(CostEntry(phase=phase, model=model, input_tokens=input_tokens,
                                      output_tokens=output_tokens, estimated_usd=cost))
    def summary(self):
        return {
            'calls':len(self.entries),
            'input_tokens':sum(e.input_tokens for e in self.entries),
            'output_tokens':sum(e.output_tokens for e in self.entries),
            'estimated_api_usd':round(sum(e.estimated_usd or 0 for e in self.entries),8) if all(e.estimated_usd is not None for e in self.entries) else None,
            'pricing_note':'Set INPUT_USD_PER_M_TOKENS and OUTPUT_USD_PER_M_TOKENS to estimate billed costs. Null means prices were not provided.',
            'entries':[e.model_dump() for e in self.entries],
            'replay_llm_cost_usd':0,
        }
