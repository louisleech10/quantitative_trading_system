'use client';

import { BarChart3 } from 'lucide-react';
import { FeaturePreview } from '@/lib/types';
import FeatureCountSummary from './FeatureCountSummary';
import FeatureDistribution from './FeatureDistribution';
import FeatureListTree from './FeatureListTree';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

interface PreviewPanelProps {
  preview: FeaturePreview | null;
}

export default function PreviewPanel({ preview }: PreviewPanelProps) {
  const { featureList } = useFeatureFactoryStore();

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-cyan-400/15 flex items-center justify-center">
          <BarChart3 className="w-5 h-5 text-cyan-200" />
        </div>
        <div>
          <div className="text-lg font-semibold text-slate-100">特徵預覽</div>
          <div className="text-xs text-slate-400">預估數量、耗時與分類分佈</div>
        </div>
      </div>

      <FeatureCountSummary preview={preview} />
      <FeatureDistribution preview={preview} />
      <FeatureListTree features={featureList} />
    </div>
  );
}
