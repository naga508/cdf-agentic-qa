"""Extract traceable PRD clauses and optionally enrich them with an LLM."""
import json
import re
from pathlib import Path
from .models import Requirement


def clauses_from_prd(path: Path) -> list[Requirement]:
    text = path.read_text(encoding='utf-8')
    section = 'General'
    requirements = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith('## '):
            section = s[3:].strip()
        if section.lower() in {'out of scope', 'requirement coverage expectations', 'purpose', 'seed data expectations'}:
            continue
        if not s.startswith('- '):
            continue
        quote = s[2:].strip()
        if quote:
            requirements.append(Requirement(
                id=f'PRD-{len(requirements)+1:03d}',
                section=section,
                source_quote=quote,
                description=re.sub(r'\*\*|`', '', quote),
                acceptance_criteria=[quote],
                preconditions=[],
            ))
    if not requirements:
        raise ValueError(f'No PRD requirement clauses found in {path}')
    return requirements


def enrich_with_llm(requirements: list[Requirement], model: str, meter) -> tuple[list[Requirement],str]:
    import os
    if not os.getenv('GEMINI_API_KEY'):
        return requirements, 'deterministic PRD parser (GEMINI_API_KEY absent)'
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
        prompt = (
            'You are a requirements analyst. For each exact ID below, return one concise '
            'acceptance criterion (directly supported by its source quote) and one '
            'precondition. Never invent new app behavior. Return a JSON array with '
            'objects {"id":"PRD-001","acceptance_criteria":["..."],"preconditions":["..."]}. '
            'Preserve IDs. Requirements:\n' + json.dumps([{'id': r.id,'source_quote':r.source_quote} for r in requirements])
        )
        response = client.models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0),
        )
        usage = getattr(response,'usage_metadata',None)
        meter.add('spec_ingestion',model,
                  getattr(usage,'prompt_token_count',0) or 0,
                  getattr(usage,'candidates_token_count',0) or 0)
        raw = json.loads(response.text)
        by_id = {item['id']: item for item in raw if isinstance(item,dict) and 'id' in item}
        for r in requirements:
            item = by_id.get(r.id)
            if item:
                criteria = item.get('acceptance_criteria')
                if isinstance(criteria,list) and all(isinstance(x,str) for x in criteria) and criteria:
                    r.acceptance_criteria = criteria
                preconditions = item.get('preconditions')
                if isinstance(preconditions,list) and all(isinstance(x,str) for x in preconditions):
                    r.preconditions = preconditions
        return requirements, f'Gemini {model} (source quotes preserved)'
    except Exception as exc:
        # An unavailable LLM must never be disguised as a successful model extraction.
        return requirements, f'deterministic fallback: {type(exc).__name__}: {str(exc)[:160]}'
