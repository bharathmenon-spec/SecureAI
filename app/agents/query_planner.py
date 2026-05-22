"""Agent 2: Query Planner - decomposes the query into retrieval subqueries."""
import re

from app.schemas import PipelineContext

_SPLIT_RE = re.compile(r"\s+and\s+|\s+versus\s+|\s+vs\.?\s+|;|\?", re.IGNORECASE)


class QueryPlannerAgent:
    name = "query_planner"
    max_subqueries = 5

    def run(self, ctx: PipelineContext) -> PipelineContext:
        subqueries = [ctx.query.strip()]
        for part in _SPLIT_RE.split(ctx.query):
            part = part.strip(" .,")
            if len(part.split()) >= 3:
                subqueries.append(part)

        seen = set()
        unique = []
        for sub in subqueries:
            key = sub.lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(sub)

        ctx.subqueries = unique[: self.max_subqueries]
        ctx.retrieval_strategy = (
            "multi-query" if len(ctx.subqueries) > 1 else "single"
        )
        ctx.log(
            self.name,
            f"planned {len(ctx.subqueries)} subqueries ({ctx.retrieval_strategy})",
            {"subqueries": ctx.subqueries},
        )
        return ctx
