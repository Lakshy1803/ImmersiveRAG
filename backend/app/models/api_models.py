from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from app.models.domain_models import JobStatus

# --- Agent Interfaces (Legacy — kept for backward compat) ---

class AgentQueryRequest(BaseModel):
    question: str
    agent_id: str
    session_id: str = Field(default="default_session", description="Used for sliding window memory")
    tenant_id: str = "default"
    collection_id: str = "default"
    top_k: int = 5
    max_tokens: int = Field(default=4000, description="Hard token budget constraint")

class ContextChunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float
    modality: str = "text"

class AgentContextResponse(BaseModel):
    agent_id: str
    session_id: str
    question: str
    extracted_context: List[ContextChunk] = Field(default_factory=list)
    total_tokens_used: int = 0
    cache_hit: bool = False

# --- Admin / System Interfaces ---

class IngestStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: Optional[str] = None
    error: Optional[str] = None

# --- Multi-Agent Chat Interfaces (New) ---

class AgentChatRequest(BaseModel):
    question: str
    agent_id: str = "doc_analyzer"
    session_id: str = "default_session"

class AgentChatResponse(BaseModel):
    answer: str
    context_chunks: List[ContextChunk] = Field(default_factory=list)
    tokens_used: int = 0
    cache_hit: bool = False

class AgentDefinition(BaseModel):
    agent_id: str
    name: str
    description: str = ""
    system_prompt: str
    icon: str = "smart_toy"
    is_system: bool = False
    base_agent_id: Optional[str] = None

class AgentConfigRequest(BaseModel):
    base_agent_id: str = "doc_analyzer"
    name: str
    system_prompt: str
    description: str = ""

