"""Guided Question Creator API endpoints for SPIN question review."""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.constants import DEFAULT_SCORE, LLM_TEMPERATURE_ANALYSIS
from app.logging_config import get_logger
from app.utils import call_llm_json

router = APIRouter()
logger = get_logger("api.questions")

# =============================================================================
# CONSTANTS
# =============================================================================

QUESTION_TYPES = ["situation", "problem", "implication", "need-payoff"]

QUESTION_REVIEW_PROMPT = """You are an expert sales coach specializing in the SPIN selling methodology.

Analyze the following sales question and provide detailed feedback.

QUESTION: {question}
STATED TYPE: {question_type}
CONTEXT: {context}

Evaluate the question against these criteria:

1. QUESTION TYPE ACCURACY
   - Is this actually a {question_type} question?
   - Situation questions: gather facts about current state
   - Problem questions: uncover difficulties, dissatisfactions, challenges
   - Implication questions: explore consequences and effects of problems
   - Need-payoff questions: focus on value and benefits of solving the problem

2. QUESTION QUALITY
   - Is it open-ended (allows elaboration) or closed (yes/no)?
   - Does it avoid leading the customer?
   - Is it clear and easy to understand?
   - Does it show preparation/research about the customer?

3. EFFECTIVENESS
   - Will this question help uncover valuable information?
   - Is it appropriate for this stage of the conversation?
   - Does it build rapport or feel interrogative?

Respond in this exact JSON format:
{{
    "is_correct_type": true/false,
    "actual_type": "situation|problem|implication|need-payoff",
    "score": 1-10,
    "is_open_ended": true/false,
    "strengths": ["strength 1", "strength 2"],
    "improvements": ["improvement 1", "improvement 2"],
    "improved_version": "A better version of the question",
    "explanation": "Brief explanation of the feedback"
}}

Return ONLY the JSON, no other text."""


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class QuestionReviewRequest(BaseModel):
    question: str
    question_type: str  # situation, problem, implication, need-payoff
    context: str = ""  # Optional context about the customer/situation


class QuestionReviewResponse(BaseModel):
    is_correct_type: bool
    actual_type: str
    score: int
    is_open_ended: bool
    strengths: list[str]
    improvements: list[str]
    improved_version: str
    explanation: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/review", response_model=QuestionReviewResponse)
async def review_question(request: QuestionReviewRequest):
    """Review a SPIN question and provide feedback with improved version.

    Analyzes the question for:
    - Correct SPIN type classification
    - Open vs closed question structure
    - Overall quality and effectiveness
    - Provides an improved version
    """
    start_time = time.perf_counter()

    # Validate question type
    question_type_lower = request.question_type.lower()
    if question_type_lower not in QUESTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid question_type. Must be one of: {QUESTION_TYPES}",
        )

    logger.info(
        "Reviewing question",
        extra={"question_type": question_type_lower, "question_length": len(request.question)},
    )

    # Build prompt
    prompt = QUESTION_REVIEW_PROMPT.format(
        question=request.question,
        question_type=question_type_lower,
        context=request.context or "No specific context provided",
    )

    # Get LLM response
    result = await call_llm_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=LLM_TEMPERATURE_ANALYSIS,
        operation_name="Question review",
    )

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Question reviewed",
        extra={
            "score": result.get("score"),
            "is_correct_type": result.get("is_correct_type"),
            "duration_ms": duration_ms,
        },
    )

    return QuestionReviewResponse(
        is_correct_type=result.get("is_correct_type", False),
        actual_type=result.get("actual_type", question_type_lower),
        score=result.get("score", DEFAULT_SCORE),
        is_open_ended=result.get("is_open_ended", True),
        strengths=result.get("strengths", []),
        improvements=result.get("improvements", []),
        improved_version=result.get("improved_version", request.question),
        explanation=result.get("explanation", ""),
    )


@router.get("/types")
async def list_question_types():
    """List available SPIN question types with descriptions."""
    return {
        "question_types": [
            {
                "type": "situation",
                "description": "Questions that gather facts about the customer's current state, background, and environment.",
                "examples": [
                    "How many employees do you have?",
                    "What systems are you currently using?",
                    "How long have you been in this role?",
                ],
            },
            {
                "type": "problem",
                "description": "Questions that uncover difficulties, dissatisfactions, and challenges the customer faces.",
                "examples": [
                    "What challenges are you facing with your current system?",
                    "Where do you see the biggest inefficiencies?",
                    "What frustrates your team about the current process?",
                ],
            },
            {
                "type": "implication",
                "description": "Questions that explore the consequences and effects of the customer's problems.",
                "examples": [
                    "How does that affect your team's productivity?",
                    "What impact does this have on your bottom line?",
                    "If this continues, what risks do you foresee?",
                ],
            },
            {
                "type": "need-payoff",
                "description": "Questions that focus on the value and benefits of solving the problem.",
                "examples": [
                    "How would it help if you could reduce that time by 50%?",
                    "What would it mean for your team if this problem was solved?",
                    "How valuable would it be to have real-time visibility?",
                ],
            },
        ]
    }
