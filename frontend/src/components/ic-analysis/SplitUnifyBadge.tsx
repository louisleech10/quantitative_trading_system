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
  // 🔴 B4 review R1（`CODEX-R1-P2-04`）：缺鍵有兩種——「全域 run 設計上不寫」與
  //    「舊／不完整 artifact」。前者要明說「不適用」，後者才是不渲染。
  //    判準用**報告本身有沒有切分 metadata**，不猜。
  const hasSplitMetadata = report?.metadata?.ic_train_test_split !== undefined;
  // 🔴 閉合確認輪 `COMPOSER-R2-P2-02`：事件批缺揭露＝後端漏寫，不是「全域不適用」。
  //    判準與後端寫 `split_unify` 的條件相同（`is_event_label_consumed` ⇔ label_source 為事件標籤）。
  const eventFilter = report?.metadata?.event_filter as { label_source?: string } | undefined;
  const isEventRun = eventFilter?.label_source === 'event_label_value';
  const view = splitUnifyView(disclosure, { hasSplitMetadata, isEventRun });
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
      {view.missingOnEventRun ? (
        <span data-testid="split-unify-missing-on-event-run" className="text-amber-300">
          （⚠️ 事件批應有此揭露，後端未寫入——這不是設計如此，請回報）
        </span>
      ) : null}
      {view.notApplicable ? (
        <span data-testid="split-unify-not-applicable" className="text-slate-500">
          （全域分析：本次不是事件批，沒有「事件」可數）
        </span>
      ) : null}
    </div>
  );
}
