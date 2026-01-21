"""Vector store service for document storage and retrieval."""

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.logging_config import get_logger
from app.retry import retry_vector_db

logger = get_logger("vector_store")


class VectorStore:
    """Qdrant vector database client for document embeddings."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "sales_trainer_docs",
        embedding_size: int = 1536,
    ):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.embedding_size = embedding_size
        self._ensure_collection()
        logger.info(
            "Vector store initialized",
            extra={"host": host, "port": port, "collection": collection_name},
        )

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist or has wrong dimensions."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists:
            # Check if dimensions match
            info = self.client.get_collection(self.collection_name)
            current_size = info.config.params.vectors.size
            if current_size != self.embedding_size:
                logger.warning(
                    "Collection dimension mismatch, recreating",
                    extra={"current": current_size, "expected": self.embedding_size},
                )
                self.client.delete_collection(self.collection_name)
                exists = False

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.embedding_size, distance=Distance.COSINE),
            )
            logger.info("Created new collection", extra={"collection": self.collection_name})

    @retry_vector_db
    def upsert(self, doc_id: str, embedding: list[float], metadata: dict) -> None:
        """Insert or update a document embedding."""
        point = PointStruct(
            id=hash(doc_id) % (2**63),
            vector=embedding,
            payload={"doc_id": doc_id, **metadata},
        )
        self.client.upsert(collection_name=self.collection_name, points=[point])
        logger.debug("Upserted document", extra={"doc_id": doc_id})

    @retry_vector_db
    def upsert_batch(
        self,
        doc_ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Insert or update multiple document embeddings."""
        points = [
            PointStruct(
                id=hash(doc_id) % (2**63),
                vector=embedding,
                payload={"doc_id": doc_id, **metadata},
            )
            for doc_id, embedding, metadata in zip(doc_ids, embeddings, metadatas)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info("Batch upserted documents", extra={"count": len(doc_ids)})

    @retry_vector_db
    def search(self, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """Search for similar documents."""
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
        )
        logger.debug("Search completed", extra={"results_count": len(results.points)})
        return [
            {
                "doc_id": hit.payload.get("doc_id"),
                "score": hit.score,
                "metadata": {k: v for k, v in hit.payload.items() if k != "doc_id"},
            }
            for hit in results.points
        ]

    @retry_vector_db
    def delete(self, doc_id: str) -> None:
        """Delete a document by ID."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[hash(doc_id) % (2**63)],
        )
        logger.info("Deleted document", extra={"doc_id": doc_id})

    def get_collection_info(self) -> dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "points_count": info.points_count,
            "status": info.status.value if info.status else "unknown",
        }
