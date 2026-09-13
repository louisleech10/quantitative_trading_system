# SPLITUNIFY b9 — stamp-r3 收斂檔補戳記 — grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-STAMP-R3`  
**family**: grok  
**brief**: `handoffs/20260911-SPLITUNIFY-B9-STAMP-R3-BRIEF.md`  
**findings-round**: R3  
**stamp-target**: `handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md`  
**禁改碼**：本輪只產 stamp 交件＋一行戳記 append；未改 SPEC／TODO／生產碼／收斂檔正文。

---

## 必答 1 — 收斂檔 body 戳記

**(1a) 對 body sha256 `3f3d0d79…`：`APPROVED`**

實跑 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md` → `3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb`（與 brief 逐字相符）。裁定段記錄 `CODEX-R17-P1-01`／`P1-02` CLOSED、SPEC 三家戳記 rc=0、Y1 已修、下一步＝`Task 9.1`；與本輪 diff `git show 3e8eff32 -- docs/SPLITUNIFY_TODO.md`（19 列＋(乙) 四 ID 具名）一致。

**(1b) `N/A`（未 REJECTED）**

---

## 必答 2 — impl 授權依據適切性（攻 assumed）

**(2a) 適切。** 本檔制度角色＝高風險派工之 `--adversarial` 標的（brief 明示），機械條件＝已填實 Verdict ＋三家 `RECONCILE-STAMP`。**攻 assumed「gate 是否還要求內容涵蓋 Task 9.1 施工面」→ 否**：實讀 `scripts/gate.sh` 之 `_check_adversarial_quality`／`_process_one_adversarial_file`，對非 `*-ADV-*` 路徑只跑 `verdict_filled_check.sh` ＋ `reconcile_stamps_check.sh`；**無** Task／施工面關鍵字或 scope 掃描。施工權威仍在已戳記之 `docs/SPLITUNIFY_SPEC.D-002.md`（body `d42b3f14…`，`reconcile_stamps_check` rc=0）與 `docs/SPLITUNIFY_TODO.md` §C-9 `Task 9.1`；本檔只閉合「進實作」程序鏈最後一環（裁定第 4 點）。

**(2b) 不應改指 r17。** 理由三條，皆可一次觀測：
1. `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260911-splitunify-b9-review-r17/synth.md` → **缺 `## 戳記` 區**，無法當 stamped `--adversarial`。
2. r17 之 `Verdict：需修補後合併` 記錄的是 X1–X3 修訂前狀態，不是「領 9.1 token」之閉合證明。
3. r17 與 stamp-r2 的 finding 本體皆不複述 `Task 9.1` 施工面（前者管 9.3 驗收閘／殘留；後者管 Y1 字面＋戳記達成）——改指 r17 **並不**增加對 9.1 的內容覆蓋，只會丟掉「SPEC 戳記 rc=0 已達成」這道最後前置之收斂證明。

---

## 必答 3 — Task 9.1 施工面

**(3a) 可直接開工。** §C-9 `Task 9.1` 已具名：`build_event_keys` → `(keyed, discarded)` 且無丟棄時 `discarded == {}`；`_derive_single_symbol` keyword-only `discarded_rows_by_feature_tf` 原樣寫入 summary；多 symbol 同鍵相加；`pipeline.py` 同批改；四條具名 pytest ＋ `M-SU-D2-01`／`02`；不動 `metadata.split_unify`。動工前置三條（SPEC stamps rc=0、probe REVERT、Rule 12）均已滿足。現行 caller 僅 `pipeline.py:747` 以單一 `DataFrame` 承接——改 tuple 後必須 unpack，契約已寫死。

**(3b) `N/A`（無阻擋開工之未解歧義）**  
中間層：單標的 wrapper（`derive_event_split_from_plans` → `_derive_single_symbol`）已 `**kwargs` 轉傳（`split_projection.py:599`），pipeline unpack 後以 keyword 傳入即可；多 symbol 相加已在要點 2 具名。不另開 finding。

---

## GROK-R3-P3-00

**斷言**: 對 stamp-target body（sha256 `3f3d0d79…`）複驗：Y1 處置已落地（`SU-RESID-C5-TARGETS` 20→19、(乙) `C5-15`／`16`／`17`／`18` 具名）、SPEC 三家戳記 rc=0、gate 對 `--adversarial` 不要求內容涵蓋 `Task 9.1` 施工面、裁定「進 Task 9.1」與 §C-9 動工前置一致；無需阻擋收斂之 finding。

**碼證**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md` → `3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb`（append 戳記前後不變）；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → 三家 APPROVED rc=0；`git show 3e8eff32 -- docs/SPLITUNIFY_TODO.md` → 19 列與四 ID 字面已入；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260911-splitunify-b9-review-r17/synth.md` → 缺 `## 戳記`（拒改指）；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 87 passed rc=0。

**來源摘要**: handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md#3f3d0d793625

[P3] 信心度=High。本輪 `brief-kind: stamp`；攻 assumed「應否改指 r17」→ 否（r17 無戳記區且非 9.1 閉合證明）。

---

## 戳記

已 append 至 `handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md` `## 戳記` 區：

```text
RECONCILE-STAMP: grok APPROVED 2026-09-13 sha256:3f3d0d7936256c9b71ebce51cf286310c55fb432a760eb68bcb60602e0f3dacb task:20260911-SPLITUNIFY-B9-STAMP-R3
```

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 3f3d0d79…；SPEC stamps rc=0；commit 3e8eff32 含 19 列與 C5-15..18；gate adversarial 只驗 Verdict＋戳記、不掃 Task 9.1 內容；r17 缺 ## 戳記；baseline pytest 87 passed
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-splitunify-b9-stamp-r2/synth.md` → 3f3d0d79…；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py` → 87 passed；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-stamp-r3-grok.md --family grok` → COMPLETENESS PASS rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（戳記 append ＋本交件檔）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-stamp-r3-grok.md
TMP_CLEANUP: /tmp 與 /private/tmp 無 `*workdir*` 可清；`claude-501` 保留

STATUS: DONE
