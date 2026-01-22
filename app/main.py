"""FastAPI application for AI Sales Trainer PoC."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import chat, navigation, qualification, questions, rag, scenarios, value_prop, voice
from app.config import get_settings
from app.logging_config import get_logger, setup_logging
from app.services.vector_store import VectorStore

# Initialize logging before anything else
setup_logging(log_level="INFO")
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, cleanup on shutdown."""
    settings = get_settings()
    logger.info("Starting AI Sales Trainer PoC")

    try:
        app.state.vector_store = VectorStore(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            collection_name=settings.qdrant_collection_name,
            embedding_size=settings.embedding_size,
        )
        logger.info("Application started successfully")
    except Exception as e:
        logger.error("Failed to initialize vector store: %s", str(e))
        raise

    yield

    logger.info("Shutting down AI Sales Trainer PoC")


app = FastAPI(
    title="AI Sales Trainer PoC",
    description="RAG, Voice Agent, and Evaluation API",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])
app.include_router(questions.router, prefix="/questions", tags=["Questions"])
app.include_router(qualification.router, prefix="/qualification", tags=["Qualification"])
app.include_router(value_prop.router, prefix="/value-prop", tags=["Value Proposition"])
app.include_router(navigation.router, prefix="/navigation", tags=["Navigation"])


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check that verifies all dependencies."""
    checks = {}

    # Check Qdrant connection
    try:
        info = app.state.vector_store.get_collection_info()
        checks["qdrant"] = {"status": "ok", "collection": info["name"]}
    except Exception as e:
        checks["qdrant"] = {"status": "error", "message": str(e)}

    all_healthy = all(c.get("status") == "ok" for c in checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_healthy else "not_ready", "checks": checks},
    )


# Serve static files (must be last, catches all unmatched routes)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
