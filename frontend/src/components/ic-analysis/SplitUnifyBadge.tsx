'use client';

import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { splitUnifyView, type SplitUnifyDisclosure } from '@/lib/splitAuthority';

/**
 * SPLITUNIFY Task 4.1（SPEC C-6）：**唯一**的驗證段數字＋它的來源標籤。
 *
 * 出生理由：同一批事件原本會在畫面上看到兩個互相矛盾的驗證段數字（實測 31 vs 33）——
 * 一個來自事件側自己的切分、一個來自 K 線 holdout。現在只有一個，而且旁邊寫著它是誰算的。
 *
 * 🔴 三條紀律：
 *   ①後端沒寫這塊（全域 run／舊報告）⇒ **不渲染**，不要顯示「0」或「無」；
 *   ②`n_test` 為 `null` ⇒ 顯示「無」＋原因，**永遠不顯示 0**；
 *   ③來源標籤一律顯示——數字沒有來源就無法判斷可不可信。
 */
export default function SplitUnifyBadge() {
  const report = useICAnalysisStore((s) => s.report);
  const disclosure = report?.metadata?.split_unify as SplitUnifyDisclosure | undefined;
  const view = splitUnifyView(disclosure);
  if (!view) return null;

  return (
    <div
      data-testid="split-unify-badge"
      data-split-authority={disclosure?.split_authority ?? ''}
      className="glass-panel rounded-2xl border border-white/10 px-4 py-2 text-xs text-slate-300 flex flex-wrap items-center gap-x-3 gap-y-1"
    >
      <span className="text-slate-400">驗證段事件數</span>
      <span
        data-testid="split-unify-n-test"
        className={view.hasCount ? 'text-slate-100 font-semibold' : 'text-amber-300 font-semibold'}
      >
        {view.countText}
      </span>
      <span className="text-slate-500">·</span>
      <span className="text-slate-400">來源</span>
      <span data-testid="split-unify-authority" className="text-slate-200">{view.authorityText}</span>
      {view.reason ? (
        <span data-testid="split-unify-reason" className="text-amber-300/90">
          （未能計算：{view.reason}）
        </span>
      ) : null}
    </div>
  );
}
