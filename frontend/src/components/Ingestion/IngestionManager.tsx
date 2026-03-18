'use client';
import React, { useState, useEffect } from 'react';
import { ConfigPanel, IngestionConfig } from './ConfigPanel';
import { UploadZone } from './UploadZone';
import { ImmersiveRagAPI, JobStatus } from '@/lib/api';

export function IngestionManager() {
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
        // Log polling errors so we don't repeatedly crash the UI
        console.error("Polling error:", err);
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [jobId, status]);

  const handleFileUpload = async (file: File) => {
    setError(null);
    setStatus('processing'); // Set early to give immediate feedback
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
    <div className="flex flex-col gap-6 w-full max-w-xl">
      <div className="flex flex-col">
         <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
           Document Control Plane
         </h1>
         <p className="text-slate-400 text-sm mt-1">Configure and index enterprise documents into the local vector layer safely.</p>
      </div>
      
      <ConfigPanel 
        config={config} 
        onChange={setConfig} 
        disabled={isUploading} 
      />
      
      <UploadZone 
        onFileSelect={handleFileUpload} 
        disabled={isUploading} 
        status={status}
        error={error}
      />
    </div>
  );
}
