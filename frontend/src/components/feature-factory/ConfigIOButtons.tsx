'use client';

import React, { useRef } from 'react';
import { Download, Upload } from 'lucide-react';
import { FeatureFactoryConfig } from '@/lib/types';

interface ConfigIOButtonsProps {
  config: FeatureFactoryConfig | null;
  onImport: (config: FeatureFactoryConfig) => void;
}

export default function ConfigIOButtons({ config, onImport }: ConfigIOButtonsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = () => {
    if (!config) return;
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feature_config_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        if (parsed && typeof parsed === 'object' && parsed.atomic_indicators) {
          onImport(parsed as FeatureFactoryConfig);
        }
      } catch {
        // Invalid JSON — silently ignore
      }
    };
    reader.readAsText(file);
    // Reset input so same file can be re-imported
    e.target.value = '';
  };

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handleExport}
        disabled={!config}
        className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-[11px] text-slate-300 hover:border-cyan-300/40 hover:text-cyan-100 transition disabled:opacity-40"
      >
        <Download className="w-3 h-3" />
        匯出
      </button>
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1.5 text-[11px] text-slate-300 hover:border-cyan-300/40 hover:text-cyan-100 transition"
      >
        <Upload className="w-3 h-3" />
        匯入
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleImport}
        className="hidden"
      />
    </div>
  );
}
