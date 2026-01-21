"""MEDDPICC Opportunity Qualification API endpoints."""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.constants import LLM_TEMPERATURE_ANALYSIS
from app.logging_config import get_logger
from app.utils import call_llm_json

router = APIRouter()
logger = get_logger("api.qualification")

# =============================================================================
# CONSTANTS
# =============================================================================

DIMENSION_STATUS_STRONG = "strong"
DIMENSION_STATUS_WEAK = "weak"
DIMENSION_STATUS_MISSING = "missing"
DEFAULT_SCORE = 0
DEFAULT_STATUS = "needs-work"

MEDDPICC_ANALYSIS_PROMPT = """You are an expert B2B sales coach specializing in the MEDDPICC qualification framework.

Analyze the following opportunity data and provide a comprehensive gap analysis.

OPPORTUNITY DATA:
- Metrics: {metrics}
- Economic Buyer: {economic_buyer}
- Decision Criteria: {decision_criteria}
- Decision Process: {decision_process}
- Paper Process: {paper_process}
- Implicate the Pain: {implicate_pain}
- Champion: {champion}
- Competition: {competition}

ADDITIONAL CONTEXT: {context}

For each MEDDPICC dimension, evaluate:
1. Is there clear, specific evidence? (Strong)
2. Is it mentioned but vague or unvalidated? (Weak)
3. Is it not addressed at all? (Missing)

Respond in this exact JSON format:
{{
    "overall_score": 0-100,
    "qualification_status": "well-qualified|needs-work|not-qualified",
    "dimensions": {{
        "metrics": {{
            "status": "strong|weak|missing",
            "evidence": "What evidence exists",
            "gap": "What's missing or needs improvement",
            "question_to_ask": "Suggested question to fill the gap"
        }},
        "economic_buyer": {{
            "status": "strong|weak|missing",
            "evidence": "What evidence exists",
            "gap": "What's missing or needs improvement",
            "question_to_ask": "Suggested question to fill the gap"
        }},
        "decision_criteria": {{
            "status": "strong|weak|missing",
            "evidence": "What evidence exists",
            "gap": "What's missing or needs improvement",
            "question_to_ask": "Suggested question to fill the gap"
        }},
        "decision_process": {{
            "status": "strong|weak|missing",
            "evidence": "What evidence exists",
            "gap": "What's missing or needs improvement",
            "question_to_ask": "Suggested question to fill the gap"
        }},
        "paper_process": {{
            "status": "strong|weak|missing",
            "evidence": "What evidence exists",
            "gap": "What's missing or needs improvement",
            "question_to_ask": "Suggested question to fill the gap"
        }},
        "implicate_pain": {{
            "status": "strong|weak|missing",
            "evidence": "What evidence exists",
            "gap": "What's missing or needs improvement",
            "question_to_ask": "Suggested question to fill the gap"
        }},
        "champion": {{
            "status": "strong|weak|missing",
            "evidence": "What evidence exists",
            "gap": "What's missing or needs improvement",
            "question_to_ask": "Suggested question to fill the gap"
        }},
        "competition": {{
            "status": "strong|weak|missing",
            "evidence": "What evidence exists",
            "gap": "What's missing or needs improvement",
            "question_to_ask": "Suggested question to fill the gap"
        }}
    }},
    "priority_actions": [
        "Most important action to take first",
        "Second priority action",
        "Third priority action"
    ],
    "risk_factors": ["Key risk 1", "Key risk 2"],
    "summary": "Brief overall assessment of the opportunity"
}}

Return ONLY the JSON, no other text."""


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class OpportunityData(BaseModel):
    metrics: str = ""  # Quantified value/ROI the customer expects
    economic_buyer: str = ""  # Person with budget authority
    decision_criteria: str = ""  # How they will evaluate solutions
    decision_process: str = ""  # Steps to make the decision
    paper_process: str = ""  # Legal, procurement, contract process
    implicate_pain: str = ""  # Business pain and its implications
    champion: str = ""  # Internal advocate for your solution
    competition: str = ""  # Competitive landscape
    context: str = ""  # Additional context about the opportunity


class DimensionAnalysis(BaseModel):
    status: str  # strong, weak, missing
    evidence: str
    gap: str
    question_to_ask: str


class QualificationResponse(BaseModel):
    overall_score: int
    qualification_status: str
    dimensions: dict[str, DimensionAnalysis]
    priority_actions: list[str]
    risk_factors: list[str]
    summary: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/analyze", response_model=QualificationResponse)
async def analyze_opportunity(request: OpportunityData):
    """Analyze an opportunity using MEDDPICC framework.

    Provides:
    - Overall qualification score (0-100)
    - Per-dimension status (strong/weak/missing)
    - Gap analysis with suggested questions
    - Priority actions to improve qualification
    - Risk factors to monitor
    """
    start_time = time.perf_counter()

    logger.info("Analyzing opportunity qualification")

    # Build prompt
    prompt = MEDDPICC_ANALYSIS_PROMPT.format(
        metrics=request.metrics or "Not provided",
        economic_buyer=request.economic_buyer or "Not provided",
        decision_criteria=request.decision_criteria or "Not provided",
        decision_process=request.decision_process or "Not provided",
        paper_process=request.paper_process or "Not provided",
        implicate_pain=request.implicate_pain or "Not provided",
        champion=request.champion or "Not provided",
        competition=request.competition or "Not provided",
        context=request.context or "No additional context",
    )

    # Get LLM response
    result = await call_llm_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=LLM_TEMPERATURE_ANALYSIS,
        operation_name="Qualification analysis",
    )

    # Convert dimensions to proper format
    dimensions = {}
    for dim_name, dim_data in result.get("dimensions", {}).items():
        dimensions[dim_name] = DimensionAnalysis(
            status=dim_data.get("status", "missing"),
            evidence=dim_data.get("evidence", ""),
            gap=dim_data.get("gap", ""),
            question_to_ask=dim_data.get("question_to_ask", ""),
        )

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Opportunity analyzed",
        extra={
            "overall_score": result.get("overall_score"),
            "status": result.get("qualification_status"),
            "duration_ms": duration_ms,
        },
    )

    return QualificationResponse(
        overall_score=result.get("overall_score", DEFAULT_SCORE),
        qualification_status=result.get("qualification_status", DEFAULT_STATUS),
        dimensions=dimensions,
        priority_actions=result.get("priority_actions", []),
        risk_factors=result.get("risk_factors", []),
        summary=result.get("summary", ""),
    )


@router.get("/framework")
async def get_meddpicc_framework():
    """Get MEDDPICC framework description and guidance."""
    return {
        "framework": "MEDDPICC",
        "description": "A B2B sales qualification methodology for complex enterprise deals",
        "dimensions": [
            {
                "letter": "M",
                "name": "Metrics",
                "description": "Quantified value the customer expects to achieve",
                "key_questions": [
                    "What ROI are they expecting?",
                    "What specific metrics will improve?",
                    "How will they measure success?",
                ],
            },
            {
                "letter": "E",
                "name": "Economic Buyer",
                "description": "The person with budget authority and final decision power",
                "key_questions": [
                    "Who controls the budget?",
                    "Who can say yes when everyone else says no?",
                    "Have you met with them directly?",
                ],
            },
            {
                "letter": "D",
                "name": "Decision Criteria",
                "description": "The formal and informal criteria used to evaluate solutions",
                "key_questions": [
                    "What criteria will they use to decide?",
                    "How important is each criterion?",
                    "Can you influence the criteria?",
                ],
            },
            {
                "letter": "D",
                "name": "Decision Process",
                "description": "The steps and timeline to reach a decision",
                "key_questions": [
                    "What are the steps to make this decision?",
                    "Who is involved at each step?",
                    "What is the timeline?",
                ],
            },
            {
                "letter": "P",
                "name": "Paper Process",
                "description": "Legal, procurement, and contract approval process",
                "key_questions": [
                    "What's the procurement process?",
                    "Are there legal or security reviews?",
                    "What contract terms are standard?",
                ],
            },
            {
                "letter": "I",
                "name": "Implicate the Pain",
                "description": "The business pain and its broader implications",
                "key_questions": [
                    "What happens if they don't solve this?",
                    "What's the cost of inaction?",
                    "Who else is affected by this problem?",
                ],
            },
            {
                "letter": "C",
                "name": "Champion",
                "description": "An internal advocate who wants you to win",
                "key_questions": [
                    "Who is actively selling for you internally?",
                    "What do they gain from your success?",
                    "Can they access the Economic Buyer?",
                ],
            },
            {
                "letter": "C",
                "name": "Competition",
                "description": "The competitive landscape including status quo",
                "key_questions": [
                    "Who else are they evaluating?",
                    "What's your differentiation?",
                    "Is 'do nothing' an option?",
                ],
            },
        ],
    }
