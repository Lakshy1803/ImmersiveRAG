export type JobStatus = 'queued' | 'processing' | 'embedding_and_indexing' | 'complete' | 'failed' | 'waiting_vpn_off' | 'waiting_vpn_on';

export interface IngestionJob {
  job_id: string;
  status: JobStatus;
  document_id: string | null;
  message?: string | null;
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
  enabled_tools: string[];
  model_settings?: Record<string, any>;
}

export interface AgentChatResponse {
  answer: string;
  context_chunks: ChunkNode[];
  tokens_used: number;
  cache_hit: boolean;
}

export const getApiBaseUrl = (): string => process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
const baseKey = getApiBaseUrl();

export const ImmersiveRagAPI = {
  // ── Ingestion ─────────────────────────────────────────────────────
  ingest: async (file: File, config: { extraction_mode: string; embedding_mode: string; collection_id?: string; tenant_id?: string }): Promise<IngestionJob> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('extraction_mode', config.extraction_mode);
    formData.append('embedding_mode', config.embedding_mode);
    if(config.collection_id) formData.append('collection_id', config.collection_id);
    if(config.tenant_id) formData.append('tenant_id', config.tenant_id);

    const response = await fetch(`${baseKey}/admin/ingest`, { method: 'POST', body: formData });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to ingest: ${response.statusText}`);
    }
    return response.json();
  },

  bulkIngest: async (files: File[], config: { extraction_mode: string; embedding_mode: string; collection_id?: string; tenant_id?: string }): Promise<{ message: string, jobs: { filename: string, job_id: string, status: JobStatus }[] }> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('extraction_mode', config.extraction_mode);
    formData.append('embedding_mode', config.embedding_mode);
    if(config.collection_id) formData.append('collection_id', config.collection_id);
    if(config.tenant_id) formData.append('tenant_id', config.tenant_id);

    const response = await fetch(`${baseKey}/admin/ingest/bulk`, { method: 'POST', body: formData });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to bulk ingest: ${response.statusText}`);
    }
    return response.json();
  },

  checkStatus: async (jobId: string): Promise<IngestionJob> => {
    const response = await fetch(`${baseKey}/admin/ingest/${jobId}/status`);
    if (!response.ok) throw new Error(`Failed to check status: ${response.statusText}`);
    return response.json();
  },

  // ── Legacy Query (retrieval only, no LLM) ──────────────────────────
  query: async (text: string, sessionId: string, agentId: string = 'default_agent'): Promise<ContextResponse> => {
    const payload = { session_id: sessionId, agent_id: agentId, question: text, top_k: 5, max_tokens: 4000 };
    const response = await fetch(`${baseKey}/agent/query`, {
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
    const response = await fetch(`${baseKey}/agent/chat`, {
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
    const response = await fetch(`${baseKey}/agent/registry`);
    if (!response.ok) throw new Error(`Failed to list agents: ${response.statusText}`);
    return response.json();
  },

  // ── Agent Configuration (Clone + Customize) ───────────────────────────
  configureAgent: async (request: { agent_id?: string; base_agent_id: string; name: string; system_prompt: string; description?: string; enabled_tools?: string[]; model_settings?: Record<string, any> }): Promise<AgentDefinition> => {
    const response = await fetch(`${baseKey}/agent/configure`, {
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
    const response = await fetch(`${baseKey}/agent/configure/${agentId}`, { method: 'DELETE' });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Delete agent failed: ${response.statusText}`);
    }
  },

  // ── Admin & Stats ──────────────────────────────────────────────────
  getAdminConfig: async () => {
    const response = await fetch(`${baseKey}/admin/config/current`);
    if (!response.ok) throw new Error("Failed to fetch admin config");
    return response.json();
  },

  getQdrantStats: async () => {
    const response = await fetch(`${baseKey}/admin/qdrant/stats`);
    if (!response.ok) throw new Error("Failed to fetch vector stats");
    return response.json();
  },

  exportToPDF: async (content: string) => {
    const res = await fetch(`${baseKey}/agent/tools/export/pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    if (!res.ok) throw new Error("PDF Export failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${Date.now()}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  },

  exportToCSV: async (content: string) => {
    const res = await fetch(`${baseKey}/agent/tools/export/csv`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    if (!res.ok) throw new Error("CSV Export failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `data_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
  },
  // ── LLM Config ─────────────────────────────────────────────────────
  getLLMConfig: async (): Promise<{ api_key_masked: string; base_url: string; model: string; configured: boolean }> => {
    const response = await fetch(`${baseKey}/admin/llm-config`);
    if (!response.ok) throw new Error(`Failed to get LLM config: ${response.statusText}`);
    return response.json();
  },

  saveLLMConfig: async (apiKey: string, baseUrl: string, model: string): Promise<{ success: boolean; message: string; model: string }> => {
    const response = await fetch(`${baseKey}/admin/llm-config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey, base_url: baseUrl, model }),
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to save LLM config: ${response.statusText}`);
    }
    return response.json();
  },

  testLLMConfig: async (apiKey: string, baseUrl: string, model: string): Promise<{ success: boolean; message: string; model: string }> => {
    const response = await fetch(`${baseKey}/admin/llm-config/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey, base_url: baseUrl, model }),
    });
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Connection test failed: ${response.statusText}`);
    }
    return response.json();
  },
};
