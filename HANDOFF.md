# HANDOFF — 當前任務狀態

**更新：2026-09-07 深夜｜狀態：`EVTALIGN` SPEC 已過 R1 修訂；使用者睡覺中，依離線規則自行續走。**

## 使用者最後的指示（逐字）
> 「那這個修正後的排序改SPEC。B26/B27等上述完成後再驗收。我要先睡了」

⇒ **B26／B27 驗收暫緩**（掃描結果瀏覽器已完成並可用，等 EVTALIGN 收完再驗）。
⇒ 依 `feedback_offline_committee_decides`：不停不問，取捨交委員／碼證，做到 commit+push。

## 當前票：`EVTALIGN`（事件對齊守衛）
SPEC=`docs/GAP3_EVENT_ALIGNMENT_SPEC.md`（TEMPLATE PASS）。TODO **尚未寫**。
R1（`20260907-evtalign-x-review-r1`）：19 條、**3 個獨立 P0**，三家一致「不可照 SPEC 開工」。
債已 `debt_clear`；reconcile 見 `handoffs/reconcile/20260907-evtalign-x-review-r1/synth.md`。

🔴 **R1 最重要的結果：我的核心修法會放行 look-ahead。**
`max(0, lag − 剩餘根數)` 在截短時期望值為 0，未 shift 的洩漏也是 0 ⇒ 通過。
已整條重寫為三層：L0 依 `label_kind` 分派／L1 尾端 NaN（同尾強度不變）／
L2 oracle（**截短時必須**，拿不到 ⇒ fail-closed raise）。

## 優先序（使用者 2026-09-07 裁定）
1. **期間守衛**（探針證**全域模式今天就有地雷**）2. 鷹架（事件模式，60 天）
3. 期間自動對齊＋丟失事件揭露 4. 進度可見＋記憶體 WARN（**不得新增阻擋閘**）
5. purge/embargo 揭露（由「安全」降為「揭露」）

## 具名殘留
`EA-RESID-1` preprocessing 峰值記憶體（實機 17 GB／8 GB、swap 15.6 GB）｜`needs-research`
`EA-RESID-2` 橫截面無 `validate_alignment`｜`blocked-by`：模組未完工，**不是缺陷**（使用者當面更正）

## 下一步
寫 `docs/GAP3_EVENT_ALIGNMENT_TODO.md` → 派 R2 由原提出方確認 → 才進實作。
🔴 **實作前必補**：`ASSUME-2`（`effective_horizon`／`purge_gap` 不受影響）**尚未實跑**。

## 已完成並可用（等使用者驗收）
`SCANCUBE` 掃描結果瀏覽器五 Phase 全完成；立方體實測正確（`8473641c` 60 列／14 指標）。
🔴 已知限制：**滿格 110 格不保證有圖表**（1,158 MB），已列為白話頭條。

## 環境
開放債為零。`scripts/_add_cube_contract_keys.py`、`scripts/_todo_r2_patch.py` 為一次性腳本
（`rm` 被權限擋下，未進版控，可刪）。`uat_samples/*`、`market_data/*` 未追蹤異動勿 commit。
