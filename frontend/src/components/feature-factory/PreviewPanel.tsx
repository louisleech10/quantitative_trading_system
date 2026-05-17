'use client';


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
    <div className="px-6 pb-6 space-y-6">
      <FeatureCountSummary preview={preview} />
      <FeatureDistribution preview={preview} />
      <FeatureListTree features={featureList} />
    </div>
  );
}
