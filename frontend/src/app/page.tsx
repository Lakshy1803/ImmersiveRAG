"use client";

import React, { useState } from "react";
import Header from "@/components/Navigation/Header";
import SidebarLeft from "@/components/Navigation/SidebarLeft";
import SidebarRight from "@/components/Navigation/SidebarRight";
import { AgentChat } from "@/components/Chat/AgentChat";
import { ChunkNode } from "@/lib/api";

export default function Home() {
  const [extractedContext, setExtractedContext] = useState<ChunkNode[]>([]);
  const [activeAgentId, setActiveAgentId] = useState("doc_analyzer");

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <Header />
      
      <div className="flex flex-1 relative overflow-hidden">
        {/* Left Navigation */}
        <SidebarLeft activeAgentId={activeAgentId} onAgentChange={setActiveAgentId} />

        {/* Main Canvas */}
        <main className="lg:ml-64 xl:mr-72 flex-1 h-screen pt-16 flex flex-col relative bg-surface">
          <div className="flex-1 flex flex-col min-h-0">
            <AgentChat activeAgentId={activeAgentId} onContextUpdate={setExtractedContext} />
          </div>

          {/* Footer Label */}
          <div className="absolute bottom-6 left-0 w-full flex justify-center gap-8 pointer-events-none z-10">
            <span className="flex items-center gap-1.5 text-[10px] text-on-surface/20 font-semibold uppercase tracking-[0.15em]">
              AGENTIC AUTOMATION
            </span>
            <span className="flex items-center gap-1.5 text-[10px] text-on-surface/20 font-semibold uppercase tracking-[0.15em]">
              <span className="material-symbols-outlined text-[12px]">verified</span>
              PwC&nbsp;
            </span>
          </div>
        </main>

        {/* Right Context & Ingestion Panel */}
        <SidebarRight extractedContext={extractedContext} />
      </div>
    </div>
  );
}
