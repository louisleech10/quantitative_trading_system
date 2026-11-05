'use client';

import type { DeepCandidateSelection } from '@/lib/types';

/**
 * ICPERF Task 0.4 ㊻（SPEC v5.81）：深度分析候選來源與逐欄篩選通過狀態之揭露。
 *
 * - 診斷模式（篩後無倖存、未手選）⇒ 橫幅「未通過篩選、Top_n僅供診斷參考」，並同屏揭露受檢特徵數、檢定數 N、
 *   倖存數、請求／實取 n、排序鍵、逐欄全域名次、原始 p 與全檢定族 BH 調整後 p（不在 Top_n 重算）。
 * - 手選含未通過者 ⇒ 橫幅列出未通過欄數，逐欄標示。
 * - 不顯示「期望偽發現數」（BH 調整後 p 非逐欄虛無後驗機率）。標示以文字表達，不只靠顏色。
 */
interface Props {
  selection: DeepCandidateSelection | null;
}

function fmtP(v: number | null): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return '—';
  return v < 1e-4 ? v.toExponential(2) : v.toFixed(4);
}

function passLabel(v: boolean | null): string {
  if (v === true) return '通過';
  if (v === false) return '未通過';
  return '未執行篩選';
}

const SOURCE_LABEL: Record<DeepCandidateSelection['source'], string> = {
  manual: '手選',
  survivors: '篩選倖存',
  diagnostic_top_n: '診斷 Top_n（無倖存）',
  unscreened_top_n: '診斷 Top_n（未執行篩選）',
};

export function DeepCandidateNotice({ selection }: Props) {
  if (!selection) return null;
  const nTests = selection.n_tests;
  const fdrMethod = selection.fdr && typeof selection.fdr.method === 'string' ? selection.fdr.method : null;
  const failed = selection.features.filter((f) => f.filter_passed === false).length;
  const showTable = selection.diagnostic_mode || failed > 0;
  const useMw = selection.p_family === 'mann_whitney';
  const n = selection.top_n_requested ?? selection.n_selected;

  return (
    <div
      role="status"
      data-testid="deep-candidate-notice"
      className={`glass-panel rounded-xl border p-4 space-y-3 ${
        selection.diagnostic_mode ? 'border-amber-400/50 text-amber-50' : 'border-white/10 text-gray-100'
      }`}
    >
      {selection.source === 'diagnostic_top_n' && (
        <p className="font-semibold" data-testid="deep-candidate-banner">
          ⚠ 未通過篩選、Top_{n}僅供診斷參考——本次 IC 篩選無任何因子通過，以下為依排序鍵取前 {n} 名之診斷結果，
          不代表顯著或有效因子（從大量未通過候選中取前段，其 IC／ICIR 有向上偏誤）。
        </p>
      )}
      {selection.source === 'unscreened_top_n' && (
        <p className="font-semibold" data-testid="deep-candidate-banner">
          ⚠ 未執行篩選、Top_{n}僅供診斷參考——本次未執行 IC 門檻篩選，以下為依排序鍵取前 {n} 名之診斷結果，
          不代表通過篩選或顯著（排名前段之 IC／ICIR 有向上偏誤）。
        </p>
      )}
      {!selection.diagnostic_mode && failed > 0 && (
        <p className="font-semibold" data-testid="deep-candidate-banner">
          ⚠ 所選 {selection.n_selected} 個特徵中有 {failed} 個未通過 IC 篩選，其深度分析結果僅供診斷參考。
        </p>
      )}
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-3">
        <div><dt className="inline text-gray-400">候選來源：</dt><dd className="inline">{SOURCE_LABEL[selection.source]}</dd></div>
        <div><dt className="inline text-gray-400">受檢特徵數：</dt><dd className="inline">{selection.n_ranked}</dd></div>
        {nTests !== null && nTests !== undefined && (
          <div>
            <dt className="inline text-gray-400">
              檢定數 N（{selection.p_family === 'mann_whitney' ? 'MW 檢定族' : 'IC 檢定族'}）：
            </dt>
            <dd className="inline">{nTests}</dd>
          </div>
        )}
        <div>
          <dt className="inline text-gray-400">通過篩選數：</dt>
          <dd className="inline">{selection.n_survivors === null ? '未執行篩選' : selection.n_survivors}</dd>
        </div>
        <div>
          <dt className="inline text-gray-400">請求／實取 n：</dt>
          <dd className="inline">{selection.top_n_requested ?? '—'}／{selection.n_selected}</dd>
        </div>
        <div><dt className="inline text-gray-400">排序鍵：</dt><dd className="inline">{selection.sort_key}</dd></div>
        {fdrMethod && (
          <div><dt className="inline text-gray-400">多重檢定校正：</dt><dd className="inline">{fdrMethod}</dd></div>
        )}
      </dl>
      {showTable && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs" data-testid="deep-candidate-table">
            <thead className="text-gray-400">
              <tr>
                <th className="px-2 py-1 text-left">全域名次</th>
                <th className="px-2 py-1 text-left">特徵</th>
                <th className="px-2 py-1 text-left">篩選</th>
                <th className="px-2 py-1 text-right">{useMw ? 'MW 原始 p' : '原始 p'}</th>
                <th className="px-2 py-1 text-right">{useMw ? 'MW BH 調整後 p' : 'BH 調整後 p（全檢定族）'}</th>
              </tr>
            </thead>
            <tbody>
              {selection.features.map((f) => (
                <tr key={f.feature_name} className="border-t border-white/5">
                  <td className="px-2 py-1">{f.global_rank ?? '—'}</td>
                  <td className="px-2 py-1 font-mono">{f.feature_name}</td>
                  <td className="px-2 py-1">{passLabel(f.filter_passed)}</td>
                  <td className="px-2 py-1 text-right">{fmtP(useMw ? f.mw_p_value : f.p_value)}</td>
                  <td className="px-2 py-1 text-right">{fmtP(useMw ? f.mw_p_value_adj : f.p_value_adj)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default DeepCandidateNotice;
