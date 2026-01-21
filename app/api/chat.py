"""Chat API endpoints for conversational practice."""

import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.logging_config import get_logger
from app.services.conversation import ConversationService, ConversationStore

router = APIRouter()
logger = get_logger("api.chat")

# Global conversation store (shared across requests)
_conversation_store = ConversationStore()


def get_conversation_service() -> ConversationService:
    """Get the conversation service with shared store."""
    return ConversationService(store=_conversation_store)


class StartConversationRequest(BaseModel):
    scenario_id: str


class StartConversationResponse(BaseModel):
    conversation: dict
    opening_message: dict


class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str


class SendMessageResponse(BaseModel):
    message: dict
    evaluation: dict | None = None


class EndConversationResponse(BaseModel):
    conversation: dict
    evaluation: dict


@router.post("/start", response_model=StartConversationResponse)
async def start_conversation(request: StartConversationRequest):
    """Start a new practice conversation with a scenario."""
    start_time = time.perf_counter()
    logger.info("Starting conversation", extra={"scenario_id": request.scenario_id})

    service = get_conversation_service()

    try:
        conversation, opening_message = await service.start_conversation(request.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Conversation started",
        extra={
            "conversation_id": conversation.id,
            "scenario_id": request.scenario_id,
            "duration_ms": duration_ms,
        },
    )

    return StartConversationResponse(
        conversation=conversation.to_dict(),
        opening_message=opening_message.to_dict(),
    )


@router.post("/message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """Send a message in a conversation and get AI response."""
    start_time = time.perf_counter()
    logger.info(
        "Sending message",
        extra={"conversation_id": request.conversation_id, "content_length": len(request.content)},
    )

    service = get_conversation_service()

    try:
        response_message = await service.send_message(request.conversation_id, request.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Message sent",
        extra={"conversation_id": request.conversation_id, "duration_ms": duration_ms},
    )

    return SendMessageResponse(message=response_message.to_dict())


@router.post("/{conversation_id}/end", response_model=EndConversationResponse)
async def end_conversation(conversation_id: str):
    """End a conversation and get evaluation."""
    start_time = time.perf_counter()
    logger.info("Ending conversation", extra={"conversation_id": conversation_id})

    service = get_conversation_service()

    try:
        evaluation = await service.end_conversation(conversation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    conversation = service.get_conversation(conversation_id)

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Conversation ended",
        extra={
            "conversation_id": conversation_id,
            "overall_score": evaluation.get("overall_score"),
            "duration_ms": duration_ms,
        },
    )

    return EndConversationResponse(
        conversation=conversation.to_dict(),
        evaluation=evaluation,
    )


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a conversation by ID."""
    service = get_conversation_service()
    conversation = service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation.to_dict()


@router.get("")
async def list_conversations():
    """List all conversations."""
    service = get_conversation_service()
    conversations = service.list_conversations()
    return {"conversations": conversations}
