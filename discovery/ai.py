"""Claude-powered synthesis of customer interviews.

Only used when an ANTHROPIC_API_KEY is available. The prompt asks Claude to
behave like a venture coach: separate evidence from assumptions, quote the
customer, and never invent findings that aren't in the transcripts.
"""
import json
import os
from typing import Dict, List

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You are a Lean Startup coach reviewing a student venture team's customer
discovery interviews. Your job is to help the team see what their evidence actually
shows - not to cheer them on and not to design the product for them.

Rules:
- Only use what is in the transcripts. Every pain point must include a direct quote.
- Classify each finding: "behaviour" (something the customer did or spent), "opinion"
  (a belief or prediction about the future), or "compliment" (praise for the idea).
  Only "behaviour" counts as strong evidence.
- Name the team's assumptions that the interviews support, contradict, or leave untested.
- Suggest next interview questions about past behaviour, never hypotheticals.
- Ask coaching questions; don't hand the team a solution."""

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "pain_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pain": {"type": "string"},
                    "quote": {"type": "string"},
                    "interview": {"type": "string"},
                    "evidence_type": {"type": "string",
                                      "enum": ["behaviour", "opinion", "compliment"]},
                    "interviews_mentioning": {"type": "integer"},
                },
                "required": ["pain", "quote", "interview", "evidence_type",
                             "interviews_mentioning"],
                "additionalProperties": False,
            },
        },
        "assumptions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "assumption": {"type": "string"},
                    "status": {"type": "string",
                               "enum": ["supported", "contradicted", "untested"]},
                    "why": {"type": "string"},
                },
                "required": ["assumption", "status", "why"],
                "additionalProperties": False,
            },
        },
        "riskiest_assumption": {"type": "string"},
        "cheapest_next_test": {"type": "string"},
        "next_interview_questions": {"type": "array", "items": {"type": "string"}},
        "coaching_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "pain_points", "assumptions", "riskiest_assumption",
                 "cheapest_next_test", "next_interview_questions", "coaching_questions"],
    "additionalProperties": False,
}


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def synthesize(interviews: Dict[str, str], hypothesis: str) -> Dict:
    import anthropic  # imported lazily so offline mode needs no SDK

    blocks: List[str] = []
    for name, text in interviews.items():
        blocks.append(f'<interview name="{name}">\n{text}\n</interview>')
    user = (f"The team's problem hypothesis:\n{hypothesis or '(not provided)'}\n\n"
            + "\n\n".join(blocks))

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
        betas=["server-side-fallback-2026-07-01"],
        extra_body={
            "output_config": {"effort": "medium",
                              "format": {"type": "json_schema", "schema": SCHEMA}},
            "fallbacks": "default",
        },
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to analyse these transcripts.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("The analysis was cut off. Try fewer or shorter transcripts.")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
