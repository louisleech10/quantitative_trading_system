'use client';

import { useEffect, useMemo, useState } from 'react';
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
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { useICAnalysis } from '@/hooks/useICAnalysis';

const EXPORT_TARGET_ID = 'ic-analysis-export';

export default function ICAnalysisPage() {
  const {
    config,
    taskId,
    status,
    progress,
    currentStage,
    error,
    report,
    selectedFeature,
    setConfig,
    setError,
    setReport,
    setSelectedFeature,
  } = useICAnalysisStore();

  const {
    startAnalysis,
    fetchResult,
    fetchSummary,
    refilter,
    connectProgress,
  } = useICAnalysis();

  const [summaryText, setSummaryText] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);
  const [isRefiltering, setIsRefiltering] = useState(false);

  const summaryTable = report?.summary_table || [];

  const activeFeature = selectedFeature || summaryTable[0]?.feature_name || null;

  useEffect(() => {
    if (!selectedFeature && summaryTable.length > 0) {
      setSelectedFeature(summaryTable[0].feature_name);
    }
  }, [selectedFeature, setSelectedFeature, summaryTable]);

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
      await startAnalysis(config);
    } catch (err) {
      const message = err instanceof Error ? err.message : '啟動分析失敗';
      setError(message);
    } finally {
      setIsRunning(false);
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
              <ExportButtons report={report} summaryTable={summaryTable} targetId={EXPORT_TARGET_ID} />
            </div>

            {summaryText && (
              <div className="glass-panel rounded-2xl border border-white/10 p-5">
                <p className="text-sm text-slate-300 mb-2">AI 摘要</p>
                <div className="text-sm text-slate-400 whitespace-pre-line">{summaryText}</div>
              </div>
            )}

            <div id={EXPORT_TARGET_ID} className="space-y-6">
              <FilterFunnelChart filterLog={report?.filter_log} />
              <ICSummaryTable
                data={summaryTable}
                selectedFeature={activeFeature}
                onSelectFeature={setSelectedFeature}
              />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ICDecayChart data={report?.ic_decay?.[activeFeature || ''] || null} featureName={activeFeature} />
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
