'use client';

import { useMemo, useState } from 'react';
import { Scatter, ScatterChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ZAxis, ReferenceLine } from 'recharts';
import {
  NetICAnalysisData,
  NetICFeatureCostEnabled,
  NetICFeatureResult,
} from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * 成本語意註記(Task 3.1):per-rebalance、未年化、禁跨 TF 直比。
 * gross-only 與 cost-enabled 皆顯示(啟用成本時亦同語意;未啟用時為預告)。
 * 對齊後端 cost_semantics=`per_rebalance_not_annualized`(含 per_rebalance 供靜態 grep)。
 */
/** 後端 cost_semantics 字面值錨點(不得年化;grep 驗 per_rebalance)。 */
export const NET_IC_COST_SEMANTICS = 'per_rebalance_not_annualized' as const;

/** 面向使用者繁中說明;括號內保留 per-rebalance 可讀寫法。 */
export const NET_IC_COST_SEMANTICS_NOTE =
  '成本為每次再平衡(per-rebalance),未年化;不同 timeframe 間不可直接比較';

interface NetICChartProps {
  data?: NetICAnalysisData;
  /** loading 態(由父層傳) */
  loading?: boolean;
  /** error 態文案 */
  error?: string | null;
}

function isSkippedFeature(
  feat: NetICFeatureResult
): feat is Extract<NetICFeatureResult, { skipped: true }> {
  return 'skipped' in feat && feat.skipped === true;
}

function isCostEnabledFeature(feat: NetICFeatureResult): feat is NetICFeatureCostEnabled {
  if (isSkippedFeature(feat)) return false;
  return (
    typeof (feat as NetICFeatureCostEnabled).cost_drag_return === 'number' ||
    Array.isArray((feat as NetICFeatureCostEnabled).cost_sensitivity)
  );
}

function hasFiniteTurnover(feat: NetICFeatureResult): boolean {
  if (isSkippedFeature(feat)) return false;
  return typeof feat.turnover === 'number' && Number.isFinite(feat.turnover);
}

function hasFiniteGrossIc(feat: NetICFeatureResult): boolean {
  if (isSkippedFeature(feat)) return false;
  return typeof feat.gross_ic === 'number' && Number.isFinite(feat.gross_ic);
}

export default function NetICChart({ data, loading = false, error = null }: NetICChartProps) {
  const features =
    data && !data.skipped && data.features ? data.features : ({} as Record<string, NetICFeatureResult>);
  const entries = Object.entries(features);

  // scenario 選項只從後端 cost_sensitivity 讀,禁硬編 [1,3,5,10,20]
  const scenarioOptions = useMemo(() => {
    const bpsSet = new Set<number>();
    for (const [, feat] of entries) {
      if (isSkippedFeature(feat) || !isCostEnabledFeature(feat)) continue;
      for (const row of feat.cost_sensitivity || []) {
        if (typeof row.cost_bps === 'number' && Number.isFinite(row.cost_bps)) {
          bpsSet.add(row.cost_bps);
        }
      }
      if (typeof feat.cost_bps === 'number' && Number.isFinite(feat.cost_bps)) {
        bpsSet.add(feat.cost_bps);
      }
    }
    return Array.from(bpsSet).sort((a, b) => a - b);
  }, [entries]);

  const [selectedBps, setSelectedBps] = useState<number | null>(null);
  const activeBps = selectedBps ?? scenarioOptions[0] ?? null;

  const allSkipped =
    entries.length > 0 && entries.every(([, feat]) => isSkippedFeature(feat));
  const hasAnyCost = entries.some(
    ([, feat]) => !isSkippedFeature(feat) && isCostEnabledFeature(feat)
  );
  const missingTurnoverOnly =
    entries.length > 0 &&
    entries.every(([, feat]) => isSkippedFeature(feat) || !hasFiniteTurnover(feat)) &&
    !allSkipped;

  const chartData = useMemo(() => {
    return entries
      .filter(([, value]) => !isSkippedFeature(value))
      .filter(([, value]) => hasFiniteTurnover(value))
      // R2-NEW-1:缺 gross_ic / 非有限 → 不造 0,直接剔除;全剔除→empty 態
      .filter(([, value]) => hasFiniteGrossIc(value))
      .map(([feature, value]) => {
        const nonSkipped = value as Exclude<NetICFeatureResult, { skipped: true }>;
        const costFeat = isCostEnabledFeature(nonSkipped) ? nonSkipped : null;
        const scenario =
          activeBps != null && costFeat
            ? (costFeat.cost_sensitivity || []).find((item) => item.cost_bps === activeBps)
            : undefined;
        const costDrag =
          scenario?.cost_drag_return ??
          (costFeat && typeof costFeat.cost_drag_return === 'number'
            ? costFeat.cost_drag_return
            : undefined);
        return {
          feature,
          gross_ic: nonSkipped.gross_ic,
          cost_drag_return: costDrag,
          turnover: nonSkipped.turnover as number,
        };
      })
      .filter((row) =>
        hasAnyCost ? typeof row.cost_drag_return === 'number' : true
      );
  }, [entries, activeBps, hasAnyCost]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">成本拖累(報酬空間)</CardTitle>
          <CardDescription
            data-testid="netic-cost-semantics-note"
            title={NET_IC_COST_SEMANTICS_NOTE}
          >
            {NET_IC_COST_SEMANTICS_NOTE}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            data-testid="netic-loading"
            className="h-[260px] flex items-center justify-center text-slate-400"
          >
            載入中...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">成本拖累(報酬空間)</CardTitle>
          <CardDescription
            data-testid="netic-cost-semantics-note"
            title={NET_IC_COST_SEMANTICS_NOTE}
          >
            {NET_IC_COST_SEMANTICS_NOTE}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="alert"
            data-testid="netic-error"
            className="h-[260px] flex items-center justify-center text-rose-300"
          >
            {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || entries.length === 0 || allSkipped || missingTurnoverOnly || chartData.length === 0) {
    const emptyMsg = allSkipped
      ? '全部特徵 SKIPPED'
      : missingTurnoverOnly || chartData.length === 0
        ? '無資料'
        : '暫無成本拖累資料';
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">成本拖累(報酬空間)</CardTitle>
          <CardDescription>
            {hasAnyCost ? 'Gross IC vs 成本拖累' : 'Gross IC（未啟用成本）'}
          </CardDescription>
          <p
            data-testid="netic-cost-semantics-note"
            title={NET_IC_COST_SEMANTICS_NOTE}
            className="text-xs text-slate-400 mt-1"
          >
            {NET_IC_COST_SEMANTICS_NOTE}
          </p>
        </CardHeader>
        <CardContent>
          <div
            data-testid="netic-empty"
            className="h-[260px] flex items-center justify-center text-slate-400"
          >
            {emptyMsg}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">成本拖累(報酬空間)</CardTitle>
            <CardDescription>
              {hasAnyCost
                ? 'Gross IC vs cost_drag_return（情境自後端 cost_sensitivity）'
                : 'Gross-only 模式（未啟用成本）'}
            </CardDescription>
            <p
              data-testid="netic-cost-semantics-note"
              title={NET_IC_COST_SEMANTICS_NOTE}
              className="text-xs text-slate-400 mt-1"
            >
              {NET_IC_COST_SEMANTICS_NOTE}
            </p>
          </div>
          {hasAnyCost && scenarioOptions.length > 0 && (
            <select
              value={activeBps ?? ''}
              onChange={(event) => setSelectedBps(Number(event.target.value))}
              className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-slate-200"
              data-testid="netic-scenario-select"
            >
              {scenarioOptions.map((item) => (
                <option key={item} value={item}>
                  {item} bps
                </option>
              ))}
            </select>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <ScatterChart>
            <XAxis dataKey="gross_ic" name="Gross IC" type="number" />
            {hasAnyCost ? (
              <YAxis dataKey="cost_drag_return" name="cost_drag_return" type="number" />
            ) : (
              <YAxis dataKey="gross_ic" name="Gross IC" type="number" hide />
            )}
            <ZAxis dataKey="turnover" range={[40, 300]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const row = payload[0]?.payload as {
                  feature?: string;
                  gross_ic?: number;
                  cost_drag_return?: number;
                  turnover?: number;
                };
                return (
                  <div className="rounded border border-white/10 bg-slate-900/95 px-2 py-1.5 text-xs text-slate-100 shadow">
                    {row.feature != null && <div className="font-medium mb-0.5">{row.feature}</div>}
                    {typeof row.gross_ic === 'number' && (
                      <div>Gross IC: {row.gross_ic.toFixed(4)}</div>
                    )}
                    {typeof row.cost_drag_return === 'number' && (
                      <div>cost_drag_return: {row.cost_drag_return.toFixed(6)}</div>
                    )}
                    {typeof row.turnover === 'number' && (
                      <div>turnover: {row.turnover.toFixed(4)}</div>
                    )}
                    <div
                      className="mt-1 max-w-[220px] text-slate-400 leading-snug"
                      data-testid="netic-tooltip-semantics"
                    >
                      {NET_IC_COST_SEMANTICS_NOTE}
                    </div>
                  </div>
                );
              }}
            />
            <ReferenceLine segment={[{ x: -1, y: -1 }, { x: 1, y: 1 }]} stroke="#94a3b8" strokeDasharray="3 3" />
            <Scatter data={chartData} fill="#38bdf8" />
          </ScatterChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
