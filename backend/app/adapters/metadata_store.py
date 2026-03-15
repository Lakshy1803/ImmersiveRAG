from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.models import IngestionJob, JobStatus, ParsedDocument, utc_now


class SqliteMetadataStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    document_id TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    collection_id TEXT NOT NULL,
                    parsed_json TEXT NOT NULL
                )
                """
            )

    def save_job(self, job: IngestionJob) -> IngestionJob:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO jobs(job_id, status, request_json, document_id, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.status.value,
                    job.request.model_dump_json(),
                    job.document_id,
                    job.error,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )
        return job

    def get_job(self, job_id: str) -> IngestionJob | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return IngestionJob.model_validate(
            {
                "job_id": row["job_id"],
                "status": row["status"],
                "request": json.loads(row["request_json"]),
                "document_id": row["document_id"],
                "error": row["error"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    def update_job_status(
        self,
        job: IngestionJob,
        status: JobStatus,
        *,
        document_id: str | None = None,
        error: str | None = None,
    ) -> IngestionJob:
        updated = job.model_copy(update={"status": status, "document_id": document_id, "error": error})
        updated.updated_at = utc_now()
        return self.save_job(updated)

    def upsert_document(self, tenant_id: str, collection_id: str, document: ParsedDocument) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents(document_id, filename, tenant_id, collection_id, parsed_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document.document_id,
                    document.filename,
                    tenant_id,
                    collection_id,
                    document.model_dump_json(),
                ),
            )

    def get_document(self, document_id: str) -> ParsedDocument | None:
        with self._connect() as conn:
            row = conn.execute("SELECT parsed_json FROM documents WHERE document_id = ?", (document_id,)).fetchone()
        if row is None:
            return None
        return ParsedDocument.model_validate_json(row["parsed_json"])

    def list_documents(self, tenant_id: str, collection_id: str) -> list[ParsedDocument]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT parsed_json
                FROM documents
                WHERE tenant_id = ? AND collection_id = ?
                """,
                (tenant_id, collection_id),
            ).fetchall()
        return [ParsedDocument.model_validate_json(row["parsed_json"]) for row in rows]
