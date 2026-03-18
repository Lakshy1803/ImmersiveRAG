"use client";

import React from "react";

const SidebarLeft: React.FC = () => {
  return (
    <aside className="h-screen w-64 fixed left-0 top-0 pt-16 bg-surface-container flex flex-col border-r border-outline-variant/30 z-40 hidden lg:flex">
      <div className="p-6">
        {/* Base Agent Selector */}
        <button className="w-full flex items-center justify-between gap-3 mb-8 p-3 bg-surface-container-low rounded-full border border-outline-variant/30 hover:border-primary/50 transition-colors shadow-sm text-left group">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary/20 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-primary text-sm">description</span>
            </div>
            <div>
              <h2 className="text-on-surface font-bold text-[13px] leading-tight group-hover:text-primary transition-colors">Document Analyser</h2>
              <p className="text-[9px] text-on-surface/50 uppercase tracking-widest font-medium">Base Agent</p>
            </div>
          </div>
          <span className="material-symbols-outlined text-on-surface/30 text-lg mr-2">unfold_more</span>
        </button>

        <button className="w-full bg-primary text-white py-3 rounded-full font-bold text-sm mb-8 flex items-center justify-center gap-2 hover:brightness-110 transition-all active:scale-95 shadow-md shadow-primary/10">
          <span className="material-symbols-outlined text-sm">add</span>
          New Chat
        </button>

        <nav className="space-y-1">
          <a className="flex items-center gap-3 px-6 py-3 text-primary font-bold bg-surface-container-high rounded-full text-sm shadow-sm" href="#">
            <span className="material-symbols-outlined">history</span>
            Chat History
          </a>
          <a className="flex items-center justify-between px-6 py-3 text-on-surface/70 hover:text-primary hover:bg-surface-container-low transition-all text-sm rounded-full" href="#">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined">settings_input_component</span>
              Model Settings
            </div>
            <span className="material-symbols-outlined text-sm opacity-50">expand_more</span>
          </a>
          <button className="w-full flex items-center gap-3 px-6 py-3 text-on-surface/70 hover:text-white hover:bg-primary transition-all text-sm rounded-full group">
            <span className="material-symbols-outlined group-hover:text-white">database</span>
            Knowledge Base
          </button>
        </nav>
      </div>

      <div className="mt-auto p-6 space-y-1">
        <a className="flex items-center gap-3 px-6 py-3 text-on-surface/70 hover:text-primary hover:bg-surface-container-low transition-all text-sm rounded-full" href="#">
          <span className="material-symbols-outlined">help</span>
          Help Center
        </a>
        <a className="flex items-center gap-3 px-6 py-3 text-on-surface/70 hover:text-primary hover:bg-surface-container-low transition-all text-sm rounded-full" href="#">
          <span className="material-symbols-outlined">account_circle</span>
          Account
        </a>
      </div>
    </aside>
  );
};

export default SidebarLeft;
