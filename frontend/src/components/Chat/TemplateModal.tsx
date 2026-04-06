'use client';
import React, { useState, useRef } from 'react';
import { ImmersiveRagAPI } from '@/lib/api';

interface StyleConfig {
    primary_color: string;
    secondary_color: string;
    font_family: string;
    markdown_skeleton?: string;
    [key: string]: string | undefined; // Allow index access for Record<string, string>
}

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

    // PDF Style extraction state
    const [isExtracting, setIsExtracting] = useState(false);
    const [extractedStyle, setExtractedStyle] = useState<StyleConfig | null>(null);
    const [extractError, setExtractError] = useState<string | null>(null);
    const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    if (!isOpen) return null;

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsExtracting(true);
        setExtractedStyle(null);
        setExtractError(null);
        setUploadedFileName(file.name);

        try {
            const style = await ImmersiveRagAPI.extractTemplateStyle(file);
            setExtractedStyle(style);

            // Auto-fill the custom textarea skeleton if in Custom mode
            if (selectedTemplate === 'Custom' && style.markdown_skeleton) {
                setCustomTemplate(style.markdown_skeleton);
            }
        } catch (err) {
            setExtractError('Could not extract style from PDF. Using default brand colors.');
            console.error(err);
        } finally {
            setIsExtracting(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleGenerate = async () => {
        setIsGenerating(true);
        try {
            const templateSkeleton = selectedTemplate === 'Custom' ? customTemplate : DEFAULT_TEMPLATES[selectedTemplate];
            const filledContent = `${templateSkeleton}\n\n---\n\n${chatContext}\n\n${instructions}`;
            await ImmersiveRagAPI.generateTemplatePDF(
                templateSkeleton,
                filledContent,
                extractedStyle ? {
                    primary_color: extractedStyle.primary_color,
                    secondary_color: extractedStyle.secondary_color,
                    font_family: extractedStyle.font_family,
                } : undefined
            );
            onClose();
        } catch (e) {
            alert('Failed to generate template PDF. Please try again.');
            console.error(e);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-surface-container rounded-3xl w-full max-w-2xl border border-outline-variant/30 shadow-2xl overflow-hidden flex flex-col">

                {/* Header */}
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

                <div className="p-6 overflow-y-auto space-y-6 max-h-[70vh] custom-scrollbar">

                    {/* Template Selection */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-bold tracking-widest text-on-surface/50 uppercase block">Select Template</label>
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
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold tracking-widest text-on-surface/50 uppercase block">
                                Custom Markdown Skeleton
                            </label>
                            <textarea
                                value={customTemplate}
                                onChange={(e) => setCustomTemplate(e.target.value)}
                                placeholder="# My Section&#10;&#10;## Subpoint..."
                                className="w-full h-32 bg-surface-container-highest border border-outline-variant/30 rounded-xl p-3 text-sm text-on-surface font-mono placeholder:text-on-surface/30 focus:outline-none focus:border-primary/50"
                            />
                        </div>
                    )}

                    {/* PDF Style Upload */}
                    <div className="space-y-3">
                        <label className="text-[10px] font-bold tracking-widest text-on-surface/50 uppercase block">
                            Match Style from PDF <span className="normal-case font-normal ml-1 text-on-surface/30">(optional)</span>
                        </label>

                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className={`relative flex items-center gap-3 p-4 rounded-xl border-2 border-dashed cursor-pointer transition-all
                ${isExtracting ? 'border-primary/40 bg-primary/5' : 'border-outline-variant/40 hover:border-primary/50 hover:bg-primary/5'}`}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf"
                                onChange={handleFileUpload}
                                className="hidden"
                            />
                            {isExtracting ? (
                                <>
                                    <span className="material-symbols-outlined text-primary animate-spin">progress_activity</span>
                                    <div>
                                        <p className="text-sm font-semibold text-on-surface">Extracting style...</p>
                                        <p className="text-xs text-on-surface/40">{uploadedFileName}</p>
                                    </div>
                                </>
                            ) : extractedStyle ? (
                                <>
                                    <span className="material-symbols-outlined text-green-500">check_circle</span>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-on-surface">Style matched from <span className="text-primary truncate">{uploadedFileName}</span></p>
                                        <p className="text-xs text-on-surface/40">Click to use a different PDF</p>
                                    </div>
                                    {/* Color swatches */}
                                    <div className="flex items-center gap-2 shrink-0">
                                        <div className="flex flex-col items-center gap-1">
                                            <div
                                                className="w-6 h-6 rounded-full border-2 border-white/20 shadow"
                                                style={{ backgroundColor: extractedStyle.primary_color }}
                                                title={`Primary: ${extractedStyle.primary_color}`}
                                            />
                                            <span className="text-[8px] text-on-surface/40 font-mono">{extractedStyle.primary_color}</span>
                                        </div>
                                        <div className="flex flex-col items-center gap-1">
                                            <div
                                                className="w-6 h-6 rounded-full border-2 border-white/20 shadow"
                                                style={{ backgroundColor: extractedStyle.secondary_color }}
                                                title={`Secondary: ${extractedStyle.secondary_color}`}
                                            />
                                            <span className="text-[8px] text-on-surface/40 font-mono">{extractedStyle.secondary_color}</span>
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <span className="material-symbols-outlined text-on-surface/40">upload_file</span>
                                    <div>
                                        <p className="text-sm font-semibold text-on-surface/70">Upload a sample PDF</p>
                                        <p className="text-xs text-on-surface/40">
                                            {selectedTemplate === 'Custom'
                                                ? "We'll extract its colors, fonts, and heading structure"
                                                : "We'll extract its colors and fonts"}
                                        </p>
                                    </div>
                                </>
                            )}
                        </div>

                        {extractError && (
                            <p className="text-xs text-orange-400 flex items-center gap-1">
                                <span className="material-symbols-outlined text-sm">warning</span>
                                {extractError}
                            </p>
                        )}

                        {extractedStyle && (
                            <button
                                onClick={() => { setExtractedStyle(null); setUploadedFileName(null); setExtractError(null); }}
                                className="text-xs text-on-surface/40 hover:text-on-surface/70 transition-colors flex items-center gap-1"
                            >
                                <span className="material-symbols-outlined text-sm">close</span>
                                Remove extracted style (revert to brand defaults)
                            </button>
                        )}
                    </div>

                    {/* Instructions Input */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold tracking-widest text-on-surface/50 uppercase block">
                            Filling Instructions <span className="normal-case font-normal ml-1 text-on-surface/30">(optional)</span>
                        </label>
                        <input
                            type="text"
                            value={instructions}
                            onChange={(e) => setInstructions(e.target.value)}
                            placeholder="E.g., Focus on financial risks and legal action items..."
                            className="w-full bg-surface-container-highest border border-outline-variant/30 rounded-xl px-4 py-3 text-sm text-on-surface placeholder:text-on-surface/40 focus:outline-none focus:border-primary/50"
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-outline-variant/20 bg-surface-container-low flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-5 py-2.5 rounded-full text-sm font-semibold text-on-surface/70 hover:bg-on-surface/10 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleGenerate}
                        disabled={isGenerating || isExtracting || (selectedTemplate === 'Custom' && !customTemplate.trim())}
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
