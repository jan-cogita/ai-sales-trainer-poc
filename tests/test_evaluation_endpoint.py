"""Evaluation endpoint integration tests.

These tests verify that:
1. The evaluation endpoint correctly processes transcripts
2. Different methodologies are supported
3. Evaluation structure is correct

All evaluations are saved to tests/outputs/ for manual quality review.
Score threshold assertions have been removed in favor of human evaluation.
"""

from typing import Callable

import pytest
from httpx import AsyncClient

from tests.conftest import format_transcript_for_evaluation


# =============================================================================
# BASIC EVALUATION ENDPOINT TESTS
# =============================================================================


@pytest.mark.integration
async def test_evaluate_empty_transcript_returns_error(client: AsyncClient):
    """Evaluating an empty transcript should return 400 error."""
    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": "", "methodology": "SPIN"},
    )

    assert response.status_code == 400


@pytest.mark.integration
async def test_evaluate_with_spin_methodology(client: AsyncClient, save_output: Callable):
    """Evaluation with SPIN methodology should return SPIN-specific scores."""
    transcript = """
    Salesperson: Thank you for your time today. I noticed your company has expanded recently - is that still accurate?

    Customer: Yes, we opened two new sites last year.

    Salesperson: I imagine managing IT across multiple locations creates coordination challenges. What's been most difficult?

    Customer: Our servers are old and we've had downtime issues affecting production.

    Salesperson: What impact does that downtime have on your delivery commitments?

    Customer: We've had to delay shipments. Our biggest client is concerned.
    """

    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": transcript, "methodology": "SPIN"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["methodology"] == "SPIN"
    assert "scores" in data
    assert "summary" in data

    # Check SPIN categories are present
    category_names = [s["category"] for s in data["scores"]]
    assert "Situation Questions" in category_names
    assert "Problem Questions" in category_names
    assert "Implication Questions" in category_names
    assert "Need-Payoff Questions" in category_names

    # Save for human review
    save_output({
        "methodology": "SPIN",
        "input": {"transcript": transcript.strip()},
        "output": {
            "scores": data["scores"],
            "summary": data["summary"],
        },
        "test_result": "passed",
        "notes": "Review: Are SPIN scores appropriate for this conversation?",
    })


@pytest.mark.integration
async def test_evaluate_with_meddic_methodology(client: AsyncClient, save_output: Callable):
    """Evaluation with MEDDIC methodology should return MEDDIC-specific scores."""
    transcript = """
    Salesperson: Who is the economic buyer for this decision?

    Customer: That would be our CFO, she has final say on budget.

    Salesperson: What metrics would demonstrate success for this project?

    Customer: We need to reduce downtime by at least 50%.
    """

    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": transcript, "methodology": "MEDDIC"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["methodology"] == "MEDDIC"

    # Check MEDDIC categories are present
    category_names = [s["category"] for s in data["scores"]]
    assert "Metrics" in category_names
    assert "Economic Buyer" in category_names
    assert "Decision Criteria" in category_names

    # Save for human review
    save_output({
        "methodology": "MEDDIC",
        "input": {"transcript": transcript.strip()},
        "output": {
            "scores": data["scores"],
            "summary": data.get("summary", ""),
        },
        "test_result": "passed",
        "notes": "Review: Are MEDDIC scores appropriate for this conversation?",
    })


@pytest.mark.integration
async def test_list_methodologies(client: AsyncClient):
    """Listing methodologies should return all supported options."""
    response = await client.get("/evaluate/methodologies")

    assert response.status_code == 200
    data = response.json()
    assert "methodologies" in data

    methodology_names = [m["name"] for m in data["methodologies"]]
    assert "SPIN" in methodology_names
    assert "MEDDIC" in methodology_names
    assert "Challenger" in methodology_names
    assert "Sandler" in methodology_names


# =============================================================================
# EXAMPLE-BASED EVALUATION TESTS
# =============================================================================


@pytest.mark.integration
async def test_excellent_discovery_transcript_evaluation(
    client: AsyncClient, excellent_discovery_example, transcript_formatter, save_output: Callable
):
    """Excellent discovery transcript - save evaluation for human review."""
    example = excellent_discovery_example
    transcript = transcript_formatter(example["transcript"])

    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": transcript, "methodology": "SPIN"},
    )

    assert response.status_code == 200
    data = response.json()

    # Structure validation only
    assert "scores" in data
    total_score = sum(s["score"] for s in data["scores"])
    max_possible = sum(s["max_score"] for s in data["scores"])

    # Save for human review (no score threshold assertions)
    save_output({
        "methodology": "SPIN",
        "example_file": example.get("_source_file", "excellent_discovery.json"),
        "input": {
            "transcript": transcript,
            "expected_quality": "excellent",
        },
        "output": {
            "scores": data["scores"],
            "total_score": total_score,
            "max_possible": max_possible,
            "percentage": round(total_score / max_possible * 100, 1) if max_possible > 0 else 0,
            "summary": data.get("summary", ""),
        },
        "test_result": "passed",
        "notes": "Review: Does excellent discovery receive high evaluation scores?",
    })


@pytest.mark.integration
async def test_premature_pitch_transcript_evaluation(
    client: AsyncClient, premature_pitch_example, transcript_formatter, save_output: Callable
):
    """Premature pitch transcript - save evaluation for human review."""
    example = premature_pitch_example
    transcript = transcript_formatter(example["transcript"])

    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": transcript, "methodology": "SPIN"},
    )

    assert response.status_code == 200
    data = response.json()

    # Structure validation only
    assert "scores" in data
    total_score = sum(s["score"] for s in data["scores"])
    max_possible = sum(s["max_score"] for s in data["scores"])

    # Save for human review (no score threshold assertions)
    save_output({
        "methodology": "SPIN",
        "example_file": example.get("_source_file", "premature_pitch.json"),
        "input": {
            "transcript": transcript,
            "expected_quality": "poor - premature pitch",
        },
        "output": {
            "scores": data["scores"],
            "total_score": total_score,
            "max_possible": max_possible,
            "percentage": round(total_score / max_possible * 100, 1) if max_possible > 0 else 0,
            "summary": data.get("summary", ""),
        },
        "test_result": "passed",
        "notes": "Review: Does premature pitch receive low evaluation scores?",
    })


@pytest.mark.integration
async def test_good_monetization_transcript_evaluation(
    client: AsyncClient, good_monetization_example, transcript_formatter, save_output: Callable
):
    """Good monetization transcript - save evaluation for human review."""
    example = good_monetization_example
    transcript = transcript_formatter(example["transcript"])

    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": transcript, "methodology": "SPIN"},
    )

    assert response.status_code == 200
    data = response.json()

    # Structure validation only
    assert "scores" in data

    # Find implication score
    implication_score = None
    for score in data["scores"]:
        if score["category"] == "Implication Questions":
            implication_score = score
            break

    # Save for human review (no score threshold assertions)
    save_output({
        "methodology": "SPIN",
        "example_file": example.get("_source_file", "good_monetization.json"),
        "input": {
            "transcript": transcript,
            "expected_quality": "good implication probing",
        },
        "output": {
            "scores": data["scores"],
            "implication_score": implication_score,
            "summary": data.get("summary", ""),
        },
        "test_result": "passed",
        "notes": "Review: Does good monetization example score well on Implication Questions?",
    })


# =============================================================================
# EVALUATION STRUCTURE TESTS
# =============================================================================


@pytest.mark.integration
async def test_evaluation_includes_feedback(client: AsyncClient, save_output: Callable):
    """Evaluation should include specific feedback for each category."""
    transcript = """
    Salesperson: What challenges are you facing?
    Customer: We have downtime issues.
    Salesperson: How does that affect your business?
    Customer: It costs us money and delays production.
    """

    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": transcript, "methodology": "SPIN"},
    )

    assert response.status_code == 200
    data = response.json()

    for score in data["scores"]:
        assert "feedback" in score
        assert len(score["feedback"]) > 0, f"Empty feedback for {score['category']}"

    # Save for human review
    save_output({
        "methodology": "SPIN",
        "input": {"transcript": transcript.strip()},
        "output": {
            "scores": data["scores"],
            "feedback_items": [{"category": s["category"], "feedback": s["feedback"]} for s in data["scores"]],
        },
        "test_result": "passed",
        "notes": "Review: Is feedback specific and actionable?",
    })


@pytest.mark.integration
async def test_evaluation_includes_strengths_and_improvements(
    client: AsyncClient, save_output: Callable
):
    """Evaluation should include identified strengths and areas for improvement."""
    transcript = """
    Salesperson: I noticed you expanded to 3 locations - is that accurate?
    Customer: Yes, that's right.
    Salesperson: What challenges has that created for your IT team?
    Customer: Coordination is difficult with servers in different locations.
    Salesperson: What happens when there's a problem at one site?
    Customer: It takes hours to resolve and affects everyone.
    """

    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": transcript, "methodology": "SPIN"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "strengths" in data
    assert "areas_for_improvement" in data
    assert isinstance(data["strengths"], list)
    assert isinstance(data["areas_for_improvement"], list)

    # Save for human review
    save_output({
        "methodology": "SPIN",
        "input": {"transcript": transcript.strip()},
        "output": {
            "scores": data["scores"],
            "strengths": data["strengths"],
            "areas_for_improvement": data["areas_for_improvement"],
        },
        "test_result": "passed",
        "notes": "Review: Are strengths and improvement areas correctly identified?",
    })


# =============================================================================
# METHODOLOGY FALLBACK TESTS
# =============================================================================


@pytest.mark.integration
async def test_unknown_methodology_defaults_to_spin(client: AsyncClient, save_output: Callable):
    """Unknown methodology should default to SPIN."""
    transcript = """
    Salesperson: What challenges are you facing?
    Customer: Various issues with our current system.
    """

    response = await client.post(
        "/evaluate/conversation",
        json={"transcript": transcript, "methodology": "UNKNOWN_METHOD"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["methodology"] == "SPIN"

    # Save for human review
    save_output({
        "methodology": "UNKNOWN_METHOD (defaulted to SPIN)",
        "input": {
            "transcript": transcript.strip(),
            "requested_methodology": "UNKNOWN_METHOD",
        },
        "output": {
            "actual_methodology": data["methodology"],
            "scores": data["scores"],
        },
        "test_result": "passed",
        "notes": "Review: Does fallback to SPIN work correctly?",
    })
