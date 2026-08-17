# GAP-1 review-R4 收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-x-review-r6/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`46b7dff1189d8b20ffd4899bab0d5a5d2f81df606c233aa7b7c63004fc84258d`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-review-r6/synth.md` 重跑確認，
不一致請 BLOCKED 而非照抄。

## 背景
GAP-1 之 SPEC 審查共跑七輪（收斂軌跡 23→7→11→7→4→1→收束）。本檔為第六輪（群集 H1–H2，宣告為最終 SPEC 輪）之收斂記錄。
較早三份（consult-r1／review-r1／review-r2）已三家 APPROVED；r5／r6／r7 於後續輪處理。

## 核可判準（勿一律 APPROVED）
1. 群集 H1–H2 是否逐條對應附錄之 6 個 canonical ID，有無掉項或「引用 ID 但義務只寫一半」。
2. Verdict 與內文是否一致。
3. 主委裁決「四條 codex FATAL 全採（不以另兩家判無 FATAL 壓過）」是否附理由；composer/grok 之兩項 RESIDUAL-OK
   （hash 演算法、平均排名代數式）主委改為當輪寫死——若你認為不當，請 BLOCKED 並附理由。
4. 對應 SPEC 修補是否確實存在（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`，可 grep finding ID）。
   註：SPEC 於本輪後又經 R7／R8 修補，那些屬後續輪次，**不影響**本檔 body hash，勿因此 BLOCK。

## 戳記格式（逐字）
```
RECONCILE-STAMP: APPROVED
family: <codex|composer|grok>
target: handoffs/reconcile/20260817-gap1-x-review-r6/synth.md
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
