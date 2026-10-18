/**
 * FF-NAME Task 3.3 — 欄名描述 map 之純函式層（無 React／store 相依，避免 store ↔ hook 循環匯入）。
 *
 * 欄名語意只由後端 Python parser 決定；前端只以欄名為鍵查 map，絕不解析欄名字串。
 * 描述鍵與介面名之單一來源：tests/_golden/ffname/contract.json（descriptor／frontend 段）。
 */
import type { FeatureDescriptor, ResolvedFeatureDescriptor } from '@/lib/types';

/** 目前支援之命名版本（對應後端 CURRENT_FEATURE_NAMING_VERSION；contract.json naming_version）。 */
export const SUPPORTED_NAMING_VERSION = 2;

/** 已知 kind（contract.json kinds）；未知 kind 一律 unsupported，不 fallback other。 */
export const KNOWN_KINDS: ReadonlySet<string> = new Set([
  'atomic',
  'derived',
  'raw-lag',
  'rolling',
  'cross-sectional',
  'meta',
  'preprocess',
  'custom',
]);

/** 列物件：欄名＋描述（描述鍵 = contract.json descriptor.row_key）。 */
export interface FeatureDescriptorSourceRow {
  name: string;
  descriptor?: FeatureDescriptor | null;
}

export type FeatureDescriptorMap = Map<string, FeatureDescriptor>;

/** 以 API 回傳之特徵列（names 或 table）建共享描述 map；無描述之列不入 map（查詢時即 unsupported）。 */
export function buildFeatureDescriptorMap(
  rows: ReadonlyArray<FeatureDescriptorSourceRow>,
  base?: FeatureDescriptorMap,
): FeatureDescriptorMap {
  const map: FeatureDescriptorMap = new Map(base ?? []);
  for (const row of rows) {
    if (row && typeof row.name === 'string' && row.descriptor && typeof row.descriptor === 'object') {
      map.set(row.name, row.descriptor);
    }
  }
  return map;
}

/** 依欄名查 map；查無、版本不符、未知 kind、後端標 unsupported ⇒ unsupported（fail-closed）。 */
export function resolveFeatureDescriptor(
  map: FeatureDescriptorMap | undefined,
  name: string,
): ResolvedFeatureDescriptor {
  const descriptor = map?.get(name);
  if (!descriptor) return { status: 'unsupported', reason: 'missing', display: name };
  if (descriptor.version !== SUPPORTED_NAMING_VERSION) {
    return { status: 'unsupported', reason: 'version', display: name };
  }
  if (descriptor.kind === 'unsupported') {
    return { status: 'unsupported', reason: descriptor.error || 'invalid', display: name };
  }
  if (!KNOWN_KINDS.has(descriptor.kind)) {
    return { status: 'unsupported', reason: 'kind', display: name };
  }
  return { status: 'ok', descriptor, display: descriptor.display || name };
}
