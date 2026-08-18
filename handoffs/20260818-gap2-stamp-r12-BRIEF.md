# GAP-2 TODO review-R11 收斂檔之 RECONCILE-STAMP 核可（收斂輪）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap2-x-review-r11/synth.md

## 任務
對 `stamp-target`（TODO adversarial R11 三家收斂檔；一群集 X1＝三家 sentinel「可 Frozen」；3 條全引用）append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`0122818edadc…`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap2-x-review-r11/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 背景
R10 收斂檔已三家 APPROVED（stamp r11）。本輪為 TODO review-R11（收斂輪）之戳記；APPROVED 後 TODO 版本行改 **FROZEN**（內容不變）並開 B1 實作。制度：reconcile 須委員戳記核可，`scripts/reconcile_stamps_check.sh` 機器強制。

## 核可判準（勿一律 APPROVED）
1. X1 是否對應附錄 3 個 canonical sentinel ID（codex／composer／grok 各 P3-00）。
2. Verdict「可合併／FROZEN」與三家 R11 回件一致（各家 BLOCKING 無、判定「可 Frozen」）；收斂判準＝每家最近一次內容審查皆 sentinel（R10 composer／grok＋R11 codex）成立。
3. 母 SPEC 未就地改；TODO 除版本行外未變。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-18 sha256:<你實跑取得的完整 body sha256> task:20260818-GAP2-X-STAMP-R12
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target（本輪產 stamp，不產 finding）。
3. 不得 commit、不得 push。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句實質理由。收尾清 /tmp workdir（保留 claude-501）。
