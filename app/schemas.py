"""Internal pipeline data structures and API request models."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Internal (non-serialized) pipeline structures
# --------------------------------------------------------------------------
@dataclass
class UserContext:
    user_id: str
    username: str
    role: str
    department: str
    clearance_level: str


@dataclass
class PipelineContext:
    """Mutable state carried through the multi-agent query pipeline."""

    request_id: str
    user: UserContext
    query: str

    intent: str = "unknown"
    risk_level: str = "low"
    routing: str = "full_pipeline"

    subqueries: List[str] = field(default_factory=list)
    retrieval_strategy: str = "single"

    guard: Dict[str, Any] = field(default_factory=dict)

    candidates: List[Dict[str, Any]] = field(default_factory=list)
    reranked: List[Dict[str, Any]] = field(default_factory=list)
    policy_decisions: List[Dict[str, Any]] = field(default_factory=list)
    approved_chunks: List[Dict[str, Any]] = field(default_factory=list)
    evidence_pack: List[Dict[str, Any]] = field(default_factory=list)

    draft_answer: str = ""
    verification: Dict[str, Any] = field(default_factory=dict)
    detok_log: List[Dict[str, Any]] = field(default_factory=list)
    final_answer: str = ""
    status: str = "ok"

    trace: List[Dict[str, Any]] = field(default_factory=list)

    def log(self, agent: str, message: str, data: Optional[dict] = None) -> None:
        self.trace.append(
            {"agent": agent, "message": message, "data": data or {}}
        )


# --------------------------------------------------------------------------
# API request models
# --------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)


class UserRoleRequest(BaseModel):
    username: str
    role: str
    department: str = "General"
    clearance_level: Optional[str] = None
    user_id: Optional[str] = None


class PolicyRuleRequest(BaseModel):
    name: str
    doc_sensitivity: str
    allowed_roles: List[str]
    redact_roles: List[str] = Field(default_factory=list)
