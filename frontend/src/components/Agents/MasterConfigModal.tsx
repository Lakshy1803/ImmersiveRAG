'use client';
import React, { useState, useEffect } from 'react';
import { ImmersiveRagAPI, AgentDefinition } from '@/lib/api';

interface MasterConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSaved: (agent: AgentDefinition) => void;
    allAgents: AgentDefinition[];           // full registry for sub-agent display
    editAgent?: AgentDefinition | null;
}

const MasterConfigModal: React.FC<MasterConfigModalProps> = ({
    isOpen, onClose, onSaved, allAgents, editAgent
}) => {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [selectedSubAgentIds, setSelectedSubAgentIds] = useState<string[]>([]);
    const [isSaving, setIsSaving] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);
    const [error, setError] = useState('');

    // Selectable agents: non-system, non-master custom agents only
    const selectableAgents = allAgents.filter(a => !a.is_system && a.kind === 'standard');

    useEffect(() => {
        if (!isOpen) return;
        if (editAgent) {
            setName(editAgent.name);
            setDescription(editAgent.description);
            setSelectedSubAgentIds(editAgent.enabled_tools || []);
        } else {
            setName(''); setDescription(''); setSelectedSubAgentIds([]);
        }
        setError('');
    }, [isOpen, editAgent]);

    const toggleAgent = (id: string) => {
        setSelectedSubAgentIds(prev =>
            prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]
        );
    };

    const save = async (publish = false) => {
        if (!name.trim()) { setError('Workflow name is required.'); return; }
        if (selectedSubAgentIds.length === 0) { setError('Select at least one agent.'); return; }

        publish ? setIsPublishing(true) : setIsSaving(true);
        setError('');

        try {
            let saved = await ImmersiveRagAPI.configureMasterAgent({
                agent_id: editAgent?.agent_id,
                name: name.trim(),
                description: description.trim(),
                sub_agent_ids: selectedSubAgentIds,
                is_published: publish,
            });

            // Explicit publish call if not creating with is_published=true
            if (publish && !saved.is_published) {
                saved = await ImmersiveRagAPI.publishMasterAgent(saved.agent_id);
            }

            onSaved(saved);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Failed to save workflow.');
        } finally {
            setIsSaving(false);
            setIsPublishing(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

            {/* Modal */}
            <div className="relative w-full max-w-2xl mx-4 bg-surface-container rounded-3xl border border-outline-variant/30 shadow-2xl overflow-hidden">

                {/* Header */}
                <div className="px-8 pt-6 pb-4 border-b border-outline-variant/20 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-2xl bg-primary/10 flex items-center justify-center">
                            <span className="material-symbols-outlined text-primary text-xl">hub</span>
                        </div>
                        <div>
                            <h2 className="text-on-surface font-bold text-lg">
                                {editAgent ? 'Edit Workflow' : 'Create Agent Workflow'}
                            </h2>
                            <p className="text-on-surface/50 text-[11px] mt-0.5">
                                Combine your agents into a reusable team workflow
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="w-9 h-9 flex items-center justify-center rounded-full text-on-surface/40 hover:bg-surface-container-high transition-all">
                        <span className="material-symbols-outlined text-xl">close</span>
                    </button>
                </div>

                {/* Body */}
                <div className="p-8 space-y-6 max-h-[65vh] overflow-y-auto custom-scrollbar">

                    {/* Name */}
                    <div>
                        <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold block mb-1.5">Workflow Name</label>
                        <input
                            type="text"
                            value={name}
                            onChange={e => setName(e.target.value)}
                            placeholder="e.g. Contract Review Pipeline"
                            className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-2.5 text-sm text-on-surface placeholder:text-on-surface/30 focus:ring-1 focus:ring-primary outline-none"
                        />
                    </div>

                    {/* Description */}
                    <div>
                        <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold block mb-1.5">Description</label>
                        <input
                            type="text"
                            value={description}
                            onChange={e => setDescription(e.target.value)}
                            placeholder="What does this workflow do?"
                            className="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-4 py-2.5 text-sm text-on-surface placeholder:text-on-surface/30 focus:ring-1 focus:ring-primary outline-none"
                        />
                    </div>

                    {/* Agent Army Selection */}
                    <div>
                        <label className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold block mb-3">
                            Select Agents ({selectedSubAgentIds.length} selected)
                        </label>

                        {selectableAgents.length === 0 ? (
                            <div className="text-center py-10 text-on-surface/40 border-2 border-dashed border-outline-variant/30 rounded-2xl">
                                <span className="material-symbols-outlined text-3xl mb-2 block">person_add</span>
                                <p className="text-sm">No custom agents yet.</p>
                                <p className="text-xs mt-1">Create agents first using the <span className="text-primary">Configure Agent</span> option.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-2 gap-3">
                                {selectableAgents.map(agent => {
                                    const selected = selectedSubAgentIds.includes(agent.agent_id);
                                    return (
                                        <button
                                            key={agent.agent_id}
                                            onClick={() => toggleAgent(agent.agent_id)}
                                            className={`p-4 rounded-2xl border-2 text-left transition-all ${selected
                                                    ? 'border-primary bg-primary/10 shadow-sm shadow-primary/10'
                                                    : 'border-outline-variant/30 bg-surface-container-low hover:border-outline-variant'
                                                }`}
                                        >
                                            <div className="flex items-center gap-3 mb-2">
                                                <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-sm ${selected ? 'bg-primary text-white' : 'bg-surface-container-high text-on-surface/60'}`}>
                                                    <span className="material-symbols-outlined text-base">{agent.icon || 'smart_toy'}</span>
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className={`text-sm font-semibold truncate ${selected ? 'text-primary' : 'text-on-surface'}`}>{agent.name}</p>
                                                </div>
                                                {selected && (
                                                    <span className="material-symbols-outlined text-primary text-base shrink-0">check_circle</span>
                                                )}
                                            </div>
                                            <p className="text-[10px] text-on-surface/50 line-clamp-2 leading-relaxed">
                                                {agent.description || 'No description'}
                                            </p>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Selected Agent Order Preview */}
                    {selectedSubAgentIds.length > 0 && (
                        <div className="bg-surface-container-low rounded-2xl p-4 border border-outline-variant/20">
                            <p className="text-[10px] uppercase tracking-widest text-on-surface/50 font-bold mb-3">Agent Army</p>
                            <div className="flex flex-wrap gap-2">
                                {selectedSubAgentIds.map((id, idx) => {
                                    const agent = allAgents.find(a => a.agent_id === id);
                                    if (!agent) return null;
                                    return (
                                        <div key={id} className="flex items-center gap-2 bg-primary/10 text-primary rounded-full px-3 py-1.5 text-xs font-semibold">
                                            <span className="text-primary/60 text-[10px] font-mono">{idx + 1}</span>
                                            <span className="material-symbols-outlined text-sm">{agent.icon || 'smart_toy'}</span>
                                            {agent.name}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Error */}
                    {error && (
                        <div className="flex items-center gap-2 text-red-500 text-[10px] font-bold uppercase tracking-wider bg-red-500/5 px-4 py-2 rounded-lg border border-red-500/20">
                            <span className="material-symbols-outlined text-sm">error</span>
                            {error}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-8 pb-8 pt-4 border-t border-outline-variant/10">
                    <button onClick={onClose} className="px-6 py-2 rounded-full text-xs font-bold text-on-surface/50 hover:text-on-surface hover:bg-surface-container-high transition-all">
                        Cancel
                    </button>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => save(false)}
                            disabled={isSaving || isPublishing}
                            className="px-6 py-2.5 border border-outline-variant/50 rounded-full text-xs font-bold text-on-surface/70 hover:bg-surface-container-high transition-all disabled:opacity-50 flex items-center gap-2"
                        >
                            {isSaving && <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>}
                            {isSaving ? 'Saving...' : 'Save Draft'}
                        </button>
                        <button
                            onClick={() => save(true)}
                            disabled={isSaving || isPublishing}
                            className="px-8 py-2.5 bg-primary text-white rounded-full text-xs font-black uppercase tracking-widest hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-primary/20 disabled:opacity-50 disabled:grayscale flex items-center gap-2"
                        >
                            {isPublishing && <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>}
                            <span className="material-symbols-outlined text-sm">publish</span>
                            {isPublishing ? 'Publishing...' : 'Publish Workflow'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MasterConfigModal;
