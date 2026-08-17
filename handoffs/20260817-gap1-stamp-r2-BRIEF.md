# GAP-1 review-R2 收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-x-review-r2/synth.md

## 任務
對 `stamp-target`（SPEC closure R2 收斂檔）append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`501fcd2fcfd2…`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-review-r2/synth.md` 重跑確認，
不一致請 BLOCKED 而非照抄。

## 為何現在補（出生事故）
主委在 R1／R2 兩輪 SPEC 審查後**漏跑戳記步驟**（制度：reconcile 須委員戳記核可，
`scripts/reconcile_stamps_check.sh` 機器強制）。R3 輪 codex 依 `AGENTS.md` 第 12 條正確停工並指出，
主委已 abandon R3 輪（kind=collection-failed，另因 composer 遇 Cursor `resource_exhausted`），
補本輪後才重派 R3。**另兩份**（`20260817-gap1-x-consult-r1`、`20260817-gap1-x-review-r1`）
於後續兩輪各自處理（stamp brief 只容許單一 stamp-target）。

## 核可判準（勿一律 APPROVED）
1. 群集 E1–E4 是否逐條對應附錄之 8 個 canonical ID，有無掉項或「引用 ID 但義務只寫一半」。
2. Verdict 與內文是否一致。
3. 「未採納」節之駁回是否附證據：主委駁回 `GROK-R2-P1-01` 之修法（DSR 改「同一 V 當分母」），
   判準＝`n_trials=1` 時 DSR 須退化為 PSR（主委實跑：論文形式 →1.000000＝PSR；grok 形式 →0.963181≠PSR）。
   **若你認為該駁回不成立，請 BLOCKED 並附可重現反例。**
4. 對應 SPEC 修補是否確實存在（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`，可 grep finding ID）。
   註：SPEC 於本輪後又修一處（移除 `variance_source="analytic"` 殘留，grok R3 指出），
   該修補不影響本 synth 之 body hash。

## 戳記格式（逐字）
```
RECONCILE-STAMP: APPROVED
family: <codex|composer|grok>
target: handoffs/reconcile/20260817-gap1-x-review-r2/synth.md
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
