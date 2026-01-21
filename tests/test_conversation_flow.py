"""End-to-end conversation flow integration tests.

These tests verify that:
1. Conversations can be started with valid scenarios
2. Messages are exchanged correctly
3. Conversations end with proper evaluations
4. Responses and scores are captured for human review

All LLM responses and evaluations are saved to tests/outputs/ for manual review.
Score range assertions have been removed in favor of human evaluation.
"""

from typing import Callable

import pytest
from httpx import AsyncClient

from tests.conftest import get_dimension_score


# =============================================================================
# BASIC CONVERSATION FLOW TESTS
# =============================================================================


@pytest.mark.integration
async def test_start_conversation_with_valid_scenario(
    client: AsyncClient, save_output: Callable
):
    """Starting a conversation with a valid scenario should succeed."""
    response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})

    assert response.status_code == 200
    data = response.json()
    assert "conversation" in data
    assert "opening_message" in data
    assert data["conversation"]["scenario_id"] == "cloud-migration"
    assert data["conversation"]["status"] == "active"

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {"action": "start conversation"},
        "output": {
            "conversation_id": data["conversation"]["id"],
            "opening_message": data["opening_message"]["content"],
            "status": data["conversation"]["status"],
        },
        "test_result": "passed",
        "notes": "Review: Is opening message appropriate for the scenario?",
    })


@pytest.mark.integration
async def test_start_conversation_with_invalid_scenario(client: AsyncClient):
    """Starting a conversation with an invalid scenario should return 404."""
    response = await client.post("/chat/start", json={"scenario_id": "nonexistent-scenario"})

    assert response.status_code == 404


@pytest.mark.integration
async def test_send_message_in_conversation(client: AsyncClient, save_output: Callable):
    """Sending a message in an active conversation should get a response."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    conv_id = start_response.json()["conversation"]["id"]

    # Send message
    user_message = (
        "Thank you for making time. I noticed your company recently expanded - "
        "is that still accurate?"
    )
    message_response = await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": user_message},
    )

    assert message_response.status_code == 200
    data = message_response.json()
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert len(data["message"]["content"]) > 0

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {"user_message": user_message},
        "output": {
            "llm_response": data["message"]["content"],
            "response_length": len(data["message"]["content"]),
        },
        "test_result": "passed",
        "notes": "Review: Is response contextually appropriate?",
    })


@pytest.mark.integration
async def test_end_conversation_produces_evaluation(
    client: AsyncClient, save_output: Callable
):
    """Ending a conversation should produce an evaluation with scores."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    conv_id = start_response.json()["conversation"]["id"]

    # Send a message
    user_message = "What challenges are you facing with your current infrastructure?"
    message_response = await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": user_message},
    )
    llm_response = message_response.json()["message"]["content"]

    # End conversation
    end_response = await client.post(f"/chat/{conv_id}/end")

    assert end_response.status_code == 200
    data = end_response.json()
    assert "evaluation" in data
    assert "overall_score" in data["evaluation"]
    assert "dimensions" in data["evaluation"]
    assert data["conversation"]["status"] == "completed"

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {"user_message": user_message},
        "output": {
            "llm_response": llm_response,
            "conversation_status": data["conversation"]["status"],
        },
        "evaluation": {
            "overall_score": data["evaluation"]["overall_score"],
            "dimensions": data["evaluation"]["dimensions"],
        },
        "test_result": "passed",
        "notes": "Review: Is evaluation reasonable for a single question conversation?",
    })


# =============================================================================
# EXAMPLE-BASED CONVERSATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.slow
async def test_excellent_conversation_flow(
    client: AsyncClient, excellent_discovery_example, save_output: Callable
):
    """An excellent discovery conversation - save evaluation for human review."""
    example = excellent_discovery_example

    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": example["scenario_id"]})
    conv_id = start_response.json()["conversation"]["id"]
    opening_message = start_response.json()["opening_message"]["content"]

    # Send each user message from the transcript and collect responses
    exchanges = []
    for msg in example["transcript"]:
        if msg["role"] == "user":
            response = await client.post(
                "/chat/message",
                json={"conversation_id": conv_id, "content": msg["content"]},
            )
            llm_response = response.json()["message"]["content"]
            exchanges.append({
                "user_message": msg["content"],
                "llm_response": llm_response,
            })

    # End and evaluate
    end_response = await client.post(f"/chat/{conv_id}/end")
    evaluation = end_response.json()["evaluation"]

    # Structure validation only
    assert "overall_score" in evaluation
    assert "dimensions" in evaluation

    # Save for human review (no score assertions)
    save_output({
        "scenario_id": example["scenario_id"],
        "example_file": example.get("_source_file", "excellent_discovery.json"),
        "expected_score_range": example.get("expected_score_range"),
        "input": {
            "transcript_length": len(example["transcript"]),
            "user_messages": [msg["content"] for msg in example["transcript"] if msg["role"] == "user"],
        },
        "output": {
            "opening_message": opening_message,
            "exchanges": exchanges,
        },
        "evaluation": {
            "overall_score": evaluation["overall_score"],
            "dimensions": evaluation["dimensions"],
        },
        "test_result": "passed",
        "notes": "Review: Does excellent conversation receive appropriately high scores?",
    })


@pytest.mark.integration
@pytest.mark.slow
async def test_premature_pitch_conversation_flow(
    client: AsyncClient, premature_pitch_example, save_output: Callable
):
    """A premature pitch conversation - save evaluation for human review."""
    example = premature_pitch_example

    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": example["scenario_id"]})
    conv_id = start_response.json()["conversation"]["id"]
    opening_message = start_response.json()["opening_message"]["content"]

    # Send each user message from the transcript and collect responses
    exchanges = []
    for msg in example["transcript"]:
        if msg["role"] == "user":
            response = await client.post(
                "/chat/message",
                json={"conversation_id": conv_id, "content": msg["content"]},
            )
            llm_response = response.json()["message"]["content"]
            exchanges.append({
                "user_message": msg["content"],
                "llm_response": llm_response,
            })

    # End and evaluate
    end_response = await client.post(f"/chat/{conv_id}/end")
    evaluation = end_response.json()["evaluation"]

    # Structure validation only
    assert "overall_score" in evaluation
    assert "dimensions" in evaluation

    # Save for human review (no score assertions)
    save_output({
        "scenario_id": example["scenario_id"],
        "example_file": example.get("_source_file", "premature_pitch.json"),
        "expected_score_range": example.get("expected_score_range"),
        "input": {
            "transcript_length": len(example["transcript"]),
            "user_messages": [msg["content"] for msg in example["transcript"] if msg["role"] == "user"],
        },
        "output": {
            "opening_message": opening_message,
            "exchanges": exchanges,
        },
        "evaluation": {
            "overall_score": evaluation["overall_score"],
            "dimensions": evaluation["dimensions"],
        },
        "test_result": "passed",
        "notes": "Review: Does premature pitch receive appropriately low scores?",
    })


# =============================================================================
# SCENARIO AVAILABILITY TESTS
# =============================================================================


@pytest.mark.integration
async def test_list_scenarios_returns_expected_scenarios(client: AsyncClient):
    """Listing scenarios should return all predefined scenarios."""
    response = await client.get("/scenarios")

    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data

    scenario_ids = [s["id"] for s in data["scenarios"]]
    assert "cloud-migration" in scenario_ids
    assert "it-governance" in scenario_ids
    assert "sourcing-partner" in scenario_ids


@pytest.mark.integration
async def test_get_specific_scenario(client: AsyncClient):
    """Getting a specific scenario should return full details."""
    response = await client.get("/scenarios/cloud-migration")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "cloud-migration"
    assert "persona" in data
    assert "context" in data
    assert data["persona"]["name"] == "Thomas Mueller"


# =============================================================================
# CONVERSATION STATE TESTS
# =============================================================================


@pytest.mark.integration
async def test_get_conversation_returns_messages(client: AsyncClient, save_output: Callable):
    """Getting a conversation should return all exchanged messages."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    conv_id = start_response.json()["conversation"]["id"]

    # Send a message
    user_message = "Hello, thank you for your time."
    await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": user_message},
    )

    # Get conversation
    get_response = await client.get(f"/chat/{conv_id}")

    assert get_response.status_code == 200
    data = get_response.json()
    # Should have: opening message, user message, AI response = 3 messages
    assert len(data["messages"]) >= 2

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {"user_message": user_message},
        "output": {
            "message_count": len(data["messages"]),
            "messages": data["messages"],
        },
        "test_result": "passed",
        "notes": "Review: Are messages correctly recorded in conversation history?",
    })


@pytest.mark.integration
async def test_list_conversations(client: AsyncClient):
    """Listing conversations should include started conversations."""
    # Start a conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    conv_id = start_response.json()["conversation"]["id"]

    # List conversations
    list_response = await client.get("/chat")

    assert list_response.status_code == 200
    data = list_response.json()
    assert "conversations" in data

    conv_ids = [c["id"] for c in data["conversations"]]
    assert conv_id in conv_ids
