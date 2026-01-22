"""Conversation state management for practice sessions."""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from app.logging_config import get_logger
from app.services.evaluation import EvaluationService
from app.services.llm import LLMService
from app.services.scenarios import ScenariosService

logger = get_logger("services.conversation")

# =============================================================================
# CONSTANTS
# =============================================================================

CONVERSATION_ID_LENGTH = 12
MESSAGE_ID_LENGTH = 8


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class ChatMessage:
    id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass
class Conversation:
    id: str
    scenario_id: str
    status: ConversationStatus
    messages: list[ChatMessage] = field(default_factory=list)
    started_at: str = ""
    completed_at: str | None = None
    evaluation: dict | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "status": self.status.value,
            "messages": [m.to_dict() for m in self.messages],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "evaluation": self.evaluation,
        }


class ConversationStore:
    """In-memory store for conversations (for PoC)."""

    def __init__(self):
        self._conversations: dict[str, Conversation] = {}

    def create(self, scenario_id: str) -> Conversation:
        """Create a new conversation."""
        conv_id = f"conv-{uuid.uuid4().hex[:CONVERSATION_ID_LENGTH]}"
        conversation = Conversation(
            id=conv_id,
            scenario_id=scenario_id,
            status=ConversationStatus.ACTIVE,
            messages=[],
            started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._conversations[conv_id] = conversation
        logger.info("Conversation created", extra={"conversation_id": conv_id, "scenario_id": scenario_id})
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self._conversations.get(conversation_id)

    def add_message(self, conversation_id: str, role: str, content: str) -> ChatMessage | None:
        """Add a message to a conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None

        message = ChatMessage(
            id=f"msg-{uuid.uuid4().hex[:MESSAGE_ID_LENGTH]}",
            role=role,
            content=content,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        conversation.messages.append(message)
        return message

    def update_status(self, conversation_id: str, status: ConversationStatus) -> None:
        """Update conversation status."""
        conversation = self._conversations.get(conversation_id)
        if conversation:
            conversation.status = status
            if status == ConversationStatus.COMPLETED:
                conversation.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def set_evaluation(self, conversation_id: str, evaluation: dict) -> None:
        """Set evaluation results for a conversation."""
        conversation = self._conversations.get(conversation_id)
        if conversation:
            conversation.evaluation = evaluation

    def list_all(self) -> list[Conversation]:
        """List all conversations."""
        return list(self._conversations.values())

    def list_active(self) -> list[Conversation]:
        """List active conversations."""
        return [c for c in self._conversations.values() if c.status == ConversationStatus.ACTIVE]


class ConversationService:
    """Service for managing practice conversations."""

    def __init__(self, store: ConversationStore | None = None):
        self.store = store or ConversationStore()
        self.scenarios_service = ScenariosService()
        self.llm_service = LLMService()
        self.evaluation_service = EvaluationService()

    async def start_conversation(self, scenario_id: str) -> tuple[Conversation, ChatMessage]:
        """Start a new conversation with a scenario."""
        scenario = self.scenarios_service.get_by_id(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_id}")

        # Create conversation
        conversation = self.store.create(scenario_id)

        # Generate opening message from AI customer
        system_prompt = self.scenarios_service.build_system_prompt(scenario)
        opening_prompt = self.scenarios_service.build_opening_prompt(scenario)

        opening_content = await self.llm_service.chat_completion(
            messages=[{"role": "user", "content": opening_prompt}],
            system_prompt=system_prompt,
        )

        # Add opening message
        opening_message = self.store.add_message(conversation.id, "assistant", opening_content)

        logger.info(
            "Conversation started",
            extra={"conversation_id": conversation.id, "scenario_id": scenario_id},
        )

        return conversation, opening_message

    async def send_message(self, conversation_id: str, content: str) -> ChatMessage:
        """Send a user message and get AI response."""
        conversation = self.store.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        if conversation.status != ConversationStatus.ACTIVE:
            raise ValueError("Conversation is not active")

        scenario = self.scenarios_service.get_by_id(conversation.scenario_id)
        if not scenario:
            raise ValueError("Scenario not found")

        # Add user message
        self.store.add_message(conversation_id, "user", content)

        # Build message history for LLM
        system_prompt = self.scenarios_service.build_system_prompt(scenario)
        messages = [{"role": m.role, "content": m.content} for m in conversation.messages]

        # Get AI response
        ai_response = await self.llm_service.chat_completion(
            messages=messages,
            system_prompt=system_prompt,
        )

        # Add AI response
        response_message = self.store.add_message(conversation_id, "assistant", ai_response)

        logger.debug(
            "Message exchanged",
            extra={"conversation_id": conversation_id, "user_length": len(content)},
        )

        return response_message

    async def end_conversation(self, conversation_id: str) -> dict:
        """End a conversation and generate evaluation."""
        conversation = self.store.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # Mark as completed
        self.store.update_status(conversation_id, ConversationStatus.COMPLETED)

        # Generate evaluation
        evaluation = await self._evaluate_conversation(conversation)
        self.store.set_evaluation(conversation_id, evaluation)

        logger.info(
            "Conversation ended",
            extra={"conversation_id": conversation_id, "score": evaluation.get("overall_score")},
        )

        return evaluation

    async def _evaluate_conversation(self, conversation: Conversation) -> dict:
        """Evaluate the conversation using the EvaluationService."""
        messages = [{"role": m.role, "content": m.content} for m in conversation.messages]
        result = await self.evaluation_service.evaluate(messages)
        return result.to_dict()

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        return self.store.get(conversation_id)

    def list_conversations(self) -> list[dict]:
        """List all conversations."""
        return [c.to_dict() for c in self.store.list_all()]
