'use client';

import { useMemo, useState } from 'react';
import { Info } from 'lucide-react';
import { FeatureTierLevel, ICMethodSettings } from '@/lib/types';
import { DEFAULT_IC_SETTINGS, IC_SETTING_KEYS, IC_SETTING_SPECS, isICSettingApplicable } from '@/lib/icConfigOverride';
import { Checkbox } from '@/components/ui/checkbox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  IC_SETTING_LABELS,
  IC_SETTING_NOT_APPLICABLE_LABEL,
  IC_SETTING_OPTION_LABELS,
  settingTip,
} from '@/components/ic-analysis/icSettingsText';

interface FeatureTierPanelProps {
  featureTier: FeatureTierLevel;
  featureToggles: Record<string, boolean>;
  onChangeTier: (tier: FeatureTierLevel) => void;
  onToggleFeature: (key: string) => void;
  /** 分析模式：xsec 無 p 閘，tooltip 需分模式誠實（D-H） */
  analysisMode?: 'global' | 'cross_sectional' | string;
  /** ICPERF Task 0.4 ㊸：方法選擇與門檻開關之現值（未給＝全預設）。 */
  settings?: ICMethodSettings;
  /** ㊸：改一項設定（未給＝唯讀顯示）。 */
  onChangeSetting?: <K extends keyof ICMethodSettings>(key: K, value: ICMethodSettings[K]) => void;
}

const LOCKED_KEYS = new Set(['ic_calculation', 'ai_summary']);

/** 一個 ⓘ：滑鼠移入一句話。 */
function InfoTip({ text, label }: { text: string; label: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button type="button" aria-label={`${label}說明`} className="text-slate-500 hover:text-slate-300">
          <Info className="h-3 w-3" />
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">{text}</TooltipContent>
    </Tooltip>
  );
}

/**
 * ㊸：IC 頁方法選擇（四個選單）＋單調性門檻開關；每項一個 ⓘ。
 * v5.58 (v)：該分析模式不適用之設定（契約 `not_applicable_modes`）停用並標「此模式不適用」；ⓘ 依模式換句。
 * v5.58 (w)：IC 自相關改為報告表之欄（不再是此處之揭露列）。
 */
function MethodSettings({
  settings,
  onChangeSetting,
  analysisMode,
}: {
  settings: ICMethodSettings;
  onChangeSetting?: FeatureTierPanelProps['onChangeSetting'];
  analysisMode?: string;
}) {
  return (
    <div className="rounded-md border border-white/10 bg-black/10 p-3 space-y-2" data-testid="ic-method-settings">
      <div className="text-xs text-slate-300">方法選擇</div>
      {IC_SETTING_KEYS.map((key) => {
        const spec = IC_SETTING_SPECS[key];
        const label = IC_SETTING_LABELS[key];
        const applicable = isICSettingApplicable(key, analysisMode);
        const changed = applicable && settings[key] !== spec.default;
        const disabled = !onChangeSetting || !applicable;
        return (
          <div
            key={key}
            className={`flex items-center gap-2 text-xs ${applicable ? 'text-slate-200' : 'text-slate-500'}`}
            data-testid={`ic-setting-${key}`}
            data-applicable={applicable ? 'true' : 'false'}
          >
            {spec.kind === 'toggle' ? (
              <label className="flex items-center gap-2">
                <Checkbox
                  aria-label={label}
                  checked={Boolean(settings[key])}
                  disabled={disabled}
                  onCheckedChange={(checked) => onChangeSetting?.(key, (checked === true) as ICMethodSettings[typeof key])}
                />
                <span className={changed ? 'text-amber-200' : undefined}>{label}</span>
              </label>
            ) : (
              <>
                <span className={`w-20 shrink-0 ${changed ? 'text-amber-200' : ''}`}>{label}</span>
                <select
                  aria-label={label}
                  value={String(settings[key])}
                  disabled={disabled}
                  onChange={(e) => onChangeSetting?.(key, e.target.value as ICMethodSettings[typeof key])}
                  className="flex-1 rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-slate-100 disabled:opacity-50"
                >
                  {(spec.options ?? []).map((opt) => (
                    <option key={opt} value={opt}>
                      {IC_SETTING_OPTION_LABELS[opt] ?? opt}
                    </option>
                  ))}
                </select>
              </>
            )}
            {!applicable && (
              <span className="shrink-0 text-slate-500" data-testid={`ic-setting-na-${key}`}>
                {IC_SETTING_NOT_APPLICABLE_LABEL}
              </span>
            )}
            <InfoTip text={settingTip(key, analysisMode, applicable)} label={label} />
          </div>
        );
      })}
    </div>
  );
}

const TOGGLES: Array<{ key: string; label: string; tier: 'L1' | 'L2' | 'L3'; tip: string }> = [
  { key: 'ic_calculation', label: 'IC 計算', tier: 'L1', tip: '核心 IC 計算流程，必須開啟；估計量見「方法選擇」之 IC 方法' },
  { key: 'ai_summary', label: 'AI Summary', tier: 'L1', tip: '自動產生摘要' },
  { key: 'ic_decay', label: 'IC Decay 分析', tier: 'L2', tip: '輸出不同 horizon 的 IC 衰減' },
  { key: 'grouped_ic', label: 'Grouped IC', tier: 'L2', tip: '分群情境下的 IC 表現' },
  { key: 'event_filtering', label: 'Event Filtering', tier: 'L2', tip: '依事件條件篩選樣本' },
  { key: 'turnover_analysis', label: 'Turnover Analysis', tier: 'L2', tip: '換手率統計' },
  { key: 'factor_return', label: '單標的因子擇時多空 (Module 1)', tier: 'L2', tip: '單標的因子擇時多空累積報酬與風險指標' },
  { key: 'trend_analysis', label: 'Trend Analysis (Module 3)', tier: 'L2', tip: '趨勢分析與綜合訊號' },
  { key: 'parameter_sensitivity', label: 'Parameter Sensitivity (Module 4)', tier: 'L2', tip: '參數穩健性分析' },
  { key: 'rolling_oos', label: 'Rolling OOS (Module 5)', tier: 'L2', tip: '滾動樣本外驗證' },
  { key: 'long_short_analysis', label: 'Long/Short Analysis (Module 8)', tier: 'L2', tip: '多空不對稱分析' },
  { key: 'feature_quality_diagnostics', label: 'Feature Quality Diag (Module 9)', tier: 'L2', tip: '品質診斷' },
  { key: 'net_ic_analysis', label: '成本拖累分析 (Module 10)', tier: 'L2', tip: '成本拖累(報酬空間),非淨 IC 混減' },
  {
    key: 'fdr_correction',
    label: 'FDR 多重比較校正',
    tier: 'L3',
    // tip 由 resolveToggleTip 依 mode 覆寫；此處為 longitudinal 預設
    tip: '啟用時 p 閘用 BH q（p_value_adj）；關閉時用 HAC raw p。預設 ON',
  },
  { key: 'marginal_ic', label: '邊際 IC／多因子組合', tier: 'L3', tip: '倖存因子 semi-partial 秩 IC（loo／sequential）＋等權組合 IC；預設 ON；關閉 ⇒ 報告節 disabled' },
  { key: 'factor_centrality', label: 'Factor Centrality/PCA (Module 2)', tier: 'L3', tip: 'PCA 因子中心性' },
  { key: 'factor_orthogonalization', label: 'Factor Orthogonalization (Module 6)', tier: 'L3', tip: '因子正交化' },
  { key: 'factor_exposure', label: 'Factor Exposure (Module 7)', tier: 'L3', tip: '因子曝險(單標的position重疊,非橫截面歸因)' },
];

/** 分模式誠實 FDR tip：xsec 無門檻行為（D-H），不得寫「關閉時用 raw p 閘」。 */
function resolveToggleTip(key: string, defaultTip: string, analysisMode?: string): string {
  if (key !== 'fdr_correction') {
    return defaultTip;
  }
  if (analysisMode === 'cross_sectional') {
    return 'Cross-sectional：計算並披露 t-stat/raw p/BH q（p_value_adj），不新增 p 閘（維持 ICIR 排序）。預設 ON';
  }
  return '啟用時 p 閘用 BH q（p_value_adj）；關閉時用 HAC raw p。預設 ON';
}

export default function FeatureTierPanel({
  featureTier,
  featureToggles,
  onChangeTier,
  onToggleFeature,
  analysisMode,
  settings = DEFAULT_IC_SETTINGS,
  onChangeSetting,
}: FeatureTierPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const enabledCount = useMemo(() => {
    return TOGGLES.filter((item) => Boolean(featureToggles[item.key])).length;
  }, [featureToggles]);

  const desc = featureTier === 'foundation'
    ? '基礎分析：IC/ICIR/篩選核心流程'
    : featureTier === 'intermediate'
      ? '進階分析：含深度分析常用模組'
      : featureTier === 'advanced'
        ? '完整分析：全部功能（含正交化、暴露度）'
        : '自訂分析：已手動調整功能開關';

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3">
      <div>
        <div className="text-sm font-medium text-slate-100 mb-2">分析深度</div>
        <div className="grid grid-cols-3 gap-2">
          <button type="button" onClick={() => onChangeTier('foundation')} className={`rounded-md px-3 py-2 text-sm ${featureTier === 'foundation' ? 'bg-emerald-500/30 text-emerald-100' : 'bg-white/5 text-slate-300'}`}>🟢 基礎</button>
          <button type="button" onClick={() => onChangeTier('intermediate')} className={`rounded-md px-3 py-2 text-sm ${featureTier === 'intermediate' ? 'bg-amber-500/30 text-amber-100' : 'bg-white/5 text-slate-300'}`}>🟡 中階</button>
          <button type="button" onClick={() => onChangeTier('advanced')} className={`rounded-md px-3 py-2 text-sm ${featureTier === 'advanced' ? 'bg-rose-500/30 text-rose-100' : 'bg-white/5 text-slate-300'}`}>🔴 高階</button>
        </div>
      </div>

      <div className="text-xs text-slate-400">{desc}</div>
      <div className="text-xs text-slate-300">已啟用 {enabledCount}/{TOGGLES.length} 項功能</div>

      <TooltipProvider>
        <MethodSettings settings={settings} onChangeSetting={onChangeSetting} analysisMode={analysisMode} />
      </TooltipProvider>

      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="text-xs text-cyan-300"
      >
        {expanded ? '▼ 收合自訂功能開關' : '▶ 自訂功能開關（進階）'}
      </button>

      {expanded && (
        <TooltipProvider>
          <div className="space-y-3 max-h-72 overflow-auto pr-1">
            {(['L1', 'L2', 'L3'] as const).map((level) => (
              <div key={level} className="rounded-md border border-white/10 bg-black/10 p-3">
                <div className="text-xs text-slate-300 mb-2">{level === 'L1' ? '🟢 基礎必用' : level === 'L2' ? '🟡 中階' : '🔴 高階'}</div>
                <div className="space-y-2">
                  {TOGGLES.filter((item) => item.tier === level).map((item) => {
                    const locked = LOCKED_KEYS.has(item.key);
                    return (
                      <label key={item.key} className={`flex items-center gap-2 text-xs ${locked ? 'text-slate-400' : 'text-slate-200'}`}>
                        <Checkbox
                          checked={Boolean(featureToggles[item.key])}
                          disabled={locked}
                          onCheckedChange={() => {
                            onToggleFeature(item.key);
                          }}
                        />
                        <span>{item.label}{locked ? ' [鎖定]' : ''}</span>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button type="button" className="text-slate-500 hover:text-slate-300">
                              <Info className="h-3 w-3" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            {resolveToggleTip(item.key, item.tip, analysisMode)}
                          </TooltipContent>
                        </Tooltip>
                      </label>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </TooltipProvider>
      )}
    </div>
  );
}
