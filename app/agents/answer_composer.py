"""Agent 7: Answer Composer - generates the answer via the Gemini gateway."""
from app.core.logger import get_logger
from app.schemas import PipelineContext
from app.services.gemini_service import get_gemini_service
from app.utils.prompt_utils import build_user_prompt

logger = get_logger(__name__)


class AnswerComposerAgent:
    name = "answer_composer"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.evidence_pack:
            ctx.draft_answer = (
                "I could not find any policy-approved context to answer this "
                "question."
            )
            ctx.status = "no_context"
            ctx.log(self.name, "no approved evidence; skipped Gemini call")
            return ctx

        prompt = build_user_prompt(ctx.query, ctx.evidence_pack)
        try:
            answer = get_gemini_service().generate(prompt)
            ctx.draft_answer = answer or "The model returned an empty response."
            ctx.log(
                self.name,
                "draft answer generated via Gemini",
                {"evidence_items": len(ctx.evidence_pack)},
            )
        except Exception as exc:
            logger.error("Gemini generation failed: %s", exc)
            ctx.draft_answer = "Answer generation is currently unavailable."
            ctx.status = "error"
            ctx.log(self.name, f"gemini error: {exc}")
        return ctx
