"""Value Proposition Assistant API endpoints."""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.constants import DEFAULT_SCORE
from app.logging_config import get_logger
from app.utils import call_llm_json

router = APIRouter()
logger = get_logger("api.value_prop")

# =============================================================================
# CONSTANTS
# =============================================================================

VALUE_PROP_REVIEW_PROMPT = """You are an expert sales messaging coach specializing in customer-centric value propositions.

Analyze the following value proposition and provide detailed feedback.

VALUE PROPOSITION: {value_prop}
TARGET CUSTOMER: {target_customer}
INDUSTRY: {industry}

Evaluate against these criteria:

1. GOLDEN CIRCLE ANALYSIS (Simon Sinek's Why/How/What)
   - WHY: Does it communicate the purpose/belief that drives the company?
   - HOW: Does it explain the unique approach or differentiators?
   - WHAT: Does it describe what is actually being offered?
   - Note: Great value props start with WHY, weak ones start with WHAT

2. CUSTOMER-CENTRICITY
   - Does it focus on customer outcomes or product features?
   - Does it address specific customer pain points?
   - Does it use "you/your" language vs "we/our" language?
   - Is it about the customer's world or the seller's world?

3. CLARITY AND IMPACT
   - Is it clear and easy to understand?
   - Is it specific and concrete (not vague buzzwords)?
   - Is it memorable and differentiated?
   - Does it create urgency or emotional resonance?

4. PROOF AND CREDIBILITY
   - Does it include quantified results or proof points?
   - Is it believable and realistic?

Respond in this exact JSON format:
{{
    "overall_score": 1-10,
    "golden_circle_analysis": {{
        "why_score": 1-10,
        "why_present": true/false,
        "why_feedback": "Feedback on the WHY element",
        "how_score": 1-10,
        "how_present": true/false,
        "how_feedback": "Feedback on the HOW element",
        "what_score": 1-10,
        "what_present": true/false,
        "what_feedback": "Feedback on the WHAT element",
        "structure_feedback": "Does it follow Why->How->What or What->How->Why?"
    }},
    "customer_centricity": {{
        "score": 1-10,
        "is_customer_focused": true/false,
        "you_vs_we_ratio": "Approximate ratio of customer vs seller language",
        "feedback": "Detailed feedback on customer focus"
    }},
    "clarity": {{
        "score": 1-10,
        "is_clear": true/false,
        "buzzword_count": 0,
        "feedback": "Feedback on clarity and specificity"
    }},
    "issues": ["Issue 1", "Issue 2"],
    "strengths": ["Strength 1", "Strength 2"],
    "improved_version": "A rewritten, customer-centric version starting with WHY",
    "quick_tips": ["Tip 1", "Tip 2", "Tip 3"]
}}

Return ONLY the JSON, no other text."""


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ValuePropReviewRequest(BaseModel):
    value_prop: str
    target_customer: str = ""  # Who is this for?
    industry: str = ""  # What industry?


class GoldenCircleAnalysis(BaseModel):
    why_score: int
    why_present: bool
    why_feedback: str
    how_score: int
    how_present: bool
    how_feedback: str
    what_score: int
    what_present: bool
    what_feedback: str
    structure_feedback: str


class CustomerCentricityAnalysis(BaseModel):
    score: int
    is_customer_focused: bool
    you_vs_we_ratio: str
    feedback: str


class ClarityAnalysis(BaseModel):
    score: int
    is_clear: bool
    buzzword_count: int
    feedback: str


class ValuePropReviewResponse(BaseModel):
    overall_score: int
    golden_circle_analysis: GoldenCircleAnalysis
    customer_centricity: CustomerCentricityAnalysis
    clarity: ClarityAnalysis
    issues: list[str]
    strengths: list[str]
    improved_version: str
    quick_tips: list[str]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/review", response_model=ValuePropReviewResponse)
async def review_value_proposition(request: ValuePropReviewRequest):
    """Review a value proposition and provide detailed feedback.

    Analyzes:
    - Golden Circle structure (Why/How/What)
    - Customer-centricity vs feature focus
    - Clarity and impact
    - Provides improved, customer-focused version
    """
    start_time = time.perf_counter()

    if not request.value_prop.strip():
        raise HTTPException(
            status_code=400,
            detail="value_prop cannot be empty",
        )

    logger.info(
        "Reviewing value proposition",
        extra={"value_prop_length": len(request.value_prop)},
    )

    # Build prompt
    prompt = VALUE_PROP_REVIEW_PROMPT.format(
        value_prop=request.value_prop,
        target_customer=request.target_customer or "Not specified",
        industry=request.industry or "Not specified",
    )

    # Get LLM response
    result = await call_llm_json(
        messages=[{"role": "user", "content": prompt}],
        operation_name="Value proposition review",
    )

    # Build response objects
    golden_circle = GoldenCircleAnalysis(
        why_score=result.get("golden_circle_analysis", {}).get("why_score", DEFAULT_SCORE),
        why_present=result.get("golden_circle_analysis", {}).get("why_present", False),
        why_feedback=result.get("golden_circle_analysis", {}).get("why_feedback", ""),
        how_score=result.get("golden_circle_analysis", {}).get("how_score", DEFAULT_SCORE),
        how_present=result.get("golden_circle_analysis", {}).get("how_present", False),
        how_feedback=result.get("golden_circle_analysis", {}).get("how_feedback", ""),
        what_score=result.get("golden_circle_analysis", {}).get("what_score", DEFAULT_SCORE),
        what_present=result.get("golden_circle_analysis", {}).get("what_present", False),
        what_feedback=result.get("golden_circle_analysis", {}).get("what_feedback", ""),
        structure_feedback=result.get("golden_circle_analysis", {}).get("structure_feedback", ""),
    )

    customer_centricity = CustomerCentricityAnalysis(
        score=result.get("customer_centricity", {}).get("score", DEFAULT_SCORE),
        is_customer_focused=result.get("customer_centricity", {}).get("is_customer_focused", False),
        you_vs_we_ratio=result.get("customer_centricity", {}).get("you_vs_we_ratio", "Unknown"),
        feedback=result.get("customer_centricity", {}).get("feedback", ""),
    )

    clarity = ClarityAnalysis(
        score=result.get("clarity", {}).get("score", DEFAULT_SCORE),
        is_clear=result.get("clarity", {}).get("is_clear", False),
        buzzword_count=result.get("clarity", {}).get("buzzword_count", 0),
        feedback=result.get("clarity", {}).get("feedback", ""),
    )

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Value proposition reviewed",
        extra={
            "overall_score": result.get("overall_score"),
            "duration_ms": duration_ms,
        },
    )

    return ValuePropReviewResponse(
        overall_score=result.get("overall_score", DEFAULT_SCORE),
        golden_circle_analysis=golden_circle,
        customer_centricity=customer_centricity,
        clarity=clarity,
        issues=result.get("issues", []),
        strengths=result.get("strengths", []),
        improved_version=result.get("improved_version", request.value_prop),
        quick_tips=result.get("quick_tips", []),
    )


@router.get("/golden-circle")
async def get_golden_circle_info():
    """Get information about the Golden Circle framework."""
    return {
        "framework": "Golden Circle",
        "author": "Simon Sinek",
        "description": "A framework for inspiring action by starting with WHY",
        "layers": [
            {
                "layer": "WHY",
                "position": "center",
                "description": "Your purpose, cause, or belief. Why does your organization exist?",
                "question": "Why do you do what you do?",
                "example": "We believe technology should empower people to achieve more.",
            },
            {
                "layer": "HOW",
                "position": "middle",
                "description": "Your unique approach, values, or differentiating process.",
                "question": "How do you do what you do differently?",
                "example": "Through intuitive design and seamless integration.",
            },
            {
                "layer": "WHAT",
                "position": "outer",
                "description": "The products or services you offer.",
                "question": "What do you do?",
                "example": "We make productivity software for teams.",
            },
        ],
        "key_principle": "People don't buy WHAT you do, they buy WHY you do it.",
        "common_mistake": "Most companies communicate from the outside in (What -> How -> Why). Inspiring companies communicate from the inside out (Why -> How -> What).",
    }


@router.get("/tips")
async def get_value_prop_tips():
    """Get tips for writing effective value propositions."""
    return {
        "tips": [
            {
                "category": "Customer Focus",
                "tips": [
                    "Use 'you' and 'your' instead of 'we' and 'our'",
                    "Focus on customer outcomes, not product features",
                    "Address specific pain points they experience",
                    "Speak in their language, not technical jargon",
                ],
            },
            {
                "category": "Clarity",
                "tips": [
                    "Avoid buzzwords like 'innovative', 'best-in-class', 'synergy'",
                    "Be specific with numbers and timeframes",
                    "Use concrete examples over abstract concepts",
                    "Keep it concise - if you can't say it in 30 seconds, simplify",
                ],
            },
            {
                "category": "Differentiation",
                "tips": [
                    "Answer: Why should they choose you over alternatives?",
                    "Highlight what you do differently, not just what you do",
                    "Address the 'do nothing' option - why act now?",
                    "Back claims with proof points or customer evidence",
                ],
            },
            {
                "category": "Structure",
                "tips": [
                    "Start with the customer's problem or desired outcome",
                    "Follow with how you uniquely solve it",
                    "End with specific, measurable results",
                    "Test: Can someone repeat it after hearing it once?",
                ],
            },
        ],
        "formula": "For [target customer] who [statement of need], [product name] is a [product category] that [key benefit]. Unlike [competition], we [key differentiator].",
    }
