from __future__ import annotations

from app.models import JobStatus


def test_health_endpoint_reports_active_stack(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["parser_provider"] == "llamaparse"
    assert body["embedding_provider"] == "fastembed"


def test_ingest_pdf_and_complete_job(client) -> None:
    payload = b"%PDF-1.4 Product roadmap includes a revenue chart and quarterly analysis."
    response = client.post(
        "/ingest",
        files={"file": ("roadmap.pdf", payload, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job"]["status"] == JobStatus.COMPLETE.value
    assert body["job"]["document_id"]


def test_reject_unsupported_upload(client) -> None:
    response = client.post(
        "/ingest",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
