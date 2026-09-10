# HANDOFF — 當前任務狀態

**更新：2026-09-10 深夜｜票：`EVTLABEL`（大；RISK a,b,c,d）｜狀態：🔴 **三 Phase 全部完工**（Task 1.1–3.11 共 17 個 Task）。四批 code review 各經三家、全部收斂（16＋19＋10 條全採納，含一條 P0）。`gate 2`／`3a`／`3b`／`3c` 皆 PASS。下一步＝`SPLITUNIFY`（切法交委員會 consult）→ `GLOBALH` → 使用者 UAT。**

## 使用者本次指示（逐字要點）
> 開工前稽核 HANDOFF/memory vs repo，稽核後直接開票不要再問方向；大任務走完整管線 SPEC+TODO+三家 adversarial+白話否決；三 Phase 順序不可調；主目標原話入 SPEC §A，任何審查延後它＝否決點彈窗；全部做完才重驗 B26–B34；每批 commit 後 push、更新白話看板。追加：TIERTOGGLE 插第 1 段前（前後端開關同步、不得再有幽靈狀態）；SPLITUNIFY 排 EVTLABEL 之後、UAT 之前（切法交委員會定）；GLOBALH 升中票；表頭一律用統計學／業界標準名；討論結論寫進 `白話說明/接下來要做的票.md`。

## 檔案
SPEC `docs/EVTLABEL_SPEC.md`／TODO `docs/EVTLABEL_TODO.md`（v4；三輪三家審 54 條全採納＋三家 RECONCILE-STAMP APPROVED，commit `0dbe40ff`）。
白話：`白話說明/EVTLABEL規格白話.md`、`白話說明/EVTLABEL施工進度.md`、`白話說明/接下來要做的票.md`。
自證：`handoffs/20260910-evtlabel-mutate.py --phase {2,3a,3b,3c}`；關卡 `scripts/evtlabel_phase_gate.sh <0|1|2|3a|3b|3c>`。
🔴 phase 已改**批次同粒度**字串：原本 3a/3b/3c 一律映射成 `"3"`，等於「前一批要對後一批才會寫的程式自證」⇒ 全 SKIP ⇒ 關卡恆紅且**無法在當批解決**。

## 已完成（commit）
- `e8903c28`＋`e18045c7` TIERTOGGLE 幽靈開關＋前端 build 修復｜`0c9cd69d`＋`b59ebcba` Phase 1 揭露與其 review 修補｜`f5ed2c48`＋`860724f0` Phase 2 purge 換算與 mutation 補洞
- `5e472611` B2 review R1 四條修補（三家皆判可進下一批、無 P0/P1）
- `fc83cce5` 修兩條靜默紅：管線順序測試（9/8 warmup 預檢前移造成）＋ IC wiring 機檢（**我 `e8903c28` TIERTOGGLE 造成**，checker 只認逐鍵字面）
- `a69287f3` Task 3.1／3.2（枚舉 SoT＋契約＋請求欄透傳）
- `648ef6e3` Task 3.3（0/1 向量、值域閘、選樣預檢、三元組第二腿）

## 驗證狀態（Phase 3 收工）
- `gate 2`／`3a`／`3b`／`3c` **全部 PASS**；mutation `--phase 2`(6)／`3a`(3)／`3b`(8) 皆全紅、對照組綠、UNCOVERED=0。
- 前端 `npm run build` rc=0；vitest **707 passed（91 檔）**；`npx tsc --noEmit` 無新錯。
- G-6 survivor golden 未漂移；解耦與 `scripts/decouple_baseline.txt` 逐值相同（R2=1 R3=17 R4=3，rc=0）。
- 真實 kline 端到端（ETHUSDT 12h，1695 事件／266 正／1429 反）：植入特徵 AUC 恰為 1、錯位必擋。
- benchmark 已併入 `gate 3b/3c`（含 10% NaN 路徑）——一次性 receipt 擋不住未來欄數膨脹時重犯。

## 🔴 既有紅盤點（跑全套才發現，**非本票造成**，建議另立 `REDSWEEP` 票）
`tests/momentum/Analysis` 全跑 **20 failed / 1615 passed**。已修 3 處；**其餘約 17 條未修**，分三類：
① `test_ic_persist_redirect_unit`／lightgbm／xgboost 共 8 條**單獨跑會綠** ⇒ 測試間污染（persist 重導洩漏）
② golden digest 3 條（`test_ic_1a_cut1_golden`／`test_ichc_p2_golden`／`test_ic_persist_redirect_golden_ab`）
③ inventory／contract sync 漂移（`factories.py:474` 新消費者未登記、`event_return_table` 節不存在）
皆以 patch 反向套用逐一確認在 HEAD 即紅。**不在 EVTLABEL scope 內**，收本票後再處理。

## 下一步（順序）
1. 🔴 **`SPLITUNIFY`**：`SplitPlan` 與 `EventSplitPlan` 兩套切分統一。切法**交委員會 consult 定共識**（使用者裁定），定案後走 SPEC → 三家審 → 實作。排在 UAT 之前——UAT 會同時看到兩個驗證段數字。
2. `SPLITUNIFY`（`SplitPlan` vs `EventSplitPlan` 兩套統一；切法交委員會 consult 定）→ `GLOBALH`（中票，全域靜默只用第一個 horizon）。
3. **全部做完才**叫使用者驗收 B26–B34＋新增項目。

## 踩坑（本 session 新增）
`tests/api/test_scan_cube.py` 的 thin staged stub 與 `_run_event_label_stages` 真實回傳漂移 ⇒ 該測試自 `efb16e4c` 起**靜默紅兩天**；已提成 `_SCAN_CELL_STAGED_STUB` 並加 AST 守衛機械擋（缺鍵指名而紅）。生產側刻意不補 `.get(...,0)` 回退——那會讓 embargo 靜默變小＝fail-open。
mutation 腳本要求工作區對 HEAD 乾淨，**須先 commit 再跑**。
G-7 trailer：產品碼 commit 一律在**最後一段**加 `Governance-Scope: momentum api tests ...`，漏了只能改寫歷史。

## 殘留
`EA-RESID-1..6`（EVTALIGN）未變；EVTLABEL `R-1..R-9` 於 SPEC §N，收案時登記 `docs/IC_QUANT_GAP_REGISTRY.md`。
