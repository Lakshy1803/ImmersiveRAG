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
  compact?: boolean;
}

export function ConfigPanel({ config, onChange, disabled, compact = false }: ConfigPanelProps) {
  return (
    <div className={`${compact ? 'p-0' : 'bg-surface-container border border-outline-variant/30 rounded-xl p-6 shadow-xl relative overflow-hidden'}`}>
      {!compact && (
        <div className="flex items-center gap-2 mb-6 relative z-10">
          <Settings2 className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold text-on-surface">Ingestion Configuration</h2>
        </div>
      )}

      <div className={`${compact ? 'space-y-4' : 'space-y-6 relative z-10'}`}>
        {/* Extraction Mode */}
        <div className="space-y-2">
          <label className="text-[10px] font-bold uppercase tracking-widest text-on-surface/40">Extraction Provider</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              suppressHydrationWarning
              disabled={disabled}
              onClick={() => onChange({ ...config, extraction_mode: 'local_markdown' })}
              className={`px-3 py-2 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all border ${
                config.extraction_mode === 'local_markdown' 
                  ? 'bg-primary/20 text-primary border-primary/50 shadow-sm'
                  : 'bg-surface-container-high/50 text-on-surface/40 border-transparent hover:bg-surface-container-high hover:text-on-surface/70'
              } ${disabled && 'opacity-50 cursor-not-allowed'}`}
            >
              Local
            </button>
            <button
              suppressHydrationWarning
              disabled={disabled}
              onClick={() => onChange({ ...config, extraction_mode: 'cloud_llamaparse' })}
              className={`px-3 py-2 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all border ${
                config.extraction_mode === 'cloud_llamaparse'
                 ? 'bg-primary/20 text-primary border-primary/50 shadow-sm'
                 : 'bg-surface-container-high/50 text-on-surface/40 border-transparent hover:bg-surface-container-high hover:text-on-surface/70'
              } ${disabled && 'opacity-50 cursor-not-allowed'}`}
            >
              Cloud
            </button>
          </div>
        </div>

        {/* Embedding Mode */}
        <div className="space-y-2">
          <label className="text-[10px] font-bold uppercase tracking-widest text-on-surface/40">Vector Strategy</label>
           <div className="grid grid-cols-2 gap-2">
            <button
              suppressHydrationWarning
              disabled={disabled}
              onClick={() => onChange({ ...config, embedding_mode: 'local_fastembed' })}
              className={`px-3 py-2 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all border ${
                config.embedding_mode === 'local_fastembed'
                 ? 'bg-primary/20 text-primary border-primary/50 shadow-sm'
                 : 'bg-surface-container-high/50 text-on-surface/40 border-transparent hover:bg-surface-container-high hover:text-on-surface/70'
              } ${disabled && 'opacity-50 cursor-not-allowed'}`}
            >
              FastEmbed
            </button>
            <button
              suppressHydrationWarning
              disabled={disabled}
              onClick={() => onChange({ ...config, embedding_mode: 'cloud_openai' })}
               className={`px-3 py-2 rounded-full text-[10px] font-bold uppercase tracking-wider transition-all border ${
                config.embedding_mode === 'cloud_openai'
                   ? 'bg-primary/20 text-primary border-primary/50 shadow-sm'
                 : 'bg-surface-container-high/50 text-on-surface/40 border-transparent hover:bg-surface-container-high hover:text-on-surface/70'
              } ${disabled && 'opacity-50 cursor-not-allowed'}`}
            >
              Corporate
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
