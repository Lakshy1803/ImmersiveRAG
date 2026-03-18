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

  const fetchAgents = async () => {
    try {
      const list = await ImmersiveRagAPI.listAgents();
      setAgents(list);
      const current = list.find(a => a.agent_id === activeAgentId) ?? list[0] ?? null;
      setActiveAgent(current);
    } catch {
      // Backend may not be ready — use a placeholder
      setActiveAgent({ agent_id: activeAgentId, name: "Document Analyzer", description: "", system_prompt: "", icon: "description", is_system: true, base_agent_id: null });
    }
  };

  useEffect(() => { fetchAgents(); }, [activeAgentId]);

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
        <div className="p-6">

          {/* Agent Selector Dropdown */}
          <div className="relative mb-8">
            <button
              onClick={() => setSelectorOpen(!selectorOpen)}
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
                        <span className="material-symbols-outlined text-primary text-sm">{agent.icon}</span>
                        <div>
                          <p className="text-on-surface font-semibold text-xs">{agent.name}</p>
                          <p className="text-on-surface/40 text-[10px] truncate max-w-[140px]">{agent.description}</p>
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
                        <div className="flex items-center gap-3">
                          <span className="material-symbols-outlined text-on-surface/50 text-sm">{agent.icon}</span>
                          <div>
                            <p className="text-on-surface font-semibold text-xs">{agent.name}</p>
                            <p className="text-on-surface/40 text-[10px] truncate max-w-[100px]">{agent.description || "Custom"}</p>
                          </div>
                        </div>
                        <span onClick={(e) => handleDeleteAgent(agent.agent_id, e)}
                          className="material-symbols-outlined text-sm text-on-surface/30 hover:text-red-500 transition-colors flex-shrink-0">delete</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Configure New Agent */}
                <div className="border-t border-outline-variant/20 p-2">
                  <button
                    onClick={() => { setSelectorOpen(false); setConfigModalOpen(true); }}
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
          <button className="w-full bg-primary text-white py-3 rounded-full font-bold text-sm mb-8 flex items-center justify-center gap-2 hover:brightness-110 transition-all active:scale-95 shadow-md shadow-primary/10">
            <span className="material-symbols-outlined text-sm">add</span>
            New Chat
          </button>

          <nav className="space-y-1">
            <a className="flex items-center gap-3 px-6 py-3 text-primary font-bold bg-surface-container-high rounded-full text-sm shadow-sm" href="#">
              <span className="material-symbols-outlined">history</span>Chat History
            </a>
            <a className="flex items-center justify-between px-6 py-3 text-on-surface/70 hover:text-primary hover:bg-surface-container-low transition-all text-sm rounded-full" href="#">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined">settings_input_component</span>
                Model Settings
              </div>
              <span className="material-symbols-outlined text-sm opacity-50">expand_more</span>
            </a>
            <button className="w-full flex items-center gap-3 px-6 py-3 text-on-surface/70 hover:text-white hover:bg-primary transition-all text-sm rounded-full group">
              <span className="material-symbols-outlined group-hover:text-white">database</span>
              Knowledge Base
            </button>
          </nav>
        </div>

        <div className="mt-auto p-6 space-y-1">
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
        onClose={() => setConfigModalOpen(false)}
        onSaved={(newAgent) => {
          fetchAgents();
          onAgentChange(newAgent.agent_id);
          setConfigModalOpen(false);
        }}
        baseAgents={baseAgents}
      />
    </>
  );
};

export default SidebarLeft;
