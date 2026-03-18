'use client';
import React, { useRef, useState } from 'react';
import { UploadCloud, CheckCircle2, XCircle } from 'lucide-react';
import { Spinner } from '../ui/Spinner';
import { JobStatus } from '@/lib/api';

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  status: JobStatus | 'idle';
  error: string | null;
}

export function UploadZone({ onFileSelect, disabled, status, error }: UploadZoneProps) {
  const [isHovered, setIsHovered] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsHovered(false);
    if (disabled) return;
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl text-center relative overflow-hidden flex flex-col items-center justify-center min-h-[300px]">
      {status === 'idle' ? (
        <div 
          onClick={() => !disabled && inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setIsHovered(true); }}
          onDragLeave={() => setIsHovered(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center w-full h-full p-8 border-2 border-dashed rounded-lg cursor-pointer transition-all duration-300 ${isHovered ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-700 hover:border-indigo-400 hover:bg-slate-800/50'} ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <UploadCloud className={`w-12 h-12 mb-4 transition-colors ${isHovered ? 'text-indigo-400' : 'text-slate-500'}`} />
          <p className="text-sm font-medium text-slate-300">
            Drag & drop your document here
          </p>
          <p className="text-xs text-slate-500 mt-2">
            Supports PDF, TXT, MD
          </p>
          <input 
             ref={inputRef} 
             type="file" 
             className="hidden" 
             onChange={(e) => e.target.files && onFileSelect(e.target.files[0])}
             accept=".pdf,.txt,.md"
          />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center space-y-4 animate-in fade-in duration-500">
           {status === 'complete' ? (
              <CheckCircle2 className="w-16 h-16 text-emerald-400" />
           ) : status === 'failed' ? (
              <XCircle className="w-16 h-16 text-red-400" />
           ) : (
              <Spinner className="w-12 h-12 text-indigo-400" />
           )}
           <h3 className="text-xl font-semibold text-slate-200 capitalize">
              {status.replace(/_/g, ' ')}
           </h3>
           <p className="text-slate-400 text-sm max-w-xs mx-auto">
             {status === 'complete' 
               ? 'Document successfully processed and vectors embedded!'
               : 'Please wait while the document pipeline processes background tasks.'}
           </p>
           {status === 'complete' && (
             <button 
               onClick={() => window.location.reload()} 
               className="mt-4 text-xs text-indigo-400 hover:text-indigo-300 underline"
             >
               Upload another
             </button>
           )}
           {status === 'failed' && (
             <button 
               onClick={() => window.location.reload()} 
               className="mt-4 text-xs text-red-400 hover:text-red-300 underline"
             >
               Retry Upload
             </button>
           )}
        </div>
      )}
      
      {error && (
        <div className="absolute bottom-4 left-4 right-4 bg-red-500/20 border border-red-500/50 text-red-200 text-xs px-4 py-3 rounded-lg flex items-center gap-2 text-left">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">{error}</span>
        </div>
      )}
    </div>
  );
}
