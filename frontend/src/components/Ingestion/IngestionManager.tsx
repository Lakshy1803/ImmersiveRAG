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
  
  const [jobIds, setJobIds] = useState<string[]>([]);
  const [status, setStatus] = useState<JobStatus | 'idle'>('idle');
  const [error, setError] = useState<string | null>(null);

  // Polling mechanism
  useEffect(() => {
    if (jobIds.length === 0 || status === 'complete' || status === 'failed') return;

    const intervalId = setInterval(async () => {
      try {
        let finishedCount = 0;
        let failedCount = 0;
        let lastError = null;

        for (const jid of jobIds) {
          const result = await ImmersiveRagAPI.checkStatus(jid);
          if (result.status === 'complete') {
             finishedCount++;
          } else if (result.status === 'failed') {
             failedCount++;
             finishedCount++; // failure is a terminal state
             lastError = result.message || 'Unknown error';
          }
        }

        if (finishedCount === jobIds.length) {
           clearInterval(intervalId);
           if (failedCount === jobIds.length) {
              setStatus('failed');
              setError(lastError || 'All files failed to process. Try using Cloud LlamaParse if these are scans.');
           } else if (failedCount > 0) {
              setStatus('complete');
              setError(`${failedCount} out of ${jobIds.length} files failed: ${lastError}. (Successful files were indexed)`);
           } else {
              setStatus('complete');
           }
        } else {
           setStatus('processing');
        }
      } catch (err: any) {
        console.error("Polling error:", err);
      }
    }, 3000);

    return () => clearInterval(intervalId);
  }, [jobIds, status]);

  const handleFilesUpload = async (files: File[]) => {
    setError(null);
    setStatus('processing'); 
    try {
      const response = await ImmersiveRagAPI.bulkIngest(files, config);
      setJobIds(response.jobs.map(j => j.job_id));
      // Start polling
      if(response.jobs.length === 0) setStatus('idle');
    } catch (err: any) {
      setError(err.message || 'Failed to upload document(s)');
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
           <p className="text-on-surface/50 text-sm mt-1">Configure and bulk-index enterprise documents into the local vector layer safely.</p>
        </div>
      )}
      
      <ConfigPanel 
        config={config} 
        onChange={setConfig} 
        disabled={isUploading} 
        compact={compact}
      />
      
      <UploadZone 
        onFilesSelect={handleFilesUpload} 
        disabled={isUploading} 
        status={status}
        error={error}
        compact={compact}
      />
    </div>
  );
}
