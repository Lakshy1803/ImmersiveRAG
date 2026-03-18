from fastapi import Depends, Request
from app.core.config import AppConfig, config
from app.storage.relations_db import get_db_session
from app.storage.vector_db import get_qdrant_client
from qdrant_client import QdrantClient
from contextlib import contextmanager

def get_config() -> AppConfig:
    return config

def get_db():
    with get_db_session() as conn:
        yield conn

def get_qdrant() -> QdrantClient:
    return get_qdrant_client()

