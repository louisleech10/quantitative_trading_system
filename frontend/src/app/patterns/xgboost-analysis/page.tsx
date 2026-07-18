'use client';

import React, { Suspense, useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import MultiIndicatorConfig from '@/components/optimization/MultiIndicatorConfig';
import EngineConfigPanel from '@/components/pattern/EngineConfigPanel';
import ComparisonPanel from '@/components/pattern/ComparisonPanel';
import ValidationTab from '@/components/pattern/details/tabs/ValidationTab';
import FeaturesTab from '@/components/pattern/details/tabs/FeaturesTab';
import MonitoringTab from '@/components/pattern/details/tabs/MonitoringTab';
import DiagnosisTab from '@/components/pattern/details/tabs/DiagnosisTab';
import { createPattern, getBatchTaskStatus, getCaseSummary, startBatchAnalysis, startModelHyperparamOptimization } from '@/lib/api/patternApi';
import { fetchWatchlist } from '@/lib/api/watchlistApi';
import type { AnalysisResult, CreatePatternRequest, IndicatorConfig, ValidationConfig } from '@/lib/patternTypes';
import { usePatternStore } from '@/store/patternStore';
import { AlertCircle, BarChart2, Brain, CheckCircle, CheckSquare, Database, Info, List, Loader2, Play, Save, Square, TrendingUp } from 'lucide-react';

interface CaseSummary {
  total_cases: number;
  positive_cases: number;
  negative_cases: number;
  symbols: string[];
  timeframes: string[];
}

interface TaskStatus {
  status: 'running' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  message: string;
  total_cases: number;
  processed_cases: number;
  result?: AnalysisResult;
  error?: string;
}

const AVAILABLE_KLINE_TIMEFRAMES = [
  { value: '1h', label: '1 小時' },
  { value: '4h', label: '4 小時' },
  { value: '12h', label: '12 小時' },
  { value: '1d', label: '1 天' }
];

function CaseSummaryCard({ summary }: { summary: CaseSummary | null }) {
  if (!summary) return <Card className="glass-panel border-slate-800/80"><CardContent className="p-6 text-slate-400">載入中...</CardContent></Card>;
  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-slate-100 flex items-center gap-2"><Database className="w-5 h-5" />案例資料統計</CardTitle>
        <CardDescription className="text-slate-400">從 cases.json 載入的案例數據</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <MetricBox label="總案例數" value={summary.total_cases} tone="slate" />
          <MetricBox label="正例" value={summary.positive_cases} tone="green" />
          <MetricBox label="反例" value={summary.negative_cases} tone="red" />
        </div>
      </CardContent>
    </Card>
  );
}

function MetricBox({ label, value, tone }: { label: string; value: number; tone: 'slate' | 'green' | 'red' }) {
  const cls = tone === 'green'
    ? 'bg-emerald-500/10 border-emerald-400/30 text-emerald-200'
    : tone === 'red'
    ? 'bg-rose-500/10 border-rose-400/30 text-rose-200'
    : 'bg-slate-900/50 border-slate-800/80 text-slate-100';
  return (
    <div className={`rounded-lg p-4 border ${cls}`}>
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-sm text-slate-400">{label}</div>
    </div>
  );
}

function SymbolMultiSelect({ availableSymbols, selectedSymbols, onChange }: { availableSymbols: string[]; selectedSymbols: string[]; onChange: (symbols: string[]) => void }) {
  const allSelected = selectedSymbols.length === availableSymbols.length;
  const someSelected = selectedSymbols.length > 0 && !allSelected;

  const toggle = (symbol: string) => {
    if (selectedSymbols.includes(symbol)) onChange(selectedSymbols.filter((s) => s !== symbol));
    else onChange([...selectedSymbols, symbol]);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 p-2 rounded-lg bg-slate-900/50 cursor-pointer hover:bg-slate-900/70 border border-slate-800/80" onClick={() => onChange(allSelected ? [] : [...availableSymbols])}>
        {allSelected ? <CheckSquare className="w-5 h-5 text-emerald-300" /> : someSelected ? <div className="w-5 h-5 border-2 border-emerald-300 rounded flex items-center justify-center"><div className="w-2 h-2 bg-emerald-300 rounded-sm" /></div> : <Square className="w-5 h-5 text-slate-500" />}
        <span className="text-sm font-medium text-slate-100">全選 ({selectedSymbols.length}/{availableSymbols.length})</span>
      </div>
      <div className="max-h-40 overflow-y-auto border border-slate-800/80 rounded-lg">
        {availableSymbols.map((symbol) => (
          <div key={symbol} className="flex items-center gap-2 p-2 hover:bg-slate-900/60 cursor-pointer border-b border-slate-800/80 last:border-b-0" onClick={() => toggle(symbol)}>
            <Checkbox checked={selectedSymbols.includes(symbol)} className="pointer-events-none" />
            <span className="text-sm text-slate-100">{symbol}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TaskProgressCard({ task }: { task: TaskStatus | null }) {
  if (!task) return null;
  const icon = task.status === 'running' ? <Loader2 className="w-5 h-5 text-emerald-300 animate-spin" /> : task.status === 'completed' ? <CheckCircle className="w-5 h-5 text-emerald-300" /> : <AlertCircle className="w-5 h-5 text-rose-300" />;
  return (
    <Card className="glass-panel border-slate-800/80">
      <CardHeader className="pb-3"><CardTitle className="text-lg text-slate-100 flex items-center gap-2">{icon}任務狀態</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <div>
          <div className="flex justify-between mb-1 text-sm text-slate-300"><span>{task.current_step}</span><span>{task.progress}%</span></div>
          <Progress value={task.progress} className="h-2" />
        </div>
        <div className="text-sm text-slate-200">{task.message}</div>
        <div className="text-sm text-slate-300">處理進度：{task.processed_cases} / {task.total_cases}</div>
        {task.error && <Alert variant="destructive" className="bg-rose-500/10 border-rose-400/30"><AlertDescription className="text-rose-200">{task.error}</AlertDescription></Alert>}
      </CardContent>
    </Card>
  );
}

function AnalysisResultView({ result }: { result: AnalysisResult }) {
  const symbols = result.symbols?.join(', ') || result.symbol;
  return (
    <div className="space-y-6">
      <Card className="glass-panel border-slate-800/80">
        <CardHeader className="pb-3"><CardTitle className="text-lg text-slate-100 flex items-center gap-2">分析摘要 <Badge className="bg-slate-900/60 border border-slate-700 text-slate-200">{result.engine_type || 'xgboost'}</Badge></CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            <SimpleStat label="交易對" value={symbols} />
            <SimpleStat label="K 線週期" value={result.timeframe} />
            <SimpleStat label="有效案例" value={result.valid_cases} />
            <SimpleStat label="生成特徵數" value={result.features_generated} />
            <SimpleStat label="模型狀態" value={result.model_saved ? '已儲存' : '未儲存'} />
          </div>
        </CardContent>
      </Card>

      <Card className="glass-panel border-slate-800/80">
        <CardHeader className="pb-3"><CardTitle className="text-lg text-slate-100 flex items-center gap-2"><TrendingUp className="w-5 h-5" />模型性能</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <SimpleMetric label="In-sample Train AUC" value={result.model_performance.in_sample_train_auc} percent />
            <SimpleMetric label="CV AUC" value={result.model_performance.cv_auc_mean} percent />
            <SimpleMetric label="Precision" value={result.model_performance.precision} percent />
            <SimpleMetric label="Recall" value={result.model_performance.recall} percent />
            <SimpleMetric label="F1" value={result.model_performance.f1_score} percent />
            <SimpleMetric label="Overfitting" value={result.model_performance.overfitting_score} percent />
            <SimpleMetric label="PR AUC" value={result.model_performance.pr_auc ?? null} percent />
            <SimpleMetric label="Brier" value={result.model_performance.brier_score ?? null} />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="glass-panel border-slate-800/80">
          <CardHeader className="pb-3"><CardTitle className="text-lg text-slate-100 flex items-center gap-2"><List className="w-5 h-5" />特徵重要性 Top15</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {result.feature_importance.slice(0, 15).map((item) => (
              <div key={item.feature} className="text-sm text-slate-200 flex justify-between gap-3"><span className="font-mono break-all">{item.feature}</span><span>{(item.importance * 100).toFixed(2)}%</span></div>
            ))}
          </CardContent>
        </Card>
        <Card className="glass-panel border-slate-800/80">
          <CardHeader className="pb-3"><CardTitle className="text-lg text-slate-100 flex items-center gap-2"><Brain className="w-5 h-5" />決策規則 Top10</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {result.decision_rules.length === 0 ? (
              <div className="text-sm text-slate-400">此引擎目前無可用決策規則</div>
            ) : (
              result.decision_rules.slice(0, 10).map((rule) => (
                <div key={rule.rule_id} className="bg-slate-900/50 rounded-lg p-3 border border-slate-800/80 text-slate-200 text-sm">{rule.condition}</div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="glass-panel border-slate-800/80">
        <CardHeader className="pb-3"><CardTitle className="text-lg text-slate-100 flex items-center gap-2"><BarChart2 className="w-5 h-5" />進階指標</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm text-slate-200">
          <div>Precision@K：{result.precision_at_k ? '可用' : '無資料'}</div>
          <div>期望值估算：{result.expectancy ? '可用' : '無資料'}</div>
          <div>Bootstrap CI：{result.bootstrap_ci ? '可用' : '無資料'}</div>
          <div>Permutation：{result.permutation_importance ? '可用' : '無資料'}</div>
          <div>Fold 穩定性：{result.fold_importance_stability ? '可用' : '無資料'}</div>
          <div>跨幣種泛化：{result.cross_symbol_validation?.length ? '可用' : '無資料'}</div>
        </CardContent>
      </Card>
    </div>
  );
}

function SimpleStat({ label, value }: { label: string; value: string | number }) {
  return <div><div className="text-xl font-bold text-slate-100">{value}</div><div className="text-xs text-slate-400">{label}</div></div>;
}

function SimpleMetric({ label, value, percent = false }: { label: string; value: number | null | undefined; percent?: boolean }) {
  const display = value === null || value === undefined || Number.isNaN(value) ? 'N/A' : percent ? `${(value * 100).toFixed(2)}%` : value.toFixed(4);
  return <div className="rounded-lg bg-slate-900/50 border border-slate-800/80 p-3"><div className="text-slate-400 text-xs">{label}</div><div className="text-slate-100 font-semibold">{display}</div></div>;
}

function XGBoostAnalysisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    currentAnalysis,
    setCurrentAnalysis,
    addPattern,
    selectedEngine,
    setSelectedEngine,
    comparisonReport,
    comparisonLoading,
    loadComparisonReport,
    loadDeepAnalysis,
    clearDeepAnalysis
  } = usePatternStore();

  const [caseSummary, setCaseSummary] = useState<CaseSummary | null>(null);
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [klineTimeframe, setKlineTimeframe] = useState<string>('12h');
  const [indicators, setIndicators] = useState<IndicatorConfig[]>([]);
  const [lookbackBars, setLookbackBars] = useState<number>(200);
  const [cvFolds, setCvFolds] = useState<number>(5);
  const [engineConfig, setEngineConfig] = useState<Record<string, unknown>>({});
  const [validationConfig, setValidationConfig] = useState<ValidationConfig>({ cv_folds: 5, purge_gap: 5, oot_enabled: false, oot_ratio: 0.2, early_stopping_rounds: 50 });
  const [optunaEnabled, setOptunaEnabled] = useState(false);
  const [optunaTrials, setOptunaTrials] = useState(100);

  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'result' | 'comparison' | 'deep'>('result');
  const [deepEngine, setDeepEngine] = useState<'xgboost' | 'lightgbm'>('xgboost');
  const [engineTaskMap, setEngineTaskMap] = useState<{ xgboost?: string; lightgbm?: string }>({});
  const [selectedWatchlistFeatures, setSelectedWatchlistFeatures] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleEngineChange = useCallback((engine: 'xgboost' | 'lightgbm' | 'both') => {
    setSelectedEngine(engine);
    if (engine !== 'both') {
      setDeepEngine(engine === 'lightgbm' ? 'lightgbm' : 'xgboost');
    }
  }, [setSelectedEngine]);

  const handleConfigChange = useCallback((config: Record<string, unknown>) => {
    setEngineConfig(config);
  }, []);

  const handleValidationChange = useCallback((validation: ValidationConfig) => {
    setValidationConfig(validation);
  }, []);

  const handleOptunaToggle = useCallback((enabled: boolean, nTrials: number) => {
    setOptunaEnabled(enabled);
    setOptunaTrials(nTrials);
  }, []);

  const result = currentAnalysis as AnalysisResult | null;
  const effectiveDeepTaskId = deepEngine === 'lightgbm' ? (engineTaskMap.lightgbm || taskId) : (engineTaskMap.xgboost || taskId);

  useEffect(() => {
    (async () => {
      try {
        const summary = await getCaseSummary();
        setCaseSummary(summary);
        if (summary.symbols.length > 0) setSelectedSymbols(summary.symbols);
      } catch {
        setError('無法載入案例統計');
      }
    })();
  }, []);

  useEffect(() => {
    const mode = searchParams.get('use_watchlist');
    if (mode !== 'verified') {
      setSelectedWatchlistFeatures([]);
      return;
    }

    (async () => {
      try {
        const response = await fetchWatchlist('verified');
        const features = response.entries.map((entry) => entry.feature_name).filter(Boolean);
        setSelectedWatchlistFeatures(features);
        if (features.length === 0) {
          setError('Watchlist 沒有已驗證因子，請先在 IC 分析或 Feature Browser 標記。');
        }
      } catch {
        setError('讀取 Watchlist 已驗證因子失敗');
      }
    })();
  }, [searchParams]);

  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (taskId && taskStatus?.status === 'running') {
      timer = setInterval(async () => {
        try {
          const status = await getBatchTaskStatus(taskId);
          setTaskStatus(status as TaskStatus);
          if (status.status === 'completed' && status.result) {
            const analysisResult: AnalysisResult = {
              ...(status.result as AnalysisResult),
              symbols: (status.result as AnalysisResult).symbols || selectedSymbols,
              engine_type: (((status.result as Partial<AnalysisResult>).engine_type) || (selectedEngine === 'both' ? 'lightgbm' : selectedEngine)),
              metadata: {
                ...(status.result as AnalysisResult).metadata,
                data_selection: { symbol: selectedSymbols[0], symbols: selectedSymbols, timeframe: klineTimeframe, lookback_bars: lookbackBars },
                indicator_config: indicators.map((ind) => ({ indicator: ind.indicator, data_source: ind.data_source, params: ind.params })),
                training_config: { time_series_split: true, cv_folds: cvFolds }
              }
            };
            setCurrentAnalysis(analysisResult);
            setEngineTaskMap({ xgboost: taskId, lightgbm: taskId });
            setIsLoading(false);

            if (selectedEngine === 'both') {
              await loadComparisonReport(taskId);
            }
          }
          if (status.status === 'failed') {
            setError(status.error || '訓練失敗');
            setIsLoading(false);
          }
        } catch {
          setError('任務狀態查詢失敗');
          setIsLoading(false);
        }
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [taskId, taskStatus?.status, selectedSymbols, klineTimeframe, lookbackBars, indicators, cvFolds, selectedEngine, setCurrentAnalysis, loadComparisonReport]);

  useEffect(() => {
    if (activeTab === 'deep' && effectiveDeepTaskId) {
      loadDeepAnalysis(effectiveDeepTaskId);
    }
    return () => {
      if (activeTab !== 'deep') clearDeepAnalysis();
    };
  }, [activeTab, effectiveDeepTaskId, loadDeepAnalysis, clearDeepAnalysis]);

  const startAnalysis = async () => {
    if (selectedSymbols.length === 0) return setError('請至少選擇一個交易對');

    const hasWatchlistFeatures = selectedWatchlistFeatures.length > 0;
    if (indicators.length === 0 && !hasWatchlistFeatures) {
      return setError('請至少配置一個指標，或使用 Watchlist 已驗證因子');
    }

    setError(null);
    setIsLoading(true);
    setTaskStatus(null);
    setCurrentAnalysis(null);

    try {
      if (optunaEnabled) {
        const engine = selectedEngine === 'both' ? 'lightgbm' : selectedEngine;
        const response = await startModelHyperparamOptimization({
          task_type: 'model_hyperparam',
          engine,
          n_trials: optunaTrials,
          objective_config: {
            engine,
            cv_folds: validationConfig.cv_folds,
            base_model_params: engineConfig
          }
        });
        router.push(`/optimization-result?task_id=${response.task_id}`);
        setIsLoading(false);
        return;
      }

      const response = await startBatchAnalysis({
        symbols: selectedSymbols,
        timeframe: klineTimeframe,
        indicators,
        selected_features: selectedWatchlistFeatures.length > 0 ? selectedWatchlistFeatures : undefined,
        lookback_bars: lookbackBars,
        cv_folds: validationConfig.cv_folds,
        engine: selectedEngine === 'both' ? 'lightgbm' : selectedEngine,
        model_params: engineConfig,
        run_comparison: selectedEngine === 'both'
      });

      setTaskId(response.task_id);
      setTaskStatus({ status: 'running', progress: 0, current_step: '初始化', message: '任務已啟動', total_cases: 0, processed_cases: 0 });
      } catch (error: unknown) {
      setError(getErrorMessage(error, '啟動分析失敗'));
      setIsLoading(false);
    }
  };

  const saveAsPattern = async () => {
    if (!result) return;
    setIsSaving(true);
    setError(null);
    try {
      const symbols = result.symbols?.join('_') || result.symbol;
      // LA-2 B3：server 權威 — 只帶 task_id；rules/metrics 由 server 從 oot_receipt 重建
      // threshold=condition 分位值（非 confidence）由 server 從 feature_conditions 寫入
      if (!taskId) {
        throw new Error('缺少 task_id，無法晉升模式（server 需 oot_receipt）');
      }
      const request: CreatePatternRequest = {
        name: `${result.engine_type || 'XGBoost'}_${symbols}_${result.timeframe}_${Date.now()}`,
        description: `${result.engine_type || 'XGBoost'} 分析結果 - ${symbols} ${result.timeframe}`,
        task_id: taskId,
        tags: [result.engine_type || 'xgboost', ...((result.symbols && result.symbols.length > 0) ? result.symbols : [result.symbol]), result.timeframe],
      };
      const response = await createPattern(request);
      if (response.success && response.pattern) addPattern(response.pattern);
    } catch (error: unknown) {
      setError(getErrorMessage(error, '儲存樣式失敗'));
    } finally {
      setIsSaving(false);
    }
  };

  const showComparisonTab = selectedEngine === 'both';

  return (
    <div className="min-h-screen bg-slate-950/40">
      <div className="bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <h1 className="text-3xl font-semibold text-slate-100">ML 模型分析</h1>
          <p className="text-slate-400 mt-1">LightGBM / XGBoost 雙引擎訓練與分析</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <CaseSummaryCard summary={caseSummary} />

            <Card className="glass-panel border-slate-800/80">
              <CardHeader className="pb-3"><CardTitle className="text-lg text-slate-100">Step 1: 數據選擇</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-slate-200 font-medium">交易對</Label>
                  <SymbolMultiSelect availableSymbols={caseSummary?.symbols || []} selectedSymbols={selectedSymbols} onChange={setSelectedSymbols} />
                </div>
                <div className="space-y-2">
                  <Label className="text-slate-200 font-medium">K 線時間週期</Label>
                  <Select value={klineTimeframe} onValueChange={setKlineTimeframe}>
                    <SelectTrigger className="bg-slate-900/60 border-slate-700 text-slate-100"><SelectValue /></SelectTrigger>
                    <SelectContent className="bg-slate-950 border-slate-800">{AVAILABLE_KLINE_TIMEFRAMES.map((tf) => <SelectItem key={tf.value} value={tf.value}>{tf.label}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2"><Label className="text-slate-200 font-medium">回看 K 線數量</Label><Info className="w-4 h-4 text-slate-500" /></div>
                  <Input type="number" value={lookbackBars} onChange={(e) => setLookbackBars(Number(e.target.value) || 200)} className="bg-slate-900/60 border-slate-700 text-slate-100" />
                </div>
                <div className="space-y-2">
                  <Label className="text-slate-200 font-medium">交叉驗證折數</Label>
                  <Input type="number" value={cvFolds} onChange={(e) => setCvFolds(Number(e.target.value) || 5)} className="bg-slate-900/60 border-slate-700 text-slate-100" />
                </div>
              </CardContent>
            </Card>

            <Card className="glass-panel border-slate-800/80">
              <CardHeader className="pb-3"><CardTitle className="text-lg text-slate-100">Step 2: 指標配置</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {selectedWatchlistFeatures.length > 0 && (
                  <Alert className="bg-emerald-500/10 border-emerald-400/30">
                    <AlertDescription className="text-emerald-200">
                      已從 Watchlist 帶入 {selectedWatchlistFeatures.length} 個已驗證因子，將優先使用這批因子訓練。
                    </AlertDescription>
                  </Alert>
                )}
                <MultiIndicatorConfig value={indicators} onChange={setIndicators} />
              </CardContent>
            </Card>

            <EngineConfigPanel
              onEngineChange={handleEngineChange}
              onConfigChange={(config) => handleConfigChange(config as unknown as Record<string, unknown>)}
              onValidationChange={handleValidationChange}
              onOptunaToggle={handleOptunaToggle}
            />

            <Button onClick={startAnalysis} disabled={isLoading || selectedSymbols.length === 0} className="w-full bg-emerald-500/20 text-emerald-100 border border-emerald-400/40 hover:bg-emerald-500/30" size="lg">
              {isLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />分析中...</> : <><Play className="w-4 h-4 mr-2" />開始訓練</>}
            </Button>

            {error && <Alert variant="destructive" className="bg-rose-500/10 border-rose-400/30"><AlertCircle className="w-4 h-4 text-rose-300" /><AlertDescription className="text-rose-200">{error}</AlertDescription></Alert>}
          </div>

          <div className="lg:col-span-2 space-y-6">
            <TaskProgressCard task={taskStatus} />

            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'result' | 'comparison' | 'deep')}>
              <TabsList className={`grid w-full ${showComparisonTab ? 'grid-cols-3' : 'grid-cols-2'} bg-slate-900/60 border border-slate-800/80`}>
                <TabsTrigger value="result">📊 訓練結果</TabsTrigger>
                {showComparisonTab && <TabsTrigger value="comparison">🆚 引擎對比</TabsTrigger>}
                <TabsTrigger value="deep">🔍 深度分析</TabsTrigger>
              </TabsList>

              <TabsContent value="result" className="space-y-4">
                {result ? (
                  <>
                    <div className="flex flex-wrap gap-3">
                      <Button onClick={saveAsPattern} disabled={isSaving} className="bg-emerald-500/20 text-emerald-100 border border-emerald-400/40 hover:bg-emerald-500/30">{isSaving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />儲存中...</> : <><Save className="w-4 h-4 mr-2" />儲存為樣式</>}</Button>
                      <Button variant="outline" onClick={() => router.push('/patterns')} className="border-slate-700 text-slate-300">前往樣式管理</Button>
                      {taskId && <Button variant="outline" onClick={() => router.push(`/patterns/xgboost-analysis/${taskId}/details`)} className="border-emerald-400/40 text-emerald-200">在新頁面開啟深度分析</Button>}
                    </div>
                    <AnalysisResultView result={result} />
                  </>
                ) : (
                  <Card className="glass-panel border-slate-800/80"><CardContent className="py-12 text-center"><Brain className="w-16 h-16 mx-auto text-slate-600 mb-4" /><h3 className="text-lg font-semibold text-slate-100 mb-2">尚未執行訓練</h3><p className="text-slate-400">配置完成後點擊「開始訓練」</p></CardContent></Card>
                )}
              </TabsContent>

              {showComparisonTab && (
                <TabsContent value="comparison">
                  <ComparisonPanel report={comparisonReport} loading={comparisonLoading} />
                </TabsContent>
              )}

              <TabsContent value="deep" className="space-y-4">
                {!effectiveDeepTaskId ? (
                  <Card className="glass-panel border-slate-800/80"><CardContent className="py-12 text-center text-slate-400">訓練完成後可查看深度分析</CardContent></Card>
                ) : (
                  <>
                    {showComparisonTab && (
                      <div className="flex items-center gap-2">
                        <Label className="text-slate-300">查看引擎</Label>
                        <Select value={deepEngine} onValueChange={(v: 'xgboost' | 'lightgbm') => setDeepEngine(v)}>
                          <SelectTrigger className="w-44 bg-slate-900/60 border-slate-700 text-slate-100"><SelectValue /></SelectTrigger>
                          <SelectContent className="bg-slate-950 border-slate-800">
                            <SelectItem value="xgboost">XGBoost</SelectItem>
                            <SelectItem value="lightgbm">LightGBM</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                    <Tabs defaultValue="validation">
                      <TabsList className="grid grid-cols-4 w-full max-w-2xl bg-slate-900/60 border border-slate-800/80">
                        <TabsTrigger value="validation">驗證</TabsTrigger>
                        <TabsTrigger value="features">特徵</TabsTrigger>
                        <TabsTrigger value="monitoring">監控</TabsTrigger>
                        <TabsTrigger value="diagnosis">診斷</TabsTrigger>
                      </TabsList>
                      <TabsContent value="validation"><ValidationTab taskId={effectiveDeepTaskId} /></TabsContent>
                      <TabsContent value="features"><FeaturesTab taskId={effectiveDeepTaskId} /></TabsContent>
                      <TabsContent value="monitoring"><MonitoringTab taskId={effectiveDeepTaskId} /></TabsContent>
                      <TabsContent value="diagnosis"><DiagnosisTab taskId={effectiveDeepTaskId} /></TabsContent>
                    </Tabs>
                  </>
                )}
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export default function XGBoostAnalysisPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950/40 p-6 text-slate-400">載入中...</div>}>
      <XGBoostAnalysisContent />
    </Suspense>
  );
}
