"""RAG (Retrieval-Augmented Generation) API endpoints."""

import time

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.config import get_settings
from app.logging_config import get_logger
from app.services.document_processor import DocumentProcessor
from app.services.llm import LLMService
from app.storage.local import LocalStorage
from app.storage.s3 import S3Storage

router = APIRouter()
logger = get_logger("api.rag")


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]


class IngestResponse(BaseModel):
    message: str
    chunks_created: int
    document_name: str


def get_storage():
    """Get configured storage backend."""
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(
            bucket_name=settings.s3_bucket_name,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region=settings.aws_region,
        )
    return LocalStorage(base_path=settings.local_data_path + "/documents")


async def build_full_context(storage) -> str:
    """Load all documents and concatenate as context.

    TODO: This currently reads raw bytes and decodes as UTF-8, which works for
    .txt files but produces garbled output for PDF/DOCX. Should use DocumentProcessor
    to properly extract text from binary formats, or read from pre-extracted text cache.
    """
    files = await storage.list_files()
    parts = []
    for filename in files:
        content = await storage.load(filename)
        text = content.decode("utf-8", errors="ignore")
        parts.append(f"--- {filename} ---\n{text}")
    return "\n\n".join(parts)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    storage=Depends(get_storage),
):
    """Ingest a document into the RAG system."""
    start_time = time.perf_counter()
    logger.info("Document ingestion started", extra={"doc_filename": file.filename})

    allowed_extensions = {".pdf", ".docx", ".txt"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_extensions:
        logger.warning("Rejected file with invalid extension", extra={"extension": file_ext})
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    content = await file.read()
    logger.debug("File read", extra={"size_bytes": len(content)})

    # Save to storage
    await storage.save(file.filename, content)

    # Process document into chunks
    processor = DocumentProcessor()
    chunks = processor.process_file(file.filename, content)

    if not chunks:
        logger.warning("No content extracted from document", extra={"doc_filename": file.filename})
        raise HTTPException(status_code=400, detail="No content could be extracted from document")

    # Get embeddings and store in vector DB
    llm_service = LLMService()
    vector_store = request.app.state.vector_store

    texts = [chunk["text"] for chunk in chunks]
    embeddings = await llm_service.get_embeddings_batch(texts)

    doc_ids = [chunk["doc_id"] for chunk in chunks]
    metadatas = [{"text": chunk["text"], **chunk["metadata"]} for chunk in chunks]

    vector_store.upsert_batch(doc_ids, embeddings, metadatas)

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Document ingestion completed",
        extra={
            "doc_filename": file.filename,
            "chunks": len(chunks),
            "duration_ms": duration_ms,
        },
    )

    return IngestResponse(
        message="Document ingested successfully",
        chunks_created=len(chunks),
        document_name=file.filename,
    )


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: Request, query: QueryRequest, storage=Depends(get_storage)):
    """Query the RAG system with a question."""
    start_time = time.perf_counter()
    settings = get_settings()
    logger.info(
        "RAG query started",
        extra={"question_length": len(query.question), "full_context_mode": settings.use_full_context},
    )

    llm_service = LLMService()
    sources = []

    if settings.use_full_context:
        # Full context mode: load all documents
        context = await build_full_context(storage)
        if not context:
            logger.info("No documents found in storage")
            return QueryResponse(
                answer="I couldn't find any documents in the knowledge base.",
                sources=[],
            )
        sources = [{"source": "full_context", "score": 1.0, "chunk_index": None}]
    else:
        # RAG mode: embed and search (vector search)
        vector_store = request.app.state.vector_store

        # Get query embedding
        query_embedding = await llm_service.get_embedding(query.question)

        # Search for relevant documents
        results = vector_store.search(query_embedding, top_k=query.top_k)

        if not results:
            logger.info("No relevant documents found")
            return QueryResponse(
                answer="I couldn't find any relevant information in the knowledge base.",
                sources=[],
            )

        # Build context from retrieved documents
        # TODO: Use filenames as reference labels instead of [1], [2] so LLM cites
        # actual document names (e.g., [sales-playbook.pdf]) for better UX.
        context_parts = []
        for i, result in enumerate(results, 1):
            text = result["metadata"].get("text", "")
            source = result["metadata"].get("source", "Unknown")
            context_parts.append(f"[{i}] Source: {source}\n{text}")

        context = "\n\n".join(context_parts)
        sources = [
            {
                "source": r["metadata"].get("source"),
                "score": r["score"],
                "chunk_index": r["metadata"].get("chunk_index"),
            }
            for r in results
        ]

    # Load RAG system prompt
    try:
        system_prompt = llm_service.load_prompt("rag_system")
    except FileNotFoundError:
        system_prompt = """You are a helpful AI assistant for sales training.
Answer questions based ONLY on the provided context.
If the answer cannot be found in the context, say so clearly.
Always cite your sources by reference number."""

    # Generate answer
    messages = [
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query.question}",
        }
    ]

    answer = await llm_service.chat_completion(messages, system_prompt=system_prompt)

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "RAG query completed",
        extra={"sources_found": len(sources), "duration_ms": duration_ms},
    )

    return QueryResponse(answer=answer, sources=sources)


@router.get("/documents")
async def list_documents(storage=Depends(get_storage)):
    """List all ingested documents."""
    files = await storage.list_files()
    logger.debug("Listed documents", extra={"count": len(files)})
    return {"documents": files}


@router.delete("/documents/{filename}")
async def delete_document(filename: str, request: Request, storage=Depends(get_storage)):
    """Delete a document from the system."""
    # TODO: Also delete associated vectors from Qdrant to avoid orphaned embeddings.
    # Currently only deletes from filesystem storage.
    if not await storage.exists(filename):
        raise HTTPException(status_code=404, detail="Document not found")

    await storage.delete(filename)
    logger.info("Document deleted", extra={"doc_filename": filename})
    return {"message": f"Document {filename} deleted"}


@router.get("/status")
async def rag_status(request: Request):
    """Get RAG system status."""
    vector_store = request.app.state.vector_store
    info = vector_store.get_collection_info()
    return {"status": "ok", "collection": info}
