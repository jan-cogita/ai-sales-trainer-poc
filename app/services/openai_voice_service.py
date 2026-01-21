"""OpenAI Realtime API service for voice conversations."""

import httpx

from app.config import get_settings
from app.logging_config import get_logger
from app.retry import retry_external_api

logger = get_logger("openai_voice")

# API configuration
REALTIME_MODEL = "gpt-4o-realtime-preview"
REALTIME_URL = "wss://api.openai.com/v1/realtime"
SESSIONS_ENDPOINT = "https://api.openai.com/v1/realtime/sessions"
REQUEST_TIMEOUT_SECONDS = 30


class OpenAIVoiceService:
    """Auth proxy for OpenAI Realtime API.

    This service generates ephemeral tokens for client-side WebSocket connections
    to the OpenAI Realtime API, keeping the API key server-side.
    """

    def __init__(self):
        self.settings = get_settings()

    @retry_external_api
    async def get_ephemeral_token(self) -> dict:
        """Get an ephemeral token for OpenAI Realtime API connection.

        Returns:
            dict with 'token' and 'url' keys for client WebSocket connection
        """
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as http:
            response = await http.post(
                SESSIONS_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": REALTIME_MODEL,
                    "voice": "verse",
                },
            )
            response.raise_for_status()
            data = response.json()

            token = data["client_secret"]["value"]
            url = f"{REALTIME_URL}?model={REALTIME_MODEL}"

            logger.info("Generated ephemeral token for OpenAI Realtime")
            return {"token": token, "url": url}
