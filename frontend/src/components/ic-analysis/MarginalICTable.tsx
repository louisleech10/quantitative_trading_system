'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import SectionStatusNotice from '@/components/ic-analysis/SectionStatusNotice';
import { isMarginalICSection } from '@/lib/types';
import type { MarginalICSection, SectionStatusObject } from '@/lib/types';

/**
 * GAP-2 Task 5.1 — 邊際 IC／多因子組合唯讀表格（B5 最小鏡像；使用者 2026-08-18 白話閘裁定：表格＋toggle 預設開）。
 *
 * - 節缺席（舊報告）⇒ 不渲染；節 status!=="ok" ⇒ 只顯示 status／reason（SectionStatusNotice），不畫表。
 * - 恆顯示揭露小字：「倖存者選於同一測試段；本節數字為描述統計，非獨立驗證」（對應 independent_oos_validation=false；
 *   D3′：文案禁含「獨立 OOS 驗證」子字串——元件測試以 not.toContain 斷言）。
 * - oos_guarantees===false ⇒ 既有 degraded 樣式警語（rose）。
 * - 數值 toFixed(4)；ci95 null ⇒ 「—」；不畫圖表；100+ 列可捲動。
 */
export const MARGINAL_IC_DISCLOSURE = '倖存者選於同一測試段；本節數字為描述統計，非獨立驗證';

function fmt(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toFixed(digits);
}

function fmtCi(ci: [number, number] | null | undefined): string {
  if (!ci || ci.length !== 2) return '—';
  return `[${fmt(ci[0])}, ${fmt(ci[1])}]`;
}

export default function MarginalICTable({
  section,
}: {
  section?: MarginalICSection | SectionStatusObject | null;
}) {
  if (!section) return null;
  if (section.status !== 'ok' || !isMarginalICSection(section)) {
    return (
      <div data-testid="marginal-ic-status">
        <SectionStatusNotice
          title="邊際 IC／多因子組合"
          status={{ status: section.status, reason: section.reason ?? undefined }}
        />
      </div>
    );
  }

  const rows = Object.entries(section.per_feature);
  const composite = section.composite;
  const degraded = section.oos_guarantees === false;

  return (
    <Card className="glass-panel" data-testid="marginal-ic-table">
      <CardHeader>
        <CardTitle className="text-base">邊際 IC／多因子組合</CardTitle>
        <CardDescription>
          semi-partial 秩 IC（loo：條件於其他倖存者）；fit_scope={section.fit_scope ?? '—'}；n_test={section.n_test ?? '—'}
        </CardDescription>
        {degraded && (
          <div
            data-testid="marginal-ic-degraded"
            className="rounded-xl border border-rose-400/50 bg-rose-500/10 p-2 text-xs text-rose-100"
          >
            ⚠ Full-sample research-only（非 OOS 保證）：pass_class={section.pass_class ?? '—'}
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="max-h-96 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-slate-900/80 text-slate-300">
              <tr>
                <th className="px-2 py-1 text-left">feature</th>
                <th className="px-2 py-1 text-right">gross_ic</th>
                <th className="px-2 py-1 text-right">marginal_ic_loo</th>
                <th className="px-2 py-1 text-right">ci95</th>
                <th className="px-2 py-1 text-right">ic_retained_ratio</th>
                <th className="px-2 py-1 text-right">marginal_ic_train_insample</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-2 py-2 text-center text-slate-400" data-testid="marginal-ic-empty">
                    無倖存者
                  </td>
                </tr>
              ) : (
                rows.map(([name, row]) => (
                  <tr key={name} className="border-t border-slate-800/60" data-testid={`marginal-ic-row-${name}`}>
                    <td className="px-2 py-1 text-left font-mono">{name}</td>
                    <td className="px-2 py-1 text-right">{fmt(row.gross_ic)}</td>
                    <td className="px-2 py-1 text-right">
                      {row.status === 'ok' ? fmt(row.marginal_ic) : `${row.status}${row.reason ? `:${row.reason}` : ''}`}
                    </td>
                    <td className="px-2 py-1 text-right">{fmtCi(row.ci95)}</td>
                    <td className="px-2 py-1 text-right">{fmt(row.ic_retained_ratio)}</td>
                    <td className="px-2 py-1 text-right">{fmt(row.marginal_ic_train_insample)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="text-xs text-slate-300" data-testid="marginal-ic-composite">
          composite：
          {composite && composite.status === 'ok' ? (
            <>
              method={composite.method ?? '—'}；composite_ic={fmt(composite.composite_ic)}；top_train_single=
              {composite.top_train_single ?? '—'}（test IC {fmt(composite.top_train_single_test_ic)}）；delta=
              {fmt(composite.delta_vs_top_train_single)} ci95 {fmtCi(composite.delta_ci95)}
            </>
          ) : (
            <>
              {composite?.status ?? 'not_computed'}
              {composite?.reason ? `:${composite.reason}` : ''}
            </>
          )}
        </div>
        <p className="text-[11px] text-slate-400" data-testid="marginal-ic-disclosure">
          {MARGINAL_IC_DISCLOSURE}
        </p>
      </CardContent>
    </Card>
  );
}
