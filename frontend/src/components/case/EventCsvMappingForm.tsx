'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  EventImportRejectedError,
  fetchLookaheadDeclarationPreview,
  uploadEventCsvMapping,
} from '@/lib/api';
import LookaheadDeclarationFields from '@/components/case/LookaheadDeclarationFields';
import {
  buildDeclarationPayload,
  initialDeclaredWindowBars,
  validateDeclaration,
  type LookaheadDeclarationPreview,
} from '@/lib/lookaheadDeclaration';
import { columnValues, countDeclaredLabels, parseCsvText, type ParsedCsv } from '@/lib/csvPreview';
import { computeExportCounts } from '@/lib/exportCounts';
import { scanBinaryColumns } from '@/lib/suspiciousBinaryColumns';
import { inspectEventIdNormalization } from '@/lib/eventIdNormalization';
import EventDimensionFields, { type EventDimensionValues } from '@/components/case/EventDimensionFields';
import { dimensionBatchDefaults, dimensionDefaultConflicts } from '@/lib/eventDimensions';
import type { EventImportRejected, EventImportResponse } from '@/lib/types';

/**
 * GAP-3 UX Task 1.5 — CSV 上傳／預覽／逐項對映 UI（SPEC L1578–1587）。
 *
 * 選檔 → 顯示前 5 列預覽與全部欄名 → 逐項下拉對映 → 填批次預設 → 顯示
 * 「你聲明的正例 X 筆／反例 Y 筆」並**要求勾選確認** → 送出到 `POST /case/import-events/csv`。
 *
 * 🔴 **不得預設任何欄位對映**（A-4′）：所有下拉初始值都是「未選」，
 *    唯一的初始值來源是 `scanBinaryColumns().suggestedLabelColumn`（恆為 `null`＝不推斷）。
 * 🔴 文案**禁用「label 正確」字樣**（D-1：語意正確性不可機械證明，只能說「你聲明」）。
 * 🔴 未勾確認 ⇒ **一個網路動作都不得發生**（執行期計數，不是把按鈕設成 disabled 就算數）。
 * 🔴 契約檢核**全部在後端**：本元件之預覽／警示只是「先講清楚」，拒收之權威一律是後端。
 */

/**
 * 可對映之契約欄名（＝契約 `required_fields` 中型別非 object 者，依契約順序）。
 *
 * 🔴 本清單由 `gap3_csv_mapping_form.test.tsx` 讀契約檔**機械對證**（同 `EVENT_ID_TEMPLATE` 之作法）
 *    ⇒ 契約增刪欄位而這裡沒跟上會轉紅，不靠紀律維持。`label_definition` 為 object，
 *    不能由單一 CSV 儲存格承載，改由批次預設提供。
 */
export const MAPPABLE_CONTRACT_FIELDS = [
  'event_id', 'symbol', 'timeframe', 't0', 'decision_offset_bars', 'entry_price_semantic',
  'direction', 'scenario', 'label', 'control_kind', 'source_file_digest', 'data_snapshot_digest',
] as const;

/** 送出前必須有值（自 CSV 對映或批次預設）之四欄——少了就連預覽都算不出來。 */
const PREVIEW_REQUIRED_FIELDS = ['symbol', 'timeframe', 't0', 'label'] as const;

interface Props {
  onImported?: (result: EventImportResponse) => void;
}

const EMPTY_PARSED: ParsedCsv = {
  columns: [], previewRows: [], rows: [], duplicateNames: [], raggedRows: [],
  unsupportedLineEnding: false,
};

export default function EventCsvMappingForm({ onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<ParsedCsv>(EMPTY_PARSED);
  /** {契約欄名: CSV **欄序**字串}；'' ＝未選。用欄序而非欄名，同名欄才分得開。 */
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [defaultsText, setDefaultsText] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  /** 勾選確認之**當下**時間（不是送出時間）——Task 1.6 記的是「你什麼時候確認的」。 */
  const [confirmedAt, setConfirmedAt] = useState<string | null>(null);
  /** 殘留 `R-B2-1`：由後端依契約模板產生 `event_id`（opt-in，預設關＝不推斷）。 */
  const [deriveEventId, setDeriveEventId] = useState(false);
  const [validateOnly, setValidateOnly] = useState(false);
  const [problems, setProblems] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<EventImportResponse | null>(null);
  const [rejected, setRejected] = useState<EventImportRejected | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<LookaheadDeclarationPreview | null>(null);
  const [declared, setDeclared] = useState<Record<string, number>>({});
  const [acknowledged, setAcknowledged] = useState(false);
  /**
   * GAP-3 UX Task 7.1：五個批次維度之下拉。
   * 🔴 初始值一律**未選**（A-4′）：本頁之 `scenario`／`control_kind` 也可以由 CSV 欄對映，
   *    帶預設值會靜默蓋掉對映；未選＝不寫該鍵 ⇒ 既有匯入流程逐位元不變。
   */
  const [dims, setDims] = useState<EventDimensionValues>({
    scenario: '', control_kind: '', entry_price_semantic: '', label_return_mode: '', decision_offset_bars: '',
  });

  const columnIndexOf = (field: string): number => {
    const raw = mapping[field];
    return raw === undefined || raw === '' ? -1 : Number(raw);
  };
  const columnNameOf = (field: string): string | null => {
    const idx = columnIndexOf(field);
    return idx >= 0 ? (parsed.columns[idx]?.name ?? null) : null;
  };

  /** {契約欄名: CSV 欄名}——只含已選項（未選者不送，後端據此判 `column_mapping_missing`）。 */
  const columnMapping = useMemo(() => {
    const out: Record<string, string> = {};
    for (const field of MAPPABLE_CONTRACT_FIELDS) {
      const idx = mapping[field] === undefined || mapping[field] === '' ? -1 : Number(mapping[field]);
      const name = idx >= 0 ? parsed.columns[idx]?.name : undefined;
      if (name !== undefined) out[field] = name;
    }
    return out;
  }, [mapping, parsed]);

  const parsedDefaults = useMemo((): { ok: boolean; value: Record<string, unknown> | null } => {
    if (defaultsText.trim() === '') return { ok: true, value: null };
    try {
      const v = JSON.parse(defaultsText);
      if (v === null || typeof v !== 'object' || Array.isArray(v)) return { ok: false, value: null };
      return { ok: true, value: v as Record<string, unknown> };
    } catch {
      return { ok: false, value: null };
    }
  }, [defaultsText]);

  /**
   * 送給後端之批次預設 ＝「JSON 文字框」∪「Task 7.1 之五維度下拉（已選者）」。
   * 🔴 兩者同時給同一欄時**不合併也不擇一**，由 `submitProblems()` 阻擋（見 `dimensionDefaultConflicts`）。
   */
  const effectiveDefaults = useMemo((): Record<string, unknown> | null => {
    if (!parsedDefaults.ok) return null;
    const merged = dimensionBatchDefaults(dims, parsedDefaults.value ?? undefined);
    return Object.keys(merged).length > 0 ? merged : null;
  }, [parsedDefaults, dims]);
  const dimsKey = JSON.stringify(dims);

  const labelColumnName = columnNameOf('label');
  /**
   * 🔴 Task 2.3：正例／反例之筆數一律由 `computeExportCounts()` 算——它是
   * Task 1.5 上傳確認、2.1 篩選面板、4.1b／7.3 動態揭露之**同一組事實的唯一來源**。
   * 這裡把「CSV 的 label 儲存格」轉成該函式吃的形狀（判讀規則仍是 `0`／`1` 不猜）。
   */
  const labelCounts = useMemo(() => {
    const cells = columnValues(parsed, columnIndexOf('label'));
    const raw = countDeclaredLabels(cells);
    const counts = computeExportCounts(
      cells.map((cell) => ({ cell })),
      [],
      (row) => {
        const s = String((row as { cell: string }).cell).trim();
        return s === '1' ? true : s === '0' ? false : null;
      },
    );
    return { positive: counts.X, negative: counts.Y, blank: raw.blank, unreadable: raw.unreadable };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parsed, mapping]);

  /** Task 1.7：可疑欄警示（只警示不阻擋、不持久化）。 */
  const binaryScan = useMemo(
    () => scanBinaryColumns(parsed.columns.map((c) => c.name), parsed.rows, labelColumnName),
    [parsed, labelColumnName],
  );

  /** 殘留 `R-B2-1`：秒級 t0 ⇒ 先把契約要求的毫秒版 `event_id` 算給使用者看。 */
  const idReport = useMemo(() => {
    const idx = {
      eventId: columnIndexOf('event_id'), symbol: columnIndexOf('symbol'),
      timeframe: columnIndexOf('timeframe'), t0: columnIndexOf('t0'),
    };
    if (Object.values(idx).some((i) => i < 0)) return { unit: 'undetected' as const, checked: 0, mismatches: [] };
    return inspectEventIdNormalization({
      rows: parsed.rows.map((r) => ({
        eventId: r[idx.eventId] ?? '', symbol: r[idx.symbol] ?? '',
        timeframe: r[idx.timeframe] ?? '', t0: r[idx.t0] ?? '',
      })),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parsed, mapping]);

  const mappingKey = JSON.stringify(columnMapping);
  useEffect(() => {
    // 🔴 **未勾確認前一個網路動作都不得發生**（SPEC L1581 逐字：`fetch` call count == 0）。
    //    R1 `COMPOSER-R1-P0-01`：本 effect 原本只看對映是否齊備，於是答案窗預填會在使用者
    //    確認之前就把檔案 POST 出去；而測試把該 helper mock 掉，完全看不到那次網路動作（假綠）。
    // 答案窗預設值須帶著對映一起問，否則後端看不到 label_definition（含 filters）。
    const ready = file !== null && parsedDefaults.ok && confirmed
      && PREVIEW_REQUIRED_FIELDS.every((f) => columnMapping[f] !== undefined || effectiveDefaults?.[f] !== undefined);
    if (!ready || file === null) { setPreview(null); return; }
    let cancelled = false;
    fetchLookaheadDeclarationPreview(file, { columnMapping, batchDefaults: effectiveDefaults })
      .then((p) => {
        if (cancelled) return;
        setPreview(p);
        setDeclared(initialDeclaredWindowBars(p));
      })
      .catch(() => {
        // 預填失敗不擋送出：後端仍會 fail-closed（未宣告即拒／封鎖切分），前端不自行放行也不自行判定
        if (!cancelled) setPreview(null);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file, mappingKey, defaultsText, dimsKey, confirmed]);

  const handleFileChange = async (next: File | null) => {
    setFile(next);
    setMapping({});
    setConfirmed(false);
    setConfirmedAt(null);
    setDeriveEventId(false);
    setProblems([]);
    setResult(null);
    setRejected(null);
    setError(null);
    setPreview(null);
    setDeclared({});
    setAcknowledged(false);
    if (!next) { setParsed(EMPTY_PARSED); return; }
    const nextParsed = parseCsvText(await next.text());
    setParsed(nextParsed);
    // 🔴 label 下拉之初始值**唯一**來自 Task 1.7 掃描之 `suggestedLabelColumn`（恆為 null ⇒ 未選）。
    //    把它接在這裡，是為了讓「只有一個二元欄就自動選它」這個 A-4′ 違規在 UI 上真的會發生
    //    ——否則那條保護是死欄位，變異了也沒有任何測試會紅。
    const scan = scanBinaryColumns(nextParsed.columns.map((c) => c.name), nextParsed.rows, null);
    const suggestedIndex = scan.suggestedLabelColumn === null
      ? -1
      : nextParsed.columns.findIndex((c) => c.name === scan.suggestedLabelColumn);
    setMapping(suggestedIndex >= 0 ? { label: String(suggestedIndex) } : {});
  };

  /** 送出前之阻擋原因；**空陣列才可以打網路**。 */
  const submitProblems = (): string[] => {
    const out: string[] = [];
    if (!file) out.push('請先選擇 CSV 檔');
    if (!parsedDefaults.ok) out.push('批次預設不是合法的 JSON 物件');
    if (parsed.raggedRows.length > 0) {
      const head = parsed.raggedRows.slice(0, 3).map((r) => `第 ${r.row + 1} 列（${r.width} 欄）`);
      out.push(`有 ${parsed.raggedRows.length} 列的欄數與標頭（${parsed.columns.length} 欄）不同：`
        + `${head.join('、')}。欄數不齊會讓後端整批拒收，也會讓上面的筆數不可信，請先修正 CSV`);
    }
    out.push(...dimensionDefaultConflicts(dims, parsedDefaults.value ?? undefined, Object.keys(columnMapping)));
    if (columnMapping.label === undefined && effectiveDefaults?.label === undefined) {
      out.push('尚未指定哪一個 CSV 欄是你標好的正反例（label）——平台不猜');
    }
    for (const field of MAPPABLE_CONTRACT_FIELDS) {
      const idx = mapping[field] === undefined || mapping[field] === '' ? -1 : Number(mapping[field]);
      const col = idx >= 0 ? parsed.columns[idx] : undefined;
      if (col?.duplicated) {
        out.push(`${field} 對映到重複欄名「${col.name}」（第 ${col.index + 1} 欄）；`
          + '對映端點以欄名定位，同名欄無法區分，請先在 CSV 內改名');
      }
    }
    if (!confirmed) out.push('請先勾選確認：這批正反例是你自己聲明的');
    if (preview) out.push(...validateDeclaration(declared, acknowledged, preview).problems);
    return out;
  };

  const handleSubmit = async () => {
    // 🔴 阻擋發生在**任何網路動作之前**（未勾確認 ⇒ fetch 呼叫次數 == 0）。
    const blocking = submitProblems();
    setProblems(blocking);
    if (blocking.length > 0 || !file) return;

    setUploading(true);
    setError(null);
    setResult(null);
    setRejected(null);
    try {
      const data = await uploadEventCsvMapping(
        file,
        {
          columnMapping,
          batchDefaults: effectiveDefaults,
          // 勾選當下之時間；理論上不會是 null（`confirmed` 為真才走到這裡），保底用送出時間。
          confirmedAt: confirmedAt ?? new Date().toISOString(),
          validateOnly,
          deriveEventId,
        },
        buildDeclarationPayload(declared, acknowledged, preview),
      );
      setResult(data);
      if (data.accepted && onImported) onImported(data);
    } catch (err) {
      if (err instanceof EventImportRejectedError) setRejected(err.payload);
      else setError(err instanceof Error ? err.message : '上傳失敗');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="glass-panel rounded-xl p-6 border border-slate-800/80" data-testid="event-csv-mapping-form">
      <h3 className="text-lg font-bold text-slate-100 mb-1">用自己的欄名匯入事件 CSV（GAP-3）</h3>
      <p className="text-xs text-slate-400 mb-4">
        不必先把標頭改成契約欄名：選檔後逐項指定「契約欄 ← 你的 CSV 欄」即可。
        預覽與警示由瀏覽器就地解析，「契約檢核一律在後端」（不符會逐列告訴你原因）。
      </p>

      <input
        type="file"
        accept=".csv,.txt"
        data-testid="csv-mapping-file"
        onChange={(e) => void handleFileChange(e.target.files?.[0] ?? null)}
        className="block w-full text-sm text-slate-300 file:mr-3 file:rounded file:border-0 file:bg-sky-500/20 file:px-3 file:py-1.5 file:text-sky-100"
      />

      {parsed.unsupportedLineEnding && (
        <div className="mt-4 rounded border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200"
             data-testid="csv-unsupported-line-ending">
          這個檔用的是舊式 Mac 換行（每行只有 CR），系統不支援：後端會整批拒收，
          而畫面上若硬解析會把整個檔黏成一行、產生看起來很像欄名的東西讓你誤選。
          請用試算表或編輯器另存為一般換行（LF 或 CRLF）後再上傳。
        </div>
      )}

      {parsed.columns.length > 0 && (
        <div className="mt-4 space-y-4">
          {/* 前 5 列預覽與全部欄名 */}
          <div className="overflow-x-auto rounded border border-slate-800/80" data-testid="csv-preview">
            <table className="min-w-full text-[11px]">
              <thead>
                <tr className="bg-slate-900/70 text-slate-300">
                  {parsed.columns.map((c) => (
                    <th key={`${c.name}-${c.index}`} className="px-2 py-1 text-left font-mono whitespace-nowrap"
                        data-testid="csv-preview-header">
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {parsed.previewRows.map((row, i) => (
                  <tr key={i} data-testid="csv-preview-row" className="text-slate-200">
                    {parsed.columns.map((c) => (
                      <td key={c.index} className="px-2 py-1 font-mono whitespace-nowrap">{row[c.index]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-[11px] text-slate-400">
            共 {parsed.rows.length} 列（上表為前 {parsed.previewRows.length} 列）。
          </p>

          {/* 逐項對映：初始值一律「未選」 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2" data-testid="csv-mapping-fields">
            {MAPPABLE_CONTRACT_FIELDS.map((field) => (
              <label key={field} className="flex items-center gap-2 text-sm text-slate-200">
                <span className="w-44 font-mono text-xs text-slate-300">{field}</span>
                <select
                  data-testid={`csv-mapping-${field}`}
                  value={mapping[field] ?? ''}
                  onChange={(e) => setMapping((prev) => ({ ...prev, [field]: e.target.value }))}
                  className="flex-1 rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-sm text-slate-100"
                >
                  <option value="">未選</option>
                  {parsed.columns.map((c) => (
                    <option key={`${c.index}`} value={String(c.index)}>{c.label}</option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          <p className="text-[11px] text-slate-400">
            沒對映到的契約欄請用下方「批次預設」補（只填補缺值，不覆蓋列自帶值）。
          </p>

          {parsed.raggedRows.length > 0 && (
            <p className="text-xs text-rose-200" data-testid="csv-ragged-rows">
              有 {parsed.raggedRows.length} 列的欄數與標頭（{parsed.columns.length} 欄）不同
              （{parsed.raggedRows.slice(0, 3).map((r) => `第 ${r.row + 1} 列 ${r.width} 欄`).join('、')}）。
              這種檔在後端會整批拒收，畫面上的筆數也不可信——請先修正 CSV 再送出。
            </p>
          )}

          {parsed.duplicateNames.length > 0 && (
            <p className="text-xs text-amber-200" data-testid="csv-duplicate-columns">
              這個檔有重複欄名：{parsed.duplicateNames.join('、')}。下拉以「第 N 欄」區分，
              但對映端點是以「欄名」定位，選到重複欄名會被擋下，請先在 CSV 內改名。
            </p>
          )}

          {/* Task 1.7：可疑欄警示 */}
          {binaryScan.suspicious.length > 0 && (
            <div className="rounded border border-amber-400/30 bg-amber-500/5 p-3 text-xs text-amber-100"
                 data-testid="csv-suspicious-binary">
              這些欄看起來也像標記（值域只有 0/1 或 true/false），請確認你選的是哪一個：
              <span className="font-mono"> {binaryScan.suspicious.join('、')}</span>
              <span className="block mt-1 text-amber-200/70">只是提醒，不會擋你送出。</span>
            </div>
          )}

          {/* 殘留 R-B2-1：秒級 t0 之 event_id 摩擦 */}
          {idReport.mismatches.length > 0 && (
            <div className="rounded border border-amber-400/30 bg-amber-500/5 p-3 text-xs text-amber-100"
                 data-testid="csv-event-id-normalization">
              <p>
                {idReport.unit === 'seconds'
                  ? '偵測到 t0 是「秒」，但契約的 event_id 一律用毫秒版；'
                  : '你寫的 event_id 與契約算出來的不一致；'}
                下面是這幾列「應該」寫的值（照抄回 CSV 即可，否則整批會被拒收）：
              </p>
              <ul className="mt-1 space-y-0.5 font-mono" data-testid="csv-event-id-expected">
                {idReport.mismatches.map((m) => (
                  <li key={m.row}>第 {m.row + 1} 列：{m.given || '（空白）'} → {m.expected}</li>
                ))}
              </ul>
              {/* 殘留 R-B2-1 之一鍵修法：不改上傳位元組，由後端在單位正規化後依契約模板產生 */}
              <label className="mt-2 flex items-start gap-2 text-amber-100">
                <input
                  type="checkbox"
                  checked={deriveEventId}
                  data-testid="csv-derive-event-id"
                  onChange={(e) => setDeriveEventId(e.target.checked)}
                  className="mt-0.5"
                />
                <span>
                  不想改檔的話，勾這個：由系統依契約公式從 symbol／週期／t0 產生 event_id
                  （時間會先換算成毫秒）。你的檔案原封不動上傳，這批的紀錄檔會註明 ID 是系統產生的。
                </span>
              </label>
            </div>
          )}

          {/* ── GAP-3 UX Task 7.1：五個批次維度（本路徑之 selectable 由同一常數導出）────
              🔴 CSV 匯入路徑之 `scenario` **四值全開**（label 由使用者自帶，系統只照抄）
                 ⇒ `/search` 之限制是**路徑級**的，不是把系統寫死於單一 scenario。 */}
          <div className="rounded border border-slate-800 bg-slate-900/40 p-3" data-testid="csv-event-dimensions">
            <p className="mb-2 text-sm text-slate-200">
              這批的五個設定
              <span className="ml-2 text-[11px] text-slate-400">
                不選就不寫該鍵（可以改用下方 JSON 或 CSV 欄對映提供；兩邊都給會擋下來）
              </span>
            </p>
            <EventDimensionFields path="/data-preparation" values={dims} onChange={setDims} allowUnset />
          </div>

          <label className="block text-sm text-slate-200">
            <span className="block mb-1">批次預設（JSON 物件；補齊沒對映到的契約欄）</span>
            <textarea
              data-testid="csv-batch-defaults"
              value={defaultsText}
              onChange={(e) => setDefaultsText(e.target.value)}
              rows={3}
              placeholder='{"direction": "long", "scenario": "A", "label_definition": {…}}'
              className="w-full rounded border border-slate-700 bg-slate-900/70 px-2 py-1 font-mono text-xs text-slate-100"
            />
          </label>

          {preview && preview.timeframes.length > 0 && (
            <LookaheadDeclarationFields
              preview={preview}
              declared={declared}
              acknowledged={acknowledged}
              problems={[]}
              onChangeWindow={(tf, value) => setDeclared((prev) => ({ ...prev, [tf]: value }))}
              onChangeAcknowledged={setAcknowledged}
            />
          )}

          {/* 強制確認：先把「你聲明了什麼」講出來 */}
          <div className="rounded border border-sky-400/30 bg-sky-500/5 p-3 space-y-2" data-testid="csv-declaration-summary">
            <p className="text-sm text-sky-100">
              你聲明的正例 <strong data-testid="csv-positive-count">{labelCounts.positive}</strong> 筆／
              反例 <strong data-testid="csv-negative-count">{labelCounts.negative}</strong> 筆
              {labelCounts.blank > 0 && <span className="text-sky-200/70">（另有 {labelCounts.blank} 列空白，由批次預設補）</span>}
              {labelCounts.unreadable > 0 && (
                <span className="text-amber-200" data-testid="csv-unreadable-count">
                  （另有 {labelCounts.unreadable} 列不是 0/1，後端會逐列拒收）
                </span>
              )}
            </p>
            <label className="flex items-start gap-2 text-sm text-sky-100">
              <input
                type="checkbox"
                checked={confirmed}
                data-testid="csv-confirm"
                onChange={(e) => {
                  setConfirmed(e.target.checked);
                  // 記的是「你何時確認」，不是「何時按送出」（R1 `CODEX-R1-P2-04`）。
                  setConfirmedAt(e.target.checked ? new Date().toISOString() : null);
                }}
                className="mt-1"
              />
              <span>
                我確認：以上正例／反例是我自己聲明的，欄位對映也是我指定的。
                系統不會、也無法替我判斷這些標記的語意對不對。
              </span>
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input type="checkbox" checked={validateOnly} data-testid="csv-validate-only"
                   onChange={(e) => setValidateOnly(e.target.checked)} />
            僅驗證不落檔
          </label>

          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={uploading}
            data-testid="csv-mapping-submit"
            className="px-4 py-2 rounded-lg bg-sky-500/20 text-sky-100 border border-sky-400/40 hover:bg-sky-500/30 disabled:opacity-50"
          >
            {uploading ? '上傳中…' : validateOnly ? '驗證' : '匯入'}
          </button>
        </div>
      )}

      {problems.length > 0 && (
        <ul className="mt-3 list-disc pl-5 text-xs text-rose-200" data-testid="csv-mapping-problems">
          {problems.map((p) => <li key={p}>{p}</li>)}
        </ul>
      )}

      {error && (
        <div className="mt-4 rounded border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200"
             data-testid="csv-mapping-error">{error}</div>
      )}

      {rejected && (
        <div className="mt-4 rounded border border-amber-400/40 bg-amber-500/10 p-3 text-sm text-amber-100"
             data-testid="csv-mapping-rejected">
          <p className="font-semibold">拒收（{rejected.kind}）：{rejected.message}</p>
          {rejected.failures.length > 0 && (
            <ul className="mt-2 space-y-0.5 font-mono text-[11px]">
              {rejected.failures.slice(0, 50).map((f, i) => (
                <li key={i} data-testid="csv-mapping-failure-row">
                  列 {f.row ?? '—'}／{f.field ?? '—'}／{f.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {result && (
        <div className="mt-4 rounded border border-emerald-400/40 bg-emerald-500/10 p-3 text-sm text-emerald-100"
             data-testid="csv-mapping-result">
          {result.import_id
            ? `已匯入 ${result.n_valid} 筆（import_id ${result.import_id}）`
            : `驗證通過 ${result.n_valid} 筆（未落檔）`}
        </div>
      )}
    </div>
  );
}
