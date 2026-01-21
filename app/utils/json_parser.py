"""Utility functions for parsing LLM JSON responses."""

import json


def parse_llm_json_response(response_text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks.

    LLMs often wrap JSON in markdown code blocks like:
    ```json
    {"key": "value"}
    ```

    This function strips those wrappers and parses the JSON.

    Args:
        response_text: Raw text response from LLM

    Returns:
        Parsed JSON as dictionary

    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    cleaned_response = response_text.strip()

    # Remove markdown code block wrapper if present
    if cleaned_response.startswith("```"):
        # Split by ``` and take the content part
        parts = cleaned_response.split("```")
        if len(parts) >= 2:
            cleaned_response = parts[1]
            # Remove language identifier (e.g., "json")
            if cleaned_response.startswith("json"):
                cleaned_response = cleaned_response[4:]

    cleaned_response = cleaned_response.strip()
    return json.loads(cleaned_response)
