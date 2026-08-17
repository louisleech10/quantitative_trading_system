# GAP-1 review-R4 收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-x-review-r4/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`61a8a01ce1bddaccbf0060b8caab542e2ff6345f432141acd87e6c50caa1b316`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-review-r4/synth.md` 重跑確認，
不一致請 BLOCKED 而非照抄。

## 重派原因（R4-restamp）
上一輪 codex 以「overview 寫 codex 5 條 BLOCKING、附錄 `[BLOCKING]` 標記為 6」BLOCKED（正確：主委把
P1-05 分開敘述造成字面不一致）。已更正為「6 條」，**語意不變**，body hash 因此改變 ⇒ 三家須重蓋。

## 背景
GAP-1 之 SPEC 審查共跑七輪（收斂軌跡 23→7→11→7→4→1→收束）。本檔為第四輪（群集 F1–F4）之收斂記錄。
較早三份（consult-r1／review-r1／review-r2）已三家 APPROVED；r5／r6／r7 於後續輪處理。

## 核可判準（勿一律 APPROVED）
1. 群集 F1–F4 是否逐條對應附錄之 11 個 canonical ID，有無掉項或「引用 ID 但義務只寫一半」。
2. Verdict 與內文是否一致。
3. 「未採納」節之裁決是否附證據：本輪主委裁決「全採 codex 較嚴版、不動用 95% 就收條款」，
   理由＝四條修補皆為 SPEC 內局部可寫死者。若你認為該裁決不成立，請 BLOCKED 並附理由。
4. 對應 SPEC 修補是否確實存在（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`，可 grep finding ID）。
   註：SPEC 於本輪後又經 R5／R6／R7 三次修補，那些屬後續輪次，**不影響**本檔 body hash，勿因此 BLOCK。

## 戳記格式（逐字）
```
RECONCILE-STAMP: APPROVED
family: <codex|composer|grok>
target: handoffs/reconcile/20260817-gap1-x-review-r4/synth.md
body_sha256: <你實跑取得的完整 sha256>
date: 2026-08-17
note: <一句實質理由；禁空話>
```
不核可時把 `APPROVED` 改 `BLOCKED`，`note` 寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict。
2. **不得**把 findings 或評論 append 進 stamp-target。
3. 不得 commit、不得 push。

## 產出
判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句理由。收尾清 /tmp workdir（保留 claude-501）。
