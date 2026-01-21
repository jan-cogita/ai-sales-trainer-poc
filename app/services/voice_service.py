"""Voice service abstraction for multiple providers."""

from app.config import get_settings
from app.logging_config import get_logger
from app.services.elevenlabs_service import ElevenLabsService
from app.services.openai_voice_service import OpenAIVoiceService

logger = get_logger("voice_service")

# Provider identifiers (must match config values)
PROVIDER_OPENAI = "openai"
PROVIDER_ELEVENLABS = "elevenlabs"


class VoiceService:
    """Unified voice service that delegates to configured provider.

    Supports:
    - OpenAI Realtime API (default): Returns ephemeral token + WebSocket URL
    - ElevenLabs: Returns signed WebSocket URL (self-authenticating)
    """

    def __init__(self):
        self.settings = get_settings()
        self._openai_service = None
        self._elevenlabs_service = None

    @property
    def provider(self) -> str:
        return self.settings.voice_provider

    async def get_conversation_credentials(self, agent_id: str | None = None) -> dict:
        """Get credentials for starting a voice conversation.

        Args:
            agent_id: Required for ElevenLabs, ignored for OpenAI

        Returns:
            dict with:
            - url: WebSocket URL to connect to
            - token: Auth token (OpenAI) or None (ElevenLabs - URL is self-authenticating)
            - provider: "openai" or "elevenlabs"
        """
        if self.provider == PROVIDER_OPENAI:
            return await self._get_openai_credentials()
        elif self.provider == PROVIDER_ELEVENLABS:
            if not agent_id:
                raise ValueError("agent_id is required for ElevenLabs provider")
            return await self._get_elevenlabs_credentials(agent_id)
        else:
            raise ValueError(f"Unknown voice provider: {self.provider}")

    async def _get_openai_credentials(self) -> dict:
        """Get OpenAI Realtime credentials."""
        if self._openai_service is None:
            self._openai_service = OpenAIVoiceService()

        result = await self._openai_service.get_ephemeral_token()
        logger.info("Retrieved OpenAI voice credentials")

        return {
            "url": result["url"],
            "token": result["token"],
            "provider": PROVIDER_OPENAI,
        }

    async def _get_elevenlabs_credentials(self, agent_id: str) -> dict:
        """Get ElevenLabs signed URL credentials."""
        if self._elevenlabs_service is None:
            self._elevenlabs_service = ElevenLabsService()

        signed_url = await self._elevenlabs_service.get_signed_conversation_url(agent_id)
        logger.info("Retrieved ElevenLabs voice credentials", extra={"agent_id": agent_id})

        return {
            "url": signed_url,
            "token": None,
            "provider": PROVIDER_ELEVENLABS,
        }
