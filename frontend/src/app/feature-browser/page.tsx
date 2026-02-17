'use client';

import { Suspense, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

import DashboardOverview from '@/components/feature-browser/DashboardOverview';
import DataQualityPanel from '@/components/feature-browser/DataQualityPanel';
import FeatureCatalogTable from '@/components/feature-browser/FeatureCatalogTable';
import FeatureCorrelationPanel from '@/components/feature-browser/FeatureCorrelationPanel';
import FeatureDataTable from '@/components/feature-browser/FeatureDataTable';
import FeatureDistributionPanel from '@/components/feature-browser/FeatureDistributionPanel';
import FeatureSelector from '@/components/feature-browser/FeatureSelector';
import FeatureTimeSeriesPanel from '@/components/feature-browser/FeatureTimeSeriesPanel';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FeatureBrowserTab } from '@/lib/types';
import { useFeatureBrowserStore } from '@/store/featureBrowserStore';


const VALID_TABS: FeatureBrowserTab[] = [
  'overview',
  'catalog',
  'distribution',
  'timeseries',
  'correlation',
  'quality',
  'datatable',
];


function FeatureBrowserPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    featuresPath,
    catalog,
    activeTab,
    selectedFeature,
    selectedFeatures,
    isLoadingCatalog,
    error,
    setFeaturesPath,
    setActiveTab,
    setSelectedFeature,
    setSelectedFeatures,
    loadCatalog,
  } = useFeatureBrowserStore();

  const featureNames = catalog?.items.map((item) => item.name) || [];

  useEffect(() => {
    const tabParam = searchParams.get('tab');
    const featureParam = searchParams.get('feature');
    const includeFeaturesParam = searchParams.get('include_features');

    if (tabParam && VALID_TABS.includes(tabParam as FeatureBrowserTab)) {
      setActiveTab(tabParam as FeatureBrowserTab);
    }
    if (featureParam) {
      setSelectedFeature(featureParam);
      setSelectedFeatures([featureParam]);
    }
    if (includeFeaturesParam) {
      const parsed = includeFeaturesParam.split(',').map((item) => item.trim()).filter(Boolean);
      if (parsed.length > 0) {
        setSelectedFeatures(parsed.slice(0, 5));
        if (!featureParam) {
          setSelectedFeature(parsed[0]);
        }
      }
    }
  }, [searchParams, setActiveTab, setSelectedFeature, setSelectedFeatures]);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-[1500px] mx-auto px-6 py-8 space-y-6">
        <div className="glass-panel rounded-2xl border border-white/10 p-6">
          <h1 className="text-3xl font-semibold text-slate-100">特徵瀏覽器</h1>
          <p className="text-sm text-slate-400 mt-2">Feature Browser（Phase 2.12）</p>

          <div className="mt-4 flex flex-col lg:flex-row gap-3">
            <Input
              value={featuresPath}
              onChange={(event) => setFeaturesPath(event.target.value)}
              placeholder="輸入 features_path，例如 /path/to/features.h5"
            />
            <Button onClick={() => loadCatalog()} disabled={isLoadingCatalog}>
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
                if (selectedFeatures.length > 0) {
                  params.set('include_features', selectedFeatures.join(','));
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
            <TabsTrigger value="overview">Dashboard</TabsTrigger>
            <TabsTrigger value="catalog">目錄</TabsTrigger>
            <TabsTrigger value="distribution">分佈</TabsTrigger>
            <TabsTrigger value="timeseries">時間序列</TabsTrigger>
            <TabsTrigger value="correlation">相關性</TabsTrigger>
            <TabsTrigger value="quality">品質</TabsTrigger>
            <TabsTrigger value="datatable">數據表</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <DashboardOverview summary={catalog?.summary || null} />
          </TabsContent>

          <TabsContent value="catalog" className="space-y-4">
            <FeatureCatalogTable
              items={catalog?.items || []}
              selectedFeatures={selectedFeatures}
              onSelectFeature={(feature) => {
                setSelectedFeature(feature);
                setSelectedFeatures([feature]);
                setActiveTab('distribution');
              }}
              onSelectFeatures={setSelectedFeatures}
            />
          </TabsContent>

          <TabsContent value="distribution" className="space-y-4">
            <FeatureSelector
              features={featureNames}
              mode="single"
              selectedFeature={selectedFeature}
              onSelectFeature={(feature) => {
                setSelectedFeature(feature);
                setSelectedFeatures([feature]);
              }}
            />
            <FeatureDistributionPanel featuresPath={featuresPath} featureName={selectedFeature} />
          </TabsContent>

          <TabsContent value="timeseries" className="space-y-4">
            <FeatureSelector
              features={featureNames}
              mode="multi"
              selectedFeatures={selectedFeatures}
              onSelectFeatures={setSelectedFeatures}
              maxMultiSelect={5}
            />
            <FeatureTimeSeriesPanel featuresPath={featuresPath} selectedFeatures={selectedFeatures} />
          </TabsContent>

          <TabsContent value="correlation" className="space-y-4">
            <FeatureSelector
              features={featureNames}
              mode="multi"
              selectedFeatures={selectedFeatures}
              onSelectFeatures={setSelectedFeatures}
              maxMultiSelect={100}
            />
            <FeatureCorrelationPanel featuresPath={featuresPath} selectedFeatures={selectedFeatures} />
          </TabsContent>

          <TabsContent value="quality" className="space-y-4">
            <FeatureSelector
              features={featureNames}
              mode="multi"
              selectedFeatures={selectedFeatures}
              onSelectFeatures={setSelectedFeatures}
              maxMultiSelect={30}
            />
            <DataQualityPanel featuresPath={featuresPath} selectedFeatures={selectedFeatures} />
          </TabsContent>

          <TabsContent value="datatable" className="space-y-4">
            <FeatureSelector
              features={featureNames}
              mode="multi"
              selectedFeatures={selectedFeatures}
              onSelectFeatures={setSelectedFeatures}
              maxMultiSelect={20}
            />
            <FeatureDataTable featuresPath={featuresPath} selectedFeatures={selectedFeatures} />
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
