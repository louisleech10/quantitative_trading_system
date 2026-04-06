'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Sparkles, AlertTriangle, Activity } from 'lucide-react';
import ICConfigPanel from '@/components/ic-analysis/ICConfigPanel';
import ICSummaryTable from '@/components/ic-analysis/ICSummaryTable';
import ICDecayChart from '@/components/ic-analysis/ICDecayChart';
import QuantileReturnChart from '@/components/ic-analysis/QuantileReturnChart';
import CorrelationHeatmap from '@/components/ic-analysis/CorrelationHeatmap';
import FilterFunnelChart from '@/components/ic-analysis/FilterFunnelChart';
import RollingICChart from '@/components/ic-analysis/RollingICChart';
import GroupedICBarChart from '@/components/ic-analysis/GroupedICBarChart';
import RegimeRadarChart from '@/components/ic-analysis/RegimeRadarChart';
import ExportButtons from '@/components/ic-analysis/ExportButtons';
import FeatureFilterPanel from '@/components/ic-analysis/FeatureFilterPanel';
import DeepAnalysisConfigPanel from '@/components/ic-analysis/DeepAnalysisConfigPanel';
import FactorReturnChart from '@/components/ic-analysis/FactorReturnChart';
import FactorCentralityChart from '@/components/ic-analysis/FactorCentralityChart';
import PCAExplainedChart from '@/components/ic-analysis/PCAExplainedChart';
import TrendDashboard from '@/components/ic-analysis/TrendDashboard';
import ParameterSensitivityHeatmap from '@/components/ic-analysis/ParameterSensitivityHeatmap';
import OOSDistributionChart from '@/components/ic-analysis/OOSDistributionChart';
import LongShortComparisonChart from '@/components/ic-analysis/LongShortComparisonChart';
import FactorExposureRadar from '@/components/ic-analysis/FactorExposureRadar';
import FeatureQualityDashboard from '@/components/ic-analysis/FeatureQualityDashboard';
import NetICChart from '@/components/ic-analysis/NetICChart';
import TurnoverTimeSeriesChart from '@/components/ic-analysis/TurnoverTimeSeriesChart';
import FactorEquityCurveChart from '@/components/ic-analysis/FactorEquityCurveChart';
import CrossSectionalICHeatmap from '@/components/ic-analysis/CrossSectionalICHeatmap';
import CrossSymbolValidationPanel from '@/components/ic-analysis/CrossSymbolValidationPanel';
import PartialFailureBanner from '@/components/ic-analysis/PartialFailureBanner';
import ChartErrorBoundary from '@/components/ic-analysis/ChartErrorBoundary';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { useICAnalysis } from '@/hooks/useICAnalysis';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

const EXPORT_TARGET_ID = 'ic-analysis-export';

function ICAnalysisPageContent() {
  const searchParams = useSearchParams();
  const {
    config,
    taskId,
    status,
    progress,
    currentStage,
    error,
    report,
    selectedFeature,
    availableFeatures,
    featureFilter,
    selectedFeatures,
    deepAnalysisModules,
    deepAnalysisStatus,
    deepAnalysisProgress,
    deepAnalysisReport,
    activeTab,
    featureTier,
    featureToggles,
    setConfig,
    setError,
    setReport,
    setSelectedFeature,
    setAvailableFeatures,
    setFeatureFilter,
    setSelectedFeatures,
    setDeepAnalysisModules,
    setDeepAnalysisStatus,
    setDeepAnalysisProgress,
    setDeepAnalysisReport,
    setDeepAnalysisModuleStatus,
    setActiveTab,
    setFeatureTier,
    toggleFeature,
  } = useICAnalysisStore();

  const {
    startAnalysis,
    fetchResult,
    fetchSummary,
    fetchAvailableFeatures,
    startDeepAnalysis,
    fetchDeepAnalysisResult,
    refilter,
    connectProgress,
  } = useICAnalysis();
  const registryEntries = useFeatureFactoryStore((state) => state.registryEntries);
  const fetchRegistry = useFeatureFactoryStore((state) => state.fetchRegistry);

  const [summaryText, setSummaryText] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);
  const [isRefiltering, setIsRefiltering] = useState(false);
  const [isDeepRunning, setIsDeepRunning] = useState(false);
  const [neutralizationMode, setNeutralizationMode] = useState<'none' | 'beta_neutral' | 'vol_neutral'>('none');

  const summaryTable = useMemo(() => report?.summary_table ?? [], [report?.summary_table]);

  const crossSectionalFeatureCount = useMemo(() => {
    const keyword = (featureFilter.include_pattern || '').trim();
    const normalizedKeyword = keyword.toLowerCase();
    let regex: RegExp | null = null;
    if (keyword) {
      try {
        regex = new RegExp(keyword, 'i');
      } catch {
        regex = null;
      }
    }

    const matched = availableFeatures.filter((item) => {
      const categoryPass =
        !featureFilter.include_categories ||
        featureFilter.include_categories.length === 0 ||
        (item.category && featureFilter.include_categories.includes(item.category));

      const sourcePass =
        !featureFilter.include_data_sources ||
        featureFilter.include_data_sources.length === 0 ||
        (item.data_source && featureFilter.include_data_sources.includes(item.data_source));

      const familyPass =
        !featureFilter.include_families ||
        featureFilter.include_families.length === 0 ||
        (item.family && featureFilter.include_families.includes(item.family));

      const textPass =
        !keyword ||
        (regex
          ? regex.test(item.feature_name)
          : item.feature_name.toLowerCase().includes(normalizedKeyword));

      return Boolean(categoryPass && sourcePass && familyPass && textPass);
    });

    const maxFeatures =
      typeof featureFilter.max_features === 'number' && featureFilter.max_features > 0
        ? featureFilter.max_features
        : matched.length;

    return Math.min(maxFeatures, matched.length);
  }, [availableFeatures, featureFilter]);

  const crossSectionalSampleSize = useMemo(() => {
    const raw = report?.metadata?.n_timestamps;
    if (typeof raw === 'number' && Number.isFinite(raw) && raw > 0) {
      return raw;
    }
    return 0;
  }, [report?.metadata]);

  const crossSectionalSymbolCount = useMemo(() => {
    const raw = report?.metadata?.n_symbols;
    if (typeof raw === 'number' && Number.isFinite(raw) && raw > 0) {
      return raw;
    }
    return 0;
  }, [report?.metadata]);

  const resultMode = useMemo(() => {
    const raw = report?.metadata?.mode;
    if (raw === 'cross_sectional') {
      return 'cross_sectional';
    }
    if (config.mode === 'cross_sectional') {
      return 'cross_sectional';
    }
    return config.mode;
  }, [config.mode, report?.metadata]);

  const activeFeature = selectedFeature || summaryTable[0]?.feature_name || null;

  const deepTabVisible = Boolean(report?.deep_analysis_enabled || deepAnalysisReport?.deep_analysis_enabled);

  const deepSummary = deepAnalysisReport?.deep_analysis_summary;

  const crossSymbolValidationData = useMemo(() => {
    const deepData = deepAnalysisReport?.cross_symbol_validation;
    if (deepData && typeof deepData === 'object') {
      return deepData;
    }

    const crossModuleStatus = (deepAnalysisReport?.module_statuses || []).find((item) =>
      item.module_name === 'cross_symbol_validation' || item.module_name === 'cross_symbol_validator'
    );
    if (crossModuleStatus && crossModuleStatus.status !== 'completed') {
      const skipDetail = (deepAnalysisReport?.deep_analysis_errors || []).find((item) =>
        item.module_name === crossModuleStatus.module_name
      );
      return {
        status: 'skipped' as const,
        reason: skipDetail?.reason || crossModuleStatus.reason || `status=${crossModuleStatus.status}`,
      };
    }

    const reportData = report?.cross_symbol_validation;
    if (reportData && typeof reportData === 'object') {
      return reportData;
    }
    return null;
  }, [
    deepAnalysisReport?.cross_symbol_validation,
    deepAnalysisReport?.deep_analysis_errors,
    deepAnalysisReport?.module_statuses,
    report?.cross_symbol_validation,
  ]);

  useEffect(() => {
    if (!selectedFeature && summaryTable.length > 0) {
      setSelectedFeature(summaryTable[0].feature_name);
    }
  }, [selectedFeature, setSelectedFeature, summaryTable]);

  useEffect(() => {
    fetchRegistry().catch(() => undefined);
  }, [fetchRegistry]);

  useEffect(() => {
    if (!config.features_path?.trim()) {
      setAvailableFeatures([]);
      return;
    }

    fetchAvailableFeatures(config.features_path.trim(), config.meta_path?.trim() || undefined)
      .then((features) => setAvailableFeatures(features))
      .catch(() => setAvailableFeatures([]));
  }, [config.features_path, config.meta_path, fetchAvailableFeatures, setAvailableFeatures]);

  useEffect(() => {
    if (summaryTable.length === 0) return;
    if (selectedFeatures.length > 0) return;
    setSelectedFeatures(
      summaryTable.slice(0, 30).map((item: { feature_name: string }) => item.feature_name)
    );
  }, [selectedFeatures.length, setSelectedFeatures, summaryTable]);

  useEffect(() => {
    const includeFeaturesRaw = searchParams.get('include_features');
    if (!includeFeaturesRaw) {
      return;
    }
    const parsed = includeFeaturesRaw
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    if (parsed.length > 0) {
      setSelectedFeatures(parsed);
      setSelectedFeature(parsed[0]);
    }
  }, [searchParams, setSelectedFeature, setSelectedFeatures]);

  useEffect(() => {
    if (!taskId || status !== 'running') {
      return;
    }
    connectProgress(taskId);
  }, [connectProgress, status, taskId]);

  useEffect(() => {
    if (status !== 'completed' || !taskId || report) {
      return;
    }

    fetchResult(taskId)
      .then((result) => {
        if (result?.ai_summary) {
          setSummaryText(result.ai_summary);
        }
        return fetchSummary(taskId);
      })
      .then((summary) => {
        if (summary) {
          setSummaryText(summary);
        }
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : '載入結果失敗';
        setError(message);
      });
  }, [fetchResult, fetchSummary, report, setError, status, taskId]);

  useEffect(() => {
    if (!report?.ai_summary) {
      return;
    }
    setSummaryText(report.ai_summary);
  }, [report?.ai_summary]);

  const thresholdsKey = useMemo(
    () => JSON.stringify(config.thresholds),
    [config.thresholds]
  );

  useEffect(() => {
    if (!taskId || status !== 'completed' || !report) {
      return;
    }

    const timer = setTimeout(() => {
      setIsRefiltering(true);
      refilter(taskId, config.thresholds)
        .catch((err) => {
          const message = err instanceof Error ? err.message : '重新篩選失敗';
          setError(message);
        })
        .finally(() => setIsRefiltering(false));
    }, 600);

    return () => clearTimeout(timer);
  }, [config.thresholds, refilter, report, setError, status, taskId, thresholdsKey]);

  const handleRunAnalysis = async () => {
    setError(null);
    setReport(null);
    setIsRunning(true);

    try {
      if (config.mode === 'cross_sectional') {
        if ((config.cross_sectional_symbols?.length || 0) < 2) {
          throw new Error('請至少選擇 2 個 Symbol');
        }
        if (crossSectionalFeatureCount > 50) {
          throw new Error('截面 IC 最多支援 50 個因子，請先在 Feature Browser 篩選');
        }
      }

      await startAnalysis(config);
    } catch (err) {
      const message = err instanceof Error ? err.message : '啟動分析失敗';
      setError(message);
    } finally {
      setIsRunning(false);
    }
  };

  const handleStartDeepAnalysis = async () => {
    if (!taskId) {
      setError('請先完成 IC 分析');
      return;
    }

    const candidates = selectedFeatures.length > 0
      ? selectedFeatures
      : summaryTable.slice(0, 30).map((item: { feature_name: string }) => item.feature_name);

    setDeepAnalysisStatus('running');
    setDeepAnalysisProgress(0);
    setIsDeepRunning(true);
    setError(null);

    try {
      await startDeepAnalysis(taskId, {
        selected_features: candidates,
        top_n: candidates.length,
        modules: deepAnalysisModules,
        config_override: {
          factor_exposure: {
            neutralization_mode: neutralizationMode,
            neutralization_lookback: 63,
          },
        },
      });

      let done = false;
      while (!done) {
        const response = await fetchDeepAnalysisResult(taskId);
        setDeepAnalysisProgress(response.progress ?? 0);

        if (response.summary) {
          const merged = {
            deep_analysis_enabled: true,
            deep_analysis_summary: {
              total: response.summary.total_modules,
              completed: response.summary.completed_count,
              skipped: response.summary.skipped_count,
              failed: response.summary.failed_count,
            },
            ...(response.results || {}),
          };
          setDeepAnalysisReport(merged);
        }

        setDeepAnalysisModuleStatus(response.module_status || []);

        if (response.status === 'completed') {
          setDeepAnalysisStatus('completed');
          setActiveTab('deep');
          done = true;
        } else if (response.status === 'failed') {
          setDeepAnalysisStatus('failed');
          setError(response.error || '深度分析失敗');
          done = true;
        } else {
          await new Promise((resolve) => setTimeout(resolve, 800));
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '啟動深度分析失敗';
      setError(message);
      setDeepAnalysisStatus('failed');
    } finally {
      setIsDeepRunning(false);
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="relative px-6 py-8 max-w-[1500px] mx-auto space-y-6">
        <div className="absolute -top-20 right-0 h-64 w-64 rounded-full bg-gradient-to-br from-cyan-400/20 via-transparent to-emerald-400/20 blur-3xl" />
        <div className="absolute -bottom-24 left-12 h-72 w-72 rounded-full bg-gradient-to-br from-indigo-400/20 via-transparent to-purple-400/20 blur-3xl" />

        <div className="glass-panel rounded-2xl border border-white/10 p-6 relative overflow-hidden">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 text-cyan-200 text-xs uppercase tracking-[0.2em]">
                <Sparkles className="w-4 h-4" />
                IC Gatekeeper
              </div>
              <h1 className="mt-4 text-3xl lg:text-4xl font-semibold text-slate-100">IC 分析儀表板</h1>
              <p className="mt-2 text-slate-400 max-w-2xl">
                聚焦因子 IC、ICIR、分位數收益與分組穩健度，快速鎖定值得保留的特徵。
              </p>
            </div>
            <div className="flex flex-col gap-3 min-w-[240px]">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>任務狀態</span>
                <Badge variant="outline" className="border-cyan-400/40 text-cyan-200">
                  {status === 'running' ? '分析中' : status === 'completed' ? '完成' : status}
                </Badge>
              </div>
              <Progress value={Math.round(progress * 100)} />
              <div className="text-xs text-slate-400 flex items-center gap-2">
                <Activity className="w-4 h-4" />
                {currentStage ? `目前階段: ${currentStage}` : '等待分析啟動'}
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="glass-panel rounded-xl p-4 border border-rose-400/30 text-rose-200 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
          <ICConfigPanel
            config={config}
            registryEntries={registryEntries}
            crossSectionalFeatureCount={crossSectionalFeatureCount}
            featureTier={featureTier}
            featureToggles={featureToggles}
            onChangeFeatureTier={setFeatureTier}
            onToggleFeature={toggleFeature}
            onConfigChange={setConfig}
            onRunAnalysis={handleRunAnalysis}
            isRunning={isRunning || status === 'running'}
          />

          <div className="space-y-6">
            <div className="glass-panel rounded-2xl border border-white/10 p-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div>
                <p className="text-sm text-slate-300">篩選進度</p>
                <p className="text-xs text-slate-500">
                  {isRefiltering ? '重新篩選中...' : '門檻變更會觸發即時 refilter'}
                </p>
              </div>
              <ExportButtons taskId={taskId} report={report} summaryTable={summaryTable} targetId={EXPORT_TARGET_ID} />
            </div>

            {summaryText && (
              <div className="glass-panel rounded-2xl border border-white/10 p-5">
                <p className="text-sm text-slate-300 mb-2">AI 摘要</p>
                <div className="text-sm text-slate-400 whitespace-pre-line">{summaryText}</div>
              </div>
            )}

            <div id={EXPORT_TARGET_ID} className="space-y-6">
              <FeatureFilterPanel
                availableFeatures={availableFeatures}
                filter={featureFilter}
                onFilterChange={setFeatureFilter}
                onFilteredFeaturesChange={setSelectedFeatures}
              />

              <ICSummaryTable
                data={summaryTable}
                selectedFeature={activeFeature}
                onSelectFeature={setSelectedFeature}
                selectable
                selectedFeatures={selectedFeatures}
                onSelectFeatures={setSelectedFeatures}
                analysisMode={resultMode}
                crossSectionalSampleSize={crossSectionalSampleSize}
                crossSectionalSymbolCount={crossSectionalSymbolCount}
                taskId={taskId}
              />

              <DeepAnalysisConfigPanel
                selectedFeatureCount={selectedFeatures.length}
                modules={deepAnalysisModules}
                neutralizationMode={neutralizationMode}
                onModulesChange={setDeepAnalysisModules}
                onNeutralizationModeChange={setNeutralizationMode}
                onStart={handleStartDeepAnalysis}
                isRunning={isDeepRunning}
              />

              {deepAnalysisStatus === 'running' && (
                <div className="glass-panel rounded-xl border border-cyan-400/30 p-4 text-cyan-100">
                  深度分析執行中... {(deepAnalysisProgress * 100).toFixed(0)}%
                </div>
              )}

              <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'basic' | 'deep')}>
                <TabsList>
                  <TabsTrigger value="basic">基礎分析</TabsTrigger>
                  {deepTabVisible && <TabsTrigger value="deep">深度分析</TabsTrigger>}
                </TabsList>

                <TabsContent value="basic" className="space-y-6">
                  <FilterFunnelChart filterLog={report?.filter_log} />

                  {resultMode === 'cross_sectional' && (
                    <ChartErrorBoundary title="Cross-Sectional IC Heatmap">
                      <CrossSectionalICHeatmap data={report?.cross_sectional_symbol_ic || null} />
                    </ChartErrorBoundary>
                  )}

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <ICDecayChart
                      data={report?.ic_decay?.[activeFeature || ''] || null}
                      featureName={activeFeature}
                      timeframe={config.timeframe}
                    />
                    <QuantileReturnChart
                      data={report?.quantile_returns?.[activeFeature || ''] || null}
                      featureName={activeFeature}
                    />
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <RollingICChart
                      series={report?.rolling_ic_series?.[activeFeature || ''] || null}
                      featureName={activeFeature}
                    />
                    <GroupedICBarChart
                      groupedIC={report?.grouped_ic || null}
                      featureName={activeFeature}
                    />
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <RegimeRadarChart groupedIC={report?.grouped_ic || null} featureName={activeFeature} />
                    <CorrelationHeatmap matrix={report?.correlation_matrix || null} />
                  </div>
                </TabsContent>

                {deepTabVisible && (
                  <TabsContent value="deep" className="space-y-6">
                    <PartialFailureBanner
                      completed={deepSummary?.completed || 0}
                      skipped={deepSummary?.skipped || 0}
                      failed={deepSummary?.failed || 0}
                      errors={deepAnalysisReport?.deep_analysis_errors || []}
                    />

                    {crossSymbolValidationData && (
                      <ChartErrorBoundary title="Cross Symbol Validation">
                        <CrossSymbolValidationPanel data={crossSymbolValidationData} />
                      </ChartErrorBoundary>
                    )}

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {featureToggles.turnover_analysis && (
                        <ChartErrorBoundary title="Turnover Time Series">
                          <TurnoverTimeSeriesChart
                            data={report?.turnover_analysis?.[activeFeature || ''] || null}
                            featureName={activeFeature}
                          />
                        </ChartErrorBoundary>
                      )}
                      <ChartErrorBoundary title="Factor Equity Curve">
                        <FactorEquityCurveChart
                          data={report?.quantile_returns?.[activeFeature || ''] || null}
                          featureName={activeFeature}
                        />
                      </ChartErrorBoundary>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <ChartErrorBoundary title="C13 Factor Return">
                        <FactorReturnChart data={deepAnalysisReport?.factor_returns} />
                      </ChartErrorBoundary>
                      <ChartErrorBoundary title="C14 Factor Centrality">
                        <FactorCentralityChart data={deepAnalysisReport?.factor_centrality} />
                      </ChartErrorBoundary>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <ChartErrorBoundary title="C15 PCA Explained">
                        <PCAExplainedChart data={deepAnalysisReport?.factor_centrality} />
                      </ChartErrorBoundary>
                      <ChartErrorBoundary title="C16 Trend Dashboard">
                        <TrendDashboard data={deepAnalysisReport?.trend_analysis} />
                      </ChartErrorBoundary>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <ChartErrorBoundary title="C17 Parameter Sensitivity">
                        <ParameterSensitivityHeatmap data={deepAnalysisReport?.parameter_sensitivity} />
                      </ChartErrorBoundary>
                      <ChartErrorBoundary title="C18 OOS Distribution">
                        <OOSDistributionChart data={deepAnalysisReport?.rolling_oos} />
                      </ChartErrorBoundary>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <ChartErrorBoundary title="C19 Long Short">
                        <LongShortComparisonChart data={deepAnalysisReport?.long_short_analysis} />
                      </ChartErrorBoundary>
                      <ChartErrorBoundary title="C20 Exposure Radar">
                        <FactorExposureRadar data={deepAnalysisReport?.factor_exposure} />
                      </ChartErrorBoundary>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <ChartErrorBoundary title="C21 Quality Dashboard">
                        <FeatureQualityDashboard data={deepAnalysisReport?.feature_quality_diagnostics} />
                      </ChartErrorBoundary>
                      <ChartErrorBoundary title="C22 Net IC">
                        <NetICChart data={deepAnalysisReport?.net_ic_analysis} />
                      </ChartErrorBoundary>
                    </div>
                  </TabsContent>
                )}
              </Tabs>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ICAnalysisPage() {
  return (
    <Suspense fallback={<div className="h-full overflow-auto"><div className="relative px-6 py-8 max-w-[1500px] mx-auto text-slate-400">載入中...</div></div>}>
      <ICAnalysisPageContent />
    </Suspense>
  );
}
