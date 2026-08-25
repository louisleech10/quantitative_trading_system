'use client';

import { useState } from 'react';
import { EventImportRejectedError, fetchLookaheadDeclarationPreview, uploadEventImport } from '@/lib/api';
import LookaheadDeclarationFields from '@/components/case/LookaheadDeclarationFields';
import {
  buildDeclarationPayload,
  initialDeclaredWindowBars,
  validateDeclaration,
  type LookaheadDeclarationPreview,
} from '@/lib/lookaheadDeclaration';
import type { EventImportRejected, EventImportResponse } from '@/lib/types';

interface EventImportFormProps {
  onImported?: (result: EventImportResponse) => void;
}

/**
 * GAP-3 B5.2：新 schema 事件匯入（CSV/JSON → /api/v1/case/import-events）。
 * 拒收一律顯示後端逐列 reason 與 migration 提示（前端不重做任何契約檢查）。
 */
export default function EventImportForm({ onImported }: EventImportFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [validateOnly, setValidateOnly] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<EventImportResponse | null>(null);
  const [rejected, setRejected] = useState<EventImportRejected | null>(null);
  const [error, setError] = useState<string | null>(null);
  // GAP-3 UX Task 1.9／1.11：答案窗宣告（逐 tf）
  const [preview, setPreview] = useState<LookaheadDeclarationPreview | null>(null);
  const [declared, setDeclared] = useState<Record<string, number>>({});
  const [acknowledged, setAcknowledged] = useState(false);
  const [declarationProblems, setDeclarationProblems] = useState<string[]>([]);

  const handleFileChange = async (next: File | null) => {
    setFile(next);
    setPreview(null);
    setDeclared({});
    setAcknowledged(false);
    setDeclarationProblems([]);
    if (!next) return;
    try {
      const p = await fetchLookaheadDeclarationPreview(next);
      setPreview(p);
      setDeclared(initialDeclaredWindowBars(p));
    } catch {
      // 預填失敗不擋上傳：後端仍會 fail-closed（未宣告即拒／封鎖切分），前端不自行放行也不自行判定
      setPreview(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('請先選擇 CSV 或 JSON 檔');
      return;
    }
    if (preview) {
      const check = validateDeclaration(declared, acknowledged, preview);
      setDeclarationProblems(check.problems);
      if (!check.ok) return;
    }
    setUploading(true);
    setError(null);
    setResult(null);
    setRejected(null);
    try {
      const data = await uploadEventImport(file, validateOnly, buildDeclarationPayload(declared, acknowledged, preview));
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
    <div className="glass-panel rounded-xl p-6 border border-slate-800/80" data-testid="event-import-form">
      <h3 className="text-lg font-bold text-slate-100 mb-1">匯入事件（GAP-3 新契約）</h3>
      <p className="text-xs text-slate-400 mb-4">
        正反例外部標好後以新 schema 匯入（每列含 <code className="font-mono">event_id / t0(ms) / label / label_definition / control_kind …</code>）。
        舊三欄 CSV 請用上方「導入案例」；兩者不互轉。
      </p>
      <div className="space-y-3">
        <input
          type="file"
          accept=".csv,.json,.txt"
          data-testid="event-import-file"
          onChange={(e) => void handleFileChange(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-300 file:mr-3 file:rounded file:border-0 file:bg-sky-500/20 file:px-3 file:py-1.5 file:text-sky-100"
        />
        {preview && preview.timeframes.length > 0 && (
          <LookaheadDeclarationFields
            preview={preview}
            declared={declared}
            acknowledged={acknowledged}
            problems={declarationProblems}
            onChangeWindow={(tf, value) => setDeclared((prev) => ({ ...prev, [tf]: value }))}
            onChangeAcknowledged={setAcknowledged}
          />
        )}
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" checked={validateOnly} onChange={(e) => setValidateOnly(e.target.checked)} />
          僅驗證不落檔
        </label>
        <button
          type="button"
          onClick={handleUpload}
          disabled={uploading || !file}
          data-testid="event-import-submit"
          className="px-4 py-2 rounded-lg bg-sky-500/20 text-sky-100 border border-sky-400/40 hover:bg-sky-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? '上傳中…' : validateOnly ? '驗證' : '匯入'}
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200" data-testid="event-import-error">
          {error}
        </div>
      )}

      {rejected && (
        <div className="mt-4 rounded border border-amber-400/40 bg-amber-500/10 p-3 text-sm text-amber-100" data-testid="event-import-rejected">
          <p className="font-semibold">拒收（{rejected.kind}）：{rejected.message}</p>
          {rejected.migration_hint && (
            <pre className="mt-2 max-h-48 overflow-auto rounded bg-slate-900/70 p-2 text-[11px] text-slate-200">
              {JSON.stringify(rejected.migration_hint, null, 2)}
            </pre>
          )}
          {rejected.detail && Object.keys(rejected.detail).length > 0 && (
            <pre
              className="mt-2 max-h-48 overflow-auto rounded bg-slate-900/70 p-2 text-[11px] text-slate-200"
              data-testid="event-import-rejected-detail"
            >
              {JSON.stringify(rejected.detail, null, 2)}
            </pre>
          )}
          {rejected.failures.length > 0 && (
            <table className="mt-2 w-full text-[11px]">
              <thead>
                <tr className="text-slate-400">
                  <th className="text-left">列</th>
                  <th className="text-left">event_id</th>
                  <th className="text-left">欄位</th>
                  <th className="text-left">reason</th>
                </tr>
              </thead>
              <tbody>
                {rejected.failures.slice(0, 200).map((f, i) => (
                  <tr key={i} data-testid="event-import-failure-row">
                    <td>{f.row ?? '—'}</td>
                    <td>{String(f.event_id ?? '—')}</td>
                    <td>{f.field ?? '—'}</td>
                    <td className="font-mono">{f.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {result && (
        <div className="mt-4 rounded border border-emerald-400/40 bg-emerald-500/10 p-3 text-sm text-emerald-100" data-testid="event-import-result">
          <p>
            {result.import_id ? `已匯入 ${result.n_valid} 筆（import_id ${result.import_id}）` : `驗證通過 ${result.n_valid} 筆（未落檔）`}
          </p>
          {result.upload_sha256 && <p className="font-mono text-[11px] text-emerald-200/80">upload sha256 {result.upload_sha256.slice(0, 16)}…</p>}
        </div>
      )}
    </div>
  );
}
