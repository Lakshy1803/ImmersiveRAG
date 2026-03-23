"use client";

import React from "react";
import { IngestionManager } from "../Ingestion/IngestionManager";
import { ChunkNode } from "@/lib/api";

interface SidebarRightProps {
  extractedContext: ChunkNode[];
}

const SidebarRight: React.FC<SidebarRightProps> = ({ extractedContext }) => {
  return (
    <aside className="h-screen w-72 fixed right-0 top-0 pt-16 bg-surface-container flex flex-col border-l border-outline-variant/30 z-40 hidden xl:flex">
      <div className="flex-1 flex flex-col overflow-hidden">
        
        {/* Ingestion Section (Top - Custom Addition to design) */}
        <div className="p-6 border-b border-outline-variant/10">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xs uppercase tracking-widest text-on-surface/50 font-bold">Ingestion</h2>
              <p className="text-[10px] text-on-surface/40 font-medium">Document Control Plane</p>
            </div>
            <span className="material-symbols-outlined text-primary scale-75">cloud_upload</span>
          </div>
          
          <div className="bg-surface-container-low p-4 rounded-2xl border border-outline-variant/30 shadow-sm mb-4">
            <IngestionManager compact={true} />
          </div>
        </div>

        {/* Context Section (Bottom - Scrollable Live Data) */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="px-6 py-4 flex items-center justify-between">
            <div>
              <h2 className="text-xs uppercase tracking-widest text-on-surface/50 font-bold">Context</h2>
              <p className="text-[10px] text-on-surface/40 font-medium">Extracted Vector Embeddings</p>
            </div>
            <span className="material-symbols-outlined text-primary scale-75">barcode_reader</span>
          </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar px-6 pb-6 space-y-3">
            {extractedContext.length > 0 ? (
              extractedContext.map((chunk, idx) => (
                <div key={idx} className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/20 shadow-sm hover:border-primary/30 transition-colors">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[9px] font-bold text-primary px-2 py-0.5 bg-primary/10 rounded-full">
                      {(chunk.score * 100).toFixed(1)}% Match
                    </span>
                    <span className="text-[9px] text-on-surface/40">
                      ID: {chunk.chunk_id?.substring(0, 8)}
                    </span>
                  </div>
                  <p className="text-[11px] text-on-surface/70 leading-relaxed italic">
                    "{chunk.text.length > 120 ? chunk.text.substring(0, 120) + '...' : chunk.text}"
                  </p>
                </div>
              ))
            ) : (
              <div className="p-8 text-center border-2 border-dashed border-outline-variant/10 rounded-2xl">
                <p className="text-[11px] text-on-surface/30 italic">No query context</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
};

export default SidebarRight;
