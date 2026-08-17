# GAP-1 stamp-v9 — composer

**task-id**: `20260817-GAP1-X-STAMP-R10`  
**stamp-target**: `handoffs/reconcile/20260817-gap1-x-review-r9/synth.md`  
**判定**: APPROVED

## body_sha256（實跑）

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-review-r9/synth.md
→ 67a5a742319c47ea4fc1cb1c640aea4d69a71cb0761150b4ef56080fb3d977d9
```

與 brief 宣告一致。

## 核可判準（1–6）

1. **0 掉項**：`bash scripts/completeness_check.sh --synth handoffs/reconcile/20260817-gap1-x-review-r9/synth.md --lock handoffs/reconcile/20260817-gap1-x-review-r9/sources.lock` → codex 3／composer 1／grok 3 共 6 ID 全覆蓋，PASS。
2. **J7 落地**：TODO sha `7ef0ec44e111`、延伸檔 sha `31c3fddb05f0`；`InvalidValidationArgument(ValueError)` 於 Task 3.1 定義，三處參數驗證＋`x>700` 皆 raise；Task 3.4 捕獲恰為 `(OSError, json.JSONDecodeError, ContractViolation)` 不含 `ValueError`；入口二分（`None`→`n_unknown`；`<=0`→上拋 5xx 非正規化）；驗收⑤ 含 `InvalidValidationArgument`⇒5xx、驗收⑧ `t_years=-1.0`⇒5xx 且不得 `reporter_failed`。
3. **J8 落地**：Task 2.4 W1／W4 收集範圍逐字為函式頂層、未嵌在 `If`／`For`／`While`／`Try`／`With` body 內；mutation ⑥ 死分支反例已列；Task 3.3「不可做」含 helper／迴圈／`setattr`／`dict(**kwargs)` 配對條款；誠實邊界具名「只做語法層無條件路徑，不做 CFG／可達性」。
4. **J9 落地**：A1-18 具名覆寫母 SPEC:653-654，含「B4 ⊃ B3」「先 revert B4 再 B3」「不採 post-B4 phase 之理由」。
5. **未動已定案**：`bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → PASS；J1 golden（band `[0.30,0.70]`、`mu=0.01*1.0/sqrt(8760)`、`alpha_undetectable>0.40`）、§V-4 新形式、驗收⑨ 文字本輪修補未改動（grep 對照 A1-1／A1-2／A1-9 仍為 R8 定版）。
6. **Verdict 一致**：內文「修補落 TODO R3＋A1-16..A1-18，經 r9 戳記輪後 Frozen」與結尾 Verdict「需修補後合併 → …經 r9 戳記輪（含落地機械核可）後 Frozen」一致。

## 判準 3：`if False:` 手推（composer 反例）

片段（mutation ⑥ 同形）：

```python
def build_validation_section(...):
    out = {"eligibility": {}, "min_btl": {}, "dsr": {}, "provenance": {}}
    if False:
        out["pbo"] = {"status": "ok", "reason": "eligible", ...}
    return out
```

新規則下 W1 只從**函式頂層**（未嵌在 `If` body 內）收集組裝鍵：`if False:` 內的 `out["pbo"] = …` 不計入 `assembled` ⇒ 頂層僅見四節（缺 `pbo`）⇒ W1 子集檢查失敗 ⇒ **rc=1**。同理九個 `eligibility_keys` 寫在 `if False:` 內亦不被 W4 計入。結論：**確定 rc=1**，死分支假綠已被擋。

## 戳記（已 append 至 stamp-target）

```
RECONCILE-STAMP: composer APPROVED 2026-08-17 sha256:67a5a742319c47ea4fc1cb1c640aea4d69a71cb0761150b4ef56080fb3d977d9 task:20260817-GAP1-X-STAMP-R10
```

## /tmp 收尾

已刪 `/tmp/sessions/*`、`/tmp/cc-socks`；保留 `claude-501`。無 `/tmp/workdir` 目錄。
