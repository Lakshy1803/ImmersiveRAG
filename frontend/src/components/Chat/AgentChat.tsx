'use client';
import React, { useState, useRef, useEffect } from 'react';
import { ImmersiveRagAPI, ChunkNode } from '@/lib/api';
import { Spinner } from '../ui/Spinner';

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  chunks?: ChunkNode[];
  cache_hit?: boolean;
}

interface AgentChatProps {
  onContextUpdate?: (chunks: ChunkNode[]) => void;
}

export function AgentChat({ onContextUpdate }: AgentChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([{
     id: 'welcome',
     role: 'agent',
     content: 'Good morning, Executive. I have synchronized the local vector space. I am ready to deep-dive into your document repositories.'
  }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const [sessionId, setSessionId] = useState('');

  useEffect(() => {
    setSessionId(`sess_${Math.random().toString(36).substr(2, 6)}`);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
       const res = await ImmersiveRagAPI.query(userMsg.content, sessionId, 'agent_demo_ui');
       
       if (res.extracted_context && res.extracted_context.length > 0) {
          onContextUpdate?.(res.extracted_context);
          const agentMsg: ChatMessage = {
             id: (Date.now() + 1).toString(),
             role: 'agent',
             content: `I have retrieved ${res.extracted_context.length} relevant context shards within your token budget. Strategic analysis complete.`,
             chunks: res.extracted_context,
             cache_hit: res.cache_hit
          };
          setMessages(prev => [...prev, agentMsg]);
       } else {
         const emptyMsg: ChatMessage = {
             id: (Date.now() + 1).toString(),
             role: 'agent',
             content: `No significant matches found in the local corporate knowledge layer.`,
             cache_hit: res.cache_hit
          };
          setMessages(prev => [...prev, emptyMsg]);
       }

    } catch (err: unknown) {
       const errMsg = err instanceof Error ? err.message : 'Connection failure in corporate network.';
       setMessages(prev => [...prev, {
         id: (Date.now() + 1).toString(),
         role: 'agent',
         content: `System Error: ${errMsg}`
       }]);
    } finally {
       setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full w-full max-w-4xl mx-auto px-6 py-10">
      {/* Message Log */}
      <div className="flex-1 space-y-8 pb-32">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex items-start gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'agent' && (
              <div className="w-10 h-10 rounded-xl bg-surface-container border border-outline-variant/30 flex-shrink-0 flex items-center justify-center shadow-md">
                <span className="material-symbols-outlined text-lg text-primary" style={{ fontVariationSettings: '"FILL" 1' }}>smart_toy</span>
              </div>
            )}
            
            <div className={`space-y-2 max-w-[85%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              {msg.cache_hit && (
                <div className="flex items-center gap-1.5 text-[9px] uppercase font-bold text-primary tracking-[0.2em] mb-1 px-1">
                   <span className="material-symbols-outlined text-[10px]">bolt</span> Cache Hit
                </div>
              )}
              
              <div className={`p-6 rounded-2xl border border-outline-variant/20 leading-relaxed shadow-sm text-base ${
                 msg.role === 'user' 
                   ? 'bg-surface-container-highest rounded-tr-none' 
                   : 'bg-surface-container-low rounded-tl-none'
              }`}
              >
                {msg.content}

                {/* Agent Action Placeholders from Sample */}
                {msg.role === 'agent' && msg.id !== 'welcome' && (
                  <div className="flex gap-2 mt-4">
                    <button className="px-5 py-2 rounded-full bg-surface-container-high text-[9px] font-bold uppercase tracking-wider text-on-surface/50 hover:text-white hover:bg-primary border border-transparent transition-all shadow-sm">
                      Generate PDF Report
                    </button>
                    <button className="px-5 py-2 rounded-full bg-surface-container-high text-[9px] font-bold uppercase tracking-wider text-on-surface/50 hover:text-white hover:bg-primary border border-transparent transition-all shadow-sm">
                      Export Data
                    </button>
                  </div>
                )}
              </div>
              
              <span className={`text-[10px] text-on-surface/30 px-1 font-mono uppercase tracking-widest ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                {msg.role === 'agent' ? 'Luminary' : 'Executive'} • {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>

            {msg.role === 'user' && (
              <div className="w-10 h-10 rounded-xl bg-surface-container-high border border-outline-variant/30 flex-shrink-0 flex items-center justify-center shadow-md">
                <span className="material-symbols-outlined text-lg text-on-surface/80" style={{ fontVariationSettings: '"FILL" 1' }}>person</span>
              </div>
            )}
          </div>
        ))}
        {isLoading && (
           <div className="flex items-start gap-4 animate-pulse">
             <div className="w-10 h-10 rounded-xl bg-surface-container border border-outline-variant/30 flex-shrink-0" />
             <div className="bg-surface-container-low py-4 px-6 rounded-2xl rounded-tl-none text-xs text-on-surface/30 w-48">
               Processing retrieval metrics...
             </div>
           </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input Section */}
      <div className="fixed bottom-0 left-64 right-72 px-6 pb-8 pt-4 bg-gradient-to-t from-background via-background/90 to-transparent z-30 transition-colors">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSend} className="bg-surface-container dark:bg-surface-container/90 backdrop-blur-xl p-1.5 rounded-full flex items-center gap-2 border border-outline-variant shadow-xl dark:shadow-2xl transition-all h-[64px]">
            <button type="button" className="w-11 h-11 flex items-center justify-center text-on-surface/50 hover:text-primary transition-all ml-2">
              <span className="material-symbols-outlined">attach_file</span>
            </button>
            <input 
              suppressHydrationWarning
              type="text" 
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={isLoading}
              placeholder="Ask Corporate Luminary anything..."
              className="flex-1 bg-transparent border-none focus:ring-0 text-on-surface placeholder:text-on-surface/40 text-sm py-4"
              autoComplete="off"
            />
            <button type="button" className="w-11 h-11 flex items-center justify-center text-on-surface/50 hover:text-primary transition-all">
              <span className="material-symbols-outlined">mic</span>
            </button>
            <button 
              type="submit" 
              disabled={!input.trim() || isLoading}
              className="h-11 px-8 bg-primary rounded-full flex items-center justify-center text-white hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-primary/20 mr-1 disabled:opacity-50 disabled:grayscale"
            >
              <span className="material-symbols-outlined text-base">send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
