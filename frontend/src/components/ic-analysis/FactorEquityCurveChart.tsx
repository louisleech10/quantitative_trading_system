'use client';

import { QuantileReturnData } from '@/lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * IC1C-FR-STOPGAP Task 2.2: Equity Curve 整圖下架。
 * producer monotonicity_tester 丟 timestamp,本圖按位置 high-low 相減——錯位同病。
 * 文案與 FactorReturnChart 一致;待 1c-FR 重建(grep 錨點: 1c-FR)。
 * producer 本體不動(修復歸 1c-FR-FULL)。
 */
export const FACTOR_EQUITY_UNAVAILABLE_NOTICE =
  '錯位序列已下架,待 1c-FR 重建';

interface FactorEquityCurveChartProps {
  /** 主流程 quantile_returns 仍可能傳入;stopgap 一律不繪 */
  data?: QuantileReturnData | null;
  featureName?: string | null;
  loading?: boolean;
  error?: string | null;
}

/**
 * stopgap: 恒不下畫 equity 點(禁位置相減 fallback)。
 * mutation M4 會模擬「恢復畫 legacy equity」使斷言轉紅。
 * 參數保留以維持 API 形狀(呼叫端仍傳 data);本體故意忽略。
 */
export function extractFactorEquityCurvePoints(
  data?: QuantileReturnData | null
): Array<{ bar_index: number; ls_spread: number }> {
  // 整圖下架:永不從 quantile_returns 位置相減出有限序列
  void data;
  return [];
}

export function shouldShowFactorEquityUnavailableNotice(
  data?: QuantileReturnData | null
): boolean {
  // 主流程與 deep 報告載入皆下架:有/無資料都警示(缺鍵走 empty)
  void data;
  return true;
}

export default function FactorEquityCurveChart({
  data,
  featureName,
  loading = false,
  error = null,
}: FactorEquityCurveChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Equity Curve（累積淨值）</CardTitle>
          <CardDescription>
            {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            data-testid="factor-equity-loading"
            className="h-[300px] flex items-center justify-center text-slate-400"
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
          <CardTitle className="text-base">Equity Curve（累積淨值）</CardTitle>
          <CardDescription>
            {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="alert"
            data-testid="factor-equity-error"
            className="h-[300px] flex items-center justify-center text-rose-300"
          >
            {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  // 缺鍵 / 無 data → empty(仍不下畫);有 data(含 legacy finite)→ 下架警示
  if (data == null) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Equity Curve（累積淨值）</CardTitle>
          <CardDescription>
            {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* 主流程缺 quantile 亦不得暗示可繪;統一下架文案 */}
          <div
            data-testid="factor-equity-unavailable"
            role="status"
            className="h-[300px] flex items-center justify-center text-amber-300 text-center px-4"
          >
            {FACTOR_EQUITY_UNAVAILABLE_NOTICE}
          </div>
        </CardContent>
      </Card>
    );
  }

  // legacy finite 或任何 quantile_returns → 警示空態;extract 恒 [] 防回歸
  void extractFactorEquityCurvePoints(data);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Equity Curve（累積淨值）</CardTitle>
        <CardDescription>
          {featureName ? `特徵：${featureName}` : '尚未選擇特徵'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          data-testid="factor-equity-unavailable"
          role="status"
          className="h-[300px] flex items-center justify-center text-amber-300 text-center px-4"
        >
          {FACTOR_EQUITY_UNAVAILABLE_NOTICE}
        </div>
      </CardContent>
    </Card>
  );
}
