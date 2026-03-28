# Backend FastAPI Standards
- **Typing Framework**: Standard Python `typing` combined heavily with Pydantic v2 schemas for all payload handling.
- **Imports**: Always use absolute imports originating from the `app` package. (e.g., `from app.core.config import config`).
- **Dependency Management**: Native FastAPI Dependency Injection combined with `@contextlib.asynccontextmanager` for root-level setups.
- **Async Standards**: Use `async`/`await` across API routes and DB operations where applicable. (e.g., `aiofiles`, `httpx`).
- **Vector Indexing**: Use `qdrant-client` strictly for storing and creating indexes of chunks with proper metadata tracking.
