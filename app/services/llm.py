"""LLM service for embeddings and chat completions."""

import time
from pathlib import Path

from google import genai
from google.genai import types
from openai import OpenAI

from app.config import get_settings
from app.logging_config import get_logger
from app.retry import retry_llm

logger = get_logger("llm")

# =============================================================================
# CONSTANTS - Model Names
# =============================================================================

GEMINI_EMBEDDING_MODEL = "text-embedding-004"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
GEMINI_CHAT_MODEL = "gemini-2.0-flash-lite"
OPENAI_CHAT_MODEL = "gpt-4o"


class LLMService:
    """Service for LLM operations (embeddings and chat completions)."""

    def __init__(self):
        self.settings = get_settings()
        self._openai_client: OpenAI | None = None
        self._gemini_client: genai.Client | None = None

    @property
    def openai_client(self) -> OpenAI:
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=self.settings.openai_api_key)
        return self._openai_client

    @property
    def gemini_client(self) -> genai.Client:
        if self._gemini_client is None:
            self._gemini_client = genai.Client(api_key=self.settings.google_api_key)
        return self._gemini_client

    @retry_llm
    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for text using configured provider."""
        start_time = time.perf_counter()
        provider = self.settings.llm_provider

        try:
            if provider == "gemini":
                response = self.gemini_client.models.embed_content(
                    model=GEMINI_EMBEDDING_MODEL,
                    contents=text,
                )
                embedding = response.embeddings[0].values
            else:
                response = self.openai_client.embeddings.create(
                    model=OPENAI_EMBEDDING_MODEL,
                    input=text,
                )
                embedding = response.data[0].embedding

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.debug("Embedding generated", extra={"duration_ms": duration_ms})
            return embedding

        except Exception as e:
            logger.error("Embedding generation failed: %s", str(e))
            raise

    @retry_llm
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts using configured provider."""
        start_time = time.perf_counter()
        provider = self.settings.llm_provider

        try:
            if provider == "gemini":
                embeddings = []
                for text in texts:
                    response = self.gemini_client.models.embed_content(
                        model=GEMINI_EMBEDDING_MODEL,
                        contents=text,
                    )
                    embeddings.append(response.embeddings[0].values)
            else:
                response = self.openai_client.embeddings.create(
                    model=OPENAI_EMBEDDING_MODEL,
                    input=texts,
                )
                embeddings = [item.embedding for item in response.data]

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "Batch embeddings generated",
                extra={"count": len(texts), "duration_ms": duration_ms},
            )
            return embeddings

        except Exception as e:
            logger.error("Batch embedding generation failed: %s", str(e))
            raise

    @retry_llm
    async def chat_completion(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Get chat completion from configured LLM provider."""
        start_time = time.perf_counter()
        provider = self.settings.llm_provider

        try:
            if provider == "openai":
                result = await self._openai_chat(messages, system_prompt, model, temperature)
            elif provider == "gemini":
                result = await self._gemini_chat(messages, system_prompt, model, temperature)
            else:
                raise ValueError(f"Unknown LLM provider: {provider}")

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "Chat completion generated",
                extra={"provider": provider, "duration_ms": duration_ms},
            )
            return result

        except Exception as e:
            logger.error("Chat completion failed: %s", str(e))
            raise

    async def _openai_chat(
        self,
        messages: list[dict],
        system_prompt: str | None,
        model: str | None,
        temperature: float,
    ) -> str:
        """OpenAI chat completion."""
        model = model or OPENAI_CHAT_MODEL
        all_messages = []

        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        response = self.openai_client.chat.completions.create(
            model=model,
            messages=all_messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def _gemini_chat(
        self,
        messages: list[dict],
        system_prompt: str | None,
        model: str | None,
        temperature: float,
    ) -> str:
        """Gemini chat completion using google-genai SDK."""
        model_name = model or GEMINI_CHAT_MODEL

        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt,
        )

        response = self.gemini_client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
        return response.text

    def load_prompt(self, prompt_name: str) -> str:
        """Load a prompt template from the prompts directory."""
        prompt_path = Path("prompts") / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_name}")
        return prompt_path.read_text()
