# HANDOFF — 當前任務狀態

**更新：2026-09-11 凌晨｜票：`SPLITUNIFY`（大；RISK a,b,c,d）｜狀態：R1 三家審已收斂（13 群集）；consult synth 經兩次修訂後三家重蓋中（grok 已核可、codex 進行中、composer 待派）。SPEC 需改 v2 才可進第一批。**

## 使用者離線授權（2026-09-10 深夜，逐字）
> 「我要睡了，你繼續做完，有問題找委員會討論共識，做完前不要停下來」

⇒ **不停、不問、斷路器交委員會共識決**；分歧看碼證不數人頭，不決則採較嚴版並具名殘留。

## 🔴 本 session 最重要的三件事

1. **戳記閘攔下我自己的收斂失誤，兩輪各抓一類。** codex（`-STAMP-R1`）REJECTED：
   synth 把 `CODEX-R1-P1-02` 反駁過的說法寫成「三家共同」。composer（`-STAMP-R2`）
   APPROVED 但附註 finding ID 歸屬錯置。我據此把 19 條逐條重對，**11 條錯或缺**——
   grok 的 7 條**全部**掛錯；D5 根本無 finding 支撐卻掛了兩條不相干 ID。
   consult synth 由 5 個決議項修正為 **8 個**（新增 D6／D7／D8）。
2. **D6 是本票的先決條件（原收斂把它弄丟了）**：`EventSplitPlan` 唯一 producer
   `split_events` 只被 `pipeline.py:691` 呼叫，其唯一生產 caller
   `case_import_service.py:1610` **既無 `SplitPlan` 也無 feature 列 universe**
   ⇒ SPEC v1 寫出的「投影」**沒有落點**。codex 之落地建議已採納：單一 boundary builder
   住 `momentum/core/split_preview.py`、orchestrator 與 pipeline 共同呼叫；
   無 canonical feature universe 之匯入流程只能明示 `event-study-only`，不得宣稱 OOS。
3. **我自己的探針否證了我自己的方案**：`handoffs/20260911-probe-splitunify-universe-gap.py`
   （receipt `20260910T154323Z-splitunify-universe-gap.log`，rc=1）——真實 ETHUSDT 1h
   20352 列，未裁切時 features 與 bars 兩 universe 逐值相同；EVTALIGN 裁頭尾後邊界位移
   5 根→2h、24 根→10h、168 根→67h。⇒「兩端各自算同一公式」不成立。

## 檔案
- SPEC `docs/SPLITUNIFY_SPEC.md`（**v1，須改 v2**）／TODO `docs/SPLITUNIFY_TODO.md`（**v1，須改 v2**）
- consult 收斂 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`（D1–D8；body-hash `120b4d042d38…`）
- R1 審收斂 `handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md`（C1–C13）
- 主委自產審查 `handoffs/20260911-splitunify-claude-selfreview.md`（`CLAUDE-R1-*` 8 條）
- 白話 `白話說明/SPLITUNIFY規格白話.md`、`白話說明/SPLITUNIFY施工進度.md`

## 下一步（順序）
1. codex `-STAMP-R4`、composer `-STAMP-R5` 重蓋 ⇒ `reconcile_stamps_check.sh` rc=0。
2. **改 SPEC v2＋TODO v2**：併入 R1 之 C1–C13 與 consult 之 D6／D7／D8。重點：
   投影簽名補 `feature_index`＋`manifest`；三態＝兩容器（`assignments`＋`purged`，
   purge reason 沿用 `event_import_contract.json:465-467`）；`summary` 12 鍵逐鍵契約；
   `clusters` 抽 `build_time_clusters`；B3 驗收改 known-red nodeid `--deselect` 後 rc=0
   （刪「failed <= 20」聚合期望數）；G-3 拆 G-3a 遷移報告／G-3b 獨立 oracle；
   mutation 由 3 條擴為 12 條。
3. SPEC v2 派三家 R2 審 → B1。

## 🔴 既有紅盤點（非本票造成，建議另立 `REDSWEEP`）
`tests/momentum/Analysis` 全跑 **20 failed / 1615 passed**：①8 條單獨跑會綠（測試間污染）
②golden digest 3 條 ③inventory／contract sync 漂移。**本票驗收以此為基準**，
且驗收方式已改為逐條 `--deselect`，不再用聚合計數。

## 後續票序
`SPLITUNIFY` → `GLOBALH`（中票）→ **使用者 UAT B26–B34**（最後）。

## 踩坑（本 session 新增）
- FF run 之 `data_cache/features/**/timestamps.parquet` 是 **epoch 秒**（int64），不是毫秒也不是
  datetime；當 ms 用會跑到 1970。同一條路徑上流著 positional／秒／毫秒三種單位。
- `reconcile_cluster_attribution_check.sh` 只驗「ID 字串出現在檔內」，**不驗是否被正確的
  決議項引用** ⇒ 兩類收斂失誤都擋不住（殘留 `SU-RESID-1`）。真正攔下來的是委員逐條對照。
- `gate.sh dispatch` 帶 `--spec` 會被當 impl 派工而要求 `--brief`＋`--reconcile`；
  review／stamp 派工不要帶 `--spec/--todo`。
- `debt_clear.sh` 要求 `sources.lock` mode=review；discovery 需
  `reconcile_build.sh <session> --mode review --rebuild`（**不可**再帶委員檔）。

## 殘留
`EA-RESID-1..6`；`EVTLABEL R-1..R-9`；stage6b `role="diagnostic"`；`REDSWEEP` 約 17 條；
`SU-RESID-1`（attribution checker 擋不住歸屬錯置）。
