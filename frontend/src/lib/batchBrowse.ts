import type { BatchTaskStatus } from './types';

export function getBackendBrowseTaskId(
  batchTask: Pick<BatchTaskStatus, 'browse_task_ids'> | null | undefined,
  symbol: string,
): string | null {
  return batchTask?.browse_task_ids?.[symbol] ?? null;
}
