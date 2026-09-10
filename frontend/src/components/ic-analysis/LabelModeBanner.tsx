'use client';

/**
 * EVTLABEL Task 3.9（R1 C14b）：本次分析用了哪一種 label 之摘要橫幅。
 *
 * 三種情形，顏色由 `kind` 決定（文案單點在 `icLabelRule.labelModeBannerText`）：
 * - **info**：用了你匯入的 0/1（寫出驗證段正反數，並說明報酬版在第二欄）。
 * - **warn**：`auto` 被退回報酬版（寫出原因），或區塊不足而無法做放行檢查（預期限制）。
 * - **danger**：負對照失敗 ⇒ 本次倖存者不可餵 ML。
 *
 * 🔴 判斷「不可餵 ML」用的是 **reason** 不是 status 字面：
 * `survivor_output.status` 之契約是封閉枚舉 `capability_status`，
 * 我們把負對照失敗表達為 `unavailable` ＋ `reason="negative_control_failed"`。
 */
import { labelModeBannerText } from '@/lib/icLabelRule';

interface Props {
  labelMode?: {
    effective?: string;
    requested?: string;
    reason?: string | null;
    n_pos_selection?: number;
    n_neg_selection?: number;
  } | null;
  /** `metadata.survivor_output.reason`（負對照失敗時為 `negative_control_failed`）。 */
  survivorReason?: string | null;
  /** `event_label_rule.permutation_receipt.status`（區塊不足時為 unavailable:…）。 */
  permutationStatus?: string | null;
}

const TONE: Record<string, string> = {
  info: 'border-sky-500/40 bg-sky-950/40 text-sky-100',
  warn: 'border-amber-500/40 bg-amber-950/40 text-amber-100',
  danger: 'border-rose-500/50 bg-rose-950/50 text-rose-100',
};

export default function LabelModeBanner({
  labelMode = null,
  survivorReason = null,
  permutationStatus = null,
}: Props) {
  const banner = labelModeBannerText(labelMode, survivorReason, permutationStatus);
  if (!banner) return null;
  return (
    <div
      className={`rounded-md border px-3 py-2 text-xs leading-relaxed ${TONE[banner.kind]}`}
      data-testid="label-mode-banner"
      data-kind={banner.kind}
      role={banner.kind === 'danger' ? 'alert' : 'status'}
    >
      {banner.text}
    </div>
  );
}
