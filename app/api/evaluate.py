"""Sales conversation evaluation API endpoints."""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.constants import DEFAULT_MAX_SCORE, DEFAULT_SCORE, LLM_TEMPERATURE_ANALYSIS
from app.logging_config import get_logger
from app.utils import call_llm_json

router = APIRouter()
logger = get_logger("api.evaluate")

# =============================================================================
# CONSTANTS
# =============================================================================

METHODOLOGY_CRITERIA = {
    "SPIN": {
        "categories": [
            "Situation Questions",
            "Problem Questions",
            "Implication Questions",
            "Need-Payoff Questions",
        ],
        "max_per_category": DEFAULT_MAX_SCORE,
    },
    "MEDDIC": {
        "categories": [
            "Metrics",
            "Economic Buyer",
            "Decision Criteria",
            "Decision Process",
            "Identify Pain",
            "Champion",
        ],
        "max_per_category": DEFAULT_MAX_SCORE,
    },
    "Challenger": {
        "categories": [
            "Teaching",
            "Tailoring",
            "Taking Control",
        ],
        "max_per_category": DEFAULT_MAX_SCORE,
    },
    "Sandler": {
        "categories": [
            "Bonding & Rapport",
            "Up-Front Contract",
            "Pain Discovery",
            "Budget Discussion",
            "Decision Process",
            "Fulfillment",
            "Post-Sell",
        ],
        "max_per_category": DEFAULT_MAX_SCORE,
    },
}


def build_evaluation_prompt(methodology: str, categories: list[str], max_score: int) -> str:
    """Build the evaluation prompt for structured JSON output."""
    categories_json = ",\n        ".join([
        f'"{cat}": {{"score": 1-{max_score}, "feedback": "Specific feedback with examples"}}'
        for cat in categories
    ])

    return f"""You are an expert sales trainer evaluating conversations using the {methodology} methodology.

Analyze the provided sales conversation transcript and score it on each category.

For each category, provide:
- A score from 1-{max_score} (1=poor, {max_score}=excellent)
- Specific feedback with examples from the transcript

Also provide:
- An overall summary of the salesperson's performance
- 3-5 specific strengths observed (with examples from transcript)
- 3-5 areas for improvement with actionable suggestions

Be constructive but honest. Reference specific parts of the conversation.

Respond in this exact JSON format:
{{
    "scores": {{
        {categories_json}
    }},
    "summary": "Overall assessment of the conversation (2-3 paragraphs)",
    "strengths": [
        "Specific strength 1 with example from transcript",
        "Specific strength 2 with example from transcript",
        "Specific strength 3 with example from transcript"
    ],
    "areas_for_improvement": [
        "Area 1 with specific suggestion",
        "Area 2 with specific suggestion",
        "Area 3 with specific suggestion"
    ]
}}

Return ONLY the JSON, no other text."""


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class EvaluationRequest(BaseModel):
    transcript: str
    methodology: str = "SPIN"
    persona: str | None = None


class EvaluationScore(BaseModel):
    category: str
    score: int
    max_score: int
    feedback: str


class EvaluationResponse(BaseModel):
    overall_score: int
    max_score: int
    methodology: str
    scores: list[EvaluationScore]
    summary: str
    strengths: list[str]
    areas_for_improvement: list[str]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/conversation", response_model=EvaluationResponse)
async def evaluate_conversation(request: EvaluationRequest):
    """Evaluate a sales conversation against a methodology.

    Provides:
    - Per-category scores with specific feedback
    - Overall summary of performance
    - Identified strengths with examples
    - Areas for improvement with suggestions
    """
    start_time = time.perf_counter()

    methodology = request.methodology.upper()
    if methodology not in METHODOLOGY_CRITERIA:
        methodology = "SPIN"

    if not request.transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="Transcript cannot be empty",
        )

    logger.info(
        "Evaluation started",
        extra={"methodology": methodology, "transcript_length": len(request.transcript)},
    )

    criteria = METHODOLOGY_CRITERIA[methodology]

    # Build structured prompt for JSON output
    system_prompt = build_evaluation_prompt(
        methodology=methodology,
        categories=criteria["categories"],
        max_score=criteria["max_per_category"],
    )

    persona_context = f"\nThe prospect persona was: {request.persona}" if request.persona else ""

    messages = [
        {
            "role": "user",
            "content": f"""Evaluate this sales conversation using the {methodology} methodology.
{persona_context}

Transcript:
{request.transcript}""",
        }
    ]

    # Get LLM evaluation
    result = await call_llm_json(
        messages,
        system_prompt=system_prompt,
        temperature=LLM_TEMPERATURE_ANALYSIS,
        operation_name="Evaluation",
    )

    # Extract scores from parsed response
    scores = []
    scores_dict = result.get("scores", {})

    for category in criteria["categories"]:
        category_data = scores_dict.get(category, {})
        scores.append(
            EvaluationScore(
                category=category,
                score=category_data.get("score", DEFAULT_SCORE),
                max_score=criteria["max_per_category"],
                feedback=category_data.get("feedback", "No specific feedback provided"),
            )
        )

    overall_score = sum(s.score for s in scores)
    max_score = len(criteria["categories"]) * criteria["max_per_category"]

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Evaluation completed",
        extra={
            "methodology": methodology,
            "overall_score": overall_score,
            "max_score": max_score,
            "duration_ms": duration_ms,
        },
    )

    return EvaluationResponse(
        overall_score=overall_score,
        max_score=max_score,
        methodology=methodology,
        scores=scores,
        summary=result.get("summary", ""),
        strengths=result.get("strengths", []),
        areas_for_improvement=result.get("areas_for_improvement", []),
    )


@router.get("/methodologies")
async def list_methodologies():
    """List available evaluation methodologies with descriptions."""
    methodology_info = {
        "SPIN": {
            "description": "Situation, Problem, Implication, Need-Payoff questioning methodology",
            "best_for": "Discovery conversations and understanding customer needs",
        },
        "MEDDIC": {
            "description": "Metrics, Economic Buyer, Decision Criteria/Process, Identify Pain, Champion",
            "best_for": "Qualifying complex B2B opportunities",
        },
        "Challenger": {
            "description": "Teaching, Tailoring, Taking Control approach",
            "best_for": "Consultative selling where you bring insights",
        },
        "Sandler": {
            "description": "Systematic sales process from bonding to post-sell",
            "best_for": "Full sales cycle management",
        },
    }

    return {
        "methodologies": [
            {
                "name": name,
                "description": methodology_info.get(name, {}).get("description", ""),
                "best_for": methodology_info.get(name, {}).get("best_for", ""),
                "categories": info["categories"],
                "max_score": len(info["categories"]) * info["max_per_category"],
            }
            for name, info in METHODOLOGY_CRITERIA.items()
        ]
    }
