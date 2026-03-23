'use client';
import React, { useState, useEffect } from 'react';
import Image from "next/image";
import { Settings2, CheckCircle } from 'lucide-react';
import ThemeToggle from "./ThemeToggle";
import { LLMConfigModal } from "@/components/Settings/LLMConfigModal";
import { ImmersiveRagAPI } from "@/lib/api";

const STORAGE_KEY = 'immersive_rag_llm_config';

const Header: React.FC = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [llmConfigured, setLlmConfigured] = useState(false);

  // On mount: if localStorage has saved config, push it to the backend
  useEffect(() => {
    const applyStoredConfig = async () => {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) return;
        const parsed = JSON.parse(stored);
        if (parsed.apiKey && parsed.baseUrl && parsed.model) {
          await ImmersiveRagAPI.saveLLMConfig(parsed.apiKey, parsed.baseUrl, parsed.model);
          setLlmConfigured(true);
        }
      } catch {
        // silently ignore — backend may not be up yet
      }
    };
    applyStoredConfig();
  }, []);

  // After modal closes, re-check if configured
  const handleModalClose = () => {
    setSettingsOpen(false);
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setLlmConfigured(!!parsed.apiKey);
      }
    } catch {
      // ignore
    }
  };

  return (
    <>
      <header className="fixed top-0 w-full z-50 bg-surface-container/80 backdrop-blur-md flex justify-between items-center px-8 h-16 border-b border-outline-variant/30">
        <div className="flex items-center gap-4">
          {/* Logo / brand slot */}
        </div>

        <div className="flex items-center gap-3">
          {/* LLM Settings Button */}
          <button
            onClick={() => setSettingsOpen(true)}
            title="LLM Connection Settings"
            className={`relative flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              llmConfigured
                ? 'border-green-500/40 bg-green-500/10 text-green-400 hover:bg-green-500/20'
                : 'border-outline-variant/40 bg-surface-container-high/40 text-on-surface/60 hover:bg-surface-container-high hover:text-on-surface'
            }`}
          >
            {llmConfigured ? (
              <CheckCircle className="w-3.5 h-3.5" />
            ) : (
              <Settings2 className="w-3.5 h-3.5" />
            )}
            <span className="hidden sm:inline">
              {llmConfigured ? 'LLM Connected' : 'Configure LLM'}
            </span>
          </button>

          <ThemeToggle />
        </div>
      </header>

      <LLMConfigModal isOpen={settingsOpen} onClose={handleModalClose} />
    </>
  );
};

export default Header;
