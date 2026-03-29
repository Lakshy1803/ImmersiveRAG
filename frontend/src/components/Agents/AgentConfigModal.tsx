"use client";

import React, { useState, useEffect } from "react";
import { ImmersiveRagAPI, AgentDefinition } from "@/lib/api";

interface AgentConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: (agent: AgentDefinition) => void;
  baseAgents: AgentDefinition[];
  editAgent?: AgentDefinition | null;
}

const AgentConfigModal: React.FC<AgentConfigModalProps> = ({ isOpen, onClose, onSaved, baseAgents, editAgent }) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedBaseId, setSelectedBaseId] = useState("doc_analyzer");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [temperature, setTemperature] = useState<number>(0.3);
  const [maxTokens, setMaxTokens] = useState<number>(512);
  const [maxContextTokens, setMaxContextTokens] = useState<number>(4096);
  const [topK, setTopK] = useState<number>(5);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const AVAILABLE_TOOLS = [
    { id: 'export_pdf', label: 'PDF Export' },
    { id: 'export_csv', label: 'CSV Data Export' }
  ];

  // Prefill state when modal opens or editAgent changes
  useEffect(() => {
    if (isOpen) {
      if (editAgent) {
        setName(editAgent.name);
        setDescription(editAgent.description);
        setSelectedBaseId(editAgent.base_agent_id || "doc_analyzer");
        setSystemPrompt(editAgent.system_prompt);
        setSelectedTools(editAgent.enabled_tools || []);

        // Load model overrides if they exist
        setTemperature(editAgent.model_settings?.temperature ?? 0.3);
        setMaxTokens(editAgent.model_settings?.max_tokens ?? 512);
        setMaxContextTokens(editAgent.model_settings?.max_context_tokens ?? 4096);
        setTopK(editAgent.model_settings?.top_k ?? 5);
      } else {
        setName("");
        setDescription("");
        setSelectedBaseId("doc_analyzer");
        setSelectedTools([]);

        setTemperature(0.3);
        setMaxTokens(512);
        setMaxContextTokens(4096);
        setTopK(5);
        // The system prompt is set by the next useEffect when selectedBaseId triggers
      }
      setError("");
    }
  }, [isOpen, editAgent]);

  // Prefill system prompt when base agent changes to doc_analyzer ONLY IF creating a new agent
  useEffect(() => {
    if (!editAgent || selectedBaseId !== editAgent.base_agent_id) {
      const base = baseAgents.find(a => a.agent_id === selectedBaseId);
      if (base) setSystemPrompt(base.system_prompt);
    }
  }, [selectedBaseId, baseAgents, editAgent]);

  const toggleTool = (toolId: string) => {
    setSelectedTools(prev =>
      prev.includes(toolId) ? prev.filter(t => t !== toolId) : [...prev, toolId]
    );
  };

  const handleSave = async () => {
    if (!name.trim() || !systemPrompt.trim()) {
      setError("Name and System Prompt are required.");
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      const newAgent = await ImmersiveRagAPI.configureAgent({
        agent_id: editAgent?.agent_id,
        base_agent_id: selectedBaseId,
        name: name.trim(),
        system_prompt: systemPrompt.trim(),
        description: description.trim(),
        enabled_tools: selectedTools,
        model_settings: {
          temperature,
          max_tokens: maxTokens,
          max_context_tokens: maxContextTokens,
          top_k: topK
        }
      });
      onSaved(newAgent);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save agent.");
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-3xl mx-4 bg-surface-container rounded-3xl border border-outline-variant/30 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-8 pt-6 pb-4 border-b border-outline-variant/20">
          <div>
            <h2 className="text-on-surface font-bold text-lg">{editAgent ? "Edit Agent" : "Configure Custom Agent"}</h2>
            <p className="text-on-surface/50 text-[11px] mt-0.5">{editAgent ? "Update properties and tool bindings" : "Build a custom AI agent from a base template"}</p>
          </div>
          <button onClick={onClose} className="w-9 h-9 flex items-center justify-center rounded-full text-on-surface/40 hover:text-on-surface hover:bg-surface-container-high transition-all">
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        {/* Form Body - Two Column Layout */}
        <div className="p-8">
          <div className="flex flex-col lg:flex-row gap-8">
            {/* Left Column: Metadata & Tools */}
            <div className="flex-1 space-y-5">
              {/* Base Agent */}
              <div>
                <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold block mb-1.5">Base Template</label>
                <select
                  value={selectedBaseId}
                  onChange={e => setSelectedBaseId(e.target.value)}
                  className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-2 text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
                >
                  {baseAgents.map(a => (
                    <option key={a.agent_id} value={a.agent_id}>{a.name}</option>
                  ))}
                </select>
              </div>

              {/* Name */}
              <div>
                <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold block mb-1.5">Agent Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Tax Auditor"
                  className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-2 text-sm text-on-surface placeholder:text-on-surface/30 focus:ring-1 focus:ring-primary outline-none"
                />
              </div>

              {/* Description */}
              <div>
                <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold block mb-1.5">Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="What does this agent do?"
                  className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-2 text-sm text-on-surface placeholder:text-on-surface/30 focus:ring-1 focus:ring-primary outline-none"
                />
              </div>

              {/* Tools Selection */}
              <div>
                <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold block mb-1.5">Capability Tools</label>
                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_TOOLS.map(tool => (
                    <label key={tool.id} className="flex items-center gap-2 text-[11px] text-on-surface cursor-pointer bg-surface-container-low px-3 py-1.5 rounded-lg border border-outline-variant/30 hover:border-primary/50 transition-colors">
                      <input
                        type="checkbox"
                        checked={selectedTools.includes(tool.id)}
                        onChange={() => toggleTool(tool.id)}
                        className="rounded border-outline-variant/50 text-primary bg-surface-container"
                      />
                      {tool.label}
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column: System Prompt */}
            <div className="flex-1 flex flex-col">
              <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold mb-1.5">System Prompt Instructions</label>
              <textarea
                value={systemPrompt}
                onChange={e => setSystemPrompt(e.target.value)}
                className="flex-1 min-h-[180px] w-full bg-surface-container-low border border-outline-variant/40 rounded-2xl px-4 py-3 text-xs text-on-surface placeholder:text-on-surface/30 focus:ring-1 focus:ring-primary outline-none resize-none leading-relaxed"
                placeholder="Act as a professional auditor..."
              />
              <p className="text-[9px] text-on-surface/30 mt-1.5 text-right font-mono italic">{systemPrompt.length} chars · ~{Math.ceil(systemPrompt.length / 4)} tokens</p>
            </div>
          </div>

          {/* Bottom Area: Model Overrides */}
          <div className="grid grid-cols-2 gap-x-12 gap-y-6 border-t border-outline-variant/10 pt-6 mt-6">
            <div>
              <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold mb-2.5 flex justify-between items-center">
                <span>Creativity (Temperature)</span>
                <span className="text-primary font-mono bg-primary/10 px-2 py-0.5 rounded text-[11px]">{temperature}</span>
              </label>
              <input
                type="range" min="0" max="1" step="0.1"
                value={temperature}
                onChange={e => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-primary h-1 bg-surface-container-high rounded-full appearance-none outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold mb-2.5 flex justify-between items-center">
                <span>Output Tokens</span>
                <span className="text-primary font-mono bg-primary/10 px-2 py-0.5 rounded text-[11px]">{maxTokens.toLocaleString()}</span>
              </label>
              <input
                type="range" min="256" max="10000" step="128"
                value={maxTokens}
                onChange={e => setMaxTokens(parseInt(e.target.value, 10))}
                className="w-full accent-primary h-1 bg-surface-container-high rounded-full appearance-none outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold mb-2.5 flex justify-between items-center">
                <span>Max Context Tokens</span>
                <span className="text-primary font-mono bg-primary/10 px-2 py-0.5 rounded text-[11px]">{maxContextTokens.toLocaleString()}</span>
              </label>
              <input
                type="range" min="1024" max="10000" step="512"
                value={maxContextTokens}
                onChange={e => setMaxContextTokens(parseInt(e.target.value, 10))}
                className="w-full accent-primary h-1 bg-surface-container-high rounded-full appearance-none outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold mb-2.5 flex justify-between items-center">
                <span>Context Chunks (Top K)</span>
                <span className="text-primary font-mono bg-primary/10 px-2 py-0.5 rounded text-[11px]">{topK}</span>
              </label>
              <input
                type="range" min="1" max="20" step="1"
                value={topK}
                onChange={e => setTopK(parseInt(e.target.value, 10))}
                className="w-full accent-primary h-1 bg-surface-container-high rounded-full appearance-none outline-none"
              />
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mt-4 flex items-center gap-2 text-red-500 text-[10px] font-bold uppercase tracking-wider bg-red-500/5 px-4 py-2 rounded-lg border border-red-500/20 animate-in fade-in slide-in-from-top-1">
              <span className="material-symbols-outlined text-sm">error</span>
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-8 pb-8">
          <button onClick={onClose} className="px-6 py-2 rounded-full text-xs font-bold text-on-surface/50 hover:text-on-surface hover:bg-surface-container-high transition-all">Cancel</button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-10 py-2.5 bg-primary text-white rounded-full text-xs font-black uppercase tracking-widest hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:grayscale flex items-center gap-2"
          >
            {isSaving && <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>}
            {isSaving ? "Saving..." : editAgent ? "Apply Changes" : "Create Agent"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AgentConfigModal;
