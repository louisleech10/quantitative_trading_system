# GAP-1 三份 reconcile 之 RECONCILE-STAMP 核可（consult-R1／review-R1／review-R2）

brief-kind: stamp

## 任務
對下列**三份**收斂檔各 append 一則 `RECONCILE-STAMP`（放在該檔 `## 戳記` 區段內，勿動其他區段）：

1. `handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md`（偵察四方收斂；body sha256=`488f367e1fd1`）
2. `handoffs/reconcile/20260817-gap1-x-review-r1/synth.md`（SPEC adversarial R1 收斂；body sha256=`b5784275dc5d`）
3. `handoffs/reconcile/20260817-gap1-x-review-r2/synth.md`（SPEC closure R2 收斂；body sha256=`501fcd2fcfd2`）

body sha256 之定義＝`## 戳記` 標題**前**之內容（`bash scripts/reconcile_body_hash.sh <synth>` 實跑取得；
請自行重跑確認與上列一致，不一致請 BLOCK 而非照抄）。

## 為何現在補（出生事故，請一併確認已修正）
主委在 R1／R2 兩輪 SPEC 審查中**漏跑本步驟**（制度要求：reconcile 須委員戳記核可，
gate 以 `scripts/reconcile_stamps_check.sh` 機器強制）。R3 輪 codex 依 `AGENTS.md` 第 12 條
正確停工並指出此缺口，主委已將 R3 輪 abandon（kind=collection-failed）並補跑本輪。
本輪通過後才會重派 R3。

## 核可判準（逐份獨立判定，勿一律 APPROVED）
對每一份 synth，確認：
1. **群集/處置** 是否逐條對應附錄之 canonical findings，有無掉項或「引用 ID 但義務只寫一半」。
2. **Verdict** 是否與內文一致（例如寫「需修補後合併」而處置卻宣稱全關）。
3. 主委標為「未採納／部分採納」者是否**附證據**（review-R2 有一條駁回 grok 修法，
   判準＝N=1 時 DSR 須退化為 PSR；如你認為該駁回不成立，請 BLOCK 並附反例）。
4. 對應之 SPEC 修補是否確實存在（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`，可 grep finding ID）。

## 戳記格式（逐字）
```
RECONCILE-STAMP: APPROVED
family: <codex|composer|grok>
target: handoffs/reconcile/<session>/synth.md
body_sha256: <你實跑取得的完整 sha256>
date: 2026-08-17
note: <一句實質理由；禁空話>
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在 `note` 寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 到各檔 `## 戳記` 區段；不得改任何 finding、群集或 Verdict 內容。
2. 不得 commit、不得 push。
3. 三份都要處理；漏一份視為未完成。
4. 不得把 findings 或評論 append 進 synth（本輪產 stamp，不產 finding）。

## 產出
在你自己的交件檔回報：三份各自的判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句理由。
收尾清 /tmp workdir（保留 claude-501）。
