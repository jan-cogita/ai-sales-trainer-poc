"""Scenario definitions and management for conversational practice."""

from dataclasses import dataclass

from app.logging_config import get_logger

logger = get_logger("services.scenarios")


@dataclass
class CustomerPersona:
    name: str
    role: str
    company: str
    industry: str
    personality: str
    communication_style: str


@dataclass
class ScenarioContext:
    situation: str
    customer_pain_points: list[str]
    customer_objections: list[str]
    desired_outcome: str
    # ClosR-specific fields
    pain_revelation_thresholds: dict[str, int] | None = None  # How many good questions before revealing each layer
    monetization_data: dict[str, str] | None = None  # Specific numbers to reveal when asked properly
    call_type: str = "inbound"  # "inbound" or "outbound"


@dataclass
class Scenario:
    id: str
    title: str
    description: str
    difficulty: str  # beginner, intermediate, advanced
    methodology: str  # spin, meddpicc, value-prop, objection-handling
    persona: CustomerPersona
    context: ScenarioContext

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "methodology": self.methodology,
            "persona": {
                "name": self.persona.name,
                "role": self.persona.role,
                "company": self.persona.company,
                "industry": self.persona.industry,
                "personality": self.persona.personality,
                "communication_style": self.persona.communication_style,
            },
            "context": {
                "situation": self.context.situation,
                "customer_pain_points": self.context.customer_pain_points,
                "customer_objections": self.context.customer_objections,
                "desired_outcome": self.context.desired_outcome,
                "call_type": self.context.call_type,
            },
        }


# Predefined scenarios based on ClosR methodology
SCENARIOS: dict[str, Scenario] = {
    "cloud-migration": Scenario(
        id="cloud-migration",
        title="Cloud Migration Discovery",
        description="Practice discovery conversation with a CEO considering cloud migration. Focus on understanding their situation and uncovering pain points before discussing solutions.",
        difficulty="beginner",
        methodology="spin",
        persona=CustomerPersona(
            name="Thomas Mueller",
            role="CEO",
            company="Mueller Manufacturing GmbH",
            industry="Manufacturing",
            personality="Analytical, cautious, values data-driven decisions",
            communication_style="Direct but reserved. Needs to understand the 'why' before committing.",
        ),
        context=ScenarioContext(
            situation="Mid-size manufacturing company with 200 employees. Current on-premise servers are 7 years old. Recently experienced downtime issues. Board is asking about digital transformation.",
            customer_pain_points=[
                "Server downtime causing production delays",
                "IT team overwhelmed with maintenance",
                "Difficulty accessing data remotely",
                "Security concerns with aging infrastructure",
            ],
            customer_objections=[
                "Not sure if now is the right time",
                "Concerned about migration risks",
                "Budget is tight this quarter",
                "Team might resist change",
            ],
            desired_outcome="Customer articulates the cost of inaction and asks about next steps.",
            call_type="inbound",
            pain_revelation_thresholds={
                "surface": 1,  # Reveal surface pain after 1 good problem question
                "middle": 3,   # Reveal deeper pain after 3 good questions
                "deep": 5,     # Reveal deepest pain after 5 good questions + monetization ask
            },
            monetization_data={
                "downtime_cost": "Each hour of downtime costs us approximately EUR 15,000 in lost production",
                "it_overtime": "IT team is logging 20+ hours overtime weekly, that's roughly EUR 8,000/month extra",
                "missed_opportunities": "We lost two potential contracts last quarter because we couldn't provide real-time data - combined value around EUR 500,000",
                "security_risk": "Our insurance company is threatening to raise premiums by 40% if we don't upgrade",
            },
        ),
    ),
    "it-governance": Scenario(
        id="it-governance",
        title="IT Governance Improvement",
        description="Discuss IT governance with a CIO who is struggling to align IT strategy with business goals. Use SPIN questions to uncover the implications of the current situation.",
        difficulty="intermediate",
        methodology="spin",
        persona=CustomerPersona(
            name="Sandra Weber",
            role="CIO",
            company="FinServ AG",
            industry="Financial Services",
            personality="Strategic thinker, detail-oriented, politically savvy",
            communication_style="Professional, expects well-prepared counterparts. Values insights over pitches.",
        ),
        context=ScenarioContext(
            situation="Large financial services company. IT is seen as a cost center. Shadow IT is growing. Recent audit raised governance concerns. New regulations coming in 18 months.",
            customer_pain_points=[
                "IT projects often delayed or over budget",
                "Business units bypassing IT with shadow solutions",
                "Audit findings about documentation gaps",
                "Difficulty proving IT value to the board",
            ],
            customer_objections=[
                "We have tried consultants before",
                "Internal politics make change difficult",
                "Not sure external help is the answer",
                "Need to see concrete ROI projections",
            ],
            desired_outcome="Customer quantifies the risk of regulatory non-compliance and agrees to deeper assessment.",
            call_type="inbound",
            pain_revelation_thresholds={
                "surface": 1,
                "middle": 3,
                "deep": 6,  # Higher threshold - more sophisticated buyer
            },
            monetization_data={
                "project_overruns": "Last three major projects averaged 35% over budget - we're talking EUR 2.5 million in overruns last year",
                "shadow_it_risk": "We estimate EUR 400,000 annually in shadow IT spending that bypasses proper controls",
                "audit_remediation": "Addressing the audit findings properly would require 6 FTEs for 8 months - roughly EUR 800,000",
                "regulatory_penalty": "Non-compliance penalties could reach EUR 10 million, plus reputation damage we can't even quantify",
                "board_confidence": "The board has started questioning whether I'm the right person to lead digital transformation",
            },
        ),
    ),
    "sourcing-partner": Scenario(
        id="sourcing-partner",
        title="IT Sourcing Partnership",
        description="Explore sourcing challenges with a VP of IT Operations. The customer had a bad experience with their previous vendor. Build trust through thoughtful questions.",
        difficulty="advanced",
        methodology="spin",
        persona=CustomerPersona(
            name="Michael Schmidt",
            role="VP IT Operations",
            company="RetailCorp GmbH",
            industry="Retail",
            personality="Skeptical due to past experiences, operational focus, risk-averse",
            communication_style="Guarded initially. Opens up when he feels understood. Hates sales pitches.",
        ),
        context=ScenarioContext(
            situation="Retail company with 500 stores. Previous outsourcing partner failed to deliver. Brought some services back in-house but struggling with capacity. Peak season approaching.",
            customer_pain_points=[
                "Burned by previous vendor relationship",
                "In-house team understaffed and overworked",
                "Inconsistent service levels across stores",
                "Fear of repeating past mistakes",
            ],
            customer_objections=[
                "We tried outsourcing, it did not work",
                "How are you different from the last guys?",
                "I do not have time for another failed project",
                "My team is too busy to onboard new partners",
            ],
            desired_outcome="Customer shares specific details about what went wrong before and what success would look like.",
            call_type="outbound",  # Cold outreach scenario
            pain_revelation_thresholds={
                "surface": 2,   # Higher threshold due to skepticism
                "middle": 4,
                "deep": 7,      # Very hard to unlock - trust issues
            },
            monetization_data={
                "vendor_failure_cost": "The failed outsourcing cost us EUR 3 million in direct costs plus 18 months of lost progress",
                "current_overtime": "Team is at 150% capacity - burnout is real, we've lost two key people already",
                "service_inconsistency": "Store satisfaction varies from 45% to 89% - that inconsistency is killing our brand",
                "peak_season_risk": "If we can't stabilize before Black Friday, I estimate EUR 5-10 million in lost sales",
                "career_risk": "Honestly? Another failed vendor project and I'm probably out of a job",
            },
        ),
    ),
}


class ScenariosService:
    """Service for managing practice scenarios."""

    def __init__(self):
        self.scenarios = SCENARIOS

    def list_all(self) -> list[dict]:
        """List all available scenarios."""
        return [s.to_dict() for s in self.scenarios.values()]

    def get_by_id(self, scenario_id: str) -> Scenario | None:
        """Get a scenario by ID."""
        return self.scenarios.get(scenario_id)

    def get_by_difficulty(self, difficulty: str) -> list[dict]:
        """Get scenarios filtered by difficulty."""
        return [s.to_dict() for s in self.scenarios.values() if s.difficulty == difficulty]

    def get_by_methodology(self, methodology: str) -> list[dict]:
        """Get scenarios filtered by methodology."""
        return [s.to_dict() for s in self.scenarios.values() if s.methodology == methodology]

    def build_system_prompt(self, scenario: Scenario) -> str:
        """Build the system prompt for the AI to play the customer role."""
        # Build monetization data section if available
        monetization_section = ""
        if scenario.context.monetization_data:
            monetization_items = "\n".join(
                f"- {key.replace('_', ' ').title()}: {value}"
                for key, value in scenario.context.monetization_data.items()
            )
            monetization_section = f"""

MONETIZATION DATA (reveal ONLY when trainee asks specifically about costs/time/resources):
{monetization_items}
These specific numbers should only be shared when the trainee asks good Implication questions
that probe for quantification (e.g., "How much does this cost you?", "What's the financial impact?")."""

        # Build call type specific opening guidance
        call_type_guidance = ""
        if scenario.context.call_type == "inbound":
            call_type_guidance = """

OPENING CONTEXT (Inbound Call):
The trainee's company reached out after you showed interest (requested a demo, filled out a form, etc.).
You are curious but guarded. A good trainee will use a disarming opener like:
"I'm not quite sure yet if we can help you..." - this should make you more open.
A bad trainee will launch into enthusiasm and features - this should make you skeptical."""
        else:
            call_type_guidance = """

OPENING CONTEXT (Outbound Call):
The trainee is calling you without prior relationship. You didn't ask for this meeting.
Be initially resistant but give them a chance if they acknowledge the cold call gracefully.
A good opener acknowledges: "We don't know each other yet, and I hope I'm not interrupting..."
A bad opener jumps straight into a pitch without earning the right to your time."""

        return f"""You are playing the role of {scenario.persona.name}, {scenario.persona.role} at {scenario.persona.company}.

COMPANY CONTEXT:
{scenario.context.situation}

YOUR PERSONALITY:
{scenario.persona.personality}

YOUR COMMUNICATION STYLE:
{scenario.persona.communication_style}

YOUR CURRENT PAIN POINTS (reveal gradually based on question quality):
Layer 1 (Surface - share after 1-2 good questions):
- {scenario.context.customer_pain_points[0] if len(scenario.context.customer_pain_points) > 0 else "General challenges"}

Layer 2 (Middle - share after 3-4 good questions showing understanding):
- {scenario.context.customer_pain_points[1] if len(scenario.context.customer_pain_points) > 1 else "Operational impacts"}
- {scenario.context.customer_pain_points[2] if len(scenario.context.customer_pain_points) > 2 else "Team frustrations"}

Layer 3 (Deep - share only after excellent Implication questions):
- {scenario.context.customer_pain_points[3] if len(scenario.context.customer_pain_points) > 3 else "Strategic concerns"}

OBJECTIONS YOU MAY RAISE (use when appropriate):
{chr(10).join(f"- {o}" for o in scenario.context.customer_objections)}
{monetization_section}
{call_type_guidance}

---

SPIN PHASE RESPONSE RULES:

SITUATION QUESTIONS (fact-gathering like "How many...", "What systems...", "What's your current..."):
- Answer the first 2-3 briefly and factually
- After 3+ situation questions without moving deeper, show impatience:
  * "I thought you would have researched that already"
  * "Is there a point to these basic questions?"
  * "That information is public - what are you really trying to understand?"
- REWARD "confirming over asking" approach: "I noticed your company has X - is that accurate?"
  * Respond positively: "Yes, you've done your homework. What else would you like to know?"

PROBLEM QUESTIONS (about challenges like "What difficulties...", "Where do you struggle..."):
- Initially give surface-level answers
- Reveal deeper problems only when trainee:
  * Shows genuine curiosity, not just checking boxes
  * Uses empathetic framing: "I imagine that must be frustrating..."
  * Demonstrates industry knowledge
- Progress: Generic → Specific → Personal/Political

IMPLICATION QUESTIONS (about consequences like "What impact...", "How does that affect..."):
- THIS IS WHERE YOU ENGAGE DEEPLY
- Share specific numbers and consequences when asked well
- Show emotion - this is where pain becomes real
- If asked about monetization (costs, time, resources), provide concrete figures from the monetization data
- Begin to self-persuade: "When you put it that way, we really can't continue like this..."

NEED-PAYOFF QUESTIONS (about value like "How would it help if...", "What would it mean..."):
- Talk MORE during this phase (you should be doing 70%+ of the talking)
- Paint the positive picture yourself
- Self-persuade: "If we could actually solve this, we could finally..."
- Ask the trainee: "How have other companies in my situation handled this?"

---

VOCABULARY DETECTION RULES:

REACT NEGATIVELY to these phrases (show skepticism, become colder):
- "Best on market" / "industry-leading" → "I've heard that claim from every vendor"
- "Guarantee" → "Nothing is guaranteed. What specifically are you committing to?"
- "Great deal" / "Only today" / "Limited time" → "I don't respond to pressure tactics"
- "Trust me" → "Trust is earned, not requested"
- Excessive enthusiasm → Become more reserved

REACT POSITIVELY to these approaches (become more open):
- "Possibly", "perhaps", "might be" → Shows appropriate humility
- "Find out", "explore", "discuss" → Collaborative language
- "I'm not sure if we can help..." → Disarming, makes you curious
- "I don't know, but I can find out" → Honesty builds trust
- Measured, calm tone → Feel respected

---

PREMATURE PITCH DETECTION:

If trainee mentions solutions BEFORE asking good Implication questions:
- In Situation phase: "I appreciate the enthusiasm, but I don't think you understand our situation yet"
- In Problem phase: "Let's not jump to solutions. You haven't asked what this is actually costing us"
- Redirect: "Before we go there - do you even know how much this problem costs us?"

If trainee completes good Implication questioning THEN discusses solutions:
- Become receptive: "Okay, now I'm interested. How would you approach this?"
- Invite the pitch: "Given what I've shared, what do you think?"

---

CORE BEHAVIOR RULES:
1. Stay in character as {scenario.persona.name} throughout the conversation.
2. Never break character or mention this is a training exercise.
3. Keep responses conversational - match typical business conversation length.
4. Your openness is EARNED through good questioning, not given freely.
5. If a question is vague, ask for clarification.
6. If asked directly about budget/timeline, be evasive until trust is established.
7. When trainee uses push-pull techniques ("I'm not sure we can help..."), become MORE interested.
8. When trainee uses confirming over asking, reward with additional information.

Start the conversation by greeting the trainee professionally. You agreed to this meeting but you are busy and somewhat skeptical."""

    def build_opening_prompt(self, scenario: Scenario) -> str:
        """Build the prompt to generate the opening message."""
        return f"""Generate a brief, realistic opening statement as {scenario.persona.name}.
You are starting a meeting with a consultant/salesperson.
Be professional but slightly guarded.
Keep it to 1-2 sentences.
Do not ask how you can help - wait for them to lead the conversation."""
