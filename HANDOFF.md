# HANDOFF — 當前任務狀態

**更新：2026-09-10 晚｜票：`EVTLABEL`（大；RISK a,b,c,d）｜狀態：Phase 1／Phase 2 之程式與驗證皆已通過（gate PASS、mutation UNCOVERED=0）；下一步＝進 Phase 3「匯入標籤模式」。**

## 使用者本次指示（逐字要點）
> 開工前稽核 HANDOFF/memory vs repo，稽核後直接開票不要再問方向；大任務走完整管線 SPEC+TODO+三家 adversarial+白話否決；三 Phase 順序不可調；主目標原話入 SPEC §A，任何審查延後它＝否決點彈窗；全部做完才重驗 B26–B34；每批 commit 後 push、更新白話看板。追加：TIERTOGGLE 插第 1 段前（前後端開關同步、不得再有幽靈狀態）；SPLITUNIFY 排 EVTLABEL 之後、UAT 之前（切法交委員會定）；GLOBALH 升中票；表頭一律用統計學／業界標準名；討論結論寫進 `白話說明/接下來要做的票.md`。

## 檔案
SPEC `docs/EVTLABEL_SPEC.md`／TODO `docs/EVTLABEL_TODO.md`（v4；三輪三家審 54 條全採納＋三家 RECONCILE-STAMP APPROVED，commit `0dbe40ff`）。
白話：`白話說明/EVTLABEL規格白話.md`、`白話說明/EVTLABEL施工進度.md`、`白話說明/接下來要做的票.md`。
自證：`handoffs/20260910-evtlabel-mutate.py --phase {2,3}`；關卡 `scripts/evtlabel_phase_gate.sh <phase>`。

## 已完成（commit）
- `e8903c28` TIERTOGGLE 幽靈開關（前後端同步）＋ `e18045c7` 前端 build 修復（`MarginalICTable.tsx` rules-of-hooks 真 bug，非本票造成）
- `0c9cd69d` B1／Phase 1 揭露（label 規則、h/k 單位＝事件週期根數）＋ `b59ebcba` review R1 修補（`consumed_event_ids` fail-closed）
- `f5ed2c48` B2／Phase 2 purge 依答案窗換算 ＋ `860724f0` mutation 補洞（原測試自己算好 purge ⇒ 假綠）
- `5e472611` B2 review R1 四條修補（三家皆判可進 B3、無 P0/P1）

## 驗證狀態（Phase 2）
Phase 2 九檔 **111 passed**；`--phase 2` **6/6 RED、控制組綠、UNCOVERED=0**；`evtlabel_phase_gate.sh 2` **PASS**；解耦與 `scripts/decouple_baseline.txt` 逐值相同（R2=1 R3=17 R4=3，rc=0）。

## 下一步（順序）
1. **B3–B6＝Phase 3「匯入標籤模式」**（SPEC Task 3.1–3.11）：CSV 0/1 直接當標籤算 rank-biserial（=2·AUC−1），顯著性走 Mann-Whitney＋block 置換、FDR 照舊；報酬版 IC 留第二欄；報告揭露用哪一種；倖存者輸出帶 `sample_scope=event` 與標籤來源。每批三家 code review、commit+push、更新看板。
2. `SPLITUNIFY`（`SplitPlan` vs `EventSplitPlan` 兩套統一；切法交委員會 consult 定）→ `GLOBALH`（中票，全域靜默只用第一個 horizon）。
3. **全部做完才**叫使用者驗收 B26–B34＋新增項目。

## 踩坑（本 session 新增）
`tests/api/test_scan_cube.py` 的 thin staged stub 與 `_run_event_label_stages` 真實回傳漂移 ⇒ 該測試自 `efb16e4c` 起**靜默紅兩天**；已提成 `_SCAN_CELL_STAGED_STUB` 並加 AST 守衛機械擋（缺鍵指名而紅）。生產側刻意不補 `.get(...,0)` 回退——那會讓 embargo 靜默變小＝fail-open。
mutation 腳本要求工作區對 HEAD 乾淨，**須先 commit 再跑**。
G-7 trailer：產品碼 commit 一律在**最後一段**加 `Governance-Scope: momentum api tests ...`，漏了只能改寫歷史。

## 殘留
`EA-RESID-1..6`（EVTALIGN）未變；EVTLABEL `R-1..R-9` 於 SPEC §N，收案時登記 `docs/IC_QUANT_GAP_REGISTRY.md`。
