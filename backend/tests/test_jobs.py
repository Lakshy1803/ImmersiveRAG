from __future__ import annotations


def test_job_lookup_returns_persisted_state(client) -> None:
    upload = client.post(
        "/ingest",
        files={"file": ("deck.pdf", b"%PDF-1.4 product screenshot and launch metrics", "application/pdf")},
    )
    job_id = upload.json()["job"]["job_id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["job"]["job_id"] == job_id
