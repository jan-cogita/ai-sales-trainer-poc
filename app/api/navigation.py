"""Opportunity Navigation Advisor API endpoints."""

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.logging_config import get_logger
from app.utils import call_llm_json

router = APIRouter()
logger = get_logger("api.navigation")

# =============================================================================
# CONSTANTS
# =============================================================================

ANALYSIS_TEMPERATURE = 0.4
DEFAULT_URGENCY = "medium"

SALES_STAGES = [
    "prospecting",
    "discovery",
    "qualification",
    "solution-presentation",
    "proposal",
    "negotiation",
    "closing",
    "won",
    "lost",
]

NAVIGATION_PROMPT = """You are an expert B2B sales coach helping a salesperson navigate a complex enterprise deal.

Based on the current deal context, recommend the next best action to move this opportunity forward.

CURRENT STAGE: {current_stage}
RECENT ACTIVITY: {recent_activity}
CURRENT CHALLENGES: {challenges}
MEDDPICC CONTEXT: {meddpicc_context}
ADDITIONAL NOTES: {notes}

Analyze the situation and provide actionable guidance. Consider:
1. What is the most important thing to do RIGHT NOW to advance this deal?
2. What preparation is needed before taking that action?
3. What red flags or risks should the salesperson be aware of?
4. What questions should they ask in their next interaction?

Respond in this exact JSON format:
{{
    "recommended_action": {{
        "action": "Specific action to take (be concrete and actionable)",
        "rationale": "Why this action is the priority right now",
        "urgency": "high|medium|low",
        "timing": "When to take this action (e.g., 'within 24 hours', 'before next meeting')"
    }},
    "preparation_items": [
        "Specific preparation item 1",
        "Specific preparation item 2",
        "Specific preparation item 3"
    ],
    "questions_to_ask": [
        "Question 1 to ask in next interaction",
        "Question 2 to ask in next interaction",
        "Question 3 to ask in next interaction"
    ],
    "red_flags": [
        "Risk or warning sign 1",
        "Risk or warning sign 2"
    ],
    "success_indicators": [
        "How you'll know the action was successful",
        "What positive signals to look for"
    ],
    "alternative_actions": [
        {{
            "action": "Alternative action if primary isn't possible",
            "when_to_use": "Condition when this is appropriate"
        }}
    ],
    "stage_assessment": {{
        "current_stage_fit": true/false,
        "suggested_stage": "If different from current, what stage should this be?",
        "stage_feedback": "Feedback on deal stage accuracy"
    }},
    "summary": "Brief 2-3 sentence summary of the recommendation"
}}

Return ONLY the JSON, no other text."""


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class NavigationRequest(BaseModel):
    current_stage: str  # prospecting, discovery, qualification, etc.
    recent_activity: str = ""  # What happened recently in the deal
    challenges: str = ""  # Current obstacles or concerns
    meddpicc_context: str = ""  # Summary of MEDDPICC status
    notes: str = ""  # Any additional context


class RecommendedAction(BaseModel):
    action: str
    rationale: str
    urgency: str
    timing: str


class AlternativeAction(BaseModel):
    action: str
    when_to_use: str


class StageAssessment(BaseModel):
    current_stage_fit: bool
    suggested_stage: str
    stage_feedback: str


class NavigationResponse(BaseModel):
    recommended_action: RecommendedAction
    preparation_items: list[str]
    questions_to_ask: list[str]
    red_flags: list[str]
    success_indicators: list[str]
    alternative_actions: list[AlternativeAction]
    stage_assessment: StageAssessment
    summary: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/recommend", response_model=NavigationResponse)
async def get_navigation_recommendation(request: NavigationRequest):
    """Get next best action recommendation for an opportunity.

    Provides:
    - Specific recommended action with rationale
    - Preparation items before taking action
    - Questions to ask in next interaction
    - Red flags to watch for
    - Success indicators
    - Alternative actions if primary isn't possible
    """
    start_time = time.perf_counter()

    # Validate stage
    stage_lower = request.current_stage.lower()
    if stage_lower not in SALES_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid current_stage. Must be one of: {SALES_STAGES}",
        )

    logger.info(
        "Getting navigation recommendation",
        extra={"current_stage": stage_lower},
    )

    # Build prompt
    prompt = NAVIGATION_PROMPT.format(
        current_stage=stage_lower,
        recent_activity=request.recent_activity or "No recent activity provided",
        challenges=request.challenges or "No specific challenges mentioned",
        meddpicc_context=request.meddpicc_context or "No MEDDPICC context provided",
        notes=request.notes or "No additional notes",
    )

    # Get LLM response
    result = await call_llm_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=ANALYSIS_TEMPERATURE,
        operation_name="Navigation recommendation",
    )

    # Build response objects
    recommended_action = RecommendedAction(
        action=result.get("recommended_action", {}).get("action", ""),
        rationale=result.get("recommended_action", {}).get("rationale", ""),
        urgency=result.get("recommended_action", {}).get("urgency", DEFAULT_URGENCY),
        timing=result.get("recommended_action", {}).get("timing", ""),
    )

    alternative_actions = [
        AlternativeAction(
            action=alt.get("action", ""),
            when_to_use=alt.get("when_to_use", ""),
        )
        for alt in result.get("alternative_actions", [])
    ]

    stage_assessment = StageAssessment(
        current_stage_fit=result.get("stage_assessment", {}).get("current_stage_fit", True),
        suggested_stage=result.get("stage_assessment", {}).get("suggested_stage", stage_lower),
        stage_feedback=result.get("stage_assessment", {}).get("stage_feedback", ""),
    )

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Navigation recommendation generated",
        extra={
            "urgency": recommended_action.urgency,
            "duration_ms": duration_ms,
        },
    )

    return NavigationResponse(
        recommended_action=recommended_action,
        preparation_items=result.get("preparation_items", []),
        questions_to_ask=result.get("questions_to_ask", []),
        red_flags=result.get("red_flags", []),
        success_indicators=result.get("success_indicators", []),
        alternative_actions=alternative_actions,
        stage_assessment=stage_assessment,
        summary=result.get("summary", ""),
    )


@router.get("/stages")
async def list_sales_stages():
    """List sales stages with descriptions and typical activities."""
    return {
        "stages": [
            {
                "stage": "prospecting",
                "description": "Identifying and reaching out to potential customers",
                "typical_activities": [
                    "Research target accounts",
                    "Initial outreach (email, phone, social)",
                    "Qualify initial interest",
                ],
                "exit_criteria": "Prospect agrees to a discovery meeting",
            },
            {
                "stage": "discovery",
                "description": "Understanding the customer's situation, problems, and needs",
                "typical_activities": [
                    "Conduct discovery calls",
                    "Ask SPIN questions",
                    "Identify pain points and implications",
                    "Map stakeholders",
                ],
                "exit_criteria": "Clear understanding of problems and business impact",
            },
            {
                "stage": "qualification",
                "description": "Determining if the opportunity is worth pursuing",
                "typical_activities": [
                    "Complete MEDDPICC analysis",
                    "Identify economic buyer",
                    "Understand decision process",
                    "Assess competition",
                ],
                "exit_criteria": "Opportunity meets qualification criteria",
            },
            {
                "stage": "solution-presentation",
                "description": "Presenting your solution aligned to customer needs",
                "typical_activities": [
                    "Tailor presentation to pain points",
                    "Demonstrate relevant capabilities",
                    "Address technical requirements",
                    "Build champion support",
                ],
                "exit_criteria": "Customer confirms solution fit",
            },
            {
                "stage": "proposal",
                "description": "Delivering formal proposal and pricing",
                "typical_activities": [
                    "Prepare proposal document",
                    "Present pricing and terms",
                    "Address initial concerns",
                    "Get feedback on proposal",
                ],
                "exit_criteria": "Proposal accepted for review by decision makers",
            },
            {
                "stage": "negotiation",
                "description": "Working through terms, pricing, and final details",
                "typical_activities": [
                    "Negotiate terms and pricing",
                    "Address final objections",
                    "Work with procurement",
                    "Navigate legal review",
                ],
                "exit_criteria": "Agreement on terms, ready for signature",
            },
            {
                "stage": "closing",
                "description": "Finalizing the deal and getting signature",
                "typical_activities": [
                    "Final contract review",
                    "Obtain signatures",
                    "Process paperwork",
                    "Plan implementation kickoff",
                ],
                "exit_criteria": "Contract signed, deal closed",
            },
            {
                "stage": "won",
                "description": "Deal successfully closed",
                "typical_activities": [
                    "Hand off to implementation",
                    "Document lessons learned",
                    "Plan for expansion",
                ],
                "exit_criteria": "N/A - Final stage",
            },
            {
                "stage": "lost",
                "description": "Deal did not close",
                "typical_activities": [
                    "Conduct loss analysis",
                    "Document reasons",
                    "Plan re-engagement strategy",
                ],
                "exit_criteria": "N/A - Final stage",
            },
        ]
    }


@router.get("/playbook/{stage}")
async def get_stage_playbook(stage: str):
    """Get detailed playbook for a specific sales stage."""
    stage_lower = stage.lower()
    if stage_lower not in SALES_STAGES:
        raise HTTPException(
            status_code=404,
            detail=f"Stage not found. Must be one of: {SALES_STAGES}",
        )

    playbooks = {
        "discovery": {
            "stage": "discovery",
            "objective": "Understand the customer's world deeply before discussing solutions",
            "key_principles": [
                "Listen more than you talk (aim for 70% customer talk time)",
                "Ask open-ended questions",
                "Don't pitch - focus on understanding",
                "Quantify the pain whenever possible",
            ],
            "spin_focus": {
                "situation": "Gather context about their current state",
                "problem": "Uncover difficulties and dissatisfactions",
                "implication": "Explore consequences of the problems",
                "need_payoff": "Help them envision the value of solving",
            },
            "common_mistakes": [
                "Pitching too early",
                "Asking closed questions",
                "Talking about your product",
                "Not digging deep enough into implications",
            ],
            "success_metrics": [
                "Customer articulates their problems clearly",
                "You understand the business impact",
                "You know who else is affected",
                "Customer is engaged and sharing openly",
            ],
        },
        "qualification": {
            "stage": "qualification",
            "objective": "Determine if this opportunity is worth pursuing and winnable",
            "key_principles": [
                "Be rigorous - not every opportunity is worth pursuing",
                "Identify gaps early so you can fill them",
                "Understand the competitive landscape",
                "Find and develop your champion",
            ],
            "meddpicc_checklist": [
                "Metrics: What quantified value do they expect?",
                "Economic Buyer: Who has budget authority?",
                "Decision Criteria: How will they evaluate?",
                "Decision Process: What are the steps?",
                "Paper Process: What's the procurement process?",
                "Implicate Pain: What's the cost of inaction?",
                "Champion: Who is selling for you internally?",
                "Competition: Who else are they considering?",
            ],
            "common_mistakes": [
                "Assuming you're qualified without evidence",
                "Not meeting the economic buyer",
                "Ignoring competition",
                "Relying on a weak champion",
            ],
            "success_metrics": [
                "All MEDDPICC elements documented",
                "Clear path to economic buyer",
                "Champion actively engaged",
                "Competitive position understood",
            ],
        },
    }

    if stage_lower in playbooks:
        return playbooks[stage_lower]

    return {
        "stage": stage_lower,
        "message": "Detailed playbook coming soon. Use /navigation/stages for overview.",
    }
