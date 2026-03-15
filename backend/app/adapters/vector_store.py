from __future__ import annotations

from hashlib import md5
from typing import Any
from uuid import UUID

from app.core.warnings import silence_llama_index_pydantic_warning

silence_llama_index_pydantic_warning()

from llama_index.core import StorageContext
from llama_index.core.indices.multi_modal import MultiModalVectorStoreIndex
from llama_index.core.schema import ImageNode, TextNode
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from app.adapters.embeddings import EmbeddingProvider
from app.adapters.llama_index import ProviderBackedMultiModalEmbedding
from app.core.config import Settings
from app.models import Citation, EvidenceModality, ParsedDocument, RetrievalResult


class CompatQdrantClient(QdrantClient):
    def search(
        self,
        collection_name: str,
        query_vector=None,
        query_filter=None,
        limit: int = 10,
        with_payload: bool = True,
        with_vectors: bool = False,
        **kwargs: Any,
    ):
        response = self.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors,
            **kwargs,
        )
        return response.points


class LlamaQdrantMultiModalIndex:
    def __init__(
        self,
        client: CompatQdrantClient,
        embedding_provider: EmbeddingProvider,
        settings: Settings,
    ) -> None:
        self.client = client
        self.embedding_provider = embedding_provider
        self.settings = settings
        self.embedding_model = ProviderBackedMultiModalEmbedding(provider=embedding_provider)
        self._ensure_collections()
        self.text_store = QdrantVectorStore(
            collection_name=self.settings.qdrant_text_collection,
            client=self.client,
            dense_config=models.VectorParams(size=self.embedding_provider.vector_size, distance=models.Distance.COSINE),
        )
        self.image_store = QdrantVectorStore(
            collection_name=self.settings.qdrant_image_collection,
            client=self.client,
            dense_config=models.VectorParams(size=self.embedding_provider.vector_size, distance=models.Distance.COSINE),
        )
        storage_context = StorageContext.from_defaults(vector_store=self.text_store, image_store=self.image_store)
        self.index = MultiModalVectorStoreIndex(
            nodes=[],
            storage_context=storage_context,
            embed_model=self.embedding_model,
            image_embed_model=self.embedding_model,
        )

    def replace_document(self, document: ParsedDocument) -> None:
        selector = self._document_filter(document.document_id)
        self.client.delete(self.settings.qdrant_text_collection, points_selector=models.FilterSelector(filter=selector))
        self.client.delete(self.settings.qdrant_image_collection, points_selector=models.FilterSelector(filter=selector))

        nodes = [
            TextNode(
                id_=self._uuid_for("text", block.chunk_id),
                text=block.text,
                metadata={
                    "document_id": document.document_id,
                    "document_name": document.filename,
                    "tenant_id": document.tenant_id,
                    "collection_id": document.collection_id,
                    "page_number": block.page_number,
                    "chunk_id": block.chunk_id,
                    "section": block.section,
                    "bbox": block.bbox,
                    "reading_order": block.reading_order,
                    "ocr_confidence": block.ocr_confidence,
                    "source_type": block.source_type,
                    "modality": "text",
                },
            )
            for block in document.text_blocks
        ]
        nodes.extend(
            ImageNode(
                id_=self._uuid_for("image", image.image_id),
                text=image.caption,
                image_path=image.path,
                metadata={
                    "document_id": document.document_id,
                    "document_name": document.filename,
                    "tenant_id": document.tenant_id,
                    "collection_id": document.collection_id,
                    "page_number": image.page_number,
                    "image_id": image.image_id,
                    "bbox": image.bbox,
                    "modality": "image",
                },
            )
            for image in document.image_regions
        )
        if nodes:
            self.index.insert_nodes(nodes)

    def retrieve(self, question: str, tenant_id: str, collection_id: str, top_k: int) -> list[RetrievalResult]:
        filters = MetadataFilters(
            filters=[
                MetadataFilter(key="tenant_id", value=tenant_id),
                MetadataFilter(key="collection_id", value=collection_id),
            ]
        )
        retriever = self.index.as_retriever(
            similarity_top_k=min(top_k, self.settings.multimodal_text_top_k),
            image_similarity_top_k=min(top_k, self.settings.multimodal_image_top_k),
            filters=filters,
        )
        results = retriever.retrieve(question)
        return [self._to_result(item) for item in results]

    def _to_result(self, node_with_score) -> RetrievalResult:
        node = node_with_score.node
        metadata = node.metadata or {}
        modality = EvidenceModality.IMAGE if metadata.get("modality") == "image" else EvidenceModality.TEXT
        return RetrievalResult(
            result_id=node.node_id,
            document_id=metadata["document_id"],
            document_name=metadata["document_name"],
            page_number=int(metadata.get("page_number", 1)),
            modality=modality,
            score=float(node_with_score.score or 0.0),
            text=node.text or "",
            image_path=getattr(node, "image_path", None),
            citation=Citation(
                document_id=metadata["document_id"],
                document_name=metadata["document_name"],
                page_number=int(metadata.get("page_number", 1)),
                chunk_id=metadata.get("chunk_id"),
                image_id=metadata.get("image_id"),
                bbox=metadata.get("bbox"),
                snippet=(node.text or "")[:220],
            ),
            retriever="multimodal",
        )

    def _ensure_collections(self) -> None:
        vector_params = models.VectorParams(size=self.embedding_provider.vector_size, distance=models.Distance.COSINE)
        existing = {item.name for item in self.client.get_collections().collections}
        for name in (self.settings.qdrant_text_collection, self.settings.qdrant_image_collection):
            if name not in existing:
                self.client.create_collection(name, vectors_config=vector_params)

    def _document_filter(self, document_id: str) -> models.Filter:
        return models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        )

    def _uuid_for(self, namespace: str, raw_id: str) -> str:
        digest = md5(f"{namespace}:{raw_id}".encode("utf-8"), usedforsecurity=False).hexdigest()
        return str(UUID(digest))


def build_qdrant_client(settings: Settings) -> CompatQdrantClient:
    if settings.qdrant_url:
        return CompatQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    location = settings.qdrant_location
    if location:
        return CompatQdrantClient(location=location)
    settings.qdrant_storage_path.mkdir(parents=True, exist_ok=True)
    return CompatQdrantClient(path=str(settings.qdrant_storage_path))
