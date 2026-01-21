"""Persona reaction validation tests.

These tests verify that:
1. Personas respond to different trainee behaviors
2. Conversation flow works correctly
3. Responses are captured for human review

All LLM responses are saved to tests/outputs/ for manual quality review.
Heuristic word-matching has been removed in favor of human evaluation.
"""

from typing import Callable

import pytest
from httpx import AsyncClient


# =============================================================================
# VOCABULARY REACTION TESTS
# =============================================================================


@pytest.mark.integration
async def test_forbidden_vocabulary_triggers_negative_reaction(
    client: AsyncClient, save_output: Callable
):
    """Using forbidden vocabulary - save response for human review."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    assert start_response.status_code == 200
    conv_id = start_response.json()["conversation"]["id"]

    # Send message with forbidden vocabulary
    forbidden_message = (
        "Our solution is the best on the market and I guarantee you'll see results. "
        "Trust me, this is a great deal!"
    )
    message_response = await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": forbidden_message},
    )

    assert message_response.status_code == 200
    response_content = message_response.json()["message"]["content"]

    # Structure validation only
    assert len(response_content) > 10, "Response should not be empty"

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {
            "user_message": forbidden_message,
            "forbidden_phrases": ["best on the market", "guarantee", "trust me", "great deal"],
        },
        "output": {
            "llm_response": response_content,
            "response_length": len(response_content),
        },
        "test_result": "passed",
        "notes": "Review: Does persona show appropriate skepticism to sales-y language?",
    })


@pytest.mark.integration
async def test_disarming_phrase_triggers_positive_reaction(
    client: AsyncClient, save_output: Callable
):
    """Using disarming phrases - save response for human review."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    assert start_response.status_code == 200
    conv_id = start_response.json()["conversation"]["id"]

    # Send message with disarming phrase
    disarming_message = (
        "I'm not sure if we can help you, but I'd like to understand your situation better. "
        "What challenges have you been facing with your infrastructure?"
    )
    message_response = await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": disarming_message},
    )

    assert message_response.status_code == 200
    response_content = message_response.json()["message"]["content"]

    # Structure validation only
    assert len(response_content) > 20, "Persona should engage with the question"

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {
            "user_message": disarming_message,
            "technique_used": "disarming phrase",
        },
        "output": {
            "llm_response": response_content,
            "response_length": len(response_content),
        },
        "test_result": "passed",
        "notes": "Review: Does persona open up and engage positively?",
    })


# =============================================================================
# QUESTION TYPE REACTION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.slow
async def test_too_many_situation_questions_triggers_impatience(
    client: AsyncClient, save_output: Callable
):
    """Asking too many basic situation questions - save responses for human review."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "it-governance"})
    assert start_response.status_code == 200
    conv_id = start_response.json()["conversation"]["id"]

    # Send multiple situation questions
    situation_questions = [
        "How many business units do you have?",
        "What's your total IT headcount?",
        "What tools do you use for project management?",
        "What's your annual IT budget?",
        "How many projects are currently in progress?",
    ]

    responses = []
    for question in situation_questions:
        response = await client.post(
            "/chat/message",
            json={"conversation_id": conv_id, "content": question},
        )
        assert response.status_code == 200
        response_content = response.json()["message"]["content"]
        responses.append({
            "question": question,
            "response": response_content,
        })

    # Structure validation only
    assert len(responses[-1]["response"]) > 10, "Final response should not be empty"

    # Save for human review
    save_output({
        "scenario_id": "it-governance",
        "input": {
            "situation_questions": situation_questions,
            "question_count": len(situation_questions),
        },
        "output": {
            "responses": responses,
            "final_response": responses[-1]["response"],
        },
        "test_result": "passed",
        "notes": "Review: Does persona show increasing impatience with basic situation questions?",
    })


@pytest.mark.integration
@pytest.mark.slow
async def test_implication_questions_trigger_deeper_sharing(
    client: AsyncClient, save_output: Callable
):
    """Good implication questions - save responses for human review."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    assert start_response.status_code == 200
    conv_id = start_response.json()["conversation"]["id"]

    # Build rapport with good implication questions
    implication_questions = [
        "I understand you've had some server reliability challenges - what's been the impact?",
        "When downtime occurs, how does that affect your production schedule?",
        "What happens to your customer relationships when deliveries are delayed?",
    ]

    responses = []
    for question in implication_questions:
        response = await client.post(
            "/chat/message",
            json={"conversation_id": conv_id, "content": question},
        )
        assert response.status_code == 200
        response_content = response.json()["message"]["content"]
        responses.append({
            "question": question,
            "response": response_content,
        })

    # Structure validation only
    assert len(responses[-1]["response"]) > 10, "Final response should not be empty"

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {
            "implication_questions": implication_questions,
            "question_type": "SPIN Implication",
        },
        "output": {
            "responses": responses,
            "final_response": responses[-1]["response"],
        },
        "test_result": "passed",
        "notes": "Review: Does persona reveal deeper business/emotional impact?",
    })


@pytest.mark.integration
async def test_confirming_over_asking_triggers_positive_reaction(
    client: AsyncClient, save_output: Callable
):
    """Using confirming-over-asking technique - save response for human review."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    assert start_response.status_code == 200
    conv_id = start_response.json()["conversation"]["id"]

    # Use confirming technique
    confirming_message = (
        "I noticed your company recently expanded to 3 new locations - is that still accurate?"
    )
    message_response = await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": confirming_message},
    )

    assert message_response.status_code == 200
    response_content = message_response.json()["message"]["content"]

    # Structure validation only
    assert len(response_content) > 10, "Response should not be empty"

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {
            "user_message": confirming_message,
            "technique_used": "confirming-over-asking",
        },
        "output": {
            "llm_response": response_content,
            "response_length": len(response_content),
        },
        "test_result": "passed",
        "notes": "Review: Does persona respond positively to demonstrated research?",
    })


# =============================================================================
# PREMATURE PITCH REACTION TESTS
# =============================================================================


@pytest.mark.integration
async def test_early_pitch_triggers_pushback(client: AsyncClient, save_output: Callable):
    """Pitching solutions too early - save response for human review."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    assert start_response.status_code == 200
    conv_id = start_response.json()["conversation"]["id"]

    # Immediately pitch without discovery
    pitch_message = (
        "Let me tell you about our cloud migration platform - it provides 99.9% uptime "
        "and can reduce your IT costs by 40%."
    )
    message_response = await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": pitch_message},
    )

    assert message_response.status_code == 200
    response_content = message_response.json()["message"]["content"]

    # Structure validation only
    assert len(response_content) > 10, "Response should not be empty"

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {
            "user_message": pitch_message,
            "behavior": "premature pitch without discovery",
        },
        "output": {
            "llm_response": response_content,
            "response_length": len(response_content),
        },
        "test_result": "passed",
        "notes": "Review: Does persona push back on premature pitching?",
    })


# =============================================================================
# SCENARIO-SPECIFIC PERSONA TESTS
# =============================================================================


@pytest.mark.integration
async def test_skeptical_persona_requires_more_trust(
    client: AsyncClient, save_output: Callable
):
    """The sourcing-partner persona (burned by vendors) - save response for human review."""
    # Start conversation with skeptical persona
    start_response = await client.post("/chat/start", json={"scenario_id": "sourcing-partner"})
    assert start_response.status_code == 200

    opening = start_response.json()["opening_message"]["content"]
    conv_id = start_response.json()["conversation"]["id"]

    # Ask about previous vendor experience
    vendor_question = (
        "I understand you've worked with external partners before. How did that go?"
    )
    message_response = await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": vendor_question},
    )

    assert message_response.status_code == 200
    response_content = message_response.json()["message"]["content"]

    # Structure validation only
    assert len(response_content) > 10, "Persona should respond to the question"

    # Save for human review
    save_output({
        "scenario_id": "sourcing-partner",
        "input": {
            "user_message": vendor_question,
            "persona_trait": "skeptical, burned by past vendors",
        },
        "output": {
            "opening_message": opening,
            "llm_response": response_content,
            "response_length": len(response_content),
        },
        "test_result": "passed",
        "notes": "Review: Does persona reference past negative experiences? Is response guarded?",
    })


@pytest.mark.integration
async def test_analytical_persona_wants_data(client: AsyncClient, save_output: Callable):
    """The cloud-migration persona (analytical CEO) - save response for human review."""
    # Start conversation
    start_response = await client.post("/chat/start", json={"scenario_id": "cloud-migration"})
    assert start_response.status_code == 200
    conv_id = start_response.json()["conversation"]["id"]

    # Ask about quantified impact
    quantification_question = (
        "When you have downtime, roughly how much does each hour cost in lost production?"
    )
    message_response = await client.post(
        "/chat/message",
        json={"conversation_id": conv_id, "content": quantification_question},
    )

    assert message_response.status_code == 200
    response_content = message_response.json()["message"]["content"]

    # Structure validation only
    assert len(response_content) > 10, "Persona should engage with the question"

    # Save for human review
    save_output({
        "scenario_id": "cloud-migration",
        "input": {
            "user_message": quantification_question,
            "persona_trait": "analytical, data-driven CEO",
        },
        "output": {
            "llm_response": response_content,
            "response_length": len(response_content),
        },
        "test_result": "passed",
        "notes": "Review: Does analytical persona share quantified data when asked properly?",
    })
