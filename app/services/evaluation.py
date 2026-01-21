"""Evaluation service for scoring practice conversations.

Implements the ClosR methodology scoring based on:
- Patience (avoiding premature pitching)
- Implication Depth (quantifying impact)
- Client Talk Ratio (letting customer talk 70%+)
- Question Quality (open vs closed questions)
"""

from dataclasses import dataclass

from app.logging_config import get_logger

logger = get_logger("services.evaluation")


# =============================================================================
# CONSTANTS - Evaluation Thresholds
# =============================================================================

EARLY_PITCH_MESSAGE_THRESHOLD = 3
MODERATE_PITCH_MESSAGE_THRESHOLD = 5

TARGET_CUSTOMER_TALK_RATIO_MIN = 0.65
TARGET_CUSTOMER_TALK_RATIO_MAX = 0.80
ACCEPTABLE_CUSTOMER_TALK_RATIO_MIN = 0.50

OPEN_QUESTION_EXCELLENT_RATIO = 0.70
OPEN_QUESTION_GOOD_RATIO = 0.50

IMPLICATION_EXCELLENT_COUNT = 3
IMPLICATION_GOOD_COUNT = 2
QUANTIFICATION_EXCELLENT_COUNT = 2
QUANTIFICATION_GOOD_COUNT = 1

# =============================================================================
# CONSTANTS - Score Values
# =============================================================================

MAX_SCORE = 10
SCORE_EXCELLENT = 9
SCORE_GOOD = 7
SCORE_MODERATE = 6
SCORE_DEVELOPING = 5
SCORE_NEEDS_WORK = 4
SCORE_POOR = 3

STRENGTH_THRESHOLD = 7


# =============================================================================
# CONSTANTS - Keyword Detection Lists
# =============================================================================

SOLUTION_KEYWORDS = [
    "our product",
    "we offer",
    "our solution",
    "we can provide",
    "let me tell you about",
    "our service",
    "we have",
    "i recommend",
    "our platform",
    "our approach",
]

IMPLICATION_KEYWORDS = [
    "impact",
    "affect",
    "consequence",
    "result in",
    "lead to",
    "cost",
    "lose",
    "risk",
    "what happens if",
    "how does that affect",
    "what would it mean",
    "effect",
]

QUANTIFICATION_KEYWORDS = [
    "how much",
    "how many",
    "percentage",
    "hours",
    "dollars",
    "euros",
    "time",
    "money",
    "budget",
    "number",
]

OPEN_QUESTION_STARTERS = [
    "what",
    "how",
    "why",
    "tell me",
    "describe",
    "explain",
    "could you elaborate",
]

CLOSED_QUESTION_STARTERS = [
    "do you",
    "are you",
    "is it",
    "have you",
    "can you",
    "will you",
    "did you",
]

# =============================================================================
# CONSTANTS - ClosR Vocabulary Lists
# =============================================================================

FORBIDDEN_VOCABULARY = [
    "best on market",
    "industry-leading",
    "industry leading",
    "guarantee",
    "guaranteed",
    "great deal",
    "only today",
    "limited time",
    "exclusive offer",
    "trust me",
    "believe me",
    "honestly",  # When used as emphasis, not genuine honesty
    "amazing",
    "incredible",
    "revolutionary",
    "cutting-edge",
    "cutting edge",
    "best-in-class",
    "best in class",
    "game-changer",
    "game changer",
]

ENCOURAGED_VOCABULARY = [
    "possibly",
    "perhaps",
    "might be",
    "could be",
    "find out",
    "explore",
    "discuss",
    "challenge",
    "concern",
    "i don't know",
    "i'm not sure",
    "let me check",
    "depends on",
    "in my experience",
    "it varies",
    "that's a fair point",
    "i understand",
]

DISARMING_PHRASES = [
    "i'm not sure if we can help",
    "not sure if we can help",
    "might not be the right fit",
    "may not be what you're looking for",
    "we don't know each other",
    "i hope i'm not interrupting",
    "this might not apply",
    "i could be wrong",
    "you might find",
    "not for everyone",
]

CONFIRMING_PATTERNS = [
    "i noticed",
    "i saw that",
    "i understand that",
    "i imagine",
    "i assume",
    "is that still",
    "is that accurate",
    "is that correct",
    "does that resonate",
    "am i on the right track",
]

# SPIN Question Type Indicators
SITUATION_INDICATORS = [
    "how many",
    "what is your",
    "what's your",
    "what systems",
    "what tools",
    "tell me about your current",
    "describe your",
    "what does your",
    "who is responsible",
    "how long have",
]

PROBLEM_INDICATORS = [
    "what challenges",
    "what difficulties",
    "where do you struggle",
    "what problems",
    "what concerns",
    "what frustrates",
    "what's not working",
    "what issues",
    "any pain points",
    "what bothers",
]

IMPLICATION_INDICATORS = [
    "what impact",
    "how does that affect",
    "what happens when",
    "what are the consequences",
    "what does that cost",
    "how much does",
    "what's the effect",
    "what would happen if",
    "how does that influence",
    "what's at stake",
]

NEED_PAYOFF_INDICATORS = [
    "how would it help",
    "what would it mean",
    "what would change",
    "how valuable would",
    "what would you gain",
    "what would be different",
    "how would that improve",
    "what would success look like",
    "if you could solve",
    "imagine if",
]


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


@dataclass
class EvaluationCriteria:
    """Weights for evaluation dimensions (must sum to 100)."""

    patience_weight: int = 25
    implication_depth_weight: int = 30
    client_talk_ratio_weight: int = 15
    question_type_weight: int = 10
    # New ClosR-specific weights
    spin_sequence_weight: int = 10
    vocabulary_compliance_weight: int = 5
    monetization_quality_weight: int = 5


# =============================================================================
# EVALUATION SERVICE
# =============================================================================

class EvaluationService:
    """Service for evaluating practice conversations against ClosR methodology."""

    def __init__(self, criteria: EvaluationCriteria | None = None):
        self.criteria = criteria or EvaluationCriteria()

    def evaluate(self, messages: list[dict]) -> EvaluationResult:
        """Evaluate a conversation and return scores with feedback."""
        patience = self._evaluate_patience(messages)
        implication = self._evaluate_implication_depth(messages)
        talk_ratio = self._evaluate_talk_ratio(messages)
        questions = self._evaluate_question_types(messages)
        # New ClosR-specific evaluations
        spin_sequence = self._evaluate_spin_sequence(messages)
        vocabulary = self._evaluate_vocabulary_compliance(messages)
        monetization = self._evaluate_monetization_quality(messages)

        dimensions = [patience, implication, talk_ratio, questions, spin_sequence, vocabulary, monetization]
        overall_score = self._calculate_weighted_score(dimensions)

        strengths = [d.feedback for d in dimensions if d.score >= STRENGTH_THRESHOLD]
        improvements = [d.feedback for d in dimensions if d.score < STRENGTH_THRESHOLD]
        summary = self._generate_summary(overall_score, dimensions)

        return EvaluationResult(
            overall_score=overall_score,
            dimensions=dimensions,
            strengths=strengths,
            improvements=improvements,
            summary=summary,
        )

    def _calculate_weighted_score(self, dimensions: list[DimensionScore]) -> float:
        """Calculate weighted overall score from dimension scores."""
        weights = {
            "Patience": self.criteria.patience_weight,
            "Implication Depth": self.criteria.implication_depth_weight,
            "Client Talk Ratio": self.criteria.client_talk_ratio_weight,
            "Question Quality": self.criteria.question_type_weight,
            "SPIN Sequence": self.criteria.spin_sequence_weight,
            "Vocabulary Compliance": self.criteria.vocabulary_compliance_weight,
            "Monetization Quality": self.criteria.monetization_quality_weight,
        }

        total_weight = sum(weights.values())
        weighted_sum = sum(d.score * weights.get(d.dimension, 0) for d in dimensions)

        return round(weighted_sum / total_weight, 1)

    def _generate_summary(self, overall_score: float, dimensions: list[DimensionScore]) -> str:
        """Generate human-readable summary of evaluation."""
        score_description = self._get_score_description(overall_score)
        top_dimension = max(dimensions, key=lambda d: d.score)
        bottom_dimension = min(dimensions, key=lambda d: d.score)

        return (
            f"Overall performance: {score_description} ({overall_score}/10). "
            f"Your strongest area was {top_dimension.dimension}. "
            f"Focus on improving {bottom_dimension.dimension} for better results. "
            f"Remember: questions create value, answers sell."
        )

    def _get_score_description(self, score: float) -> str:
        """Convert numeric score to description."""
        if score >= 8:
            return "excellent"
        if score >= 6:
            return "good"
        if score >= 4:
            return "developing"
        return "needs improvement"

    def _get_user_messages(self, messages: list[dict]) -> list[dict]:
        """Extract user messages from conversation."""
        return [m for m in messages if m.get("role") == "user"]

    def _get_assistant_messages(self, messages: list[dict]) -> list[dict]:
        """Extract assistant messages from conversation."""
        return [m for m in messages if m.get("role") == "assistant"]

    def _evaluate_patience(self, messages: list[dict]) -> DimensionScore:
        """Evaluate if trainee avoided pitching too early."""
        user_messages = self._get_user_messages(messages)
        premature_pitch_index = self._find_first_solution_mention(user_messages)

        if premature_pitch_index >= 0 and premature_pitch_index < EARLY_PITCH_MESSAGE_THRESHOLD:
            return DimensionScore(
                dimension="Patience",
                score=SCORE_POOR,
                max_score=MAX_SCORE,
                feedback="Solution offered too early. Spend more time understanding the problem before presenting solutions.",
            )

        if premature_pitch_index >= EARLY_PITCH_MESSAGE_THRESHOLD and premature_pitch_index < MODERATE_PITCH_MESSAGE_THRESHOLD:
            return DimensionScore(
                dimension="Patience",
                score=SCORE_MODERATE,
                max_score=MAX_SCORE,
                feedback="Good restraint, but could explore implications deeper before discussing solutions.",
            )

        return DimensionScore(
            dimension="Patience",
            score=SCORE_EXCELLENT,
            max_score=MAX_SCORE,
            feedback="Excellent patience. Focused on understanding before offering solutions.",
        )

    def _find_first_solution_mention(self, user_messages: list[dict]) -> int:
        """Find index of first message mentioning solutions. Returns -1 if none found."""
        for index, message in enumerate(user_messages):
            content = message.get("content", "").lower()
            if any(keyword in content for keyword in SOLUTION_KEYWORDS):
                return index
        return -1

    def _evaluate_implication_depth(self, messages: list[dict]) -> DimensionScore:
        """Evaluate depth of implication questions."""
        user_messages = self._get_user_messages(messages)
        implication_count, quantification_count = self._count_implication_keywords(user_messages)

        if implication_count >= IMPLICATION_EXCELLENT_COUNT and quantification_count >= QUANTIFICATION_EXCELLENT_COUNT:
            return DimensionScore(
                dimension="Implication Depth",
                score=SCORE_EXCELLENT,
                max_score=MAX_SCORE,
                feedback="Excellent exploration of implications with quantification of impact.",
            )

        if implication_count >= IMPLICATION_GOOD_COUNT or quantification_count >= QUANTIFICATION_GOOD_COUNT:
            return DimensionScore(
                dimension="Implication Depth",
                score=SCORE_GOOD,
                max_score=MAX_SCORE,
                feedback="Good implication questions. Try to quantify the impact more (costs, time, resources).",
            )

        if implication_count >= 1:
            return DimensionScore(
                dimension="Implication Depth",
                score=SCORE_DEVELOPING,
                max_score=MAX_SCORE,
                feedback="Some exploration of implications. Dig deeper into consequences and quantify the pain.",
            )

        return DimensionScore(
            dimension="Implication Depth",
            score=SCORE_POOR,
            max_score=MAX_SCORE,
            feedback="Limited implication exploration. Ask more about the impact and consequences of problems.",
        )

    def _count_implication_keywords(self, user_messages: list[dict]) -> tuple[int, int]:
        """Count implication and quantification keywords in messages."""
        implication_count = 0
        quantification_count = 0

        for message in user_messages:
            content = message.get("content", "").lower()
            if any(keyword in content for keyword in IMPLICATION_KEYWORDS):
                implication_count += 1
            if any(keyword in content for keyword in QUANTIFICATION_KEYWORDS):
                quantification_count += 1

        return implication_count, quantification_count

    def _evaluate_talk_ratio(self, messages: list[dict]) -> DimensionScore:
        """Evaluate if customer is talking more than trainee."""
        user_word_count = self._count_words(self._get_user_messages(messages))
        assistant_word_count = self._count_words(self._get_assistant_messages(messages))
        total_word_count = user_word_count + assistant_word_count

        if total_word_count == 0:
            return DimensionScore(
                dimension="Client Talk Ratio",
                score=SCORE_DEVELOPING,
                max_score=MAX_SCORE,
                feedback="Not enough data to evaluate.",
            )

        customer_talk_ratio = assistant_word_count / total_word_count

        if TARGET_CUSTOMER_TALK_RATIO_MIN <= customer_talk_ratio <= TARGET_CUSTOMER_TALK_RATIO_MAX:
            return DimensionScore(
                dimension="Client Talk Ratio",
                score=SCORE_EXCELLENT,
                max_score=MAX_SCORE,
                feedback="Excellent balance. Customer doing most of the talking indicates good questioning.",
            )

        if ACCEPTABLE_CUSTOMER_TALK_RATIO_MIN <= customer_talk_ratio < TARGET_CUSTOMER_TALK_RATIO_MIN:
            return DimensionScore(
                dimension="Client Talk Ratio",
                score=SCORE_GOOD,
                max_score=MAX_SCORE,
                feedback="Good listening. Ask more open questions to let the customer talk more.",
            )

        if customer_talk_ratio < ACCEPTABLE_CUSTOMER_TALK_RATIO_MIN:
            return DimensionScore(
                dimension="Client Talk Ratio",
                score=SCORE_NEEDS_WORK,
                max_score=MAX_SCORE,
                feedback="You are talking too much. Ask more questions and listen more.",
            )

        return DimensionScore(
            dimension="Client Talk Ratio",
            score=SCORE_MODERATE,
            max_score=MAX_SCORE,
            feedback="Customer talking a lot. Make sure to guide the conversation effectively.",
        )

    def _count_words(self, messages: list[dict]) -> int:
        """Count total words in a list of messages."""
        return sum(len(m.get("content", "").split()) for m in messages)

    def _evaluate_question_types(self, messages: list[dict]) -> DimensionScore:
        """Evaluate the quality and type of questions asked."""
        user_messages = self._get_user_messages(messages)
        open_count, closed_count = self._count_question_types(user_messages)
        total_questions = open_count + closed_count

        if total_questions == 0:
            return DimensionScore(
                dimension="Question Quality",
                score=SCORE_NEEDS_WORK,
                max_score=MAX_SCORE,
                feedback="Few questions asked. Use more questions to guide the discovery.",
            )

        open_ratio = open_count / total_questions

        if open_ratio >= OPEN_QUESTION_EXCELLENT_RATIO:
            return DimensionScore(
                dimension="Question Quality",
                score=SCORE_EXCELLENT,
                max_score=MAX_SCORE,
                feedback="Excellent use of open questions to explore the customer situation.",
            )

        if open_ratio >= OPEN_QUESTION_GOOD_RATIO:
            return DimensionScore(
                dimension="Question Quality",
                score=SCORE_GOOD,
                max_score=MAX_SCORE,
                feedback="Good mix of questions. Try to use more open questions (what, how, why).",
            )

        return DimensionScore(
            dimension="Question Quality",
            score=SCORE_DEVELOPING,
            max_score=MAX_SCORE,
            feedback="Too many closed questions. Use open questions to get richer information.",
        )

    def _count_question_types(self, user_messages: list[dict]) -> tuple[int, int]:
        """Count open and closed questions in messages."""
        open_count = 0
        closed_count = 0

        for message in user_messages:
            content = message.get("content", "").lower().strip()
            if "?" not in content:
                continue

            if any(content.startswith(starter) for starter in OPEN_QUESTION_STARTERS):
                open_count += 1
            elif any(content.startswith(starter) for starter in CLOSED_QUESTION_STARTERS):
                closed_count += 1
            else:
                open_count += 1  # Default unclear questions to open

        return open_count, closed_count

    # =========================================================================
    # NEW ClosR-SPECIFIC EVALUATION METHODS
    # =========================================================================

    def _evaluate_spin_sequence(self, messages: list[dict]) -> DimensionScore:
        """Evaluate if trainee follows proper S->P->I->N question progression."""
        user_messages = self._get_user_messages(messages)
        question_types = self._classify_spin_questions(user_messages)

        if not question_types:
            return DimensionScore(
                dimension="SPIN Sequence",
                score=SCORE_DEVELOPING,
                max_score=MAX_SCORE,
                feedback="Not enough questions to evaluate SPIN sequence.",
            )

        # Check for proper progression
        violations = self._count_sequence_violations(question_types)
        situation_overuse = self._count_situation_questions(question_types) > 3

        if violations == 0 and not situation_overuse:
            return DimensionScore(
                dimension="SPIN Sequence",
                score=SCORE_EXCELLENT,
                max_score=MAX_SCORE,
                feedback="Excellent SPIN progression. Questions flowed naturally from Situation through Need-Payoff.",
            )

        if violations <= 1 and not situation_overuse:
            return DimensionScore(
                dimension="SPIN Sequence",
                score=SCORE_GOOD,
                max_score=MAX_SCORE,
                feedback="Good SPIN sequence with minor deviations. Continue building depth before moving phases.",
            )

        if situation_overuse:
            return DimensionScore(
                dimension="SPIN Sequence",
                score=SCORE_NEEDS_WORK,
                max_score=MAX_SCORE,
                feedback="Too many Situation questions (max 3 recommended). Move to Problem questions sooner.",
            )

        return DimensionScore(
            dimension="SPIN Sequence",
            score=SCORE_DEVELOPING,
            max_score=MAX_SCORE,
            feedback="SPIN sequence needs work. Follow S->P->I->N progression more consistently.",
        )

    def _classify_spin_questions(self, user_messages: list[dict]) -> list[str]:
        """Classify each user message into SPIN category."""
        categories = []

        for message in user_messages:
            content = message.get("content", "").lower()

            if any(indicator in content for indicator in NEED_PAYOFF_INDICATORS):
                categories.append("N")
            elif any(indicator in content for indicator in IMPLICATION_INDICATORS):
                categories.append("I")
            elif any(indicator in content for indicator in PROBLEM_INDICATORS):
                categories.append("P")
            elif any(indicator in content for indicator in SITUATION_INDICATORS):
                categories.append("S")
            else:
                categories.append("O")  # Other (statement, non-SPIN question)

        return categories

    def _count_sequence_violations(self, question_types: list[str]) -> int:
        """Count backward movements in SPIN sequence (e.g., I->S is a violation)."""
        spin_order = {"S": 0, "P": 1, "I": 2, "N": 3, "O": -1}
        violations = 0
        max_reached = -1

        for q_type in question_types:
            if q_type == "O":
                continue

            current_order = spin_order.get(q_type, -1)

            # Going back more than one step is a violation
            if current_order < max_reached - 1:
                violations += 1

            max_reached = max(max_reached, current_order)

        return violations

    def _count_situation_questions(self, question_types: list[str]) -> int:
        """Count Situation questions in the sequence."""
        return sum(1 for q in question_types if q == "S")

    def _evaluate_vocabulary_compliance(self, messages: list[dict]) -> DimensionScore:
        """Evaluate use of forbidden vs encouraged vocabulary."""
        user_messages = self._get_user_messages(messages)

        forbidden_count = 0
        encouraged_count = 0
        disarming_count = 0
        confirming_count = 0

        for message in user_messages:
            content = message.get("content", "").lower()

            # Count forbidden phrases
            for phrase in FORBIDDEN_VOCABULARY:
                if phrase in content:
                    forbidden_count += 1

            # Count encouraged phrases
            for phrase in ENCOURAGED_VOCABULARY:
                if phrase in content:
                    encouraged_count += 1

            # Count disarming techniques
            for phrase in DISARMING_PHRASES:
                if phrase in content:
                    disarming_count += 1

            # Count confirming patterns
            for phrase in CONFIRMING_PATTERNS:
                if phrase in content:
                    confirming_count += 1

        total_positive = encouraged_count + disarming_count + confirming_count

        if forbidden_count >= 3:
            return DimensionScore(
                dimension="Vocabulary Compliance",
                score=SCORE_POOR,
                max_score=MAX_SCORE,
                feedback=f"Used {forbidden_count} forbidden phrases ('best on market', 'guarantee', etc.). Avoid sales pressure language.",
            )

        if forbidden_count >= 1:
            return DimensionScore(
                dimension="Vocabulary Compliance",
                score=SCORE_DEVELOPING,
                max_score=MAX_SCORE,
                feedback=f"Used {forbidden_count} forbidden phrase(s). Replace with consultative language like 'possibly', 'explore', 'find out'.",
            )

        if total_positive >= 3 and disarming_count >= 1:
            return DimensionScore(
                dimension="Vocabulary Compliance",
                score=SCORE_EXCELLENT,
                max_score=MAX_SCORE,
                feedback="Excellent NEPQ vocabulary. Good use of disarming phrases and consultative language.",
            )

        if total_positive >= 2:
            return DimensionScore(
                dimension="Vocabulary Compliance",
                score=SCORE_GOOD,
                max_score=MAX_SCORE,
                feedback="Good vocabulary choices. Try adding more disarming phrases ('I'm not sure if we can help...').",
            )

        return DimensionScore(
            dimension="Vocabulary Compliance",
            score=SCORE_MODERATE,
            max_score=MAX_SCORE,
            feedback="Neutral vocabulary. Use more NEPQ-encouraged phrases like 'possibly', 'find out', 'I'm not sure if...'.",
        )

    def _evaluate_monetization_quality(self, messages: list[dict]) -> DimensionScore:
        """Evaluate if trainee asked about quantifying the problem (costs, time, resources)."""
        user_messages = self._get_user_messages(messages)
        assistant_messages = self._get_assistant_messages(messages)

        monetization_asks = 0
        monetization_received = 0

        monetization_question_patterns = [
            "how much does",
            "what does that cost",
            "how many hours",
            "what's the financial",
            "what is the cost",
            "quantify",
            "in terms of money",
            "in terms of time",
            "dollar",
            "euro",
            "€",
            "$",
            "budget impact",
            "resources lost",
            "time lost",
            "what's it costing",
        ]

        monetization_response_patterns = [
            "€",
            "$",
            "euro",
            "dollar",
            "thousand",
            "million",
            "percent",
            "%",
            "hours per",
            "days per",
            "weeks per",
            "annually",
            "monthly",
            "quarterly",
            "per year",
            "per month",
        ]

        for message in user_messages:
            content = message.get("content", "").lower()
            if any(pattern in content for pattern in monetization_question_patterns):
                monetization_asks += 1

        for message in assistant_messages:
            content = message.get("content", "").lower()
            if any(pattern in content for pattern in monetization_response_patterns):
                monetization_received += 1

        if monetization_asks >= 2 and monetization_received >= 1:
            return DimensionScore(
                dimension="Monetization Quality",
                score=SCORE_EXCELLENT,
                max_score=MAX_SCORE,
                feedback="Excellent problem monetization. Successfully quantified the customer's pain in concrete terms.",
            )

        if monetization_asks >= 1 and monetization_received >= 1:
            return DimensionScore(
                dimension="Monetization Quality",
                score=SCORE_GOOD,
                max_score=MAX_SCORE,
                feedback="Good monetization effort. Continue probing for specific costs, time, and resource impacts.",
            )

        if monetization_asks >= 1:
            return DimensionScore(
                dimension="Monetization Quality",
                score=SCORE_MODERATE,
                max_score=MAX_SCORE,
                feedback="Asked about quantification but didn't unlock specific numbers. Probe deeper with follow-up questions.",
            )

        return DimensionScore(
            dimension="Monetization Quality",
            score=SCORE_NEEDS_WORK,
            max_score=MAX_SCORE,
            feedback="Missing problem monetization. Ask 'How much does this cost you?' or 'What's the financial impact?'",
        )
