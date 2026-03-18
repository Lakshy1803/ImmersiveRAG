'use client';
import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Database, Zap, BookOpen } from 'lucide-react';
import { ImmersiveRagAPI, ChunkNode } from '@/lib/api';
import { Spinner } from '../ui/Spinner';

interface ChatMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  chunks?: ChunkNode[];
  cache_hit?: boolean;
}

export function AgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([{
     id: 'welcome',
     role: 'agent',
     content: 'I am the Local LangGraph Agent sandbox. Query the Qdrant semantic space directly!'
  }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  // Generate a stable sliding window ID for testing cache hits
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
          const agentMsg: ChatMessage = {
             id: (Date.now() + 1).toString(),
             role: 'agent',
             content: `Retrieved ${res.extracted_context.length} relevant context shards within budget constraints (${res.total_tokens_used} tokens).`,
             chunks: res.extracted_context,
             cache_hit: res.cache_hit
          };
          setMessages(prev => [...prev, agentMsg]);
       } else {
         const emptyMsg: ChatMessage = {
             id: (Date.now() + 1).toString(),
             role: 'agent',
             content: `No significant matches found in the local Qdrant instance.`,
             cache_hit: res.cache_hit
          };
          setMessages(prev => [...prev, emptyMsg]);
       }

    } catch (err: unknown) {
       const errMsg = err instanceof Error
         ? err.message
         : typeof err === 'string'
           ? err
           : 'Could not connect to backend. Is the server running on port 8000?';
       setMessages(prev => [...prev, {
         id: (Date.now() + 1).toString(),
         role: 'agent',
         content: `Error: ${errMsg}`
       }]);
    } finally {
       setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[700px] max-h-[90vh] bg-slate-900 border border-slate-800 shadow-2xl rounded-xl overflow-hidden w-full max-w-3xl">
      {/* Header */}
      <div className="bg-slate-800/50 p-4 border-b border-slate-800 flex items-center justify-between">
         <div className="flex items-center gap-3">
             <div className="p-2 bg-indigo-500/20 rounded-lg">
                <Bot className="w-5 h-5 text-indigo-400" />
             </div>
             <div>
                <h2 className="font-semibold text-slate-100">Context Interrogation Sandbox</h2>
                <p className="text-xs text-slate-400 flex items-center gap-1">
                   <Database className="w-3 h-3" /> Session ID: {sessionId || 'Initializing...'}
                </p>
             </div>
         </div>
      </div>

      {/* Message Log */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'agent' && (
              <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex flex-shrink-0 flex-col items-center justify-center mt-1">
                 <Bot className="w-4 h-4 text-indigo-400" />
              </div>
            )}
            
            <div className={`max-w-[85%] flex flex-col gap-2`}>
              {msg.cache_hit && (
                <div className="flex items-center gap-1 text-[10px] uppercase font-bold text-amber-400 tracking-wider mb-1 ml-1 self-start">
                   <Zap className="w-3 h-3" /> Local DB Hit (Cache Bypass)
                </div>
              )}
              
              <div className={`p-4 rounded-xl ${
                 msg.role === 'user' 
                   ? 'bg-indigo-600/80 text-white rounded-tr-sm shadow-[0_0_20px_rgba(79,70,229,0.15)]' 
                   : 'bg-slate-800 text-slate-200 rounded-tl-sm shadow-inner overflow-hidden'
              } text-sm leading-relaxed`}
              >
                {msg.content}
              </div>
              
              {/* Context Chunks Map */}
              {msg.chunks && msg.chunks.length > 0 && (
                <div className="flex flex-col gap-2 mt-2">
                   {msg.chunks.map((chunk, idx) => (
                      <div key={idx} className="bg-slate-950 border border-slate-700 p-3 rounded-lg hover:border-indigo-500/50 transition-colors">
                         <div className="flex items-center justify-between mb-2">
                             <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                                <BookOpen className="w-3 h-3" />
                                UUID: {chunk.chunk_id?.substring(0, 8) ?? '?'}...
                             </div>
                             <span className="text-[10px] flex items-center justify-center bg-indigo-500/10 text-indigo-300 font-mono py-1 px-2 rounded">
                                Score: {chunk.score.toFixed(3)}
                             </span>
                         </div>
                         <p className="text-xs text-slate-300 leading-snug break-words">
                            {chunk.text.length > 300 ? chunk.text.substring(0, 300) + '...' : chunk.text}
                         </p>
                      </div>
                   ))}
                </div>
              )}
            </div>

            {msg.role === 'user' && (
               <div className="w-8 h-8 rounded-full bg-purple-500 flex flex-shrink-0 flex-col items-center justify-center -mr-1 mt-1 shadow-lg shadow-purple-500/20">
                 <User className="w-4 h-4 text-white" />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
           <div className="flex gap-4 p-4 items-center">
             <Bot className="w-5 h-5 text-indigo-400/50 animate-pulse" />
             <div className="bg-slate-800 py-3 px-4 rounded-xl text-xs text-slate-400 animate-pulse w-48 shadow-inner">
               Querying Qdrant...
             </div>
           </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-4 bg-slate-800/80 border-t border-slate-800">
        <div className="flex relative items-center justify-center rounded-xl bg-slate-950 overflow-hidden border border-slate-700 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 transition-all">
           <input 
             suppressHydrationWarning
             type="text" 
             value={input}
             onChange={e => setInput(e.target.value)}
             disabled={isLoading}
             placeholder="Search knowledge layer... (e.g. What is the standard configuration?)"
             className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 p-4 focus:outline-none disabled:opacity-50"
             autoComplete="off"
           />
           <button 
             type="submit" 
             disabled={!input.trim() || isLoading}
             className="absolute right-2 p-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 disabled:bg-slate-700 disabled:text-slate-500 text-white transition-colors"
           >
             <Send className="w-4 h-4" />
           </button>
        </div>
      </form>
    </div>
  );
}
