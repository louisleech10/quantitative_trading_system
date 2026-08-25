'use client';

import {
  UNVERIFIABLE_DECLARATION_WARNING,
  loweredTimeframes,
  type LookaheadDeclarationPreview,
} from '@/lib/lookaheadDeclaration';

interface Props {
  preview: LookaheadDeclarationPreview;
  declared: Record<string, number>;
  acknowledged: boolean;
  problems: string[];
  onChangeWindow: (timeframe: string, value: number) => void;
  onChangeAcknowledged: (value: boolean) => void;
}

/**
 * GAP-3 UX Task 1.9／1.11 — 答案窗宣告區塊（**逐 timeframe 各一個輸入框**）。
 *
 * 🔴 批內有幾個 timeframe 就有幾個輸入框：`future72_*` 在 1h 是 72 根、在 12h 是 6 根，
 * 以單一輸入框套用全部 tf 會在小時命名欄上把深度算錯（後端亦 fail-closed 擋）。
 * 🔴 調低須勾選不可驗聲明；警語逐字揭露錯報後果。
 */
export default function LookaheadDeclarationFields({
  preview, declared, acknowledged, problems, onChangeWindow, onChangeAcknowledged,
}: Props) {
  const lowered = loweredTimeframes(declared, preview);
  return (
    <div
      className="rounded-lg border border-amber-400/30 bg-amber-500/5 p-3 space-y-3"
      data-testid="lookahead-declaration"
    >
      <div>
        <p className="text-sm font-semibold text-amber-100">答案窗宣告（每個 K 線週期各填一次）</p>
        <p className="text-xs text-amber-200/80">
          你的正例條件最遠用到 t₀ 之後第幾根？這個值同時決定 train/test 的隔離寬度（purge），
          {preview.requires_declaration
            ? '本批引用了系統無法驗證深度的欄位，因此必須宣告。'
            : '預設已填入檔內最大可用的 horizon。'}
        </p>
        {preview.referenced_columns.length > 0 && (
          <p className="mt-1 text-[11px] font-mono text-amber-200/70" data-testid="lookahead-referenced-columns">
            條件引用欄：{preview.referenced_columns.join(', ')}
          </p>
        )}
      </div>

      <div className="space-y-2">
        {preview.timeframes.map((tf) => (
          <label key={tf} className="flex items-center gap-2 text-sm text-slate-200">
            <span className="w-16 font-mono text-xs text-slate-300">{tf}</span>
            <input
              type="number"
              min={1}
              step={1}
              data-testid={`lookahead-window-${tf}`}
              value={Number.isFinite(declared[tf]) ? declared[tf] : ''}
              onChange={(e) => onChangeWindow(tf, Number.parseInt(e.target.value, 10))}
              className="w-24 rounded border border-slate-700 bg-slate-900/70 px-2 py-1 text-sm text-slate-100"
            />
            <span className="text-xs text-slate-400">
              根（檔內最大可用 {preview.default_window_bars[tf] ?? 0}）
            </span>
          </label>
        ))}
      </div>

      {lowered.length > 0 && (
        <label className="flex items-start gap-2 text-sm text-amber-100" data-testid="lookahead-ack-row">
          <input
            type="checkbox"
            checked={acknowledged}
            data-testid="lookahead-acknowledge"
            onChange={(e) => onChangeAcknowledged(e.target.checked)}
            className="mt-1"
          />
          <span>
            我的篩選條件未用到超過所填的根數（{lowered.join('、')}）。
            <strong className="text-amber-200"> {UNVERIFIABLE_DECLARATION_WARNING}</strong>
          </span>
        </label>
      )}

      {problems.length > 0 && (
        <ul className="list-disc pl-5 text-xs text-rose-200" data-testid="lookahead-declaration-problems">
          {problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
