'use client';

import { Info } from 'lucide-react';
import { DeepAnalysisModules, NetICAnalysisRequest } from '@/lib/types';
import { Checkbox } from '@/components/ui/checkbox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface DeepAnalysisConfigPanelProps {
  selectedFeatureCount: number;
  modules: DeepAnalysisModules;
  netIcConfig: NetICAnalysisRequest;
  neutralizationMode: 'none' | 'beta_neutral' | 'vol_neutral';
  onModulesChange: (modules: DeepAnalysisModules) => void;
  onNetIcConfigChange: (config: NetICAnalysisRequest) => void;
  onNeutralizationModeChange: (mode: 'none' | 'beta_neutral' | 'vol_neutral') => void;
  onStart: () => void;
  isRunning?: boolean;
  /** API 422 等表單錯誤文字 */
  formError?: string | null;
}

const moduleMeta: Array<{ key: keyof DeepAnalysisModules; label: string; tip: string }> = [
  { key: 'factor_return', label: 'Factor Return', tip: '分位收益與風險指標' },
  { key: 'factor_centrality', label: 'Factor Centrality', tip: 'PCA 與擁擠度分析' },
  { key: 'trend_analysis', label: 'Trend Analysis', tip: 'IC/中心性趨勢訊號' },
  { key: 'parameter_sensitivity', label: 'Parameter Sensitivity', tip: '參數家族穩健性' },
  { key: 'rolling_oos', label: 'Rolling OOS', tip: '滾動樣本外驗證' },
  { key: 'factor_orthogonalization', label: 'Factor Orthogonalization', tip: '因子正交化' },
  { key: 'factor_exposure', label: 'Factor Exposure', tip: '因子曝險與集中度' },
  { key: 'long_short_analysis', label: 'Long/Short', tip: '多空不對稱與建議' },
  { key: 'feature_quality_diagnostics', label: 'Quality Diagnostics', tip: 'ADF/LB/漂移/覆蓋率' },
  { key: 'net_ic_analysis', label: '成本拖累(報酬空間)', tip: '成本拖累分析(非淨 IC 混減)' },
];

export default function DeepAnalysisConfigPanel({
  selectedFeatureCount,
  modules,
  netIcConfig,
  neutralizationMode,
  onModulesChange,
  onNetIcConfigChange,
  onNeutralizationModeChange,
  onStart,
  isRunning = false,
  formError = null,
}: DeepAnalysisConfigPanelProps) {
  const selectedModuleCount = moduleMeta.filter((item) => modules[item.key]).length;
  const disabled = selectedModuleCount === 0 || selectedFeatureCount === 0 || isRunning;
  const showCostFields = Boolean(modules.net_ic_analysis);

  const handleToggle = (key: keyof DeepAnalysisModules, checked: boolean) => {
    onModulesChange({ ...modules, [key]: checked });
  };

  const handleCostEnabled = (checked: boolean) => {
    onNetIcConfigChange({
      cost_enabled: checked,
      // 關閉時保留輸入值於 UI 狀態,但 request 仍可帶(API 非 None 一律驗域)
      cost_bps: netIcConfig.cost_bps,
    });
  };

  const handleCostBps = (raw: string) => {
    if (raw === '' || raw === null) {
      onNetIcConfigChange({ ...netIcConfig, cost_bps: null });
      return;
    }
    const n = Number(raw);
    onNetIcConfigChange({
      ...netIcConfig,
      cost_bps: Number.isFinite(n) ? n : null,
    });
  };

  return (
    <div className="glass-panel rounded-2xl border border-white/10 p-5 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-slate-100">深度分析模組設定</h3>
        <span className="text-xs text-slate-400">已選 {selectedModuleCount} 個模組</span>
      </div>

      <TooltipProvider>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {moduleMeta.map((item) => (
            <label
              key={item.key}
              className="flex items-center gap-2 text-sm text-slate-200 rounded-md border border-white/10 bg-white/5 px-3 py-2"
            >
              <Checkbox
                checked={modules[item.key]}
                onCheckedChange={(checked) => handleToggle(item.key, Boolean(checked))}
              />
              <span>{item.label}</span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button type="button" className="text-slate-400 hover:text-slate-200">
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>{item.tip}</TooltipContent>
              </Tooltip>
            </label>
          ))}
        </div>
      </TooltipProvider>

      {showCostFields && (
        <div
          className="rounded-md border border-cyan-400/20 bg-cyan-500/5 p-3 space-y-3"
          data-testid="net-ic-cost-panel"
        >
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <Checkbox
              checked={Boolean(netIcConfig.cost_enabled)}
              onCheckedChange={(checked) => handleCostEnabled(Boolean(checked))}
              data-testid="net-ic-cost-enabled"
            />
            <span>啟用成本</span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button type="button" className="text-slate-400 hover:text-slate-200">
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  成本拖累(報酬空間)=(cost_bps/10000)×turnover;0 bps 非法;關閉=無成本
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          {netIcConfig.cost_enabled && (
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400" htmlFor="net-ic-cost-bps">
                成本 (bps，0.1–1000)
              </label>
              <input
                id="net-ic-cost-bps"
                data-testid="net-ic-cost-bps"
                type="number"
                min={0.1}
                max={1000}
                step={0.1}
                value={netIcConfig.cost_bps ?? ''}
                onChange={(event) => handleCostBps(event.target.value)}
                className="h-9 w-40 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-slate-100"
              />
            </div>
          )}
        </div>
      )}

      <div className="flex flex-col gap-1">
        <label className="text-xs text-slate-400">Factor Neutralization（搭配 Factor Exposure）</label>
        <select
          value={neutralizationMode}
          onChange={(event) => onNeutralizationModeChange(event.target.value as 'none' | 'beta_neutral' | 'vol_neutral')}
          className="h-9 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-slate-100"
        >
          <option value="none">None</option>
          <option value="beta_neutral">Beta Neutral</option>
          <option value="vol_neutral">Vol Neutral</option>
        </select>
      </div>

      {formError && (
        <div
          role="alert"
          data-testid="net-ic-form-error"
          className="text-sm text-rose-300 border border-rose-400/30 bg-rose-500/10 rounded-md px-3 py-2"
        >
          {formError}
        </div>
      )}

      <button
        type="button"
        disabled={disabled}
        onClick={onStart}
        className="px-4 py-2 rounded-md text-sm bg-cyan-500/20 border border-cyan-400/20 text-cyan-100 hover:bg-cyan-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isRunning
          ? '深度分析執行中...'
          : `分析 ${selectedFeatureCount} 個因子 × ${selectedModuleCount} 個模組`}
      </button>
    </div>
  );
}
