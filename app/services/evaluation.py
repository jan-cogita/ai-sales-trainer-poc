"""Evaluation service for scoring practice conversations using LLM-as-judge.

Implements the ClosR methodology scoring based on 8 dimensions:
- Opening/Rapport (professional entry, permission to ask questions)
- Patience (avoiding premature pitching)
- Implication Depth (exploring consequences, Domino Effect)
- Monetization Quality (quantifying customer pain in EUR/hours)
- SPIN Sequence (proper S->P->I->N progression)
- Vocabulary Compliance (NEPQ methodology, no "commission breath")
- Question Quality (open vs closed questions)
- Client Talk Ratio (customer talking 70%+)
"""

from dataclasses import dataclass

from app.logging_config import get_logger
from app.services.llm import LLMService
from app.utils.json_parser import parse_llm_json_response

logger = get_logger("services.evaluation")


# =============================================================================
# CONSTANTS
# =============================================================================

MAX_SCORE = 10
STRENGTH_THRESHOLD = 7

# Dimensions with display names and weights
DIMENSIONS = {
    "opening": {"name": "Opening/Rapport", "weight": 10},
    "patience": {"name": "Patience", "weight": 25},
    "implication_depth": {"name": "Implication Depth", "weight": 25},
    "monetization": {"name": "Monetization Quality", "weight": 5},
    "spin_sequence": {"name": "SPIN Sequence", "weight": 5},
    "vocabulary": {"name": "Vocabulary Compliance", "weight": 5},
    "question_quality": {"name": "Question Quality", "weight": 10},
    "talk_ratio": {"name": "Client Talk Ratio", "weight": 15},
}

EVALUATION_PROMPT = """You are an expert sales trainer evaluating a discovery conversation using the ClosR/SPIN methodology.

Analyze the transcript and score the SALESPERSON (not the customer) on each dimension.

DIMENSIONS TO EVALUATE:

1. OPENING/RAPPORT (10%): Did they get permission to ask questions? Demonstrate research? Avoid premature pitch? Use disarming phrases?

2. PATIENCE (25%): Did they wait until the customer articulated pain before mentioning solutions? No "we offer..." before Need-Payoff phase?

3. IMPLICATION DEPTH (25%): Did they explore consequences? Technical → Business → Personal impact? Help customer realize the full scope?

4. MONETIZATION (5%): Did they get specific numbers? EUR, hours, percentages? "Can you put a number on that?"

5. SPIN SEQUENCE (5%): Proper S→P→I→N flow? Limited Situation questions (2-3 max)? Confirmed facts vs asking basics?

6. VOCABULARY (5%): Avoided forbidden words (guarantee, best, trust me, great deal)? Used tentative language (perhaps, might, possibly)?

7. QUESTION QUALITY (10%): Mostly open questions (What, How, Tell me)? Good follow-up? Avoided rapid-fire interrogation?

8. TALK RATIO (15%): Is the customer doing most of the talking? Detailed responses? Salesperson asking concise questions?

Respond in this exact JSON format:
{
    "dimensions": {
        "opening": {"score": 1-10, "feedback": "1-2 sentence feedback"},
        "patience": {"score": 1-10, "feedback": "1-2 sentence feedback"},
        "implication_depth": {"score": 1-10, "feedback": "1-2 sentence feedback"},
        "monetization": {"score": 1-10, "feedback": "1-2 sentence feedback"},
        "spin_sequence": {"score": 1-10, "feedback": "1-2 sentence feedback"},
        "vocabulary": {"score": 1-10, "feedback": "1-2 sentence feedback"},
        "question_quality": {"score": 1-10, "feedback": "1-2 sentence feedback"},
        "talk_ratio": {"score": 1-10, "feedback": "1-2 sentence feedback"}
    },
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "improvements": ["improvement 1", "improvement 2", "improvement 3"],
    "summary": "2-3 sentence overall assessment"
}

Return ONLY valid JSON."""


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""

    dimension: str
    score: int
    max_score: int
    feedback: str

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "max_score": self.max_score,
            "feedback": self.feedback,
        }


@dataclass
class EvaluationResult:
    """Complete evaluation result for a conversation."""

    overall_score: float
    dimensions: list[DimensionScore]
    strengths: list[str]
    improvements: list[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "strengths": self.strengths,
            "improvements": self.improvements,
            "summary": self.summary,
        }


# =============================================================================
# EVALUATION SERVICE
# =============================================================================


class EvaluationService:
    """Service for evaluating practice conversations using LLM-as-judge.

    Uses a single LLM call to evaluate all dimensions for speed and consistency.
    """

    def __init__(self):
        self.llm_service = LLMService()

    async def evaluate(self, messages: list[dict]) -> EvaluationResult:
        """Evaluate a conversation and return scores with feedback."""
        transcript = self._format_transcript(messages)

        logger.info("Starting evaluation", extra={"message_count": len(messages)})

        # Single LLM call to evaluate all dimensions
        full_prompt = f"{EVALUATION_PROMPT}\n\nTranscript:\n{transcript}"

        response = await self.llm_service.chat_completion(
            messages=[{"role": "user", "content": full_prompt}],
        )

        result = parse_llm_json_response(response)

        # Parse dimension scores
        dimensions = []
        dim_scores = result.get("dimensions", {})

        for key, config in DIMENSIONS.items():
            dim_data = dim_scores.get(key, {})
            score = dim_data.get("score", 5)
            score = max(1, min(10, int(score)))
            feedback = dim_data.get("feedback", "No feedback provided.")

            dimensions.append(DimensionScore(
                dimension=config["name"],
                score=score,
                max_score=MAX_SCORE,
                feedback=feedback,
            ))

        overall_score = self._calculate_weighted_score(dimensions)

        strengths = result.get("strengths", [])
        improvements = result.get("improvements", [])
        summary = result.get("summary", self._generate_summary(overall_score, dimensions))

        logger.info("Evaluation completed", extra={"overall_score": overall_score})

        return EvaluationResult(
            overall_score=overall_score,
            dimensions=dimensions,
            strengths=strengths,
            improvements=improvements,
            summary=summary,
        )

    def _format_transcript(self, messages: list[dict]) -> str:
        """Format messages into a readable transcript."""
        lines = []
        for message in messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")

            if role == "user":
                speaker = "Salesperson"
            elif role == "assistant":
                speaker = "Customer"
            else:
                speaker = role.capitalize()

            lines.append(f"{speaker}: {content}")

        return "\n\n".join(lines)

    def _calculate_weighted_score(self, dimensions: list[DimensionScore]) -> float:
        """Calculate weighted overall score from dimension scores."""
        total_weight = sum(d["weight"] for d in DIMENSIONS.values())

        weighted_sum = 0
        for dim in dimensions:
            for key, config in DIMENSIONS.items():
                if config["name"] == dim.dimension:
                    weighted_sum += dim.score * config["weight"]
                    break

        return round(weighted_sum / total_weight, 1)

    def _generate_summary(self, overall_score: float, dimensions: list[DimensionScore]) -> str:
        """Generate fallback summary if LLM doesn't provide one."""
        if overall_score >= 8:
            level = "excellent"
        elif overall_score >= 6:
            level = "good"
        elif overall_score >= 4:
            level = "developing"
        else:
            level = "needs improvement"

        top = max(dimensions, key=lambda d: d.score)
        bottom = min(dimensions, key=lambda d: d.score)

        return (
            f"Overall: {level} ({overall_score}/10). "
            f"Strongest: {top.dimension}. "
            f"Focus on: {bottom.dimension}."
        )
