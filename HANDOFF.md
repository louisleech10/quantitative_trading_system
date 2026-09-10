# HANDOFF — 當前任務狀態

**更新：2026-09-11 凌晨｜票：`SPLITUNIFY`（大；RISK a,b,c,d）｜狀態：consult 收斂完成、SPEC＋TODO 皆過 `doc_format_precheck`，下一步＝三家 adversarial 審 → B1 實作。**

## 使用者離線授權（2026-09-10 深夜，逐字）
> 「我要睡了，你繼續做完，有問題找委員會討論共識，做完前不要停下來」

⇒ **不停、不問、斷路器交委員會共識決**；分歧看碼證不數人頭，不決則採較嚴版並具名殘留。
切法亦由使用者裁定「你跟委員討論共識」，故不回頭問方向。

## 前一票 `EVTLABEL`：已收（commit `bcea2c6a`）
三 Phase／17 Task 全完工。四批 code review 各經三家全員收斂（16＋19＋10 條全採納，含一條 P0）。
`gate 2`／`3a`／`3b`／`3c` 全 PASS；mutation 6＋3＋8 全紅、對照組綠、UNCOVERED=0。
前端 `npm run build` rc=0、vitest 707 passed。真實 ETHUSDT 12h 端到端：1695 事件／266 正／1429 反，植入特徵 AUC 恰為 1。

## 當前 `SPLITUNIFY`
- **consult 共識**（`handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`，commit `9f75e4a7`）：
  D1 時間切分（`SplitPlan`）為 canonical 權威、事件切分改為**投影**；
  🔴 D2 禁以全域 scalar 冒充 per-symbol，多 symbol 未支援前 **fail-closed**；
  D3 投影是 train／purged／test **三態**（不可回退二態）；D4 GAP-3 走 `D-002` 延伸檔；D5 大票分四批。
- **文件**：`docs/SPLITUNIFY_SPEC.md`、`docs/SPLITUNIFY_TODO.md`（B1–B4／Task 1.1–4.1，各含九欄）皆 rc=0。
- **批次**：B1 文件＋枚舉 SoT（不動生產碼）／B2 純函式＋golden（不接線）／B3 接線＋多 symbol fail-closed／B4 報告與前端。
- **下一步**：三家 adversarial 審（session 名須為 `20260911-splitunify-x-review-r1` 形式）→ B1。

## 🔴 既有紅盤點（非本票造成，建議另立 `REDSWEEP`）
`tests/momentum/Analysis` 全跑 **20 failed / 1615 passed**（已修 3 條，其餘約 17 條未修）：
① 8 條單獨跑會綠 ⇒ 測試間污染（persist 重導洩漏）②golden digest 3 條 ③inventory／contract sync 漂移。
**本票驗收以此為基準**，不得把它們算進 `SPLITUNIFY`。

## 後續票序
`SPLITUNIFY` → `GLOBALH`（中票，全域靜默只用第一個 horizon）→ **使用者 UAT B26–B34**（最後）。

## 踩坑（沿用）
mutation 腳本要求工作區對 HEAD 乾淨，**須先 commit 再跑**。
G-7 trailer：產品碼 commit 一律在**最後一段**加 `Governance-Scope: momentum api tests ...`。
`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc；rc 一律直接取。

## 殘留
`EA-RESID-1..6`（EVTALIGN）；`EVTLABEL R-1..R-9`（SPEC §N，已登記）；stage6b `role="diagnostic"`；`REDSWEEP` 約 17 條。
