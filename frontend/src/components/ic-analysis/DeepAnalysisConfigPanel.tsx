'use client';

import { Info } from 'lucide-react';
import { DeepAnalysisModules } from '@/lib/types';
import { Checkbox } from '@/components/ui/checkbox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface DeepAnalysisConfigPanelProps {
  selectedFeatureCount: number;
  modules: DeepAnalysisModules;
  onModulesChange: (modules: DeepAnalysisModules) => void;
  onStart: () => void;
  isRunning?: boolean;
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
  { key: 'net_ic_analysis', label: 'Net IC', tip: '成本調整後淨 IC' },
];

export default function DeepAnalysisConfigPanel({
  selectedFeatureCount,
  modules,
  onModulesChange,
  onStart,
  isRunning = false,
}: DeepAnalysisConfigPanelProps) {
  const selectedModuleCount = moduleMeta.filter((item) => modules[item.key]).length;
  const disabled = selectedModuleCount === 0 || selectedFeatureCount === 0 || isRunning;

  const handleToggle = (key: keyof DeepAnalysisModules, checked: boolean) => {
    onModulesChange({ ...modules, [key]: checked });
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
