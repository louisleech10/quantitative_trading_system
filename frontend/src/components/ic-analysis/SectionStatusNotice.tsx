'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { SectionStatusObject } from '@/lib/types';

/**
 * ICHC Task 3.2：節級 capability status 的契約化文案（取代通用「暫無數據」）。
 * status 值域＝契約檔 capability_status；未知值 fallback 通用文案＋console.warn。
 */
const STATUS_TEXT: Record<string, string> = {
  not_applicable: '此分析模式不適用本圖表',
  not_computed: '本次分析未產生此資料',
  computation_failed: '此分析計算失敗',
  disabled: '此分析已停用',
  unavailable: '此分析目前不可用',
};

const REASON_TEXT: Record<string, string> = {
  cross_sectional_mode: '橫截面模式只計算逐期 IC 與跨標的矩陣',
  turnover_disabled: '換手率分析已停用',
  insufficient_events: '事件樣本不足',
};

export default function SectionStatusNotice({
  title,
  status,
}: {
  title: string;
  status: SectionStatusObject;
}) {
  const main = STATUS_TEXT[status.status];
  if (!main) {
    // 未知 status 值：契約外——fallback 並警告（Task 3.2 邊界）
    console.warn(`[SectionStatusNotice] unknown capability status: ${status.status}`);
  }
  const reason = status.reason ? REASON_TEXT[status.reason] ?? status.reason : null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        {reason && <CardDescription>{reason}</CardDescription>}
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-center h-[240px] text-slate-400">
          {main ?? '暫無數據'}
        </div>
      </CardContent>
    </Card>
  );
}
