# HANDOFF — 當前任務狀態

**更新：2026-09-06｜狀態：`G3-D2` **五段全部收工，票已 CLOSED**。等使用者實機 UAT。**

## ✅ G3-D2 收案完成

五段串行皆過三家 code review 至閉合：
B-D0 `49204458`／B-D1 `54d8eb8e`／B-D3 `52295c6a`／B-D4 `bc8c5e1e`／**B-D5 `2538b4f4`**。
逐批收據（測試選擇器、golden、mutation、review 輪次）＝`docs/GAP3D2_IMPL_HANDOFF.md` §5。

`/search` 五維度之灰／鎖**全部解除**，只剩兩對幾何零窗組合依契約 `rejected_pairs` 灰掉並寫理由。

## 🔴 下一件＝**使用者實機 UAT**（我不能代驗）

`白話說明/GAP-3驗收清單.md` 之 **B3** 已由「必定未完成」改為「待你實機驗」。
其餘 19 項多數先前已 OK。UAT 通過前**不要**在此票上再堆新工作。

## 收案時的終局數字（B-D5 R2 後）

`tests/momentum/event_samples` **532**；`tests/api/test_gap3_random_control.py` **27**；
`cd frontend && npx vitest run` **546／72 檔**；`tsc --noEmit` **8 行既有債**；
golden **label 46 ／ random_control 2**（皆 rc=0）；解耦 **BASELINE OK**；
mutation `handoffs/20260906-gap3d2-b5-mutate.py` **39/39 符合預期**。

**`B1-VERIFY-1` 已履行**：`tests/api` 867 passed／6 failed／3 errors、
`tests/governance` 1739 passed／10 failed——失敗集合經**父 commit 對等比較**
（detached worktree ＋ `comm -23`）確認**無一由本 epic 造成**。

## 開放殘留（21 條，皆具三值理由）

`docs/IC_QUANT_GAP_REGISTRY.md`「G3-D2 實作批殘留」表。B-D5 新增四條：
`B5-SPECGAP-1`／`B5-SINGLECLASS-1`／`B5-GENERATOR-WIRE-1`／`B5-BARPRECOND-1`。
另新增治理殘留 `R-G7-OFF-2`（2 條 `test_gov_check_cheap_first` 長期紅，係 G-7 停用之 fallout）。

## 環境現況

開放債為零；無未推送 commit。工作區餘 2026-09-01 遺留之三個 `uat_samples/*`、
九個 `.claude/gate/*baseline*` 未追蹤檔與 `market_data/*` 快取異動——**皆非主線產物，勿順手 commit**。
另有一個先前既有的 `stash@{0}: review-temp`（非本 session 產生，未動）。
🔴 紀律：`pytest tests/governance` 小時級（實測 3050s）且不含量化測試，只有「動共用控制流」
**且**「收 epic 前」兩條件皆成立才跑；**且不得與其他 mutate-restore 型 pytest 並行**（本批踩過）。
