/**
 * GAP-3 UX Task 6.3（前端半）——把「後端無回應」與「任務執行中」分成**兩個不同的字串**。
 *
 * 為什麼這件事重要（UAT 之實際症狀）：使用者看到進度停在同一個數字時，
 * 分不出「分析還在跑，只是很慢」與「後端已經沒回應了」。這兩者該做的事完全相反——
 * 前者是等，後者是去看後端。畫面若用同一句話表達，等於什麼都沒說。
 *
 * 🔴 抽成**純函式**而不是寫在元件裡：錨在元件事件處理器裡的判斷測不到
 *（本 epic §4.2 第 6 條之教訓：錨點落在無測試涵蓋處 ⇒ mutation 錄到空紅集合）。
 *
 * 🔴 階段字串為**可擴充集合**：GAP-6 會細分更多階段，本檔**不以固定 enum 窮舉**，
 * 未知階段一律原樣顯示，不映射成「其他」。
 */

/** 輪詢仍在成功回報、任務尚未結束。 */
export const IC_LABEL_RUNNING = '任務執行中';
/** 輪詢失敗（後端沒回應／連不上），**不是**任務本身的狀態。 */
export const IC_LABEL_NO_RESPONSE = '後端無回應';
/** 尚未送出分析。 */
export const IC_LABEL_IDLE = '尚未開始分析';

export interface IcTaskStatusInput {
  /** 後端回報之任務狀態；`null` ＝ 還沒拿到過任何狀態 */
  status?: string | null;
  /** 最近一次輪詢是否失敗（連線錯誤／非 2xx）。🔴 與 `status==='failed'` 是兩回事 */
  pollFailed?: boolean;
  /** 後端回報之細分階段（可擴充集合，原樣顯示） */
  currentStage?: string | null;
}

/**
 * 回傳畫面該顯示的狀態文字。
 *
 * 🔴 **判準的順序是刻意的**：輪詢失敗優先於任務狀態——後端沒回應時，
 * 我們手上那個 `status` 是**過期的快照**，拿它顯示「執行中」會讓使用者以為一切正常。
 */
export function icTaskStatusLabel(input: IcTaskStatusInput): string {
  if (input.pollFailed) return IC_LABEL_NO_RESPONSE;
  const status = input.status ?? null;
  if (status === null || status === 'idle') return IC_LABEL_IDLE;
  if (status === 'running' || status === 'pending') {
    // 階段是可擴充集合：有就原樣附上，沒有就只講「執行中」
    return input.currentStage ? `${IC_LABEL_RUNNING}：${input.currentStage}` : IC_LABEL_RUNNING;
  }
  return status;   // completed／failed 等終態原樣顯示，不另造詞
}

/** Task 6.3：特徵數之顯示；**解析不到就明說不知道**，不填假數字。 */
export function icFeatureCountLabel(featureCount: number | null | undefined): string {
  return typeof featureCount === 'number' && Number.isFinite(featureCount)
    ? `${featureCount} 個特徵`
    : '特徵數未知';
}
