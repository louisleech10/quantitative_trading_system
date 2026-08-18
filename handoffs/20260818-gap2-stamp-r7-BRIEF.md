# GAP-2 SPEC review-R6 收斂檔（SPEC 定版之最終收斂檔）之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap2-x-review-r6/synth.md

## 任務
對 `stamp-target`（SPEC adversarial R6 三家收斂檔；一群集 Q1；三家皆 sentinel）append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`8d065f9aa131…`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap2-x-review-r6/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 為何現在補（出生事故）
主委在 consult-R1、review-R1、review-R2 三輪後**漏跑戳記步驟**（制度：reconcile 須委員戳記核可，`scripts/reconcile_stamps_check.sh` 機器強制），R3 輪 codex 依 `AGENTS.md` 第 12 條正確停工。前六份 synth 已三家 APPROVED；本輪為 review-R6 之常規戳記；APPROVED 後 SPEC 定版、進白話閘與 TODO 生成（stamp brief 只容許單一 stamp-target）。全數補齊後重派 R4。

## 核可判準（勿一律 APPROVED）
1. 群集 Q1 是否對應附錄 3 個 sentinel ID；有無掉項或「引用 ID 但義務只寫一半」。
2. Verdict「可進 TODO；SPEC 定版」與三家 R6 review 一致；SPEC 自 R5 修訂後未再改動（`git log -1 -- docs/GAP2_MARGINAL_IC_SPEC.md`）。
3. 對應 SPEC 修補是否確實存在（`docs/GAP2_MARGINAL_IC_SPEC.md`，grep finding ID）。註：SPEC 於 R2／R3 又修多處，不影響本 synth 之 body hash。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-18 sha256:<你實跑取得的完整 body sha256> task:20260818-GAP2-X-STAMP-R7
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target（本輪產 stamp，不產 finding）。
3. 不得 commit、不得 push。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句實質理由。收尾清 /tmp workdir（保留 claude-501）。
