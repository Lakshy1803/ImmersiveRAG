'use client';
import React from 'react';
import { Settings2 } from 'lucide-react';

export interface IngestionConfig {
  extraction_mode: string;
  embedding_mode: string;
}

interface ConfigPanelProps {
  config: IngestionConfig;
  onChange: (cfg: IngestionConfig) => void;
  disabled?: boolean;
}

export function ConfigPanel({ config, onChange, disabled }: ConfigPanelProps) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden group">
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"/>
      
      <div className="flex items-center gap-2 mb-6 relative z-10">
        <Settings2 className="w-5 h-5 text-indigo-400" />
        <h2 className="text-lg font-semibold text-slate-100">Ingestion Configuration</h2>
      </div>

      <div className="space-y-6 relative z-10">
        {/* Extraction Mode */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-slate-300">Extraction Provider</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              suppressHydrationWarning
              disabled={disabled}
              onClick={() => onChange({ ...config, extraction_mode: 'local_markdown' })}
              className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                config.extraction_mode === 'local_markdown' 
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.2)]'
                  : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:bg-slate-800 hover:text-slate-200'
              } ${disabled && 'opacity-50 cursor-not-allowed'}`}
            >
              Local Fallback
            </button>
            <button
              suppressHydrationWarning
              disabled={disabled}
              onClick={() => onChange({ ...config, extraction_mode: 'cloud_llamaparse' })}
              className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                config.extraction_mode === 'cloud_llamaparse'
                 ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50 shadow-[0_0_15px_rgba(168,85,247,0.2)]'
                 : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:bg-slate-800 hover:text-slate-200'
              } ${disabled && 'opacity-50 cursor-not-allowed'}`}
            >
              LlamaParse (Cloud)
            </button>
          </div>
        </div>

        {/* Embedding Mode */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-slate-300">Vector Embedding Strategy</label>
           <div className="grid grid-cols-2 gap-3">
            <button
              suppressHydrationWarning
              disabled={disabled}
              onClick={() => onChange({ ...config, embedding_mode: 'local_fastembed' })}
              className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                config.embedding_mode === 'local_fastembed'
                 ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.2)]'
                 : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:bg-slate-800 hover:text-slate-200'
              } ${disabled && 'opacity-50 cursor-not-allowed'}`}
            >
              FastEmbed (Local)
            </button>
            <button
              suppressHydrationWarning
              disabled={disabled}
              onClick={() => onChange({ ...config, embedding_mode: 'cloud_openai' })}
               className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                config.embedding_mode === 'cloud_openai'
                   ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
                 : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:bg-slate-800 hover:text-slate-200'
              } ${disabled && 'opacity-50 cursor-not-allowed'}`}
            >
              OpenAI (Corporate API)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
