from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes import container_dep, create_app
from app.core.config import Settings
from app.services.container import ServiceContainer


def test_ready_endpoint_fails_for_missing_openai_generation_key(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        qdrant_path=tmp_path / "qdrant",
        parser_provider="llamaparse",
        embedding_provider="fastembed",
        generation_provider="openai",
        generation_api_key=None,
        openai_api_key=None,
    )
    container = ServiceContainer(app_settings=settings)
    app = create_app()
    app.dependency_overrides[container_dep] = lambda: container
    client = TestClient(app)

    response = client.get("/health/ready")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "degraded"
    assert any(item["name"] == "generation_config" and item["ok"] is False for item in detail["checks"])
    container.qdrant_client.close()
