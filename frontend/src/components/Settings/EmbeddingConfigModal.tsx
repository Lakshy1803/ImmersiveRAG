'use client';
import React, { useState, useEffect } from 'react';
import { X, Eye, EyeOff, Zap, CheckCircle, AlertCircle, Loader2, Settings2 } from 'lucide-react';
import { ImmersiveRagAPI } from '@/lib/api';

interface EmbeddingConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const STORAGE_KEY = 'immersive_rag_embedding_config';

const PRESETS = [
    { label: 'OpenAI small', baseUrl: 'https://api.openai.com/v1', model: 'text-embedding-3-small' },
    { label: 'OpenAI large', baseUrl: 'https://api.openai.com/v1', model: 'text-embedding-3-large' },
    { label: 'AWS Bedrock (us-west-2)', baseUrl: 'https://bedrock-mantle.us-west-2.api.aws/v1', model: 'amazon.titan-embed-text-v2:0' },
    { label: 'AWS Bedrock (ap-southeast-2)', baseUrl: 'https://bedrock-mantle.ap-southeast-2.api.aws/v1', model: 'amazon.titan-embed-text-v2:0' },
];

export function EmbeddingConfigModal({ isOpen, onClose }: EmbeddingConfigModalProps) {
    const [apiKey, setApiKey] = useState('');
    const [baseUrl, setBaseUrl] = useState('https://api.openai.com/v1');
    const [model, setModel] = useState('text-embedding-3-small');
    const [showKey, setShowKey] = useState(false);

    const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
    const [testMessage, setTestMessage] = useState('');
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

    // Load from localStorage on open
    useEffect(() => {
        if (!isOpen) return;
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                if (parsed.apiKey) setApiKey(parsed.apiKey);
                if (parsed.baseUrl) setBaseUrl(parsed.baseUrl);
                if (parsed.model) setModel(parsed.model);
            }
        } catch {
            // ignore
        }
        setTestStatus('idle');
        setTestMessage('');
        setSaveStatus('idle');
    }, [isOpen]);

    // Reset test status when any input changes
    useEffect(() => {
        setTestStatus('idle');
        setTestMessage('');
    }, [apiKey, baseUrl, model]);

    const handlePreset = (preset: typeof PRESETS[0]) => {
        setBaseUrl(preset.baseUrl);
        setModel(preset.model);
    };

    const handleTest = async () => {
        if (!apiKey.trim()) {
            setTestStatus('error');
            setTestMessage('API key is required.');
            return;
        }
        setTestStatus('testing');
        setTestMessage('');
        try {
            const result = await ImmersiveRagAPI.testEmbeddingConfig(apiKey.trim(), baseUrl.trim(), model.trim());
            setTestStatus('success');
            setTestMessage(result.message);
        } catch (err: unknown) {
            setTestStatus('error');
            setTestMessage(err instanceof Error ? err.message : 'Embedding test failed.');
        }
    };

    const handleSave = async () => {
        if (!apiKey.trim()) {
            setSaveStatus('error');
            return;
        }
        setSaveStatus('saving');
        try {
            await ImmersiveRagAPI.saveEmbeddingConfig(apiKey.trim(), baseUrl.trim(), model.trim());
            // Persist to localStorage with verification status
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                apiKey: apiKey.trim(),
                baseUrl: baseUrl.trim(),
                model: model.trim(),
                verified: testStatus === 'success',
            }));
            setSaveStatus('saved');
            setTimeout(() => {
                setSaveStatus('idle');
                onClose();
            }, 1200);
        } catch (err: unknown) {
            setSaveStatus('error');
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative z-10 w-full max-w-lg mx-4 bg-surface-container border border-outline-variant/40 rounded-2xl shadow-2xl overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant/30 bg-surface-container-high/50">
                    <div className="flex items-center gap-3">
                        <div className="p-1.5 rounded-lg bg-primary/10">
                            <Settings2 className="w-4 h-4 text-primary" />
                        </div>
                        <div>
                            <h2 className="text-sm font-semibold text-on-surface">Embedding Provider Settings</h2>
                            <p className="text-xs text-on-surface/50">Configure your vector embedding engine</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg hover:bg-surface-container-highest transition-colors text-on-surface/50 hover:text-on-surface"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                {/* Body */}
                <div className="px-6 py-5 space-y-5">
                    {/* Presets */}
                    <div>
                        <label className="block text-xs font-medium text-on-surface/60 mb-2 uppercase tracking-wider">Quick Presets</label>
                        <div className="grid grid-cols-2 gap-2">
                            {PRESETS.map((p) => (
                                <button
                                    key={p.label}
                                    onClick={() => handlePreset(p)}
                                    className={`text-left px-3 py-2 rounded-lg border text-xs transition-all ${baseUrl === p.baseUrl && model === p.model
                                        ? 'border-primary/60 bg-primary/10 text-primary'
                                        : 'border-outline-variant/30 bg-surface-container-high/30 text-on-surface/70 hover:border-outline-variant/60 hover:bg-surface-container-high/60'
                                        }`}
                                >
                                    {p.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* API Key */}
                    <div>
                        <label className="block text-xs font-medium text-on-surface/60 mb-1.5 uppercase tracking-wider">
                            API Key <span className="text-error">*</span>
                        </label>
                        <div className="relative">
                            <input
                                type={showKey ? 'text' : 'password'}
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                                placeholder="sk-... or bedrock-api-key-..."
                                className="w-full bg-surface-container-high border border-outline-variant/40 rounded-lg px-3 py-2.5 pr-10 text-sm text-on-surface placeholder-on-surface/30 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30 transition-all"
                            />
                            <button
                                type="button"
                                onClick={() => setShowKey(!showKey)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface/40 hover:text-on-surface/70 transition-colors"
                            >
                                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>

                    {/* Base URL */}
                    <div>
                        <label className="block text-xs font-medium text-on-surface/60 mb-1.5 uppercase tracking-wider">Base URL</label>
                        <input
                            type="text"
                            value={baseUrl}
                            onChange={(e) => setBaseUrl(e.target.value)}
                            placeholder="https://api.openai.com/v1"
                            className="w-full bg-surface-container-high border border-outline-variant/40 rounded-lg px-3 py-2.5 text-sm text-on-surface placeholder-on-surface/30 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30 transition-all"
                        />
                    </div>

                    {/* Model */}
                    <div>
                        <label className="block text-xs font-medium text-on-surface/60 mb-1.5 uppercase tracking-wider">Model</label>
                        <input
                            type="text"
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            placeholder="text-embedding-3-small"
                            className="w-full bg-surface-container-high border border-outline-variant/40 rounded-lg px-3 py-2.5 text-sm text-on-surface placeholder-on-surface/30 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30 transition-all"
                        />
                        <p className="text-[10px] text-on-surface/40 mt-1.5 italic px-1">
                            Note: Switching embedding models requires re-indexing existing documents to maintain vector compatibility.
                        </p>
                    </div>

                    {/* Test result banner */}
                    {testStatus !== 'idle' && testMessage && (
                        <div className={`flex items-start gap-2 px-3 py-2.5 rounded-lg text-xs ${testStatus === 'success'
                            ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                            : testStatus === 'error'
                                ? 'bg-red-500/10 border border-red-500/30 text-red-400'
                                : 'bg-primary/10 border border-primary/30 text-primary'
                            }`}>
                            {testStatus === 'success' && <CheckCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />}
                            {testStatus === 'error' && <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />}
                            {testStatus === 'testing' && <Loader2 className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 animate-spin" />}
                            <span className="break-all">{testMessage}</span>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-outline-variant/30 bg-surface-container-high/30">
                    <button
                        onClick={handleTest}
                        disabled={testStatus === 'testing' || saveStatus === 'saving'}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg border border-outline-variant/40 text-xs font-medium text-on-surface/70 hover:bg-surface-container-highest hover:text-on-surface disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        {testStatus === 'testing' ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                            <Zap className="w-3.5 h-3.5" />
                        )}
                        Test Connection
                    </button>

                    <div className="flex items-center gap-2">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 rounded-lg text-xs font-medium text-on-surface/60 hover:text-on-surface hover:bg-surface-container-highest transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={!apiKey.trim() || saveStatus === 'saving' || saveStatus === 'saved'}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all disabled:cursor-not-allowed ${saveStatus === 'saved'
                                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                : 'bg-primary text-on-primary hover:bg-primary/90 disabled:opacity-50'
                                }`}
                        >
                            {saveStatus === 'saving' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                            {saveStatus === 'saved' && <CheckCircle className="w-3.5 h-3.5" />}
                            {saveStatus === 'saved' ? 'Saved!' : saveStatus === 'saving' ? 'Saving...' : 'Save & Apply'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
