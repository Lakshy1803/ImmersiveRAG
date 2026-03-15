from __future__ import annotations


def test_text_and_image_retrieval_pipeline(client) -> None:
    upload = client.post(
        "/ingest",
        files={"file": ("report.pdf", b"%PDF-1.4 The sales chart shows growth in Europe and Asia.", "application/pdf")},
    )
    assert upload.status_code == 200
    response = client.post("/query", json={"question": "What does the sales chart show?", "top_k": 5})
    assert response.status_code == 200
    body = response.json()["response"]
    assert body["citations"]
    assert any(item["modality"] in {"text", "image"} for item in body["evidence"])


def test_low_confidence_query_abstains(client) -> None:
    client.post(
        "/ingest",
        files={"file": ("image.png", b"PNG binary with dashboard screenshot", "image/png")},
    )
    response = client.post("/query", json={"question": "Explain the legal terms of the merger agreement", "top_k": 3})
    assert response.status_code == 200
    body = response.json()["response"]
    assert body["grounded"] is False
    assert body["guardrails"]
