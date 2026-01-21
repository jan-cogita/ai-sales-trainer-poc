"""Voice API endpoint for conversation auth proxy (OpenAI / ElevenLabs)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.logging_config import get_logger
from app.services.voice_service import VoiceService

router = APIRouter()
logger = get_logger("api.voice")


class ConversationRequest(BaseModel):
    agent_id: str | None = None  # Required for ElevenLabs, optional for OpenAI


class ConversationResponse(BaseModel):
    url: str
    token: str | None = None
    provider: str


@router.post("/conversation/start", response_model=ConversationResponse)
async def start_conversation(request: ConversationRequest):
    """Get credentials for starting a voice conversation.

    The response format depends on the configured VOICE_PROVIDER:
    - OpenAI: Returns WebSocket URL + ephemeral token (token must be sent as auth header)
    - ElevenLabs: Returns signed WebSocket URL (self-authenticating, no token needed)

    The client connects directly to the provider using these credentials.
    This endpoint acts as an auth proxy - keeping API keys server-side.
    """
    service = VoiceService()

    logger.info(
        "Requesting voice credentials",
        extra={"provider": service.provider, "agent_id": request.agent_id},
    )

    try:
        credentials = await service.get_conversation_credentials(request.agent_id)
        logger.info(
            "Voice credentials generated",
            extra={"provider": credentials["provider"]},
        )
        return ConversationResponse(**credentials)
    except ValueError as e:
        logger.warning("Invalid request: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to get voice credentials: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get voice credentials: {str(e)}")
