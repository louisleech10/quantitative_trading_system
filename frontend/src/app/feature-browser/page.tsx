'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

import CorrelationHeatmap from '@/components/feature-browser/CorrelationHeatmap';
import DriftMonitor from '@/components/feature-browser/DriftMonitor';
import FeatureSummaryTable from '@/components/feature-browser/FeatureSummaryTable';
import ICDashboard from '@/components/feature-browser/ICDashboard';
import ModelAttribution from '@/components/feature-browser/ModelAttribution';
import QualityScorecard from '@/components/feature-browser/QualityScorecard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FeatureBrowserTab } from '@/lib/types';
import { useFeatureBrowserStore } from '@/store/featureBrowserStore';


const VALID_TABS: FeatureBrowserTab[] = [
  'overview',
  'ic_dashboard',
  'quality',
  'correlation',
  'drift',
  'attribution',
];


function FeatureBrowserPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    featuresPath,
    overview,
    activeTab,
    selectedFeature,
    isLoadingCatalog,
    error,
    setFeaturesPath,
    setActiveTab,
    setSelectedFeature,
    loadOverview,
  } = useFeatureBrowserStore();

  useEffect(() => {
    const tabParam = searchParams.get('tab');
    const featureParam = searchParams.get('feature');

    if (tabParam && VALID_TABS.includes(tabParam as FeatureBrowserTab)) {
      setActiveTab(tabParam as FeatureBrowserTab);
    }
    if (featureParam) {
      setSelectedFeature(featureParam);
    }
  }, [searchParams, setActiveTab, setSelectedFeature]);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1500px] mx-auto px-6 py-8 space-y-6">
        <div className="glass-panel rounded-2xl border border-white/10 p-6">
          <h1 className="text-3xl font-semibold text-slate-100">特徵瀏覽器</h1>
          <p className="text-sm text-slate-400 mt-2">Feature Browser（Phase 8 / M9）</p>

          <div className="mt-4 flex flex-col lg:flex-row gap-3">
            <Input
              value={featuresPath}
              onChange={(event) => setFeaturesPath(event.target.value)}
              placeholder="輸入 features_path，例如 /path/to/features.h5"
            />
            <Button onClick={() => loadOverview()} disabled={isLoadingCatalog}>
              {isLoadingCatalog ? '載入中...' : '載入目錄'}
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                const params = new URLSearchParams();
                params.set('tab', activeTab);
                if (selectedFeature) {
                  params.set('feature', selectedFeature);
                }
                router.replace(`/feature-browser?${params.toString()}`);
              }}
            >
              同步 URL
            </Button>
          </div>
          {error && <div className="mt-3 text-sm text-rose-300">{error}</div>}
        </div>

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as FeatureBrowserTab)}>
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="ic_dashboard">IC Dashboard</TabsTrigger>
            <TabsTrigger value="quality">Quality</TabsTrigger>
            <TabsTrigger value="correlation">相關性</TabsTrigger>
            <TabsTrigger value="drift">Drift</TabsTrigger>
            <TabsTrigger value="attribution">Attribution</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <FeatureSummaryTable
              overview={overview}
              featuresPath={featuresPath}
              selectedFeature={selectedFeature}
              onSelectFeature={setSelectedFeature}
            />
          </TabsContent>

          <TabsContent value="ic_dashboard" className="space-y-4">
            <ICDashboard
              featuresPath={featuresPath}
              selectedFeature={selectedFeature}
              onSelectFeature={setSelectedFeature}
            />
          </TabsContent>

          <TabsContent value="quality" className="space-y-4">
            <QualityScorecard
              featuresPath={featuresPath}
              selectedFeature={selectedFeature}
              onSelectFeature={setSelectedFeature}
            />
          </TabsContent>

          <TabsContent value="correlation" className="space-y-4">
            <CorrelationHeatmap featuresPath={featuresPath} />
          </TabsContent>

          <TabsContent value="drift" className="space-y-4">
            <DriftMonitor featuresPath={featuresPath} />
          </TabsContent>

          <TabsContent value="attribution" className="space-y-4">
            <ModelAttribution featuresPath={featuresPath} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}


export default function FeatureBrowserPage() {
  return (
    <Suspense fallback={<div className="h-full overflow-auto"><div className="max-w-[1500px] mx-auto px-6 py-8 text-slate-400">載入中...</div></div>}>
      <FeatureBrowserPageContent />
    </Suspense>
  );
}
