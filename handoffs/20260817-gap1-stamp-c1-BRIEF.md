# GAP-1 review-R2 收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md

## 任務
對 `stamp-target`（偵察四方收斂檔(31 findings)）append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`488f367e1fd1…`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md` 重跑確認，
不一致請 BLOCKED 而非照抄。

## 為何現在補（出生事故）
主委在 R1／R2 兩輪 SPEC 審查後**漏跑戳記步驟**（制度：reconcile 須委員戳記核可，
`scripts/reconcile_stamps_check.sh` 機器強制）。R3 輪 codex 依 `AGENTS.md` 第 12 條正確停工並指出，
主委已 abandon R3 輪（kind=collection-failed，另因 composer 遇 Cursor `resource_exhausted`），
補本輪後才重派 R3。`20260817-gap1-x-review-r2` 已於前一輪取得三家 APPROVED（`reconcile_stamps_check.sh` 實跑 PASS）；
本輪處理 consult-r1，`review-r1` 於下一輪處理（stamp brief 只容許單一 stamp-target）。

## 核可判準（勿一律 APPROVED）
1. 群集 C1–C5 是否逐條對應附錄之 21 個 canonical ID(三家鎖定;claude 10 條為非鎖來源)，有無掉項或「引用 ID 但義務只寫一半」。
2. Verdict 與內文是否一致。
3. 「未採納/部分採納」節：主委對 composer 之 Phase A 分期理由做了具名裁決（理由＝`MinBTL` 公式分子
   即 `ln(N)`，故 MinBTL 吃 N，不能在無 N 帳本時先上線）。若你認為該裁決不成立，請 BLOCKED 並附反例。
   另「前提修正」節載入使用者兩次 session 中途補充（成熟度地圖），請確認其與 repo 實況一致
   （receipt：`ls data/optuna*` 無、`results/optimization_results` 不存在）。
4. 對應 SPEC 修補是否確實存在（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`，可 grep finding ID）。
   註：本檔為**偵察階段**收斂（產出 SPEC 之義務來源），非 SPEC 審查輪；勿以「SPEC 尚缺某函式」BLOCK。

## 戳記格式（逐字）
```
RECONCILE-STAMP: APPROVED
family: <codex|composer|grok>
target: handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md
body_sha256: <你實跑取得的完整 sha256>
date: 2026-08-17
note: <一句實質理由；禁空話>
```
不核可時把 `APPROVED` 改 `BLOCKED`，`note` 寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict。
2. **不得**把 findings 或評論 append 進 stamp-target（本輪產 stamp，不產 finding）。
3. 不得 commit、不得 push。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句理由。
收尾清 /tmp workdir（保留 claude-501）。
