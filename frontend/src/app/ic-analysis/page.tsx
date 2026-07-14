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
    netIcConfig,
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
    setNetIcConfig,
    setDeepAnalysisStatus,
    setDeepAnalysisProgress,
    setDeepAnalysisReport,
    setDeepAnalysisModuleStatus,
    setActiveTab,
    setFeatureTier,
    toggleFeature,
    buildDeepAnalysisRequest,
  } = useICAnalysisStore();

  const {
    startAnalysis,
    fetchResult,
    fetchSummary,
    fetchAvailableFeatures,
    startDeepAnalysis,
    fetchDeepAnalysisResult,
    refilter,
    applyTransforms,
    connectProgress,
  } = useICAnalysis();
  const runs = useFeatureFactoryStore((state) => state.runs);
  const fetchRuns = useFeatureFactoryStore((state) => state.fetchRuns);
  const runsLoading = useFeatureFactoryStore((state) => state.runsLoading);
  const runsError = useFeatureFactoryStore((state) => state.runsError);

  const [summaryText, setSummaryText] = useState<string>('');
  const [featuresError, setFeaturesError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isRefiltering, setIsRefiltering] = useState(false);
  const [isDeepRunning, setIsDeepRunning] = useState(false);
  const [neutralizationMode, setNeutralizationMode] = useState<'none' | 'beta_neutral' | 'vol_neutral'>('none');

  // apply-transforms state
  const [applyTransformRank, setApplyTransformRank] = useState(true);
  const [applyTransformZscore, setApplyTransformZscore] = useState(true);
  const [applyTransformGaussian, setApplyTransformGaussian] = useState(false);
  const [isApplyingTransforms, setIsApplyingTransforms] = useState(false);
  const [applyTransformsResult, setApplyTransformsResult] = useState<{
    selected_feature_count: number;
    transforms_applied: string[];
    output_path: string;
    output_rows: number;
    output_cols: number;
  } | null>(null);

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
    fetchRuns().catch(() => undefined);
  }, [fetchRuns]);

  useEffect(() => {
    const anchor = config.cross_sectional_runs?.[0];
    const symbol = anchor?.symbol || config.symbol;
    const timeframe = config.timeframe;
    const configHash = anchor?.config_hash || config.config_hash;

    if (!symbol?.trim() || !timeframe?.trim() || !configHash?.trim()) {
      setAvailableFeatures([]);
      setFeaturesError(null);
      return;
    }

    setFeaturesError(null);
    fetchAvailableFeatures(symbol.trim(), timeframe.trim(), configHash.trim())
      .then((features) => {
        setAvailableFeatures(features);
        setFeaturesError(null);
      })
      .catch((err) => {
        setAvailableFeatures([]);
        const message = err instanceof Error ? err.message : '載入特徵清單失敗';
        setFeaturesError(message);
      });
  }, [
    config.symbol,
    config.timeframe,
    config.config_hash,
    config.cross_sectional_runs,
    fetchAvailableFeatures,
    setAvailableFeatures,
  ]);

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

  const handleApplyTransforms = async () => {
    if (!taskId) {
      setError('請先完成 IC 分析');
      return;
    }
    if (selectedFeatures.length === 0) {
      setError('請在表格中選擇至少一個特徵');
      return;
    }
    setIsApplyingTransforms(true);
    setApplyTransformsResult(null);
    try {
      const result = await applyTransforms(taskId, {
        selected_features: selectedFeatures,
        rank: applyTransformRank,
        zscore: applyTransformZscore,
        gaussian: applyTransformGaussian,
      });
      setApplyTransformsResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : '套用後處理失敗');
    } finally {
      setIsApplyingTransforms(false);
    }
  };

  const handleRunAnalysis = async () => {
    setError(null);
    setReport(null);
    setIsRunning(true);

    try {
      if (config.mode === 'cross_sectional') {
        if ((config.cross_sectional_runs?.length || 0) < 2) {
          throw new Error('請選擇至少含 2 個 Symbol 的批次');
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
      const payload = buildDeepAnalysisRequest({
        selected_features: candidates,
        top_n: candidates.length,
        config_override: {
          factor_exposure: {
            neutralization_mode: neutralizationMode,
            neutralization_lookback: 63,
          },
        },
      });
      await startDeepAnalysis(taskId, payload);

      let done = false;
      while (!done) {
        const response = await fetchDeepAnalysisResult(taskId);
        setDeepAnalysisProgress(response.progress ?? 0);

        if (response.summary) {
          // deep report 結構: { results: { net_ic_analysis, ... }, module_summary, ... }
          const deepPayload = (response.results || {}) as Record<string, unknown>;
          const moduleResults =
            deepPayload.results && typeof deepPayload.results === 'object'
              ? (deepPayload.results as Record<string, unknown>)
              : deepPayload;
          const merged = {
            deep_analysis_enabled: true,
            deep_analysis_summary: {
              total: response.summary.total_modules,
              completed: response.summary.completed_count,
              skipped: response.summary.skipped_count,
              failed: response.summary.failed_count,
            },
            deep_analysis_errors: deepPayload.deep_analysis_errors,
            module_statuses: response.module_status,
            ...moduleResults,
          };
          setDeepAnalysisReport(merged as typeof deepAnalysisReport);
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

        {featuresError && (
          <div className="glass-panel rounded-xl p-4 border border-amber-400/30 text-amber-200 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            <span>{featuresError}</span>
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
          <ICConfigPanel
            config={config}
            runs={runs}
            runsLoading={runsLoading}
            runsError={runsError}
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

              {/* Apply L6.5 post-processing panel — IC-First workflow — 常住顯示 */}
              <div className="glass-panel rounded-2xl border border-emerald-400/30 p-5 space-y-4">
                {/* 標題列 + 測試說明徽章 */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-emerald-200">套用 L6.5 後處理</p>
                      <span className="rounded-full bg-amber-400/15 border border-amber-400/40 px-2 py-0.5 text-[10px] text-amber-300 font-medium tracking-wide">
                        待測試
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      IC-First 工作流程最後一步：對 IC 篩選後的特徵執行 Rank / Z-Score / Gaussian。
                      套用順序固定為 <span className="text-emerald-300">Rank → Z-Score → Gaussian</span>（Gaussian 一定最後）。
                    </p>
                  </div>
                </div>

                {/* 待測試項目清單 */}
                <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 px-4 py-3 space-y-1.5">
                  <p className="text-[11px] font-semibold text-amber-300 uppercase tracking-wider mb-2">📋 測試項目</p>
                  <ul className="space-y-1 text-[11px] text-slate-400 leading-relaxed list-none">
                    <li><span className="text-amber-200 mr-1">①</span>需先完成 IC 分析（status = completed）才能呼叫，否則應顯示錯誤訊息</li>
                    <li><span className="text-amber-200 mr-1">②</span>需在表格中勾選特徵後，按鈕才可用（未勾選應顯示 disabled）</li>
                    <li><span className="text-amber-200 mr-1">③</span>三個轉換至少勾選一個，按鈕才可用</li>
                    <li><span className="text-amber-200 mr-1">④</span>Rank + ZScore 預設開啟，Gaussian 預設關閉</li>
                    <li><span className="text-amber-200 mr-1">⑤</span>執行後應顯示輸出路徑 <code className="bg-slate-800 px-1 rounded">data_cache/reports/post_ic_transforms_&lt;task_id&gt;.h5</code></li>
                    <li><span className="text-amber-200 mr-1">⑥</span>已套用的轉換依序列出（e.g. rank → zscore）</li>
                    <li><span className="text-amber-200 mr-1">⑦</span>若 Feature Factory 以 IC-First 模式生成，驗證輸出 .h5 只含 Rank/ZScore 結果（不含原始 legacy L6.5）</li>
                    <li><span className="text-amber-200 mr-1">⑧</span>API <code className="bg-slate-800 px-1 rounded">POST /api/v1/ic/apply-transforms/&#123;task_id&#125;</code> 應回傳 selected_feature_count、transforms_applied、output_path、output_rows、output_cols</li>
                  </ul>
                </div>

                {/* 前置條件提示 */}
                {!report && (
                  <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
                    <span className="text-amber-400">⚠</span>
                    請先執行 IC 分析並等待完成，才可使用此功能。
                  </div>
                )}
                {report && selectedFeatures.length === 0 && (
                  <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
                    <span className="text-amber-400">⚠</span>
                    請在上方表格中勾選至少一個特徵。
                  </div>
                )}

                {/* 轉換勾選 */}
                <div className="flex flex-wrap gap-5 text-xs">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={applyTransformRank}
                      onChange={(e) => setApplyTransformRank(e.target.checked)}
                      className="accent-emerald-400"
                    />
                    <span className="text-slate-200">Rank Transform</span>
                    <span className="text-slate-500 text-[10px]">（預設開）</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={applyTransformZscore}
                      onChange={(e) => setApplyTransformZscore(e.target.checked)}
                      className="accent-emerald-400"
                    />
                    <span className="text-slate-200">Adaptive Z-Score</span>
                    <span className="text-slate-500 text-[10px]">（預設開）</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={applyTransformGaussian}
                      onChange={(e) => setApplyTransformGaussian(e.target.checked)}
                      className="accent-emerald-400"
                    />
                    <span className="text-slate-200">Gaussian Normalize</span>
                    <span className="text-slate-500 text-[10px]">（預設關 · 最後執行）</span>
                  </label>
                </div>

                {/* 執行按鈕 + 結果 */}
                <div className="flex items-center gap-3 flex-wrap">
                  <button
                    onClick={handleApplyTransforms}
                    disabled={
                      isApplyingTransforms ||
                      !report ||
                      selectedFeatures.length === 0 ||
                      (!applyTransformRank && !applyTransformZscore && !applyTransformGaussian)
                    }
                    className="rounded-lg px-4 py-2 text-xs font-medium bg-emerald-500/20 text-emerald-100 border border-emerald-400/40 hover:bg-emerald-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {isApplyingTransforms
                      ? '處理中…'
                      : selectedFeatures.length > 0
                      ? `套用後處理（${selectedFeatures.length} 個特徵）`
                      : '套用後處理（請先選擇特徵）'}
                  </button>
                  {applyTransformsResult && (
                    <span className="text-xs text-emerald-300 flex flex-col gap-0.5">
                      <span>
                        ✓ 完成 <strong>{applyTransformsResult.selected_feature_count}</strong> 個特徵 ·{' '}
                        {applyTransformsResult.output_rows} 行 · {applyTransformsResult.output_cols} 欄
                      </span>
                      <span>套用：{applyTransformsResult.transforms_applied.join(' → ')}</span>
                      {applyTransformsResult.output_path && (
                        <span className="text-slate-400 text-[10px] break-all">{applyTransformsResult.output_path}</span>
                      )}
                    </span>
                  )}
                </div>
              </div>

              <DeepAnalysisConfigPanel
                selectedFeatureCount={selectedFeatures.length}
                modules={deepAnalysisModules}
                netIcConfig={netIcConfig}
                neutralizationMode={neutralizationMode}
                onModulesChange={setDeepAnalysisModules}
                onNetIcConfigChange={setNetIcConfig}
                onNeutralizationModeChange={setNeutralizationMode}
                onStart={handleStartDeepAnalysis}
                isRunning={isDeepRunning}
                formError={
                  deepAnalysisStatus === 'failed' && error ? error : null
                }
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
                      <ChartErrorBoundary title="C22 成本拖累">
                        <NetICChart
                          data={deepAnalysisReport?.net_ic_analysis}
                          loading={isDeepRunning || deepAnalysisStatus === 'running'}
                          error={
                            deepAnalysisStatus === 'failed' && error
                              ? error
                              : null
                          }
                        />
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
