"use client";

import React, { useState, useEffect } from "react";
import { ImmersiveRagAPI, AgentDefinition } from "@/lib/api";

interface AgentConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: (agent: AgentDefinition) => void;
  baseAgents: AgentDefinition[];
}

const AgentConfigModal: React.FC<AgentConfigModalProps> = ({ isOpen, onClose, onSaved, baseAgents }) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedBaseId, setSelectedBaseId] = useState("doc_analyzer");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  // Prefill system prompt when base agent changes
  useEffect(() => {
    const base = baseAgents.find(a => a.agent_id === selectedBaseId);
    if (base) setSystemPrompt(base.system_prompt);
  }, [selectedBaseId, baseAgents]);

  const handleSave = async () => {
    if (!name.trim() || !systemPrompt.trim()) {
      setError("Name and System Prompt are required.");
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      const newAgent = await ImmersiveRagAPI.configureAgent({
        base_agent_id: selectedBaseId,
        name: name.trim(),
        system_prompt: systemPrompt.trim(),
        description: description.trim(),
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
      <div className="relative w-full max-w-lg mx-4 bg-surface-container rounded-3xl border border-outline-variant/30 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-outline-variant/20">
          <div>
            <h2 className="text-on-surface font-bold text-lg">Configure Agent</h2>
            <p className="text-on-surface/50 text-xs mt-0.5">Build a custom AI agent from a base template</p>
          </div>
          <button onClick={onClose} className="w-9 h-9 flex items-center justify-center rounded-full text-on-surface/40 hover:text-on-surface hover:bg-surface-container-high transition-all">
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        {/* Form */}
        <div className="p-6 space-y-5">
          {/* Base Agent */}
          <div>
            <label className="text-[11px] uppercase tracking-widest text-on-surface/50 font-bold block mb-2">Base Agent</label>
            <select
              value={selectedBaseId}
              onChange={e => setSelectedBaseId(e.target.value)}
              className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-2.5 text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
            >
              {baseAgents.map(a => (
                <option key={a.agent_id} value={a.agent_id}>{a.name}</option>
              ))}
            </select>
          </div>

          {/* Name */}
          <div>
            <label className="text-[11px] uppercase tracking-widest text-on-surface/50 font-bold block mb-2">Agent Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Tax Document Auditor"
              className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-2.5 text-sm text-on-surface placeholder:text-on-surface/30 focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-[11px] uppercase tracking-widest text-on-surface/50 font-bold block mb-2">Description <span className="text-on-surface/30 normal-case">(optional)</span></label>
            <input
              type="text"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Brief description of what this agent does"
              className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-2.5 text-sm text-on-surface placeholder:text-on-surface/30 focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          {/* System Prompt */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-[11px] uppercase tracking-widest text-on-surface/50 font-bold">System Prompt</label>
            </div>
            <textarea
              value={systemPrompt}
              onChange={e => setSystemPrompt(e.target.value)}
              rows={6}
              placeholder="Describe what this agent should do, its tone, and any constraints..."
              className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-3 text-sm text-on-surface placeholder:text-on-surface/30 focus:ring-1 focus:ring-primary outline-none resize-none leading-relaxed"
            />
            <p className="text-[10px] text-on-surface/30 mt-1 px-1">{systemPrompt.length} characters · ~{Math.ceil(systemPrompt.length / 4)} tokens</p>
          </div>

          {/* Error message */}
          {error && (
            <p className="text-red-500 text-xs bg-red-500/10 px-4 py-2.5 rounded-xl border border-red-500/20">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 pb-6">
          <button onClick={onClose} className="px-6 py-2.5 rounded-full text-sm text-on-surface/60 hover:text-on-surface hover:bg-surface-container-high transition-all">Cancel</button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-8 py-2.5 bg-primary text-white rounded-full text-sm font-bold hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:grayscale flex items-center gap-2"
          >
            {isSaving && <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>}
            {isSaving ? "Saving..." : "Create Agent"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AgentConfigModal;
