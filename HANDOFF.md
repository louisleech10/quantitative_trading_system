# HANDOFF — 當前任務狀態

**更新：2026-09-08 早｜狀態：`EVTALIGN` 路線由三家共識裁定 **B＋D**；SPEC/TODO 已改，尚未實作。**

## 使用者最後兩條指示（逐字）
> 「那這個修正後的排序改SPEC。B26/B27等上述完成後再驗收。我要先睡了」
> 「你跟委員討論決定共識看要怎麼做」

⇒ B26／B27 驗收暫緩至 EVTALIGN 收完。路線已由 consult 共識決定，**不再問使用者**。

## 當前票：`EVTALIGN`
SPEC=`docs/GAP3_EVENT_ALIGNMENT_SPEC.md`／TODO=`docs/GAP3_EVENT_ALIGNMENT_TODO.md`（皆 TEMPLATE PASS）。

**審查軌跡**：R1 19 條（3 P0）→ R2 19 條（**6 P0**，變差）→ consult 三家一致 **B＋D**。
R2 六個 P0 同一形狀＝「每個判準都做成呼叫端傳入，可偽造」。
codex：「A 為堵洞而改…實質收斂成 B＋D 的較大改動面」⇒ A 之終點就是 B＋D。
三輪債皆 `debt_clear`；收斂檔 `handoffs/reconcile/2026090{7,8}-evtalign-x-*/synth.md`。

## 裁定的路線
- **B**（Task 1.1）：**不動 `validate_alignment` 任何一行**。label 生成前把 `close` 裁到 feature 尾
  （`_coterminalize_close`，單一 helper），**stage0 `:2790` 與 stage2 `:2923` 兩呼叫點都接**。
  不新增任何參數 ⇒ R2 之「可偽造」形狀無從產生。
  前提已實跑：`handoffs/20260908-probe-option-b-trim.py` rc=0（裁切把截短化約為同尾，label 逐位元組相同）。
- **D**（Task 2.1，**B 之必要配套**）：驗實際被消費的 label；`label_kind` 由 producer 之 `label_source` 導出；
  `event_given` 加 `(event_id, timestamp, label_value)` 三元組逐筆綁定。
  codex：不做 D ＝ event_id 錯配進條件 IC ＝**錯誤輸出**。
- P3 期間自動對齊＋丟失事件 ID 揭露；P4 進度＋記憶體 WARN（**不得擋**）；P5 purge/embargo 揭露。

## B0 完成（2026-09-08）
Task 0.2 golden 重做：`handoffs/20260907-probe-split-baseline.py --write` → 9 組（8 ok＋1 skip），
含 stage0 預載（`horizon_source=column_parse`）、`split_row_fingerprint`、`retained_event_ids`；
sha256=`e378c706…ba7201`，重跑對證 True。
Task 0.1 scaffold：`scripts/evtalign_phase_gate.sh`、`handoffs/20260907-evtalign-mutate.py`、
三個 placeholder 測試（`pytest.skip`）。實測 rc 直接取：phase 0 PASS；phase 1 rc=1（2 skip＋UNCOVERED=5）＝預期。
🔴 mutate 首版把 pytest rc=5（沒收集到測試）當「紅」⇒ B3 假 PASS；已改為 rc=5 計 UNCOVERED、紅只認 rc=1。

## B1 完成（2026-09-08，commit `efb16e4c`）
Task 1.1：`_coterminalize_close` 接 stage0＋stage2；守衛 sha256 `9c8aeb69…` 釘在測試。
Task 2.1：contracts `derive_label_kind`／`validate_event_given`／`validate_consumed_label`；stage3 覆寫後驗；
`event_label_owners` 透傳＋service `_assert_event_triple_bound` 回比 `event_label_by_id`。
🔴 **更正**：我曾寫「golden 8 檔通過」——實為 **4 failed／78 passed（rc=1）**，我只看 harness exit code 沒讀 pytest rc。
A/B（`097dae40` worktree）證實四條在 B1 前就紅（reporter stub 缺 kwarg×2、config_hash 凍結過期、event_timestamps kwarg 正則），
登記 `EA-RESID-6`；事故寫在 reconcile R3 E4。**驗收一律逐檔看 pytest 的 rc／summary 行，禁看 harness exit code。**

## R3 完成（2026-09-08）
三家一致「可合併、無新 P0」；D1–D4／D6／D7／D9 CLOSED。共同 P1＝D5（事件 label 將覆寫時 stage2 仍硬擋鷹架）：
三家裁「資料驅動延後」不違 §C-6 ⇒ 已實作 `_settle_deferred_scaffold`（覆寫 ⇒ 診斷揭露；未覆寫 ⇒ 原樣 raise），
TODO 2.1 要點 3／SPEC Task 2.1 要點 5 改寫；P1-02（stage0 預載）以 fail-closed 測試閉合；mutation 加 E1／E2。
新測試 18 條 rc=0；template_check 兩份 PASS；reconcile `handoffs/reconcile/20260908-evtalign-x-review-r3/synth.md`。

## 下一步
commit R3 修法 → `evtalign_phase_gate.sh 1`（mutation 10 條）→ `debt_clear` → **B2** Task 2.2 跨模式不變式 → B3 期間自動對齊。

## 具名殘留
`EA-RESID-1` preprocessing 峰值記憶體（17 GB／8 GB）｜`EA-RESID-2` 橫截面無守衛（模組未完工，**非缺陷**）
`EA-RESID-3` `_validate_expected_frequency` 對 tz-aware 拋 `TypeError`（潛伏，現行 naive）
`EA-RESID-4` close 指紋不證原始 K 線品質｜`EA-RESID-5` `excess`/`risk_adjusted` 無 oracle（B 下不再阻擋，但登記）

## 已完成待驗收
`SCANCUBE` 五 Phase 全完成，立方體實測正確。限制：滿格 110 格不保證圖表（已列白話頭條）。

## 環境
開放債為零。`scripts/_add_cube_contract_keys.py`、`scripts/_todo_r2_patch.py` 為一次性腳本（可刪）。
`uat_samples/*`、`market_data/*` 未追蹤異動勿 commit。
