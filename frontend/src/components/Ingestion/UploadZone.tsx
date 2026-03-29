'use client';
import React, { useRef, useState } from 'react';
import { UploadCloud, CheckCircle2, XCircle } from 'lucide-react';
import { Spinner } from '../ui/Spinner';
import { JobStatus } from '@/lib/api';

interface UploadZoneProps {
  onFilesSelect: (files: File[]) => void;
  disabled?: boolean;
  status: JobStatus | 'idle';
  error: string | null;
  compact?: boolean;
}

export function UploadZone({ onFilesSelect, disabled, status, error, compact = false }: UploadZoneProps) {
  const [isHovered, setIsHovered] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsHovered(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFilesSelect(Array.from(e.dataTransfer.files));
    }
  };

  const isProcessing = status !== 'idle' && status !== 'complete' && status !== 'failed';

  return (
    <div className={`${compact ? 'bg-transparent' : 'bg-surface-container border border-outline-variant/30 rounded-xl p-6 shadow-xl'} text-center relative overflow-hidden flex flex-col items-center justify-center ${compact ? 'min-h-[140px]' : 'min-h-[300px]'}`}>
      {status === 'idle' ? (
        <div
          onClick={() => !disabled && inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setIsHovered(true); }}
          onDragLeave={() => setIsHovered(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center w-full h-full ${compact ? 'p-4' : 'p-8'} border-2 border-dashed rounded-2xl cursor-pointer transition-all duration-300 ${isHovered ? 'border-primary bg-primary/5' : 'border-outline-variant/30 hover:border-primary/50 hover:bg-surface-container-high/40'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <span className={`material-symbols-outlined mb-2 transition-colors ${compact ? 'text-2xl' : 'text-4xl'} ${isHovered ? 'text-primary' : 'text-on-surface/30'}`}>
            upload_file
          </span>
          <p className={`${compact ? 'text-[10px]' : 'text-sm'} font-bold uppercase tracking-wider text-on-surface/60`}>
            {compact ? 'Click or Drop File' : 'Drag & drop document here'}
          </p>
          {!compact && (
            <p className="text-xs text-on-surface/30 mt-2 font-medium">
              Supports PDF, TXT, MD
            </p>
          )}
          <input
            ref={inputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => e.target.files && onFilesSelect(Array.from(e.target.files))}
            accept=".pdf,.txt,.md"
          />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center space-y-3 animate-in fade-in duration-500 w-full">
          {status === 'complete' ? (
            <span className="material-symbols-outlined text-4xl text-emerald-500 scale-125">check_circle</span>
          ) : status === 'failed' ? (
            <span className="material-symbols-outlined text-4xl text-primary scale-125">error</span>
          ) : (
            <Spinner className={`text-primary ${compact ? 'w-8 h-8' : 'w-12 h-12'}`} />
          )}

          {!compact && (
            <h3 className="text-lg font-bold text-on-surface capitalize tracking-tight">
              {status.replace(/_/g, ' ')}
            </h3>
          )}

          <p className={`text-on-surface/60 font-medium leading-tight ${compact ? 'text-[10px]' : 'text-xs max-w-xs'}`}>
            {status === 'complete'
              ? 'Vectors successfully indexed.'
              : status === 'failed'
                ? 'Processing failed.'
                : `Current State: ${status.replace(/_/g, ' ')}`}
          </p>

          {(status === 'complete' || status === 'failed') && (
            <button
              onClick={() => window.location.reload()}
              className={`mt-2 font-bold uppercase tracking-widest text-primary hover:brightness-125 underline decoration-2 underline-offset-4 transition-all ${compact ? 'text-[9px]' : 'text-[10px]'}`}
            >
              {status === 'complete' ? 'Reset Workspace' : 'Retry Upload'}
            </button>
          )}
        </div>
      )}

      {error && (
        <div className={`mt-3 w-full bg-primary/10 border border-primary/20 text-on-surface/80 px-3 py-2 rounded-lg flex items-center gap-2 text-left ${compact ? 'text-[9px]' : 'text-[10px] mt-4'}`}>
          <span className="material-symbols-outlined text-primary" style={{ fontSize: compact ? '12px' : '16px' }}>warning</span>
          <span className="truncate font-medium">{error}</span>
        </div>
      )}

    </div>
  );
}
