"""Tests for RAG source citation formatting."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_rag_query_returns_filename_citations(client: AsyncClient, save_output):
    """Verify RAG responses include filename-based citations and formatted sources."""
    test_filename = "test_sales_guide.txt"
    test_content = b"The SPIN selling methodology uses Situation, Problem, Implication, and Need-payoff questions."

    # Ingest test document
    ingest_response = await client.post(
        "/rag/ingest",
        files={"file": (test_filename, test_content, "text/plain")},
    )
    assert ingest_response.status_code == 200

    # Query the document
    query_response = await client.post(
        "/rag/query",
        json={"question": "What is the SPIN methodology?", "top_k": 3},
    )
    assert query_response.status_code == 200
    data = query_response.json()

    # Verify sources_formatted field exists and contains filename
    assert "sources_formatted" in data
    assert test_filename in data["sources_formatted"]
    assert data["sources_formatted"].startswith("Sources:\n- ")

    # Verify sources are deduplicated (filename appears once even if multiple chunks)
    lines = data["sources_formatted"].strip().split("\n")
    source_lines = [l for l in lines if l.startswith("- ")]
    filenames = [l.replace("- ", "") for l in source_lines]
    assert len(filenames) == len(set(filenames)), "Sources should be deduplicated"

    # Save for human review
    save_output({
        "input": {"question": "What is the SPIN methodology?"},
        "output": {
            "answer": data["answer"],
            "sources_formatted": data["sources_formatted"],
            "sources": data["sources"],
        },
        "notes": "Review: Does answer cite [test_sales_guide.txt]? Is sources_formatted correct?",
    })
