"""Helper functions for LLM operations with standard error handling."""

import json

from fastapi import HTTPException

from app.services.llm import LLMService
from app.utils.json_parser import parse_llm_json_response


async def call_llm_json(
    messages: list[dict],
    system_prompt: str | None = None,
    operation_name: str = "LLM call",
) -> dict:
    """Call LLM and parse JSON response with standard error handling.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        system_prompt: Optional system prompt for the LLM.
        operation_name: Name of the operation for error messages.

    Returns:
        Parsed JSON response as a dictionary.

    Raises:
        HTTPException: On JSON parse failure (500) or other errors (500).
    """
    llm_service = LLMService()
    try:
        response_text = await llm_service.chat_completion(
            messages,
            system_prompt=system_prompt,
        )
        return parse_llm_json_response(response_text)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse {operation_name} response",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{operation_name} failed: {str(e)}",
        )
