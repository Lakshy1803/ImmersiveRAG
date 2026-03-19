from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import config
import os

COLLECTION_NAME = "rag_text"

_qdrant_client = None

def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        if config.qdrant_url:
            client_kwargs = {
                "url": config.qdrant_url,
            }
            if config.bypass_ssl_verify:
                # Qdrant client uses httpx internally, this disables verification
                client_kwargs["verify"] = False
            _qdrant_client = QdrantClient(**client_kwargs)
        else:
            os.makedirs(config.qdrant_path, exist_ok=True)
            _qdrant_client = QdrantClient(path=config.qdrant_path)
    return _qdrant_client

def reset_qdrant_client():
    """Closes the current Qdrant client and clears the singleton so the next call gets a fresh connection."""
    global _qdrant_client
    if _qdrant_client is not None:
        try:
            _qdrant_client.close()
        except Exception:
            pass
        _qdrant_client = None

def ensure_collection(client: QdrantClient) -> None:
    """Creates the rag_text collection if it doesn't exist."""
    dim_size = 1536 if config.embedding_api_key else 384
    try:
        client.get_collection(COLLECTION_NAME)
    except Exception:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=dim_size, distance=Distance.COSINE, on_disk=True)
        )

def init_qdrant_collections():
    client = get_qdrant_client()
    ensure_collection(client)

    # Image vectors collection (Multimodal)
    try:
        client.get_collection("rag_image")
    except Exception:
        client.create_collection(
            collection_name="rag_image",
            vectors_config=VectorParams(size=512, distance=Distance.COSINE, on_disk=True)
        )

# Removed top-level init to prevent import-time crashes.
# Call init_qdrant_collections() during app startup.
