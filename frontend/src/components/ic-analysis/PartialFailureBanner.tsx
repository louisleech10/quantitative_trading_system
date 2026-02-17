'use client';

import { SkippedResult } from '@/lib/types';

interface PartialFailureBannerProps {
  completed: number;
  skipped: number;
  failed: number;
  errors: SkippedResult[];
}

export default function PartialFailureBanner({
  completed,
  skipped,
  failed,
  errors,
}: PartialFailureBannerProps) {
  if (skipped === 0 && failed === 0) {
    return null;
  }

  const skippedItems = errors.filter((item) => item.error_type !== 'INTERNAL_ERROR');
  const failedItems = errors.filter((item) => item.error_type === 'INTERNAL_ERROR');

  return (
    <div className="glass-panel rounded-2xl border border-amber-400/40 p-4 text-amber-100 space-y-2">
      <div className="font-medium">
        ⚠ 深度分析部分完成：{completed} 成功 | {skipped} 跳過 | {failed} 失敗
      </div>
      {skippedItems.length > 0 && (
        <p className="text-sm text-amber-200">
          跳過：{skippedItems.map((item) => `${item.module_name}（${item.reason}）`).join('、')}
        </p>
      )}
      {failedItems.length > 0 && (
        <p className="text-sm text-rose-200">
          失敗：{failedItems.map((item) => `${item.module_name}（${item.reason}）`).join('、')}
        </p>
      )}
    </div>
  );
}
