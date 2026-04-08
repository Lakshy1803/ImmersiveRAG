'use client';
import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChunkNode, ImmersiveRagAPI, AgentDefinition, getApiBaseUrl } from '@/lib/api';
import { TemplateModal } from './TemplateModal';

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  chunks?: ChunkNode[];
  cache_hit?: boolean;
  streaming?: boolean;
}

interface AgentChatProps {
  activeAgentId: string;
  onContextUpdate?: (chunks: ChunkNode[]) => void;
}

export function AgentChat({ activeAgentId, onContextUpdate }: AgentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([{
    id: 'welcome',
    role: 'agent',
    content: 'Good morning, Executive. I am ready to analyze your documents. Upload files via the right panel, then ask me anything.',
  }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());
  const [mounted, setMounted] = useState(false);
  const [activeAgentDef, setActiveAgentDef] = useState<AgentDefinition | null>(null);
  const [exportingStates, setExportingStates] = useState<Record<string, boolean>>({});
  const [templateModalMsg, setTemplateModalMsg] = useState<string | null>(null);
  const [routingBanner, setRoutingBanner] = useState<{ agent: string; intent: string } | null>(null);
  const [clarification, setClarification] = useState<{ question: string; options: string[] } | null>(null);
  const [executionPlan, setExecutionPlan] = useState<{ step: number; label: string; action: string }[]>([]);
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const endRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setMounted(true);
    setSessionId(`sess_${Math.random().toString(36).substr(2, 8)}`);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset chat on agent switch and fetch agent def
  useEffect(() => {
    setMessages([{
      id: 'welcome',
      role: 'agent',
      content: 'Good morning, Executive. I am ready to analyze your documents. Upload files via the right panel, then ask me anything.',
    }]);
    // Reset orchestration state on agent switch
    setExecutionPlan([]);
    setActiveStep(null);
    setCompletedSteps(new Set());
    setRoutingBanner(null);
    setClarification(null);

    // Fetch active agent definition to get enabled_tools
    ImmersiveRagAPI.listAgents()
      .then(agents => {
        const ag = agents.find(a => a.agent_id === activeAgentId);
        if (ag) setActiveAgentDef(ag);
      })
      .catch(console.error);

  }, [activeAgentId]);

  const toggleChunks = (msgId: string) => {
    setExpandedChunks(prev => {
      const next = new Set(prev);
      next.has(msgId) ? next.delete(msgId) : next.add(msgId);
      return next;
    });
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userContent = input.trim();
    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: userContent };
    const agentMsgId = (Date.now() + 1).toString();

    setMessages(prev => [...prev, userMsg, {
      id: agentMsgId, role: 'agent', content: '', streaming: true,
    }]);
    setInput('');
    setIsLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const baseUrl = window.location.hostname === 'localhost' ? 'http://127.0.0.1:8000' : '';

      const res = await fetch(`${baseUrl}/agent/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userContent,
          agent_id: activeAgentId,
          session_id: sessionId,
        }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error('No response body');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? ''; // keep incomplete last line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event: { type: string; text?: string; chunks?: ChunkNode[]; cache_hit?: boolean; tokens_used?: number; agent?: string; intent?: string; question?: string; options?: string[]; data?: string; filename?: string; step?: number; label?: string; action?: string; steps?: { step: number; label: string; action: string }[]; content?: string };
          try { event = JSON.parse(raw); } catch { continue; }

          if (event.type === 'plan' && event.steps) {
            setExecutionPlan(event.steps);
            setCompletedSteps(new Set());
            setActiveStep(null);
          } else if (event.type === 'step_start') {
            setActiveStep(event.step ?? null);
          } else if (event.type === 'step_done') {
            setCompletedSteps(prev => new Set([...prev, event.step!]));
            setActiveStep(null);
          } else if (event.type === 'routing') {
            setRoutingBanner({ agent: event.agent || 'Orchestrator', intent: event.intent || '' });
          } else if (event.type === 'clarification') {
            setClarification({ question: event.question || '', options: event.options || [] });
          } else if (event.type === 'open_template_tool' && event.content) {
            // Open the Template Modal with the orchestrator-generated content pre-filled
            setTemplateModalMsg(event.content);
          } else if (event.type === 'pdf_ready' && event.data) {
            // Auto-download PDF
            try {
              const byteChars = atob(event.data);
              const byteNums = new Array(byteChars.length).fill(0).map((_, i) => byteChars.charCodeAt(i));
              const blob = new Blob([new Uint8Array(byteNums)], { type: 'application/pdf' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = event.filename || `report_${Date.now()}.pdf`;
              document.body.appendChild(a); a.click();
              URL.revokeObjectURL(url); a.remove();
            } catch (pdfErr) { console.error('PDF download failed:', pdfErr); }
          } else if (event.type === 'csv_ready' && event.data) {
            // Auto-download CSV
            try {
              const csvText = atob(event.data);
              const blob = new Blob([csvText], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = event.filename || `export_${Date.now()}.csv`;
              document.body.appendChild(a); a.click();
              URL.revokeObjectURL(url); a.remove();
            } catch (csvErr) { console.error('CSV download failed:', csvErr); }
          } else if (event.type === 'context') {
            setMessages(prev => prev.map(m =>
              m.id === agentMsgId
                ? { ...m, chunks: event.chunks, cache_hit: event.cache_hit }
                : m
            ));
            if (event.chunks && event.chunks.length > 0) onContextUpdate?.(event.chunks);
          } else if (event.type === 'chunk' && event.text) {
            setMessages(prev => prev.map(m =>
              m.id === agentMsgId
                ? { ...m, content: m.content + event.text, streaming: true }
                : m
            ));
          } else if (event.type === 'done') {
            setRoutingBanner(null);
            setActiveStep(null);
            // Keep executionPlan and completedSteps so the tracker remains visible with all checkmarks
            setMessages(prev => prev.map(m =>
              m.id === agentMsgId ? { ...m, streaming: false } : m
            ));
          }
        }
      }

    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return;
      const errMsg = err instanceof Error ? err.message : 'Connection failure.';
      setMessages(prev => prev.map(m =>
        m.id === agentMsgId
          ? { ...m, content: `⚠️ System Error: ${errMsg}`, streaming: false }
          : m
      ));
      // Reset plan state on error
      setExecutionPlan([]);
      setActiveStep(null);
      setCompletedSteps(new Set());
      setRoutingBanner(null);
    } finally {
      setIsLoading(false);
      abortRef.current = null;
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full w-full max-w-4xl mx-auto px-6 py-10">
      {/* Execution Plan Tracker — shown during and after master agent run */}
      {executionPlan.length > 0 && (() => {
        const allDone = executionPlan.every(s => completedSteps.has(s.step)) && activeStep === null && !isLoading;
        return (
          <div className="mx-auto w-full max-w-4xl px-6 mb-4">
            <div className={`border rounded-2xl px-5 py-4 shadow-sm transition-all ${allDone
              ? 'bg-green-500/5 border-green-500/20'
              : 'bg-surface-container border-outline-variant/20'
              }`}>
              <p className={`text-[9px] uppercase tracking-widest font-black mb-3 flex items-center gap-2 ${allDone ? 'text-green-600' : 'text-primary'
                }`}>
                <span className={`material-symbols-outlined text-sm ${allDone ? '' : 'animate-pulse'}`}>
                  {allDone ? 'verified' : 'hub'}
                </span>
                {allDone ? 'Workflow Complete' : 'Orchestrating Workflow'}
              </p>
              <div className="flex flex-col gap-2">
                {executionPlan.map(s => {
                  const isDone = completedSteps.has(s.step);
                  const isActive = activeStep === s.step;
                  const actionIcon: Record<string, string> = {
                    sub_agent: 'smart_toy', export_csv: 'table_chart', export_pdf: 'picture_as_pdf', export_template: 'description'
                  };
                  return (
                    <div key={s.step} className={`flex items-center gap-3 transition-all ${isDone ? 'opacity-100' : isActive ? 'opacity-100' : 'opacity-40'}`}>
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${isDone ? 'bg-green-500/20' : isActive ? 'bg-primary/20' : 'bg-surface-container-high'}`}>
                        {isDone ? (
                          <span className="material-symbols-outlined text-green-500 text-[12px]">check</span>
                        ) : isActive ? (
                          <span className="material-symbols-outlined text-primary text-[12px] animate-spin">progress_activity</span>
                        ) : (
                          <span className="material-symbols-outlined text-on-surface/30 text-[12px]">{actionIcon[s.action] || 'radio_button_unchecked'}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="material-symbols-outlined text-[13px] text-on-surface/50">{actionIcon[s.action] || 'circle'}</span>
                        <span className={`text-xs font-semibold truncate ${isActive ? 'text-primary' : isDone ? 'text-green-700 dark:text-green-400' : 'text-on-surface/50'}`}>{s.label}</span>
                      </div>
                      <span className={`text-[9px] uppercase tracking-widest font-bold flex-shrink-0 ${isDone ? 'text-green-600' : isActive ? 'text-primary' : 'text-on-surface/30'
                        }`}>
                        {isDone ? 'Done ✓' : isActive ? 'Running...' : 'Pending'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );
      })()}

      {/* Message Log */}
      <div className="flex-1 overflow-y-auto pr-2 space-y-8 pb-32 custom-scrollbar">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex items-start gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'agent' && (
              <div className="w-10 h-10 rounded-xl bg-surface-container border border-outline-variant/30 flex-shrink-0 flex items-center justify-center shadow-md mt-1">
                <span className="material-symbols-outlined text-lg text-primary" style={{ fontVariationSettings: '"FILL" 1' }}>smart_toy</span>
              </div>
            )}

            <div className={`space-y-2 max-w-[85%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              {msg.cache_hit && (
                <div className="flex items-center gap-1.5 text-[9px] uppercase font-bold text-primary tracking-[0.2em] mb-1 px-1">
                  <span className="material-symbols-outlined text-[10px]">bolt</span> Cache Hit
                </div>
              )}

              {/* Message Bubble */}
              <div className={`p-5 rounded-2xl border border-outline-variant/20 shadow-sm text-sm leading-relaxed ${msg.role === 'user'
                ? 'bg-surface-container-highest rounded-tr-none text-on-surface'
                : 'bg-surface-container-low rounded-tl-none text-on-surface'
                }`}>
                {msg.role === 'user' ? (
                  <p>{msg.content}</p>
                ) : (
                  <>
                    {/* Rich Markdown Rendering */}
                    <div className="prose prose-sm dark:prose-invert max-w-none
                      prose-headings:text-on-surface prose-headings:font-bold prose-headings:mt-4 prose-headings:mb-2
                      prose-h1:text-lg prose-h2:text-base prose-h3:text-sm
                      prose-p:text-on-surface/90 prose-p:leading-relaxed prose-p:mb-3
                      prose-strong:text-on-surface prose-strong:font-semibold
                      prose-em:text-on-surface/80
                      prose-ul:my-2 prose-ul:space-y-1 prose-ol:my-2 prose-ol:space-y-1
                      prose-li:text-on-surface/90 prose-li:marker:text-primary
                      prose-code:text-primary prose-code:bg-surface-container-high prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-mono
                      prose-pre:bg-surface-container-high prose-pre:border prose-pre:border-outline-variant/30 prose-pre:rounded-xl prose-pre:p-4
                      prose-blockquote:border-l-4 prose-blockquote:border-primary/40 prose-blockquote:pl-4 prose-blockquote:text-on-surface/60 prose-blockquote:italic
                      prose-table:w-full prose-th:text-left prose-th:font-bold prose-th:text-on-surface prose-th:border-b prose-th:border-outline-variant/30 prose-th:pb-2
                      prose-td:border-b prose-td:border-outline-variant/10 prose-td:py-2 prose-td:text-on-surface/80
                      prose-hr:border-outline-variant/30
                      prose-a:text-primary prose-a:underline">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>

                    {/* No cursor span here */}

                    {/* Action buttons for completed agent messages */}
                    {!msg.streaming && msg.id !== 'welcome' && activeAgentDef?.enabled_tools && activeAgentDef.enabled_tools.length > 0 && (
                      <div className="flex gap-2 mt-4 flex-wrap pt-3 border-t border-outline-variant/10">
                        {activeAgentDef.enabled_tools.includes('export_pdf') && (
                          <button
                            onClick={async () => {
                              setExportingStates(prev => ({ ...prev, [`${msg.id}-pdf`]: true }));
                              setExportingStates(prev => ({ ...prev, [`${msg.id}-pdf`]: true }));
                              try { await ImmersiveRagAPI.exportToPDF(msg.content); } catch (e) { alert("Failed to export PDF"); }
                              setExportingStates(prev => ({ ...prev, [`${msg.id}-pdf`]: false }));
                              setExportingStates(prev => ({ ...prev, [`${msg.id}-pdf`]: false }));
                            }}
                            disabled={exportingStates[`${msg.id}-pdf`]}
                            className="px-4 py-1.5 rounded-full bg-surface-container-high text-[9px] font-bold uppercase tracking-wider text-on-surface/50 hover:text-white hover:bg-primary border border-transparent transition-all shadow-sm disabled:opacity-50"
                          >
                            {exportingStates[`${msg.id}-pdf`] ? 'Exporting...' : 'Generate PDF Report'}
                          </button>
                        )}
                        {activeAgentDef.enabled_tools.includes('export_csv') && (
                          <button
                            onClick={async () => {
                              setExportingStates(prev => ({ ...prev, [`${msg.id}-csv`]: true }));
                              setExportingStates(prev => ({ ...prev, [`${msg.id}-csv`]: true }));
                              try { await ImmersiveRagAPI.exportToCSV(msg.content); } catch (e) { alert("Failed to export CSV"); }
                              setExportingStates(prev => ({ ...prev, [`${msg.id}-csv`]: false }));
                              setExportingStates(prev => ({ ...prev, [`${msg.id}-csv`]: false }));
                            }}
                            disabled={exportingStates[`${msg.id}-csv`]}
                            className="px-4 py-1.5 rounded-full bg-surface-container-high text-[9px] font-bold uppercase tracking-wider text-on-surface/50 hover:text-white hover:bg-primary border border-transparent transition-all shadow-sm disabled:opacity-50"
                          >
                            {exportingStates[`${msg.id}-csv`] ? 'Exporting...' : 'Export Data (CSV)'}
                          </button>
                        )}
                        {activeAgentDef.enabled_tools.includes('generate_template') && (
                          <button
                            onClick={() => setTemplateModalMsg(msg.content)}
                            className="px-4 py-1.5 rounded-full bg-surface-container-high text-[9px] font-bold uppercase tracking-wider text-on-surface/50 hover:text-white hover:bg-primary border border-transparent transition-all shadow-sm"
                          >
                            Generate Document
                          </button>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Collapsible Source Chunks */}
              {msg.chunks && msg.chunks.length > 0 && (
                <div className="w-full">
                  <button
                    onClick={() => toggleChunks(msg.id)}
                    className="flex items-center gap-1.5 text-[10px] text-on-surface/40 hover:text-primary transition-colors px-1 font-semibold"
                  >
                    <span className="material-symbols-outlined text-[12px]">
                      {expandedChunks.has(msg.id) ? 'expand_less' : 'expand_more'}
                    </span>
                    Sources ({msg.chunks.length})
                  </button>

                  {expandedChunks.has(msg.id) && (
                    <div className="mt-2 space-y-2">
                      {msg.chunks.map((chunk, idx) => (
                        <div key={idx} className="p-3 bg-surface-container rounded-xl border border-outline-variant/20 text-[11px]">
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-primary font-bold px-2 py-0.5 bg-primary/10 rounded-full text-[9px]">
                              {(chunk.score * 100).toFixed(0)}% match
                            </span>
                            <span className="text-on-surface/30 font-mono text-[9px]">
                              chunk:{chunk.chunk_id?.substring(0, 10)}
                            </span>
                          </div>
                          {(chunk.metadata?.file_name || chunk.metadata?.page_label) && (
                            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                              {chunk.metadata?.file_name && (
                                <span className="flex items-center gap-1 text-[9px] text-on-surface/50 bg-surface-container-high px-2 py-0.5 rounded-full font-mono truncate max-w-[160px]">
                                  <span className="material-symbols-outlined text-[10px]">description</span>
                                  {chunk.metadata.file_name}
                                </span>
                              )}
                              {chunk.metadata?.page_label && (
                                <span className="text-[9px] text-on-surface/40 bg-surface-container-high px-2 py-0.5 rounded-full">
                                  p.{chunk.metadata.page_label}
                                </span>
                              )}
                            </div>
                          )}
                          {(chunk.metadata?.file_name || chunk.metadata?.page_label) && (
                            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                              {chunk.metadata?.file_name && (
                                <span className="flex items-center gap-1 text-[9px] text-on-surface/50 bg-surface-container-high px-2 py-0.5 rounded-full font-mono truncate max-w-[160px]">
                                  <span className="material-symbols-outlined text-[10px]">description</span>
                                  {chunk.metadata.file_name}
                                </span>
                              )}
                              {chunk.metadata?.page_label && (
                                <span className="text-[9px] text-on-surface/40 bg-surface-container-high px-2 py-0.5 rounded-full">
                                  p.{chunk.metadata.page_label}
                                </span>
                              )}
                            </div>
                          )}
                          <p className="text-on-surface/60 leading-relaxed italic">
                            "{chunk.text.length > 200 ? chunk.text.substring(0, 200) + '…' : chunk.text}"
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <span className={`text-[10px] text-on-surface/30 px-1 font-mono uppercase tracking-widest ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                {msg.role === 'agent' ? 'Luminary' : 'Executive'} • {mounted ? new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'}
              </span>
            </div>

            {msg.role === 'user' && (
              <div className="w-10 h-10 rounded-xl bg-surface-container-high border border-outline-variant/30 flex-shrink-0 flex items-center justify-center shadow-md mt-1">
                <span className="material-symbols-outlined text-lg text-on-surface/80" style={{ fontVariationSettings: '"FILL" 1' }}>person</span>
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {templateModalMsg !== null && (
        <TemplateModal
          isOpen={true}
          onClose={() => setTemplateModalMsg(null)}
          chatContext={templateModalMsg}
        />
      )}

      {/* Input Section */}
      <div className="fixed bottom-0 left-64 right-72 px-6 pb-8 pt-4 bg-gradient-to-t from-background via-background/90 to-transparent z-30 transition-colors">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSend} className="bg-surface-container dark:bg-surface-container/90 backdrop-blur-xl p-1.5 rounded-full flex items-center gap-2 border border-outline-variant shadow-xl dark:shadow-2xl transition-all h-[64px]">
            <button suppressHydrationWarning type="button" className="w-11 h-11 flex items-center justify-center text-on-surface/50 hover:text-primary transition-all ml-2">
              <span className="material-symbols-outlined">attach_file</span>
            </button>
            <input
              suppressHydrationWarning
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={isLoading}
              placeholder="Ask your agent anything..."
              className="flex-1 bg-transparent border-none focus:ring-0 text-on-surface placeholder:text-on-surface/40 text-sm py-4"
              autoComplete="off"
            />
            {isLoading ? (
              <button
                type="button"
                suppressHydrationWarning
                onClick={() => { abortRef.current?.abort(); setIsLoading(false); }}
                className="h-11 px-6 bg-red-500/80 rounded-full flex items-center justify-center text-white hover:bg-red-600 active:scale-95 transition-all shadow-lg mr-1 text-xs font-bold gap-1.5"
              >
                <span className="material-symbols-outlined text-sm">stop</span>
                Stop
              </button>
            ) : (
              <button
                type="submit"
                suppressHydrationWarning
                disabled={!input.trim()}
                className="h-11 px-8 bg-primary rounded-full flex items-center justify-center text-white hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-primary/20 mr-1 disabled:opacity-50 disabled:grayscale"
              >
                <span className="material-symbols-outlined text-base">send</span>
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
