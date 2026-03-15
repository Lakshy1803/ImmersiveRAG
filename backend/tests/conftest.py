from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.embeddings import HashEmbeddingProvider
from app.api.routes import container_dep, create_app
from app.core.config import Settings
from app.models import DocumentIngestRequest, ImageRegion, ParsedDocument, TextBlock
from app.services.container import ServiceContainer
from app.services.parsing import Parser


TEXT_RE = re.compile(rb"[A-Za-z0-9][A-Za-z0-9 ,.:;()/%_-]{3,}")


class FakeParser(Parser):
    def __init__(self, images_dir: Path) -> None:
        self.images_dir = images_dir
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, request: DocumentIngestRequest) -> ParsedDocument:
        payload = Path(request.source_path).read_bytes()
        text = " ".join(match.decode("utf-8", errors="ignore").strip() for match in TEXT_RE.findall(payload))
        text = text or f"Document {request.filename}"
        image_path = self.images_dir / f"{Path(request.filename).stem}.bin"
        image_path.write_bytes(payload)
        return ParsedDocument(
            filename=request.filename,
            content_type=request.content_type,
            tenant_id=request.tenant_id,
            collection_id=request.collection_id,
            metadata=request.metadata,
            text_blocks=[TextBlock(page_number=1, section="body", text=text)],
            image_regions=[
                ImageRegion(
                    page_number=1,
                    path=str(image_path),
                    caption=text[:120],
                    bbox=[0, 0, 1000, 1000],
                )
            ],
            page_count=1,
            source_path=request.source_path,
        )


@pytest.fixture
def app_container(tmp_path: Path):
    app_settings = Settings(
        data_dir=tmp_path / "data",
        qdrant_path=tmp_path / "qdrant",
        parser_provider="llamaparse",
        embedding_provider="fastembed",
        min_supported_score=0.7,
    )
    app_settings.data_dir.mkdir(parents=True, exist_ok=True)
    parser = FakeParser(app_settings.extracted_images_dir)
    embedding_provider = HashEmbeddingProvider(dimensions=24)
    container = ServiceContainer(
        app_settings=app_settings,
        parser=parser,
        embedding_provider=embedding_provider,
    )
    yield container
    container.close()


@pytest.fixture
def client(app_container: ServiceContainer) -> TestClient:
    app = create_app()
    app.dependency_overrides[container_dep] = lambda: app_container
    return TestClient(app)
