# GAP-2 TODO review-R10 收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap2-x-review-r10/synth.md

## 任務
對 `stamp-target`（TODO adversarial R10 三家收斂檔；兩群集 W1（codex 1 MINOR，一行同文寫回 TODO DRAFT R5）／W2（composer／grok sentinel「可 Frozen」）；3 條全引用）append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`72bf9378c846…`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap2-x-review-r10/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 背景
R9 收斂檔已三家 APPROVED（stamp r10）。本輪為 TODO review-R10 之常規戳記；APPROVED 後派 R11 窄範圍確認（三家 sentinel ⇒ TODO FROZEN → B1）。制度：reconcile 須委員戳記核可，`scripts/reconcile_stamps_check.sh` 機器強制。

## 核可判準（勿一律 APPROVED）
1. W1／W2 是否逐條對應附錄 3 個 canonical ID（codex 1／composer 1／grok 1）。
2. W1 處置是否確實寫入 `docs/GAP2_MARGINAL_IC_TODO.md`（DRAFT R5）：`grep -n 'mutation_probe_check.sh\`' docs/GAP2_MARGINAL_IC_TODO.md` → rc=1（無無路徑殘留）；Phase B4 小節與 §B「B4→B5」列同文。
3. 母 SPEC 未就地改；A1-5 只加一句 pointer 指向補正、決策內容未變。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-18 sha256:<你實跑取得的完整 body sha256> task:20260818-GAP2-X-STAMP-R11
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target（本輪產 stamp，不產 finding）。
3. 不得 commit、不得 push。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句實質理由。收尾清 /tmp workdir（保留 claude-501）。
