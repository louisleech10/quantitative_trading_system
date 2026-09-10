# HANDOFF — 當前任務狀態

**更新：2026-09-11 凌晨｜票：`SPLITUNIFY`（大；RISK a,b,c,d）｜狀態：SPEC/TODO 已到 **v4**；四輪審查（R1 13 群集／R2 11／R3 7／R4 進行中）＋五輪戳記全數收斂；尚未進第一批實作。**

## 使用者離線授權（2026-09-10 深夜，逐字）
> 「我要睡了，你繼續做完，有問題找委員會討論共識，做完前不要停下來」

⇒ **不停、不問、斷路器交委員會共識決**；分歧看碼證不數人頭，不決則採較嚴版並具名殘留。

## 🔴 本 session 最重要的四件事

1. **戳記閘攔下我三處收斂掉項。** codex（`-STAMP-R1`）REJECTED、composer（`-STAMP-R2`）
   附註 ⇒ 我把 19 條 consult findings 逐條重對，**11 條歸屬錯誤或缺漏**（grok 的 7 條全錯）。
   consult synth 由 5 個決議項修正為 **8 個**。五輪戳記後三家全數 APPROVED，
   `reconcile_stamps_check.sh` rc=0。
2. **C-0（接線落點）**：`EventSplitPlan` 唯一 producer `split_events` 只被 `pipeline.py:691`
   呼叫，其唯一生產 caller `case_import_service.py:1610` **既無 `SplitPlan` 也無 feature
   universe** ⇒ v1 的「投影」沒有落點。裁定：事件掃描端**恆走** event-study-only，
   本票不新增 universe 供給路徑（殘留 `R-5`）。
3. 🔴 **R3 codex 抓到我造成的真 OOS leakage（本 session 最嚴重）**：v3 的投影只做集合成員
   判定，簽名裡沒有 `label_end_ms` ⇒ 把 `event_split.py:114` 那道
   `label_end_ms > test_start - embargo` 的答案窗 purge **整個刪掉**，
   答案窗已跨進測試段的 train 事件會留在 train。而 C-1 附帶約束①「不得刪除任一既有 guard」
   是我自己寫的。R1／R2 兩輪都沒抓到，R3 才由 codex 以「介面可執行性」掃法抓出。
   ⇒ v4 改**兩段式判定**（先驗答案窗跨界 ⇒ purged，再做集合判定），新增 `M-SU-13`。
4. **我自己的探針否證過我自己兩次**：①多 symbol 全域 vs per-symbol 不等價
   （12 列 vs 8 列）；②「兩端各自用同一公式算 canonical 邊界」不成立——真實 ETHUSDT 1h
   20352 列，EVTALIGN 裁頭尾後邊界位移 5 根→2h、24 根→10h、168 根→67h。

## 檔案
- SPEC `docs/SPLITUNIFY_SPEC.md`（**v4**，sha256 `384aa22961d0…`）／
  TODO `docs/SPLITUNIFY_TODO.md`（**v4**，sha256 `cd95ee642a9e…`）
- consult 收斂 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`
  （D1–D8；body-hash `120b4d042d38…`；三家 APPROVED）
- 審查收斂 `handoffs/reconcile/20260911-splitunify-x-review-r{1,2,3}/synth.md`（C1–C13／D1–D11／E1–E7）
- 主委自產審查 `handoffs/20260911-splitunify-claude-selfreview{,-r2,-r3}.md`
- 探針 `handoffs/20260911-probe-splitunify-universe-gap.py`
  ＋ receipt `handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`
- 白話 `白話說明/SPLITUNIFY規格白話.md`、`白話說明/SPLITUNIFY施工進度.md`

## 下一步（順序）
1. **R4 定向確認輪**（`20260911-splitunify-x-review-r4`，進行中）——只問 E1／E2 是否閉合。
   🔴 其必答 1 是主委自己也沒把握的一條：v4 寫 `label_end_ms >= test_start_ms`，
   既有實作是 `label_end_ms > test_start - embargo`，兩者不等價；正確條件式待三家給。
2. R4 收斂 → 若無 P0/P1 即**進第一批**（B1：`D-002` 延伸檔、`split_unify.json`、既有紅 nodeid 清單；
   **不動生產碼**）。
3. B2a（boundary builder）→ B2b（投影）→ B2c（golden）→ B3（接線）→ B4（報告與畫面）。

## 🔴 既有紅盤點（非本票造成，建議另立 `REDSWEEP`）
`tests/momentum/Analysis` 全跑 **20 failed / 1615 passed**：①8 條單獨跑會綠（測試間污染）
②golden digest 3 條 ③inventory／contract sync 漂移。B1 之 Task 1.3 會把它們凍成逐條 nodeid 清單，
驗收改「只准變短」的方向性判準（不再用聚合計數）。

## 後續票序
`SPLITUNIFY` → `GLOBALH`（中票）→ **使用者 UAT B26–B34**（最後）。

## 踩坑（本 session 新增）
- FF run 之 `data_cache/features/**/timestamps.parquet` 是 **epoch 秒**（int64）。
  同一條路徑上流著 positional／秒／毫秒三種單位。
- `_normalize_ic_time_index`（`ic_filter_orchestrator.py:259`）是**「秒」語意**，
  餵毫秒會 raise。事件側時鐘是毫秒 ⇒ 不可復用它。
- `reconcile_cluster_attribution_check.sh` 只驗「ID 字串出現在檔內」，**不驗歸屬是否正確**
  （殘留 `SU-RESID-1`）。攔下兩類收斂失誤的是委員逐條對照，不是機檢。
- `gate.sh dispatch` 帶 `--spec` 會被當 impl 派工而要求 `--brief`＋`--reconcile`；
  review／stamp 派工不要帶 `--spec/--todo`。session `kind` 只准
  `{impl, review, stamp, consult, fix}`——`confirm` 會 fail-closed。
- `debt_clear.sh` 要求 `sources.lock` mode=review；discovery 需
  `reconcile_build.sh <session> --mode review --rebuild`（**不可**再帶委員檔）。
- 🔴 **grep 加 `head -N` 會讓我做出錯誤結論**：v3 曾據截斷輸出宣稱
  `extract_event_patterns` 無任何 caller，實際有 8 處測試 caller（`CODEX-R3-P2-04` 抓出）。

## 殘留
`EA-RESID-1..6`；`EVTLABEL R-1..R-9`；stage6b `role="diagnostic"`；`REDSWEEP` 約 17 條；
`SPLITUNIFY R-1..R-5` 與 `SU-RESID-1`（見 SPEC §N）。
