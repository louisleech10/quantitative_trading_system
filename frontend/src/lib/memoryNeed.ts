/**
 * IC 分析啟動准入（ICPERF SPEC v5.87 Task 0.6 (h)「⑤ IC 分析啟動准入」）之 need／have 顯示。
 * 後端拒收 detail 與排隊等待原因皆帶 `need_bytes`／`have_bytes`（位元組）；顯示為 GB（2^30，小數兩位）。
 */
const GIB = 2 ** 30;

export interface MemoryNeedHave {
  need_bytes: number;
  have_bytes: number;
  measurement_source?: string;
}

export function formatGiB(bytes: number): string {
  return (bytes / GIB).toFixed(2);
}

/** 「需要 X GB、可用 Y GB」；欄位不全 ⇒ null（不補假值）。 */
export function memoryNeedHaveText(value: unknown): string | null {
  if (!value || typeof value !== 'object') return null;
  const v = value as Record<string, unknown>;
  if (typeof v.need_bytes !== 'number' || typeof v.have_bytes !== 'number') return null;
  return `需要 ${formatGiB(v.need_bytes)} GB、可用 ${formatGiB(v.have_bytes)} GB`;
}
