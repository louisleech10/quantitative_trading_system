'use client';

import { Download } from 'lucide-react';
import { FeatureFactoryConfig } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

interface ExportButtonsProps {
  config: FeatureFactoryConfig | null;
}

export default function ExportButtons({ config }: ExportButtonsProps) {
  const { featureList } = useFeatureFactoryStore();

  const exportConfig = () => {
    if (!config) {
      return;
    }

    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: 'application/json;charset=utf-8',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feature_factory_config_${Date.now()}.json`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const exportFeatureList = () => {
    if (!featureList.length) {
      return;
    }

    const blob = new Blob([featureList.join('\n')], {
      type: 'text/plain;charset=utf-8',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `feature_factory_features_${Date.now()}.txt`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div>
        <div className="text-lg font-semibold text-slate-100">匯出</div>
        <div className="text-xs text-slate-400">快速保存當前設定與特徵清單</div>
      </div>

      <div className="space-y-3">
        <button
          onClick={exportConfig}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition"
        >
          <Download className="w-4 h-4" />
          匯出 Config
        </button>
        <button
          onClick={exportFeatureList}
          disabled={!featureList.length}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 hover:bg-white/10 transition disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          匯出特徵清單
        </button>
      </div>
    </div>
  );
}
