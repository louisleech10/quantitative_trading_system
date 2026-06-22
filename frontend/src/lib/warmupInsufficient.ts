import type { WarmupInsufficient } from '@/lib/types';

/** B6：`key in payload` 權威清除；缺 key 保留 previous（undefined）。 */
export function normalizeWarmupInsufficient(
  payload: Record<string, unknown>,
): WarmupInsufficient | null | undefined {
  if (!('warmup_insufficient' in payload)) {
    return undefined;
  }
  const raw = payload.warmup_insufficient;
  if (raw == null) {
    return null;
  }
  if (typeof raw !== 'object') {
    return null;
  }
  const record = raw as Record<string, unknown>;
  const needed = Number(record.needed);
  const available = Number(record.available);
  const affected_bars = Number(record.affected_bars);
  if (![needed, available, affected_bars].every((n) => Number.isFinite(n) && n >= 0)) {
    return null;
  }
  return { needed, available, affected_bars };
}

export function formatWarmupInsufficientMessage(warmup: WarmupInsufficient): string {
  return `起點前歷史僅 ${warmup.available}/${warmup.needed} 根，前 ${warmup.affected_bars} 根特徵品質降級`;
}

export function extractWarmupInsufficientFromPayload(
  payload: Record<string, unknown>,
): WarmupInsufficient | null | undefined {
  const direct = normalizeWarmupInsufficient(payload);
  if (direct !== undefined) {
    return direct;
  }
  const result = payload.result;
  if (result && typeof result === 'object') {
    const metadata = (result as Record<string, unknown>).metadata;
    if (metadata && typeof metadata === 'object') {
      return normalizeWarmupInsufficient(metadata as Record<string, unknown>);
    }
  }
  return undefined;
}
