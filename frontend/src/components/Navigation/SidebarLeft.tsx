"use client";

import React, { useState, useEffect } from "react";
import { ImmersiveRagAPI, AgentDefinition } from "@/lib/api";
import AgentConfigModal from "@/components/Agents/AgentConfigModal";

interface SidebarLeftProps {
  activeAgentId: string;
  onAgentChange: (agentId: string) => void;
}

const SidebarLeft: React.FC<SidebarLeftProps> = ({ activeAgentId, onAgentChange }) => {
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [activeAgent, setActiveAgent] = useState<AgentDefinition | null>(null);
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [editAgent, setEditAgent] = useState<AgentDefinition | null>(null);

  // Stats and Config States
  const [config, setConfig] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [settingsExpanded, setSettingsExpanded] = useState(false);
  const [kbExpanded, setKbExpanded] = useState(false);

  const fetchAgents = async () => {
    try {
      const list = await ImmersiveRagAPI.listAgents();
      setAgents(list);
      const current = list.find(a => a.agent_id === activeAgentId) ?? list[0] ?? null;
      setActiveAgent(current);
    } catch {
      // Backend may not be ready — use a placeholder
      setActiveAgent({ agent_id: activeAgentId, name: "Document Analyzer", description: "", system_prompt: "", icon: "description", is_system: true, base_agent_id: null, enabled_tools: [] });
    }
  };

  useEffect(() => {
    fetchAgents();
    ImmersiveRagAPI.getAdminConfig().then(setConfig).catch(console.error);
    ImmersiveRagAPI.getQdrantStats().then(setStats).catch(console.error);
  }, [activeAgentId]);

  const handleSelectAgent = (agent: AgentDefinition) => {
    setActiveAgent(agent);
    onAgentChange(agent.agent_id);
    setSelectorOpen(false);
  };

  const handleDeleteAgent = async (agentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await ImmersiveRagAPI.deleteAgent(agentId);
    fetchAgents();
  };

  const baseAgents = agents.filter(a => a.is_system);
  const customAgents = agents.filter(a => !a.is_system);

  return (
    <>
      <aside className="h-screen w-64 fixed left-0 top-0 pt-16 bg-surface-container flex flex-col border-r border-outline-variant/30 z-40 hidden lg:flex">
        {/* Top Static Content */}
        <div className="p-6 pb-0">
          {/* Agent Selector Dropdown */}
          <div className="relative mb-8">
            <button
              onClick={() => setSelectorOpen(!selectorOpen)}
              suppressHydrationWarning
              className="w-full flex items-center justify-between gap-3 p-3 bg-surface-container-low rounded-full border border-outline-variant/30 hover:border-primary/50 transition-colors shadow-sm text-left group"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-primary text-sm">{activeAgent?.icon ?? "smart_toy"}</span>
                </div>
                <div>
                  <h2 className="text-on-surface font-bold text-[13px] leading-tight group-hover:text-primary transition-colors truncate max-w-[100px]">{activeAgent?.name ?? "Select Agent"}</h2>
                  <p className="text-[9px] text-on-surface/50 uppercase tracking-widest font-medium">{activeAgent?.is_system ? "Base Agent" : "Custom Agent"}</p>
                </div>
              </div>
              <span className="material-symbols-outlined text-on-surface/30 text-lg mr-2">{selectorOpen ? "expand_less" : "unfold_more"}</span>
            </button>

            {/* Dropdown Panel */}
            {selectorOpen && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-surface-container-high border border-outline-variant/40 rounded-2xl shadow-xl z-50 overflow-hidden">
                {baseAgents.length > 0 && (
                  <div>
                    <p className="text-[9px] uppercase tracking-widest text-on-surface/40 font-bold px-4 pt-3 pb-1">Base Agents</p>
                    {baseAgents.map(agent => (
                      <button key={agent.agent_id} onClick={() => handleSelectAgent(agent)}
                        className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-primary/10 transition-all text-left ${activeAgentId === agent.agent_id ? "border-l-2 border-primary bg-primary/5" : ""}`}>
                        <span className="material-symbols-outlined text-primary text-sm flex-shrink-0">{agent.icon}</span>
                        <div className="min-w-0 flex-1">
                          <p className="text-on-surface font-semibold text-xs truncate">{agent.name}</p>
                          <p className="text-on-surface/40 text-[10px] truncate">{agent.description}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {customAgents.length > 0 && (
                  <div className="border-t border-outline-variant/20">
                    <p className="text-[9px] uppercase tracking-widest text-on-surface/40 font-bold px-4 pt-3 pb-1">My Agents</p>
                    {customAgents.map(agent => (
                      <button key={agent.agent_id} onClick={() => handleSelectAgent(agent)}
                        className={`w-full flex items-center justify-between gap-2 px-4 py-3 hover:bg-primary/10 transition-all text-left ${activeAgentId === agent.agent_id ? "border-l-2 border-primary bg-primary/5" : ""}`}>
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          <span className="material-symbols-outlined text-on-surface/50 text-sm flex-shrink-0">{agent.icon}</span>
                          <div className="min-w-0 flex-1">
                            <p className="text-on-surface font-semibold text-xs truncate">{agent.name}</p>
                            <p className="text-on-surface/40 text-[10px] truncate">{agent.description || "Custom"}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span onClick={(e) => { e.stopPropagation(); setEditAgent(agent); setConfigModalOpen(true); setSelectorOpen(false); }}
                            className="material-symbols-outlined text-sm text-on-surface/30 hover:text-primary transition-colors flex-shrink-0">edit</span>
                          <span onClick={(e) => handleDeleteAgent(agent.agent_id, e)}
                            className="material-symbols-outlined text-sm text-on-surface/30 hover:text-red-500 transition-colors flex-shrink-0">delete</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {/* Configure New Agent */}
                <div className="border-t border-outline-variant/20 p-2">
                  <button
                    onClick={() => { setEditAgent(null); setSelectorOpen(false); setConfigModalOpen(true); }}
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-primary hover:bg-primary/10 rounded-xl transition-all text-xs font-bold"
                  >
                    <span className="material-symbols-outlined text-sm">add_circle</span>
                    Configure New Agent
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* New Chat */}
          <button
            suppressHydrationWarning
            className="w-full bg-primary text-white py-3 rounded-full font-bold text-sm mb-4 flex items-center justify-center gap-2 hover:brightness-110 active:scale-95 transition-all shadow-md shadow-primary/10 flex-shrink-0"
          >
            <span className="material-symbols-outlined text-sm">add</span>
            New Chat
          </button>

          {/* Chat History - Now Static */}
          <a className="flex items-center gap-3 px-6 py-3 text-primary font-bold bg-surface-container-high rounded-full text-sm shadow-sm mb-4" href="#">
            <span className="material-symbols-outlined">history</span>Chat History
          </a>
        </div>

        {/* Scrollable Nav Area */}
        <nav className="flex-1 overflow-y-auto custom-scrollbar p-6 pt-0 space-y-1">
          <div className="flex flex-col">
            <button
              onClick={() => setSettingsExpanded(!settingsExpanded)}
              suppressHydrationWarning
              className="w-full flex items-center justify-between px-6 py-3 text-on-surface/70 hover:text-primary hover:bg-surface-container-low transition-all text-sm rounded-full"
            >
              <div className="flex items-center gap-3 whitespace-nowrap">
                <span className="material-symbols-outlined">settings_input_component</span>
                Model Settings
              </div>
              <span className="material-symbols-outlined text-sm opacity-50 flex-shrink-0">
                {settingsExpanded ? 'expand_less' : 'expand_more'}
              </span>
            </button>

            {settingsExpanded && (
              <div className="px-6 pb-4 pt-2 space-y-3 text-[10px] text-on-surface/50">
                {config ? (
                  (() => {
                    const displayTemp = activeAgent?.model_settings?.temperature ?? config.temperature;
                    const displayTokens = activeAgent?.model_settings?.max_tokens ?? config.llm_max_answer_tokens;
                    const isCustomTemp = activeAgent?.model_settings?.temperature !== undefined;
                    const isCustomTokens = activeAgent?.model_settings?.max_tokens !== undefined;

                    return (
                      <>
                        <div className="flex flex-col">
                          <span className="uppercase tracking-widest font-bold opacity-60 text-[8px] mb-0.5">Embedding Model</span>
                          <span className="font-mono text-primary font-bold truncate leading-tight" title={config.embedding_model}>{config.embedding_model}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="uppercase tracking-widest font-bold opacity-60 text-[8px] mb-0.5">Generation Model</span>
                          <span className="font-mono text-primary font-bold truncate leading-tight" title={config.generation_model}>{config.generation_model}</span>
                        </div>
                        <div className="flex flex-col border-t border-outline-variant/10 pt-2">
                          <span className="uppercase tracking-widest font-bold opacity-60 text-[8px] mb-0.5">Temperature</span>
                          <span className={`font-mono font-bold ${isCustomTemp ? 'text-primary' : 'text-on-surface/80'}`}>
                            {displayTemp} {isCustomTemp && <span className="text-[8px] ml-1 opacity-70">(Custom)</span>}
                          </span>
                        </div>
                        <div className="flex flex-col border-t border-outline-variant/10 pt-2">
                          <span className="uppercase tracking-widest font-bold opacity-60 text-[8px] mb-0.5">Max Output</span>
                          <span className={`font-mono font-bold ${isCustomTokens ? 'text-primary' : 'text-on-surface/80'}`}>
                            {displayTokens} tkns {isCustomTokens && <span className="text-[8px] ml-1 opacity-70">(Custom)</span>}
                          </span>
                        </div>
                        <div className="flex items-center justify-between border-t border-outline-variant/10 pt-2">
                          <span className="uppercase tracking-widest font-bold opacity-60 text-[8px]">Context Window</span>
                          <span className="font-mono font-bold text-on-surface/80">{config.max_context_tokens} tkns</span>
                        </div>
                      </>
                    );
                  })()
                ) : (
                  <div className="text-center italic pb-2">Loading params...</div>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col">
            <button
              suppressHydrationWarning
              onClick={() => setKbExpanded(!kbExpanded)}
              className="w-full flex items-center justify-between px-6 py-3 text-on-surface/70 hover:text-white hover:bg-primary transition-all text-sm rounded-full group"
            >
              <div className="flex items-center gap-3 whitespace-nowrap">
                <span className="material-symbols-outlined group-hover:text-white">database</span>
                Knowledge Base
              </div>
              <span className="material-symbols-outlined text-sm opacity-50 group-hover:text-white flex-shrink-0">
                {kbExpanded ? 'expand_less' : 'expand_more'}
              </span>
            </button>

            {kbExpanded && (
              <div className="px-6 pb-4 pt-2 space-y-3 text-[10px] text-on-surface/50">
                {stats ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="uppercase tracking-widest font-bold opacity-60 text-[8px]">Status</span>
                      <span className={`font-mono font-bold uppercase ${stats.status === 'green' ? 'text-green-500' : 'text-red-500'}`}>
                        {stats.status}
                      </span>
                    </div>
                    <div className="flex flex-col border-t border-outline-variant/10 pt-2">
                      <span className="uppercase tracking-widest font-bold opacity-60 text-[8px] mb-0.5">Collection</span>
                      <span className="font-mono text-primary font-bold truncate leading-tight" title={stats.collection_name}>{stats.collection_name}</span>
                    </div>
                    <div className="flex items-center justify-between border-t border-outline-variant/10 pt-2">
                      <span className="uppercase tracking-widest font-bold opacity-60 text-[8px]">Vectors Configured</span>
                      <span className="font-mono font-bold text-on-surface/80">{stats.vector_count.toLocaleString()}</span>
                    </div>
                  </>
                ) : (
                  <div className="text-center italic pb-2">Loading stats...</div>
                )}
              </div>
            )}
          </div>
        </nav>

        {/* Static Footer */}
        <div className="p-6 space-y-1 border-t border-outline-variant/10 flex-shrink-0">
          <a className="flex items-center gap-3 px-6 py-3 text-on-surface/70 hover:text-primary hover:bg-surface-container-low transition-all text-sm rounded-full" href="#">
            <span className="material-symbols-outlined">help</span>Help Center
          </a>
          <a className="flex items-center gap-3 px-6 py-3 text-on-surface/70 hover:text-primary hover:bg-surface-container-low transition-all text-sm rounded-full" href="#">
            <span className="material-symbols-outlined">account_circle</span>Account
          </a>
        </div>
      </aside>

      {/* Agent Config Modal */}
      <AgentConfigModal
        isOpen={configModalOpen}
        onClose={() => { setConfigModalOpen(false); setEditAgent(null); }}
        editAgent={editAgent}
        onSaved={(newAgent) => {
          fetchAgents();
          onAgentChange(newAgent.agent_id);
          setConfigModalOpen(false);
          setEditAgent(null);
        }}
        baseAgents={baseAgents}
      />
    </>
  );
};

export default SidebarLeft;
