'use client';
import React, { useState, useEffect } from 'react';
import Image from "next/image";
import { Settings2, CheckCircle } from 'lucide-react';
import ThemeToggle from "./ThemeToggle";
import { LLMConfigModal } from "@/components/Settings/LLMConfigModal";
import { EmbeddingConfigModal } from "@/components/Settings/EmbeddingConfigModal";
import { ImmersiveRagAPI } from "@/lib/api";

const LLM_STORAGE_KEY = 'immersive_rag_llm_config';
const EMBED_STORAGE_KEY = 'immersive_rag_embedding_config';

const Header: React.FC = () => {
  const [llmModalOpen, setLlmModalOpen] = useState(false);
  const [embedModalOpen, setEmbedModalOpen] = useState(false);
  const [llmStatus, setLlmStatus] = useState<'none' | 'set' | 'verified'>('none');
  const [embedStatus, setEmbedStatus] = useState<'none' | 'set' | 'verified'>('none');

  // On mount: sync localStorage to backend
  useEffect(() => {
    const syncConfig = async () => {
      try {
        const storedLlm = localStorage.getItem(LLM_STORAGE_KEY);
        if (storedLlm) {
          const parsed = JSON.parse(storedLlm);
          if (parsed.apiKey) {
            await ImmersiveRagAPI.saveLLMConfig(parsed.apiKey, parsed.baseUrl, parsed.model);
            setLlmStatus(parsed.verified ? 'verified' : 'set');
          }
        }

        const storedEmbed = localStorage.getItem(EMBED_STORAGE_KEY);
        if (storedEmbed) {
          const parsed = JSON.parse(storedEmbed);
          if (parsed.apiKey) {
            await ImmersiveRagAPI.saveEmbeddingConfig(parsed.apiKey, parsed.baseUrl, parsed.model);
            setEmbedStatus(parsed.verified ? 'verified' : 'set');
          }
        }
      } catch (err) {
        console.warn("Header config sync failed:", err);
      }
    };
    syncConfig();
  }, []);

  const refreshStatus = () => {
    try {
      const llm = localStorage.getItem(LLM_STORAGE_KEY);
      if (llm) {
        const parsed = JSON.parse(llm);
        setLlmStatus(parsed.apiKey ? (parsed.verified ? 'verified' : 'set') : 'none');
      } else setLlmStatus('none');

      const embed = localStorage.getItem(EMBED_STORAGE_KEY);
      if (embed) {
        const parsed = JSON.parse(embed);
        setEmbedStatus(parsed.apiKey ? (parsed.verified ? 'verified' : 'set') : 'none');
      } else setEmbedStatus('none');
    } catch { /* ignore */ }
  };

  return (
    <>
      <header className="fixed top-0 w-full z-50 bg-surface-container/80 backdrop-blur-md flex justify-between items-center px-8 h-16 border-b border-outline-variant/30">
        {/* Left side spacer */}
        <div className="flex-1" />

        {/* Centered Title */}
        <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
          <span className="text-2xl font-black tracking-tighter text-on-surface">
            Agentic<span className="text-primary"> Lab</span>
          </span>
        </div>

        {/* Right side controls */}
        <div className="flex-1 flex items-center justify-end gap-4">
          {/* Config Controls */}
          <div className="flex items-center gap-2 bg-surface-container-high/40 p-1 rounded-full border border-outline-variant/20">
            {/* LLM Config Pill */}
            <button
              onClick={() => setLlmModalOpen(true)}
              suppressHydrationWarning
              className={`group flex items-center gap-2 h-8 px-2 rounded-full border overflow-hidden transition-all duration-300 ease-out max-w-[2.2rem] hover:max-w-[10rem] hover:px-3 ${llmStatus === 'verified'
                ? 'border-green-500/30 bg-green-500/10 text-green-400'
                : llmStatus === 'set'
                  ? 'border-amber-500/30 bg-amber-500/10 text-amber-500'
                  : 'border-outline-variant/30 bg-surface-container-high/30 text-on-surface/50 hover:text-on-surface hover:border-primary/30'
                }`}
            >
              <div className="relative flex-shrink-0">
                <Settings2 className="w-4 h-4" />
                {llmStatus !== 'none' && (
                  <div className={`absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full border border-surface-container shadow-sm ${llmStatus === 'verified' ? 'bg-green-500' : 'bg-amber-500'}`} />
                )}
              </div>
              <span className="hidden group-hover:inline whitespace-nowrap text-[10px] font-bold uppercase tracking-wider">
                {llmStatus === 'verified' ? 'LLM OK' : llmStatus === 'set' ? 'LLM SET (Untested)' : 'Set LLM'}
              </span>
            </button>

            {/* Embedding Config Pill */}
            <button
              onClick={() => setEmbedModalOpen(true)}
              suppressHydrationWarning
              className={`group flex items-center gap-2 h-8 px-2 rounded-full border overflow-hidden transition-all duration-300 ease-out max-w-[2.2rem] hover:max-w-[10rem] hover:px-3 ${embedStatus === 'verified'
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                : embedStatus === 'set'
                  ? 'border-amber-500/30 bg-amber-500/10 text-amber-500'
                  : 'border-outline-variant/30 bg-surface-container-high/30 text-on-surface/50 hover:text-on-surface hover:border-primary/30'
                }`}
            >
              <div className="relative flex-shrink-0">
                <span className="material-symbols-outlined text-[18px]">Layers</span>
                {embedStatus !== 'none' && (
                  <div className={`absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full border border-surface-container shadow-sm ${embedStatus === 'verified' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                )}
              </div>
              <span className="hidden group-hover:inline whitespace-nowrap text-[10px] font-bold uppercase tracking-wider">
                {embedStatus === 'verified' ? 'Embed OK' : embedStatus === 'set' ? 'Embed SET (Untested)' : 'Set Embed'}
              </span>
            </button>
          </div>

          <div className="w-px h-4 bg-outline-variant/30" />
          <ThemeToggle />
        </div>
      </header>

      <LLMConfigModal
        isOpen={llmModalOpen}
        onClose={() => { setLlmModalOpen(false); refreshStatus(); }}
      />

      <EmbeddingConfigModal
        isOpen={embedModalOpen}
        onClose={() => { setEmbedModalOpen(false); refreshStatus(); }}
      />
    </>
  );
};

export default Header;
