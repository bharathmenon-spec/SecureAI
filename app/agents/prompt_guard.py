"""Agent 10: Adversarial Prompt Guard - detects injection / jailbreak attempts.

``scan_for_injection`` is reused by the Policy Agent to screen retrieved chunk
text and by the Answer Verifier to screen model output.
"""
import re
from typing import Dict

from app.schemas import PipelineContext

_INJECTION_PATTERNS = [
    (re.compile(r"ignore\s+(all\s+|the\s+)?(previous|prior|above)", re.I),
     "instruction override"),
    (re.compile(r"disregard\s+(all\s+|the\s+)?(previous|prior|above|instructions)",
                re.I), "instruction override"),
    (re.compile(r"reveal\s+(the\s+)?(system|hidden|secret|raw|unmasked|original)",
                re.I), "exfiltration attempt"),
    (re.compile(r"show\s+(me\s+)?(the\s+)?(system\s+prompt|hidden|raw\s+value)",
                re.I), "prompt disclosure"),
    (re.compile(r"print\s+(the\s+)?(full|entire|whole)?\s*(unmasked|raw|original)",
                re.I), "raw disclosure"),
    (re.compile(r"un-?mask|de-?tokeni[sz]e|decode\s+the\s+token", re.I),
     "token release attempt"),
    (re.compile(r"(developer|admin|god)\s+mode", re.I), "privilege escalation"),
    (re.compile(r"jailbreak|do\s+anything\s+now|\bDAN\b", re.I), "jailbreak"),
    (re.compile(r"you\s+are\s+now\s+(a|an|the)?", re.I), "role reassignment"),
    (re.compile(r"new\s+instructions\s*:", re.I), "instruction override"),
]


def scan_for_injection(text: str) -> Dict:
    """Return injection risk metadata for an arbitrary text fragment."""
    segments = []
    reasons = set()
    for pattern, reason in _INJECTION_PATTERNS:
        for match in pattern.finditer(text or ""):
            segments.append(match.group(0).strip())
            reasons.add(reason)
    return {
        "flagged": bool(segments),
        "risk_score": round(min(1.0, 0.34 * len(segments)), 2),
        "segments": segments,
        "reasons": sorted(reasons),
    }


class PromptGuardAgent:
    name = "prompt_guard"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        result = scan_for_injection(ctx.query)
        ctx.guard = result
        if result["flagged"]:
            ctx.risk_level = "high"
        ctx.log(
            self.name,
            "injection detected" if result["flagged"] else "query clean",
            result,
        )
        return ctx
