import type { GroupedICData } from '@/lib/types';

/**
 * ICRESULT_PAGING Task 2.3：單特徵投影 `grouped_ic`＝`{kind: {label: value}}`（後端 project_feature 對實機三層
 * `{kind: {label: {feature: value}}}` 取該特徵）⇒ 還原為既有 GroupedICBarChart／RegimeRadarChart 期望之
 * `{kind: {label: {feature: value}}}`。kind 為 null（後端不適用）⇒ 略過；不補假值。
 */
export function reshapeGroupedForFeature(
  grouped: Record<string, Record<string, unknown> | null> | null | undefined,
  featureName: string | null,
): GroupedICData | null {
  if (!grouped || !featureName) return null;
  const out: GroupedICData = {};
  for (const [kind, labels] of Object.entries(grouped)) {
    if (!labels || typeof labels !== 'object') continue;
    const perLabel: Record<string, Record<string, number>> = {};
    for (const [label, value] of Object.entries(labels)) {
      if (typeof value === 'number') perLabel[label] = { [featureName]: value };
    }
    out[kind] = perLabel;
  }
  return out;
}
