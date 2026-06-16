import type { BatchTaskStatus, FeatureRegistryEntry, FeatureTask, RunIdentity, RunInfo } from '@/lib/types';
import { runKey } from '@/store/featureFactoryStore';

/** 從穩定 browse task id 解析 run identity（browse_{symbol}_{timeframe}_{config_hash}） */
export function identityFromBrowseTaskId(browseTaskId: string): RunIdentity | null {
  const match = /^browse_([^_]+)_([^_]+)_(.+)$/.exec(browseTaskId.trim());
  if (!match) return null;
  return { symbol: match[1], timeframe: match[2], config_hash: match[3] };
}

function findRunByBrowseTaskId(runs: RunInfo[], browseTaskId: string): RunInfo | null {
  const direct = runs.find((run) => run.browse_task_id === browseTaskId);
  if (direct) return direct;
  const identity = identityFromBrowseTaskId(browseTaskId);
  if (!identity) return null;
  return runs.find((run) => runKey(run) === runKey(identity)) ?? null;
}

function findRunForBatchSymbol(
  browseReady: RunInfo[],
  batchTask: BatchTaskStatus,
  symbol: string,
): RunInfo | null {
  const browseTaskId = batchTask.browse_task_ids?.[symbol];
  if (browseTaskId) {
    const match = findRunByBrowseTaskId(browseReady, browseTaskId);
    if (match) return match;
  }

  const batchTimeframe = batchTask.current_timeframe;
  if (!batchTimeframe) return null;

  const outputPath = batchTask.output_paths?.find(
    (entry) => entry.symbol === symbol && entry.timeframe === batchTimeframe,
  );
  if (outputPath?.path) {
    const normalizedPath = outputPath.path.replace(/\\/g, '/');
    const byPath = browseReady.find((run) => {
      if (run.symbol !== symbol || run.timeframe !== batchTimeframe) return false;
      const browsePath = run.browse_path?.replace(/\\/g, '/');
      if (!browsePath) return false;
      return (
        browsePath === normalizedPath ||
        browsePath.endsWith(normalizedPath) ||
        normalizedPath.endsWith(browsePath)
      );
    });
    if (byPath) return byPath;
  }

  return null;
}

export function runsToRegistryEntries(runs: RunInfo[]): FeatureRegistryEntry[] {
  return runs
    .filter((run) => run.browse_ready)
    .map((run) => ({
      symbol: run.symbol,
      timeframe: run.timeframe,
      config_hash: run.config_hash,
      feature_count: run.feature_count ?? 0,
      row_count: run.row_count ?? 0,
      created_at: run.created_at ? Math.floor(Date.parse(run.created_at) / 1000) : 0,
      hdf5_relative_path: run.browse_path ?? '',
    }));
}

/** 格式化為本地 24 小時制 `YYYY-MM-DD HH:mm`；無法解析則退回前 10 字(日期)。 */
export function formatRunTimestamp(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso.slice(0, 10);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function formatRunLabel(run: RunInfo): string {
  const title = run.alias?.trim() || `${run.symbol} / ${run.timeframe} / ${run.config_hash}`;
  const count = run.feature_count != null ? ` · ${run.feature_count.toLocaleString()} 特徵` : '';
  const when = run.created_at ? ` · ${formatRunTimestamp(run.created_at)}` : '';
  return `${title}${count}${when}`;
}

export function pickDefaultRun(
  runs: RunInfo[],
  currentTask: FeatureTask | null,
  batchTask: BatchTaskStatus | null,
): RunInfo | null {
  if (runs.length === 0) return null;

  const browseReady = runs.filter((run) => run.browse_ready);
  if (browseReady.length === 0) return runs[0] ?? null;

  if (currentTask?.status === 'completed' && currentTask.run_identity) {
    const identity = currentTask.run_identity;
    const match = browseReady.find((run) => runKey(run) === runKey(identity));
    if (match) return match;
  }

  if (
    batchTask &&
    (batchTask.status === 'completed' || batchTask.status === 'partial') &&
    batchTask.results
  ) {
    const firstSymbol = Object.keys(batchTask.results)[0];
    if (firstSymbol) {
      const match = findRunForBatchSymbol(browseReady, batchTask, firstSymbol);
      if (match) return match;
    }
  }

  const sorted = sortRunsByRecency(browseReady);
  return sorted[0] ?? browseReady[0] ?? null;
}

/** Run 列表依建立/最近生成時間降序（最新在上） */
export function sortRunsByRecency(runs: RunInfo[]): RunInfo[] {
  return [...runs].sort((a, b) => {
    const aTime = Date.parse(a.last_generated_at ?? a.created_at ?? '') || 0;
    const bTime = Date.parse(b.last_generated_at ?? b.created_at ?? '') || 0;
    return bTime - aTime;
  });
}
