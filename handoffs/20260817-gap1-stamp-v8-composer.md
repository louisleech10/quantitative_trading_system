# GAP-1 stamp-v8 — composer

**task-id**: `20260817-GAP1-X-STAMP-R9`  
**stamp-target**: `handoffs/reconcile/20260817-gap1-x-review-r8/synth.md`  
**判定**: APPROVED

## body_sha256（實跑）

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-review-r8/synth.md
→ f6385eb7ce27d0c9d15ee1d5c558d8160b87ae234e8b3bea5d26885bcd00ac14
```

與 brief 宣告一致。

## 核可判準（1–5）

1. **0 掉項**：`bash scripts/completeness_check.sh --synth handoffs/reconcile/20260817-gap1-x-review-r8/synth.md --lock handoffs/reconcile/20260817-gap1-x-review-r8/sources.lock` → 三家 12+3+7=22 ID 全覆蓋，PASS。
2. **裁定附碼證**：`CODEX-R8-P0-01` 層界限制（純統計層無 exhaustive SoT）以 `universe_scope=ledger_recorded_only`＋強制 `display_downgrade`＋registry **G1-R9** 具名殘留處置，誠實標示「未證明 ledger 非 top-K」而非假綠；`CODEX-R8-P0-02` 以 `pos[champion]` 映射＋§V-14 mutation 落地，可接受。
3. **處置落地**：`universe_scope`×17、`G1-R9` 命中 registry、`pos[champion]`／`n_rows_rejected`×7／`reporter_failed` 皆在 TODO；Task 2.4（L420）晚於 Task 4.3（L402）；`template_check todo` PASS。
4. **J1 數值可重現**：對照 receipt `20260817T143000Z-gap1-todoadv-claude-pbo-probe.log`（alpha `sr_pp=0.15`→pbo 0.0054/0.0000＜0.30；噪音三變體 0.6483/0.6158/0.5357∈[0.30,0.70]）與 `20260817T150000Z-gap1-minbtl-conservatism-probe.log`（mean max SR=0.843077 vs analytic 0.833943，rtol&lt;0.05）；band／mu 選擇在 A1-1/A1-2 附實跑理由，未重跑探針。
5. **Verdict 一致**：內文「修補已落 A1＋TODO R2、交 R9 複驗後 Frozen」與結尾 Verdict「需修補後合併」一致（修補指文件層，非重作架構）。

## 戳記（已 append 至 stamp-target）

```
RECONCILE-STAMP: composer APPROVED 2026-08-17 sha256:f6385eb7ce27d0c9d15ee1d5c558d8160b87ae234e8b3bea5d26885bcd00ac14 task:20260817-GAP1-X-STAMP-R9
```

## /tmp 收尾

已刪 `gap1-stamp-evidence.log`、`/tmp/sessions/*`、`/tmp/cc-socks`；保留 `claude-501`。
