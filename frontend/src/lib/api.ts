export type JobStatus = 'queued' | 'processing' | 'embedding_and_indexing' | 'complete' | 'failed' | 'waiting_vpn_off' | 'waiting_vpn_on';

export interface IngestionJob {
  job_id: string;
  status: JobStatus;
  document_id: string | null;
  error?: string | null;
}

export interface ChunkNode {
  text: string;
  score: number;
  chunk_id: string;
  document_id: string;
  modality: string;
}

export interface ContextResponse {
  session_id: string;
  question: string;
  cache_hit: boolean;
  extracted_context: ChunkNode[];
  total_tokens_used: number;
  agent_id: string;
}

export interface AgentDefinition {
  agent_id: string;
  name: string;
  description: string;
  system_prompt: string;
  icon: string;
  is_system: boolean;
  base_agent_id: string | null;
}

export interface AgentChatResponse {
  answer: string;
  context_chunks: ChunkNode[];
  tokens_used: number;
  cache_hit: boolean;
}

export const ImmersiveRagAPI = {
  // ── Ingestion ─────────────────────────────────────────────────────
  ingest: async (file: File, config: { extraction_mode: string; embedding_mode: string; collection_id?: string; tenant_id?: string }): Promise<IngestionJob> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('extraction_mode', config.extraction_mode);
    formData.append('embedding_mode', config.embedding_mode);
    if(config.collection_id) formData.append('collection_id', config.collection_id);
    if(config.tenant_id) formData.append('tenant_id', config.tenant_id);

    const response = await fetch('/api/admin/ingest', { method: 'POST', body: formData });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to ingest: ${response.statusText}`);
    }
    return response.json();
  },

  checkStatus: async (jobId: string): Promise<IngestionJob> => {
    const response = await fetch(`/api/admin/ingest/${jobId}/status`);
    if (!response.ok) throw new Error(`Failed to check status: ${response.statusText}`);
    return response.json();
  },

  // ── Legacy Query (retrieval only, no LLM) ──────────────────────────
  query: async (text: string, sessionId: string, agentId: string = 'default_agent'): Promise<ContextResponse> => {
    const payload = { session_id: sessionId, agent_id: agentId, question: text, top_k: 5, max_tokens: 4000 };
    const response = await fetch(`/api/agent/query`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Query failed: ${response.statusText}`);
    }
    return response.json();
  },

  // ── Multi-Agent Chat (RAG + LLM generation) ────────────────────────
  chat: async (question: string, agentId: string, sessionId: string): Promise<AgentChatResponse> => {
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, agent_id: agentId, session_id: sessionId }),
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Chat failed: ${response.statusText}`);
    }
    return response.json();
  },

  // ── Agent Registry ─────────────────────────────────────────────────
  listAgents: async (): Promise<AgentDefinition[]> => {
    const response = await fetch('/api/agent/registry');
    if (!response.ok) throw new Error(`Failed to list agents: ${response.statusText}`);
    return response.json();
  },

  configureAgent: async (request: { base_agent_id: string; name: string; system_prompt: string; description?: string }): Promise<AgentDefinition> => {
    const response = await fetch('/api/agent/configure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Configure agent failed: ${response.statusText}`);
    }
    return response.json();
  },

  deleteAgent: async (agentId: string): Promise<void> => {
    const response = await fetch(`/api/agent/configure/${agentId}`, { method: 'DELETE' });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Delete agent failed: ${response.statusText}`);
    }
  },
};
