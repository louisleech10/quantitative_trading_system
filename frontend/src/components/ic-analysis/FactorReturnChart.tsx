'use client';

import { FactorReturnData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * IC1C-FR-STOPGAP: C13 Factor Return 圖下架警示。
 * 錯位序列已下架,待 1c-FR 重建(grep 錨點: 1c-FR)。
 */
export const FACTOR_RETURN_UNAVAILABLE_NOTICE =
  '錯位序列已下架,待 1c-FR 重建';

interface FactorReturnChartProps {
  /** §U union;runtime 亦可能收到 legacy 有限 map(無 status 鍵) */
  data?: FactorReturnData | Record<string, unknown> | null;
  loading?: boolean;
  error?: string | null;
}

/** 是否為 §U unavailable 佔位 */
export function isFactorReturnUnavailableUnion(data: unknown): boolean {
  if (data == null || typeof data !== 'object' || Array.isArray(data)) {
    return false;
  }
  const obj = data as Record<string, unknown>;
  return obj.status === 'unavailable' && obj.value === null;
}

/**
 * 是否為 legacy 有限 payload(無 status 鍵的 feature map)。
 * 此形狀在 stopgap 前為 FactorReturnData;不得再繪圖。
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
 * 是否應顯示下架警示(union 佔位或 legacy 有限;禁 fallback 數值繪圖)。
 * 匯出供 vitest / mutation probe 使用。
 */
export function shouldShowFactorReturnUnavailableNotice(data: unknown): boolean {
  if (data == null) {
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
  return false;
}

/**
 * 是否允許繪製有限圖點。stopgap 恒 false(禁任何 fallback 數值)。
 * mutation M3 會模擬「恢復畫 legacy」路徑使此語意被破壞時測試轉紅。
 */
export function extractFactorReturnChartPoints(data: unknown): Array<{ name: string; value: number }> {
  // IC1C-FR-STOPGAP: 永不從 legacy / union 抽出有限點
  if (data == null) {
    return [];
  }
  if (shouldShowFactorReturnUnavailableNotice(data)) {
    return [];
  }
  // status===ok 亦不下畫有限值,待 1c-FR-FULL 重建正確序列後再開
  return [];
}

export default function FactorReturnChart({
  data,
  loading = false,
  error = null,
}: FactorReturnChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">C13 Factor Return</CardTitle>
          <CardDescription>Q1~Qn 平均收益</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            data-testid="factor-return-loading"
            className="h-[240px] flex items-center justify-center text-slate-400"
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
          <CardTitle className="text-base">C13 Factor Return</CardTitle>
          <CardDescription>Q1~Qn 平均收益</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="alert"
            data-testid="factor-return-error"
            className="h-[240px] flex items-center justify-center text-rose-300"
          >
            {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  // 缺鍵 / null → 與 Equity 一致:統一下架警示(禁「暫無資料」通用空態)
  if (data == null) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">C13 Factor Return</CardTitle>
          <CardDescription>Q1~Qn 平均收益</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            data-testid="factor-return-unavailable"
            role="status"
            className="h-[240px] flex items-center justify-center text-amber-300 text-center px-4"
          >
            {FACTOR_RETURN_UNAVAILABLE_NOTICE}
          </div>
        </CardContent>
      </Card>
    );
  }

  // union 佔位 / legacy 有限 / 非可繪 → 警示空態;禁 LineChart 數值
  if (
    shouldShowFactorReturnUnavailableNotice(data) ||
    extractFactorReturnChartPoints(data).length === 0
  ) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">C13 Factor Return</CardTitle>
          <CardDescription>Q1~Qn 平均收益</CardDescription>
        </CardHeader>
        <CardContent>
          <div
            data-testid="factor-return-unavailable"
            role="status"
            className="h-[240px] flex items-center justify-center text-amber-300 text-center px-4"
          >
            {FACTOR_RETURN_UNAVAILABLE_NOTICE}
          </div>
        </CardContent>
      </Card>
    );
  }

  // 不可達:stopgap 禁任何 fallback 數值路徑
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">C13 Factor Return</CardTitle>
        <CardDescription>Q1~Qn 平均收益</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          data-testid="factor-return-unavailable"
          role="status"
          className="h-[240px] flex items-center justify-center text-amber-300 text-center px-4"
        >
          {FACTOR_RETURN_UNAVAILABLE_NOTICE}
        </div>
      </CardContent>
    </Card>
  );
}
