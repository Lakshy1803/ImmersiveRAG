'use client';
import React, { useState, useEffect } from 'react';
import { ConfigPanel, IngestionConfig } from './ConfigPanel';
import { UploadZone } from './UploadZone';
import { ImmersiveRagAPI, JobStatus } from '@/lib/api';

export function IngestionManager({ compact = false }: { compact?: boolean }) {
  const [config, setConfig] = useState<IngestionConfig>({
    extraction_mode: 'local_markdown',
    embedding_mode: 'local_fastembed',
  });
  
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | 'idle'>('idle');
  const [error, setError] = useState<string | null>(null);

  // Polling mechanism
  useEffect(() => {
    if (!jobId || status === 'complete' || status === 'failed') return;

    const intervalId = setInterval(async () => {
      try {
        const result = await ImmersiveRagAPI.checkStatus(jobId);
        setStatus(result.status);
        if (result.status === 'failed' && result.error) {
           setError(result.error);
        }
      } catch (err: any) {
        console.error("Polling error:", err);
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [jobId, status]);

  const handleFileUpload = async (file: File) => {
    setError(null);
    setStatus('processing'); 
    try {
      const response = await ImmersiveRagAPI.ingest(file, config);
      setJobId(response.job_id);
      setStatus(response.status);
    } catch (err: any) {
      setError(err.message || 'Failed to upload document');
      setStatus('failed');
    }
  };

  const isUploading = status !== 'idle' && status !== 'complete' && status !== 'failed';

  return (
    <div className={`flex flex-col gap-4 w-full ${compact ? '' : 'max-w-xl'}`}>
      {!compact && (
        <div className="flex flex-col mb-2">
           <h1 className="text-2xl font-bold text-on-surface">
             Document Control Plane
           </h1>
           <p className="text-on-surface/50 text-sm mt-1">Configure and index enterprise documents into the local vector layer safely.</p>
        </div>
      )}
      
      <ConfigPanel 
        config={config} 
        onChange={setConfig} 
        disabled={isUploading} 
        compact={compact}
      />
      
      <UploadZone 
        onFileSelect={handleFileUpload} 
        disabled={isUploading} 
        status={status}
        error={error}
        compact={compact}
      />
    </div>
  );
}
