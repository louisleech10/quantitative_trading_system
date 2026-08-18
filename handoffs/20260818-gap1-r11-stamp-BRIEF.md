# G1-R11 修補收斂檔 RECONCILE-STAMP（三家；探針**只由 codex 跑**）——PASS 即關 G1-R11

VERIFY-EXEMPT:doc-example:gap1-r11-stamp-criteria

> 本檔為給委員的核可判準清單（實測項目），非主委之 operational 結論。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap1-x-review-r21/synth.md

## 背景
- 你們三家 R21 對 G1-R11 修補（`16e5971c`）之 review 共 4 條（codex 2／composer 1 sentinel／grok 1 sentinel），一致「可合併」；收斂為 **P1**（docstring 同步，已於 `c17560e6` 補）與 **P2**（`np.ptp` +0.5s／PBO，已量測、記錄不改）。
- 🔴 主委已 commit＋push；本輪主委**不動任何檔、不跑探針**。`scripts/governance_families.json` 既有 no-op dirty 請忽略。自建探針加 timeout；產出檔尾 `STATUS: DONE`。

## 任務
對 `stamp-target` append `RECONCILE-STAMP`（`## 戳記` 區段）。body sha256 ＝ `008b9d2af02af89bf87ef39d106423aec8fb266459c6a6a7fbefc4926930e682`（`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap1-x-review-r21/synth.md`；請自行重跑確認）。

## 核可判準
1. `bash scripts/completeness_check.sh --synth handoffs/reconcile/20260818-gap1-x-review-r21/synth.md --lock handoffs/reconcile/20260818-gap1-x-review-r21/sources.lock` ⇒ rc=0；你的 ID 被群集引用且處置對得上。
2. codex：`sharpe.py` Returns 與 `pbo._sharpe_pp_1d` docstring 現含 `ptp==0`／位元全等 scope（`git show c17560e6`）。
3. `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` ⇒ **281 passed**。
4. 探針（🔴 只由 codex 跑）：`bash scripts/gap1_b1_mutation_probe.sh` ⇒ rc=0、21 條 rc=1（receipt `handoffs/run_receipts/20260818T120000Z-gap1-r11-mutation.log`）。
5. Verdict 與內文一致；P2 之「記錄不改」是否誠實（有量測、有理由、無效能門檻）。

## 戳記格式（逐字，單行；FAMILY ∈ codex／composer／grok）
```
RECONCILE-STAMP: <FAMILY> APPROVED 2026-08-18 sha256:<你實跑取得的完整 sha256> task:20260818-GAP1-X-STAMP-R22
```
不核可就寫 `BLOCKED` 並具名理由。**只** append 到 `## 戳記` 區段；不得改碼／SPEC／TODO／延伸檔；不 commit／push。

## 產出
判定＋實跑 body_sha256＋判準 3／4 之 rc 與計數＋一句 Verdict 理由。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
