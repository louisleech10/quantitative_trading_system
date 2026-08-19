# GAP-2 B5 code review 收斂檔之 RECONCILE-STAMP 核可（三家 sentinel「可收案」；GAP-2 收案前最後一次戳記）

VERIFY-EXEMPT:doc-example:gap2-b5-stamp-brief-criteria

> 本檔為**給委員的核可判準清單**。🔴 **輕量輪**：只讀 receipt＋跑秒級 vitest；**禁跑 python 探針／pytest 重測／npm run build**（三家並行會互搶 CPU——B4 教訓摩擦七十七）；in-memory only；主委派出後不動工作區。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260819-gap2-b5-review-r24/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`2d0102371d30834714b98fdf84f5370283f02261949858d0d0433d550c0d5d47`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260819-gap2-b5-review-r24/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 背景
B5 code review（`20260819-GAP2-B5-REVIEW-R24`）三家皆 sentinel「可收案」；收斂為 O1（無修補；三條新殘留 G2-R6／R7／R8 待主委登記 registry）。本輪 APPROVED ⇒ B5 CLOSED ⇒ 主委做 GAP-2 收案文件（registry／ROADMAP／白話／HANDOFF）。

## 核可判準（逐項查；任一不成立即 BLOCKED）
1. **0 掉項**：`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260819-gap2-b5-review-r24/sources.lock` → PASS；O1 引用全部 3 個 sentinel ID。
2. **Verdict 與三家回件一致**：三家皆「可收案」、BLOCKING 無；O1 之三條新殘留與三家段 E 建議一致（tsc 既有 8 紅／bench 內嵌 gate／REASON_TEXT）；三值理由（blocked-by／needs-research／user-ruling）是否貼切。
3. **輕量重驗**：`cd frontend && npx vitest run src/components/ic-analysis/MarginalICTable.test.tsx src/store/icAnalysisStore.marginalIc.test.ts` → 9 passed（<10 秒）；`bash scripts/ic_wiring_check.sh` rc=0（~15 秒）；build／探針以 receipt 為準（`handoffs/run_receipts/20260819-gap2-b5-npm-build.log`；`20260819T031612Z/031810Z/031911Z/032022Z-gap2-B{1,2,3,4}-probe.log`）。
4. `git diff e686ed73 HEAD --name-only` 只含 handoffs（receipts／brief／synth）；`ffb728ab` 之程式檔只有白名單四檔＋新元件／測試。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-19 sha256:<你實跑取得的完整 body sha256> task:20260819-GAP2-B5-STAMP-R25
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段（**請務必 append，勿只寫在交件檔**）；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target；不得 commit／push；禁就地改檔；禁重測試。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋判準 1–4 逐項結果。收尾清 /tmp workdir（保留 claude-501）。
