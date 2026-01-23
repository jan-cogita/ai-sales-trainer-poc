"""Test configuration and fixtures for integration tests."""

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.main import app


# =============================================================================
# TEST OUTPUT MANAGER
# =============================================================================


class TestOutputManager:
    """Manages saving test outputs to JSON files for human review.

    Creates timestamped directories for each test run and saves
    LLM responses, inputs, and metadata for later analysis.
    """

    _instance = None
    _run_dir = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._run_dir = None
        self._outputs_base = Path(__file__).parent / "outputs"

    def _ensure_run_dir(self) -> Path:
        """Create and return the timestamped run directory."""
        if self._run_dir is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            self._run_dir = self._outputs_base / timestamp
            self._run_dir.mkdir(parents=True, exist_ok=True)
            self._write_run_metadata()
        return self._run_dir

    def _write_run_metadata(self):
        """Write metadata about the test run."""
        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": self._get_git_commit(),
            "git_branch": self._get_git_branch(),
        }
        metadata_path = self._run_dir / "run_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def _get_git_branch(self) -> str:
        """Get current git branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def save_output(
        self,
        test_name: str,
        category: str,
        data: dict[str, Any],
    ) -> Path:
        """Save test output to a JSON file.

        Args:
            test_name: Name of the test function
            category: Category directory (e.g., "persona_reactions", "conversation_flow")
            data: Dictionary with test data to save

        Returns:
            Path to the saved file
        """
        run_dir = self._ensure_run_dir()
        category_dir = run_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        # Add timestamp to the data
        output_data = {
            "test_name": test_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }

        # Generate filename from test name
        filename = f"{test_name}.json"
        output_path = category_dir / filename

        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        return output_path


# Global instance
_output_manager = TestOutputManager()


@pytest.fixture
def save_output(request) -> Callable[[dict[str, Any]], Path]:
    """Fixture providing a function to save test outputs for human review.

    Usage:
        def test_something(save_output):
            # ... run test ...
            save_output({
                "input": {"user_message": "..."},
                "output": {"llm_response": "..."},
                "notes": "Review: Does this look correct?"
            })
    """
    # Determine category from the test file name
    test_file = Path(request.fspath).stem  # e.g., "test_persona_reactions"
    category = test_file.replace("test_", "")  # e.g., "persona_reactions"

    def _save(data: dict[str, Any]) -> Path:
        return _output_manager.save_output(
            test_name=request.node.name,
            category=category,
            data=data,
        )

    return _save

# Path to examples directory
EXAMPLES_DIR = Path(__file__).parent / "examples"


# =============================================================================
# EXAMPLE LOADING FIXTURES
# =============================================================================


def load_example(relative_path: str) -> dict[str, Any]:
    """Load a JSON example file from the examples directory.

    Args:
        relative_path: Path relative to tests/examples/, e.g., "conversations/excellent_discovery.json"

    Returns:
        Parsed JSON content as a dictionary
    """
    file_path = EXAMPLES_DIR / relative_path
    if not file_path.exists():
        raise FileNotFoundError(f"Example file not found: {file_path}")

    with open(file_path) as f:
        return json.load(f)


def load_all_examples(category: str) -> list[dict[str, Any]]:
    """Load all JSON example files from a category directory.

    Args:
        category: Directory name under tests/examples/, e.g., "questions" or "conversations"

    Returns:
        List of parsed JSON contents
    """
    category_path = EXAMPLES_DIR / category
    if not category_path.exists():
        raise FileNotFoundError(f"Example category not found: {category_path}")

    examples = []
    for file_path in category_path.glob("*.json"):
        with open(file_path) as f:
            data = json.load(f)
            data["_source_file"] = file_path.name
            examples.append(data)

    return examples


@pytest.fixture
def example_loader():
    """Fixture providing example loading functions."""
    return {
        "load": load_example,
        "load_all": load_all_examples,
    }


# =============================================================================
# CONVERSATION EXAMPLE FIXTURES
# =============================================================================


@pytest.fixture
def excellent_discovery_example() -> dict[str, Any]:
    """Load the excellent discovery conversation example."""
    return load_example("conversations/excellent_discovery.json")


@pytest.fixture
def premature_pitch_example() -> dict[str, Any]:
    """Load the premature pitch conversation example."""
    return load_example("conversations/premature_pitch.json")


@pytest.fixture
def too_many_situation_example() -> dict[str, Any]:
    """Load the too many situation questions example."""
    return load_example("conversations/too_many_situation.json")


@pytest.fixture
def good_monetization_example() -> dict[str, Any]:
    """Load the good monetization conversation example."""
    return load_example("conversations/good_monetization.json")


# =============================================================================
# QUESTION EXAMPLE FIXTURES
# =============================================================================


@pytest.fixture
def spin_question_examples() -> dict[str, dict[str, Any]]:
    """Load all SPIN question category examples."""
    return {
        "situation": load_example("questions/spin_situation.json"),
        "problem": load_example("questions/spin_problem.json"),
        "implication": load_example("questions/spin_implication.json"),
        "need_payoff": load_example("questions/spin_needpayoff.json"),
    }


# =============================================================================
# OPPORTUNITY EXAMPLE FIXTURES
# =============================================================================


@pytest.fixture
def cloud_migration_opportunity() -> dict[str, Any]:
    """Load the cloud migration opportunity example."""
    return load_example("opportunities/cloud_migration.json")


@pytest.fixture
def it_governance_opportunity() -> dict[str, Any]:
    """Load the IT governance opportunity example."""
    return load_example("opportunities/it_governance.json")


# =============================================================================
# METHODOLOGY EXAMPLE FIXTURES
# =============================================================================


@pytest.fixture
def spin_methodology() -> dict[str, Any]:
    """Load SPIN methodology Q&A."""
    return load_example("methodology/spin_qa.json")


@pytest.fixture
def nepq_methodology() -> dict[str, Any]:
    """Load NEPQ methodology Q&A."""
    return load_example("methodology/nepq_qa.json")


# =============================================================================
# ASYNC HTTP CLIENT FIXTURE
# =============================================================================


@pytest.fixture
async def client() -> AsyncClient:
    """Create an async HTTP client for testing the FastAPI app.

    Uses LifespanManager to properly initialize app state (vector store, etc.)
    before running tests.

    Yields:
        AsyncClient instance for making requests to the app
    """
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def format_transcript_for_evaluation(transcript: list[dict]) -> str:
    """Format a transcript list into a string for the evaluation endpoint.

    Args:
        transcript: List of message dicts with 'role' and 'content' keys

    Returns:
        Formatted transcript string
    """
    lines = []
    for msg in transcript:
        role = "Customer" if msg["role"] == "assistant" else "Salesperson"
        lines.append(f"{role}: {msg['content']}")
    return "\n\n".join(lines)


def get_dimension_score(evaluation: dict, dimension_name: str) -> int | None:
    """Extract a specific dimension score from an evaluation result.

    Args:
        evaluation: Evaluation result dict with 'dimensions' list
        dimension_name: Name of the dimension to find

    Returns:
        Score value or None if dimension not found
    """
    dimensions = evaluation.get("dimensions", [])
    for dim in dimensions:
        if dim.get("dimension") == dimension_name:
            return dim.get("score")
    return None


@pytest.fixture
def transcript_formatter():
    """Fixture providing the transcript formatting function."""
    return format_transcript_for_evaluation


@pytest.fixture
def dimension_score_getter():
    """Fixture providing the dimension score getter function."""
    return get_dimension_score


# =============================================================================
# PYTEST MARKERS
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require API keys, make real LLM calls)",
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (involve multiple LLM calls)",
    )
