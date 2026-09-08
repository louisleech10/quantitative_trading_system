import type { ICSubProgress, ICTaskWarning } from '@/lib/types';

/**
 * EVTALIGN Task 4.1：階段內進度之顯示文字。
 * 🔴 `eta_state==='estimating'` 或 `eta_seconds` 缺 ⇒ 「預估中」，**不顯示假 ETA**；
 *    後端沒送（null）⇒ 回 null，由呼叫端不渲染（不顯示 0/0 這種假數字）。
 */
export function icSubProgressLabel(sub: ICSubProgress | null | undefined): string | null {
  if (!sub || typeof sub.total !== 'number' || sub.total <= 0) return null;
  const done = typeof sub.done === 'number' ? sub.done : 0;
  const step = sub.step ? `${sub.step} ` : '';
  const eta = icEtaLabel(sub);
  return `${step}${done}/${sub.total}（剩餘 ${eta}）`;
}

export function icEtaLabel(sub: ICSubProgress): string {
  if (sub.eta_state === 'done') return '完成';
  if (sub.eta_state !== 'ok' || typeof sub.eta_seconds !== 'number' || !Number.isFinite(sub.eta_seconds)) {
    return '預估中';
  }
  const s = Math.max(0, Math.round(sub.eta_seconds));
  if (s < 60) return `約 ${s} 秒`;
  const m = Math.floor(s / 60);
  return m < 60 ? `約 ${m} 分 ${s % 60} 秒` : `約 ${Math.floor(m / 60)} 小時 ${m % 60} 分`;
}

const WARNING_TEXT: Record<string, string> = {
  memory_pressure_observed:
    '記憶體吃緊（處理程序用量超過實體記憶體或 swap 持續增長）。分析**照跑**、不會中止；只是會變慢。想快一點可以縮小特徵數或時間範圍。',
};

/** WARN 只揭露、不擋（使用者：「可以跑的話，幹嘛擋?」）。未知代碼原樣顯示，不吞掉。 */
export function icTaskWarningLabel(w: ICTaskWarning): string {
  return WARNING_TEXT[w.code] ?? `後端警告：${w.code}`;
}
