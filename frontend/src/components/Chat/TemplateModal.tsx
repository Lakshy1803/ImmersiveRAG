'use client';
import React, { useState } from 'react';
import { ImmersiveRagAPI } from '@/lib/api';

interface TemplateModalProps {
    isOpen: boolean;
    onClose: () => void;
    chatContext: string;
}

const DEFAULT_TEMPLATES: Record<string, string> = {
    'Executive Summary': `# Executive Summary\n\n## Overview\n\n## Key Findings\n\n## Recommendations\n\n## References`,
    'Technical Report': `# Technical Report\n\n## Introduction\n\n## Methodology\n\n## Results\n\n## Analysis\n\n## Conclusion\n\n## References`,
    'Meeting Notes': `# Meeting Notes\n\n## Agenda\n\n## Discussion Points\n\n## Action Items\n\n## Next Steps\n\n## References`,
    'Custom': ''
};

export function TemplateModal({ isOpen, onClose, chatContext }: TemplateModalProps) {
    const [selectedTemplate, setSelectedTemplate] = useState<string>('Executive Summary');
    const [customTemplate, setCustomTemplate] = useState<string>('');
    const [instructions, setInstructions] = useState<string>('');
    const [isGenerating, setIsGenerating] = useState(false);

    if (!isOpen) return null;

    const handleGenerate = async () => {
        setIsGenerating(true);
        try {
            const templateSkeleton = selectedTemplate === 'Custom' ? customTemplate : DEFAULT_TEMPLATES[selectedTemplate];

            const filledContent = `${templateSkeleton}\n\n---\n\n${chatContext}\n\n${instructions}`;

            await ImmersiveRagAPI.generateTemplatePDF(templateSkeleton, filledContent);
            onClose();
        } catch (e) {
            alert('Failed to generate template PDF');
            console.error(e);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div
                className="bg-surface-container rounded-3xl w-full max-w-2xl border border-outline-variant/30 shadow-2xl overflow-hidden flex flex-col"
            >
                <div className="px-6 py-4 border-b border-outline-variant/20 flex items-center justify-between bg-surface-container-low">
                    <h2 className="text-lg font-bold text-on-surface flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">view_quilt</span>
                        Generate Document Template
                    </h2>
                    <button
                        onClick={onClose}
                        className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-on-surface/10 text-on-surface/60 transition-colors"
                    >
                        <span className="material-symbols-outlined text-lg">close</span>
                    </button>
                </div>

                <div className="p-6 overflow-y-auto space-y-6 max-h-[70vh]">
                    {/* Template Selection */}
                    <div className="space-y-3">
                        <label className="text-sm font-bold tracking-wide text-on-surface/60 uppercase">Select Template</label>
                        <div className="grid grid-cols-2 gap-3">
                            {Object.keys(DEFAULT_TEMPLATES).map((key) => (
                                <button
                                    key={key}
                                    onClick={() => setSelectedTemplate(key)}
                                    className={`p-3 rounded-xl border text-sm text-left transition-all ${selectedTemplate === key
                                        ? 'bg-primary/10 border-primary text-primary shadow-sm'
                                        : 'bg-surface-container-highest border-outline-variant/20 text-on-surface hover:border-outline-variant'
                                        }`}
                                >
                                    <div className="font-semibold">{key}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Custom Template Editor */}
                    {selectedTemplate === 'Custom' && (
                        <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                            <label className="text-sm font-bold tracking-wide text-on-surface/60 uppercase">Custom Markdown Skeleton</label>
                            <textarea
                                value={customTemplate}
                                onChange={(e) => setCustomTemplate(e.target.value)}
                                placeholder="# My Section\n\n## Subpoint..."
                                className="w-full h-32 bg-surface-container-highest border border-outline-variant/30 rounded-xl p-3 text-sm text-on-surface font-mono placeholder:text-on-surface/30 focus:outline-none focus:border-primary/50"
                            />
                        </div>
                    )}

                    {/* Instructions Input */}
                    <div className="space-y-2">
                        <label className="text-sm font-bold tracking-wide text-on-surface/60 uppercase">Filling Instructions (Optional)</label>
                        <input
                            type="text"
                            value={instructions}
                            onChange={(e) => setInstructions(e.target.value)}
                            placeholder="E.g., Focus on financial risks and legal action items..."
                            className="w-full bg-surface-container-highest border border-outline-variant/30 rounded-xl px-4 py-3 text-sm text-on-surface placeholder:text-on-surface/40 focus:outline-none focus:border-primary/50"
                        />
                    </div>
                </div>

                <div className="px-6 py-4 border-t border-outline-variant/20 bg-surface-container-low flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-5 py-2.5 rounded-full text-sm font-semibold text-on-surface/70 hover:bg-on-surface/10 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleGenerate}
                        disabled={isGenerating || (selectedTemplate === 'Custom' && !customTemplate.trim())}
                        className="px-6 py-2.5 rounded-full text-sm font-bold bg-primary text-white hover:brightness-110 disabled:opacity-50 transition-all flex items-center gap-2 shadow-md shadow-primary/20"
                    >
                        {isGenerating ? (
                            <>
                                <span className="material-symbols-outlined animate-spin text-sm">progress_activity</span>
                                Generating...
                            </>
                        ) : (
                            <>
                                <span className="material-symbols-outlined text-sm">magic_button</span>
                                Generate PDF
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
