"""ElevenLabs service for conversation URL signing."""

import httpx

from app.config import get_settings
from app.logging_config import get_logger
from app.retry import retry_external_api

logger = get_logger("elevenlabs")


class ElevenLabsService:
    """Auth proxy for ElevenLabs conversational AI.

    This service only handles signed URL generation - keeping the API key
    server-side while letting clients connect directly to ElevenLabs WebSocket.
    """

    def __init__(self):
        self.settings = get_settings()

    @retry_external_api
    async def get_signed_conversation_url(self, agent_id: str) -> str:
        """Get a signed URL for real-time conversation with an agent."""
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.get(
                "https://api.elevenlabs.io/v1/convai/conversation/get_signed_url",
                params={"agent_id": agent_id},
                headers={"xi-api-key": self.settings.elevenlabs_api_key},
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Got signed conversation URL", extra={"agent_id": agent_id})
            return data["signed_url"]
