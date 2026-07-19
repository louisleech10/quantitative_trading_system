'use client';

import { useMemo, type ReactNode } from 'react';
import {
  Line,
  LineChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { FactorReturnData, FactorReturnDataOk } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * IC1C-FR-FULL F3: 單標的因子擇時多空 — ok 路徑繪 ls_cumulative_sampled。
 * legacy 裸 map / unavailable → 空態警示不繪(grep 錨點: 1c-FR)。
 */
export const FACTOR_RETURN_CHART_TITLE = '單標的因子擇時多空';

/** 下架/legacy/unavailable 警示(仍含 1c-FR 錨點)。 */
export const FACTOR_RETURN_UNAVAILABLE_NOTICE =
  '錯位序列已下架,待 1c-FR 重建';

/** legacy 裸 map 專用警示(不繪有限數值)。 */
export const FACTOR_RETURN_LEGACY_REJECTED_NOTICE =
  'legacy 形狀已拒收(非 §U ok);單標的擇時序列不可用';

interface FactorReturnChartProps {
  /** §U union;runtime 亦可能收到 legacy 有限 map(無 status 鍵) */
  data?: FactorReturnData | Record<string, unknown> | null;
  loading?: boolean;
  error?: string | null;
}

export type FactorReturnChartPoint = {
  index: number;
  /** 各 feature 的累積報酬;key=feature name */
  [feature: string]: number | null;
};

/** 是否為 §U unavailable 佔位 */
export function isFactorReturnUnavailableUnion(data: unknown): boolean {
  if (data == null || typeof data !== 'object' || Array.isArray(data)) {
    return false;
  }
  const obj = data as Record<string, unknown>;
  return obj.status === 'unavailable' && obj.value === null;
}

/** §U ok value 五個 required metadata(fail-closed;缺任一 → 非 ok)。 */
export const FACTOR_RETURN_OK_SCHEMA_VERSION = 'fr_full_v1' as const;
export const FACTOR_RETURN_OK_SEMANTICS = 'single_asset_factor_timing_ls' as const;
export const FACTOR_RETURN_OK_QUANTILE_FIT = 'pit_expanding' as const;
export const FACTOR_RETURN_OK_RETURN_TRANSFORM = 'identity' as const;

/**
 * 是否為 §U ok union。
 * fail-closed 驗五鍵: schema_version / semantics / quantile_fit / return_transform / features(非空)。
 */
export function isFactorReturnOkUnion(data: unknown): data is FactorReturnDataOk {
  if (data == null || typeof data !== 'object' || Array.isArray(data)) {
    return false;
  }
  const obj = data as Record<string, unknown>;
  if (obj.status !== 'ok' || obj.reason != null) {
    return false;
  }
  const value = obj.value;
  if (value == null || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }
  const v = value as Record<string, unknown>;
  // 五個 required metadata — 字面量嚴格相等,禁任意 string 放寬
  if (v.schema_version !== FACTOR_RETURN_OK_SCHEMA_VERSION) {
    return false;
  }
  if (v.semantics !== FACTOR_RETURN_OK_SEMANTICS) {
    return false;
  }
  if (v.quantile_fit !== FACTOR_RETURN_OK_QUANTILE_FIT) {
    return false;
  }
  if (v.return_transform !== FACTOR_RETURN_OK_RETURN_TRANSFORM) {
    return false;
  }
  if (v.features == null || typeof v.features !== 'object' || Array.isArray(v.features)) {
    return false;
  }
  // features 非空
  if (Object.keys(v.features as Record<string, unknown>).length === 0) {
    return false;
  }
  return true;
}

/**
 * 是否為 legacy 有限 payload(無 status 鍵的 feature map)。
 * 此形狀在 stopgap 前為舊 FactorReturnData;不得再繪圖。
 */
export function isFactorReturnLegacyFinitePayload(data: unknown): boolean {
  if (data == null || typeof data !== 'object' || Array.isArray(data)) {
    return false;
  }
  const obj = data as Record<string, unknown>;
  if ('status' in obj) {
    return false;
  }
  return hasFiniteNumericLeaf(obj);
}

function hasFiniteNumericLeaf(value: unknown): boolean {
  if (typeof value === 'number') {
    return Number.isFinite(value);
  }
  if (Array.isArray(value)) {
    return value.some(hasFiniteNumericLeaf);
  }
  if (value != null && typeof value === 'object') {
    return Object.values(value as Record<string, unknown>).some(hasFiniteNumericLeaf);
  }
  return false;
}

/**
 * 是否應顯示空態警示(union 佔位或 legacy 有限;禁 fallback 數值繪圖)。
 */
export function shouldShowFactorReturnUnavailableNotice(data: unknown): boolean {
  if (data == null) {
    return true;
  }
  if (isFactorReturnOkUnion(data)) {
    return false;
  }
  if (isFactorReturnUnavailableUnion(data)) {
    return true;
  }
  if (isFactorReturnLegacyFinitePayload(data)) {
    return true;
  }
  // 其他有 status 但非 ok 可繪路徑、或非預期形狀 → 不畫數值
  if (typeof data === 'object' && data !== null && 'status' in data) {
    const status = (data as { status?: unknown }).status;
    if (status !== 'ok') {
      return true;
    }
  }
  // status===ok 但缺 schema/features → 拒繪
  return true;
}

/**
 * 從 §U ok union 抽出 ls_cumulative_sampled 圖點;legacy/unavailable → []。
 */
export function extractFactorReturnChartPoints(data: unknown): FactorReturnChartPoint[] {
  if (!isFactorReturnOkUnion(data)) {
    return [];
  }
  const features = data.value.features;
  const seriesEntries: Array<{ name: string; values: number[] }> = [];
  for (const [name, payload] of Object.entries(features)) {
    if (payload == null || typeof payload !== 'object') continue;
    const sampled = (payload as { ls_cumulative_sampled?: unknown }).ls_cumulative_sampled;
    if (!Array.isArray(sampled) || sampled.length === 0) continue;
    const values = sampled.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : NaN));
    if (!values.some((v) => Number.isFinite(v))) continue;
    seriesEntries.push({ name, values });
  }
  if (seriesEntries.length === 0) {
    return [];
  }
  const maxLen = Math.max(...seriesEntries.map((s) => s.values.length));
  const points: FactorReturnChartPoint[] = [];
  for (let i = 0; i < maxLen; i += 1) {
    const row: FactorReturnChartPoint = { index: i };
    for (const series of seriesEntries) {
      const raw = series.values[i];
      row[series.name] = typeof raw === 'number' && Number.isFinite(raw) ? raw : null;
    }
    points.push(row);
  }
  return points;
}

/** 取得 ok union 中有可繪 series 的 feature 名清單 */
export function listFactorReturnSeriesNames(data: unknown): string[] {
  if (!isFactorReturnOkUnion(data)) return [];
  const names: string[] = [];
  for (const [name, payload] of Object.entries(data.value.features)) {
    if (payload == null || typeof payload !== 'object') continue;
    const sampled = (payload as { ls_cumulative_sampled?: unknown }).ls_cumulative_sampled;
    if (Array.isArray(sampled) && sampled.some((v) => typeof v === 'number' && Number.isFinite(v))) {
      names.push(name);
    }
  }
  return names;
}

const SERIES_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f472b6', '#a78bfa', '#fb7185'];

function ChartShell({
  children,
  description,
}: {
  children: ReactNode;
  description?: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{FACTOR_RETURN_CHART_TITLE}</CardTitle>
        <CardDescription>
          {description ?? '單標的擇時累積多空報酬(ls_cumulative_sampled)'}
        </CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export default function FactorReturnChart({
  data,
  loading = false,
  error = null,
}: FactorReturnChartProps) {
  const chartPoints = useMemo(() => extractFactorReturnChartPoints(data), [data]);
  const seriesNames = useMemo(() => listFactorReturnSeriesNames(data), [data]);
  const isLegacy = isFactorReturnLegacyFinitePayload(data);

  if (loading) {
    return (
      <ChartShell>
        <div
          data-testid="factor-return-loading"
          className="h-[240px] flex items-center justify-center text-slate-400"
        >
          載入中...
        </div>
      </ChartShell>
    );
  }

  if (error) {
    return (
      <ChartShell>
        <div
          role="alert"
          data-testid="factor-return-error"
          className="h-[240px] flex items-center justify-center text-rose-300"
        >
          {error}
        </div>
      </ChartShell>
    );
  }

  // legacy 裸 map → 空態警示,不繪
  if (isLegacy) {
    return (
      <ChartShell description="legacy 形狀拒收">
        <div
          data-testid="factor-return-unavailable"
          role="status"
          className="h-[240px] flex items-center justify-center text-amber-300 text-center px-4"
        >
          {FACTOR_RETURN_LEGACY_REJECTED_NOTICE}
        </div>
      </ChartShell>
    );
  }

  // null / unavailable / 非 ok → 警示空態
  if (data == null || shouldShowFactorReturnUnavailableNotice(data) || chartPoints.length === 0) {
    return (
      <ChartShell>
        <div
          data-testid="factor-return-unavailable"
          role="status"
          className="h-[240px] flex items-center justify-center text-amber-300 text-center px-4"
        >
          {FACTOR_RETURN_UNAVAILABLE_NOTICE}
        </div>
      </ChartShell>
    );
  }

  // §U ok → 繪 ls_cumulative_sampled
  return (
    <ChartShell
      description={
        seriesNames.length === 1
          ? `特徵：${seriesNames[0]} · 單標的擇時累積多空`
          : `單標的擇時累積多空 · ${seriesNames.length} 特徵`
      }
    >
      <div data-testid="factor-return-chart" className="w-full">
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={chartPoints} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-white/10" />
            <XAxis dataKey="index" className="text-xs" />
            <YAxis className="text-xs" />
            <Tooltip
              contentStyle={{
                background: '#1a233a',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
              }}
            />
            {seriesNames.length > 1 && <Legend />}
            {seriesNames.map((name, i) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                name={name}
                stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                strokeWidth={2}
                dot={chartPoints.length <= 20}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </ChartShell>
  );
}
