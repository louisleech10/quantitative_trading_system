'use client';

/**
 * 掃描結果瀏覽器（`SCANCUBE` Task 4.1）。
 *
 * ## 這個元件在解什麼
 *
 * 使用者原話：「不論IC分析是有幾種參數組合計算出來，不同參數組合計算出來的
 * 每個特徵的每個數據，在前端每個數據表格和圖像，都要能讓使用者能看到分析，
 * 無法一次呈現所有數據，也要有方式可以讓使者選擇要如何呈現和篩選」。
 *
 * 本票之前：掃描每格跑完整分析，但**只留一個事件筆數，其餘算完就丟**。
 *
 * ## 三個視圖
 *
 * 1. `cell` — 單格明細（欄頭可排序；原「單指標排行」已合併進來）
 * 2. `feature` — 單特徵跨格（k × h 矩陣）🔴 必附跨 h 之比較限制
 * 3. `charts` — 單格單特徵之圖表
 *
 * ## 🔴 三條規則
 *
 * - **只信 `stored`**，不以路徑存在與否推論（未保存時後端一律填 `null`）。
 * - **不做跨格排名**（SPEC §C-4：跨格取 max 是向上偏誤估計量）。
 * - **不一次抓全部**：一律走分頁；`total` 是篩選後真實總數。
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ScanCubeTierNotStored,
  getScanCubeCharts,
  getScanCubeManifest,
  getScanCubeRows,
} from '@/lib/api';
import {
  CHARTS_NOT_STORED_HEAD,
  CROSS_H_WARNING,
  EXCLUDED_SECTION_NOTE,
  SCAN_CUBE_DOCS,
} from '@/lib/scanCubeDocs';
import type {
  ICScanCubeCharts,
  ICScanCubeManifest,
  ICScanCubeRow,
} from '@/lib/types';

type ViewMode = 'cell' | 'feature' | 'charts';

interface Props {
  taskId?: string;
  /** 沒有掃描（單值模式）時不傳／傳 false ⇒ 整個區塊不 render。 */
  hasScan?: boolean;
}

/** 文案之唯一 render 點；元件內不得另寫說明字面。 */
function CubeDoc({ docKey }: { docKey: keyof typeof SCAN_CUBE_DOCS }) {
  const doc = SCAN_CUBE_DOCS[docKey];
  if (!doc) return null;
  return (
    <p className="mt-1 text-[11px] leading-relaxed text-slate-400"
       data-testid={`ic-cube-doc-${docKey}`}>
      {doc.what} {doc.effect}
    </p>
  );
}

export default function ScanCubeBrowser({ taskId, hasScan = true }: Props) {
  const [manifest, setManifest] = useState<ICScanCubeManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>('cell');

  const [selK, setSelK] = useState<number | null>(null);
  const [selH, setSelH] = useState<number | null>(null);
  const [feature, setFeature] = useState('');
  const [metric, setMetric] = useState('');
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDesc, setSortDesc] = useState(true);
  const [offset, setOffset] = useState(0);
  const [pageSize, setPageSize] = useState(50);

  const [rows, setRows] = useState<ICScanCubeRow[]>([]);
  const [total, setTotal] = useState(0);
  const [rowsBlocked, setRowsBlocked] = useState<Record<string, unknown> | null>(null);

  const [charts, setCharts] = useState<ICScanCubeCharts | null>(null);
  const [chartsBlocked, setChartsBlocked] = useState<Record<string, unknown> | null>(null);

  // ── manifest ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!taskId || !hasScan) { setManifest(null); return; }
    let cancelled = false;
    getScanCubeManifest(taskId)
      .then((m) => {
        if (cancelled) return;
        setManifest(m);
        setError(null);
        setSelK((prev) => (prev ?? m.k_axis[0] ?? null));
        setSelH((prev) => (prev ?? m.h_axis[0] ?? null));
        setMetric((prev) => prev || m.metrics[0] || '');
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : '讀取立方體失敗');
      });
    return () => { cancelled = true; };
  }, [taskId, hasScan]);

  // ── rows（cell／feature 兩個視圖共用，只是參數不同）────────────────────
  const loadRows = useCallback(async () => {
    if (!taskId || !manifest) return;
    // 🔴 只信 `stored`
    if (!manifest.tier_a.stored) { setRowsBlocked(manifest.tier_a as never); return; }
    try {
      const page = await getScanCubeRows(taskId, {
        k: view === 'cell' && selK !== null ? [selK] : undefined,
        h: view === 'cell' && selH !== null ? [selH] : undefined,
        feature: view === 'feature' ? (feature || undefined) : (feature || undefined),
        metric: view === 'feature' && metric ? [metric] : undefined,
        sort: view === 'cell' && sortField ? `${sortField}:${sortDesc ? 'desc' : 'asc'}` : undefined,
        offset,
        limit: pageSize,
      });
      setRows(page.rows);
      setTotal(page.total);
      setRowsBlocked(null);
    } catch (e: unknown) {
      if (e instanceof ScanCubeTierNotStored) setRowsBlocked(e.info);
      else setError(e instanceof Error ? e.message : '查詢失敗');
    }
  }, [taskId, manifest, view, selK, selH, feature, metric, sortField, sortDesc, offset, pageSize]);

  useEffect(() => { void loadRows(); }, [loadRows]);

  // ── charts ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (view !== 'charts' || !taskId || !manifest) return;
    // 🔴 Tier B 未保存 ⇒ **不發請求**（省一趟必然 409 的往返）
    if (!manifest.tier_b.stored) { setChartsBlocked(manifest.tier_b as never); return; }
    if (selK === null || selH === null || !feature) return;
    let cancelled = false;
    getScanCubeCharts(taskId, selK, selH, feature)
      .then((c) => { if (!cancelled) { setCharts(c); setChartsBlocked(null); } })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof ScanCubeTierNotStored) setChartsBlocked(e.info);
        else setError(e instanceof Error ? e.message : '讀取圖表失敗');
      });
    return () => { cancelled = true; };
  }, [view, taskId, manifest, selK, selH, feature]);

  const metrics = manifest?.metrics ?? [];
  const shownFrom = total === 0 ? 0 : offset + 1;
  const shownTo = Math.min(offset + pageSize, total);

  const crossGrid = useMemo(() => {
    if (view !== 'feature' || !manifest || !metric) return null;
    const byCell = new Map<string, ICScanCubeRow>();
    rows.forEach((r) => byCell.set(`${r.k}|${r.h}`, r));
    return { byCell };
  }, [view, manifest, metric, rows]);

  if (!taskId || !hasScan) return null;

  return (
    <section className="mt-4 rounded-2xl border border-slate-700/60 bg-slate-900/40 p-3"
             data-testid="ic-cube">
      <h4 className="text-sm font-medium text-slate-100">掃描結果瀏覽器</h4>

      {error && (
        <p className="mt-1 text-[11px] text-rose-300" data-testid="ic-cube-error">{error}</p>
      )}

      {/* ── 視圖切換 ─────────────────────────────────────────────────── */}
      <label className="mt-2 block text-xs text-slate-200">
        <span className="mb-1 block">看法</span>
        <select
          data-testid="ic-cube-view"
          data-doc="cube_view"
          value={view}
          onChange={(e) => { setView(e.target.value as ViewMode); setOffset(0); }}
          className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-xs text-slate-100"
        >
          <option value="cell">單格明細（一個 k,h 的所有特徵）</option>
          <option value="feature">單特徵跨格（一個特徵在所有 k,h）</option>
          <option value="charts">圖表（一個 k,h 的一個特徵）</option>
        </select>
      </label>
      <CubeDoc docKey="cube_view" />

      {/* ── 選格 ─────────────────────────────────────────────────────── */}
      {view !== 'feature' && manifest && (
        <div className="mt-2 flex flex-wrap gap-3">
          <label className="text-[11px] text-slate-300">
            k
            <select
              data-testid="ic-cube-k" data-doc="cube_cell"
              value={selK ?? ''} onChange={(e) => { setSelK(Number(e.target.value)); setOffset(0); }}
              className="ml-1 rounded bg-slate-800 px-1 py-0.5 text-slate-100"
            >
              {manifest.k_axis.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label className="text-[11px] text-slate-300">
            h
            <select
              data-testid="ic-cube-h" data-doc="cube_cell"
              value={selH ?? ''} onChange={(e) => { setSelH(Number(e.target.value)); setOffset(0); }}
              className="ml-1 rounded bg-slate-800 px-1 py-0.5 text-slate-100"
            >
              {manifest.h_axis.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
        </div>
      )}
      {view !== 'feature' && <CubeDoc docKey="cube_cell" />}

      {/* ── 篩選 ─────────────────────────────────────────────────────── */}
      <div className="mt-2 flex flex-wrap gap-3">
        <label className="text-[11px] text-slate-300">
          特徵名含
          <input
            type="text" data-testid="ic-cube-feature" data-doc="cube_feature"
            value={feature} onChange={(e) => { setFeature(e.target.value); setOffset(0); }}
            className="ml-1 w-40 rounded bg-slate-800 px-1 py-0.5 text-slate-100"
          />
        </label>
        {view === 'feature' && (
          <label className="text-[11px] text-slate-300">
            比哪個指標
            <select
              data-testid="ic-cube-metric" data-doc="cube_metric"
              value={metric} onChange={(e) => setMetric(e.target.value)}
              className="ml-1 rounded bg-slate-800 px-1 py-0.5 text-slate-100"
            >
              {metrics.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </label>
        )}
        <label className="text-[11px] text-slate-300">
          每頁
          <input
            type="number" data-testid="ic-cube-page-size" data-doc="cube_page_size"
            min={1} value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setOffset(0); }}
            className="ml-1 w-20 rounded bg-slate-800 px-1 py-0.5 text-slate-100"
          />
        </label>
      </div>
      <CubeDoc docKey="cube_feature" />
      {view === 'feature' && <CubeDoc docKey="cube_metric" />}
      <CubeDoc docKey="cube_page_size" />

      {/* ── Tier A 未保存 ─────────────────────────────────────────────── */}
      {rowsBlocked && (
        <p className="mt-2 text-[11px] text-amber-200/90" data-testid="ic-cube-not-saved">
          指標表沒有保存下來（原因代號 <code>{String(rowsBlocked.reason)}</code>）——
          這次掃描的資料量超過上限。縮小 k／h 的掃描範圍後重跑即可取得。
        </p>
      )}

      {/* ── 視圖 1／2：表格 ───────────────────────────────────────────── */}
      {!rowsBlocked && view !== 'charts' && (
        <>
          {view === 'feature' && (
            <p className="mt-2 text-[11px] leading-relaxed text-amber-200/90"
               data-testid="ic-cube-cross-h-warning">
              {CROSS_H_WARNING}
            </p>
          )}
          <p className="mt-2 text-[11px] text-slate-400" data-testid="ic-cube-paging">
            共 {total} 筆，正在看 {shownFrom}–{shownTo}
          </p>
          <div className="mt-1 flex gap-2">
            <button type="button" data-testid="ic-cube-prev"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - pageSize))}
                    className="rounded border border-slate-700 px-2 py-0.5 text-[11px] text-slate-200 disabled:opacity-40">
              上一頁
            </button>
            <button type="button" data-testid="ic-cube-next"
                    disabled={shownTo >= total}
                    onClick={() => setOffset(offset + pageSize)}
                    className="rounded border border-slate-700 px-2 py-0.5 text-[11px] text-slate-200 disabled:opacity-40">
              下一頁
            </button>
          </div>

          {view === 'cell' ? (
            <div className="mt-2 overflow-x-auto">
              <table className="text-[11px] text-slate-200" data-testid="ic-cube-cell-table">
                <thead>
                  <tr>
                    <th className="px-2 text-left font-normal text-slate-400">feature</th>
                    {metrics.map((m) => (
                      <th key={m} className="px-2 text-left font-normal">
                        <button
                          type="button"
                          data-testid={`ic-cube-sort-${m}`}
                          onClick={() => {
                            if (sortField === m) setSortDesc(!sortDesc);
                            else { setSortField(m); setSortDesc(true); }
                            setOffset(0);
                          }}
                          className="text-slate-400 underline underline-offset-2"
                        >
                          {m}{sortField === m ? (sortDesc ? ' ↓' : ' ↑') : ''}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={`${r.k}-${r.h}-${r.feature_name}`}
                        data-testid={`ic-cube-row-${r.feature_name}`}>
                      <td className="px-2">{r.feature_name}</td>
                      {metrics.map((m) => (
                        <td key={m} className="px-2">{fmt(r[m])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="mt-2 overflow-x-auto">
              <table className="text-[11px] text-slate-200" data-testid="ic-cube-cross-table">
                <thead>
                  <tr>
                    <th className="px-2 text-left font-normal text-slate-400">k \ h</th>
                    {(manifest?.h_axis ?? []).map((h) => (
                      <th key={h} className="px-2 text-left font-normal text-slate-400">h={h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(manifest?.k_axis ?? []).map((k) => (
                    <tr key={k}>
                      <th className="px-2 text-left font-normal text-slate-400">k={k}</th>
                      {(manifest?.h_axis ?? []).map((h) => (
                        <td key={h} className="px-2"
                            data-testid={`ic-cube-cross-${k}-${h}`}>
                          {fmt(crossGrid?.byCell.get(`${k}|${h}`)?.[metric] ?? null)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* ── 視圖 3：圖表 ─────────────────────────────────────────────── */}
      {view === 'charts' && (
        <div className="mt-2">
          {chartsBlocked ? (
            <div className="text-[11px] text-amber-200/90" data-testid="ic-cube-charts-not-stored">
              <p>{CHARTS_NOT_STORED_HEAD}</p>
              <p className="mt-1">
                原因代號 <code>{String(chartsBlocked.reason)}</code>
                {fitsHintLine(chartsBlocked)}
              </p>
            </div>
          ) : !feature ? (
            <p className="text-[11px] text-slate-400" data-testid="ic-cube-charts-pick-feature">
              先在上面的「特徵名含」填入完整特徵名，才能顯示該格該特徵的圖表。
            </p>
          ) : charts ? (
            <div data-testid="ic-cube-charts">
              {(manifest?.chart_sections ?? []).map((name) => (
                <details key={name} className="mt-1 rounded border border-slate-700/60 p-2">
                  <summary className="cursor-pointer text-[11px] text-slate-300"
                           data-testid={`ic-cube-section-${name}`}>
                    {name}
                  </summary>
                  <pre className="mt-1 max-h-64 overflow-auto text-[10px] text-slate-400">
                    {JSON.stringify(charts.sections[name] ?? null, null, 1)}
                  </pre>
                </details>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-slate-400">載入中…</p>
          )}
        </div>
      )}

      {/* ── 被排除的節：必須明講，不得靜默省略 ─────────────────────────── */}
      {(manifest?.excluded_sections?.length ?? 0) > 0 && (
        <p className="mt-2 text-[11px] leading-relaxed text-slate-400"
           data-testid="ic-cube-corr-excluded">
          {EXCLUDED_SECTION_NOTE}
        </p>
      )}
    </section>
  );
}

function fmt(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return Number.isFinite(value) ? value.toFixed(4) : '—';
  return String(value);
}

/** `fits_hint` 由後端**實測**導出；前端只負責把數字唸出來，不自己算。 */
function fitsHintLine(info: Record<string, unknown>): string {
  const hint = info?.fits_hint as
    | { examples?: { cells: number; features_per_cell: number }[] }
    | null
    | undefined;
  const examples = hint?.examples ?? [];
  if (!examples.length) return '';
  const parts = examples.map((e) => `${e.cells} 格 × ${e.features_per_cell} 特徵`);
  return `。以這次的資料量估，存得下的規模約是：${parts.join('、')}`;
}
