# P2DEBT-T2-CE8-REVERIFY — grok (CE8 原提出方 §B8 複驗+代跑)

- task-id: `p2debt-t2-ce8-reverify`
- role: CE8 原提出方；§B8 閉合複驗 + V7 hermetic 代跑
- date: 2026-07-12
- scope: **read-only**（僅本檔產出；未改任何其他檔）
- fix anchor: codex `MIN_INSTALLER_ARITY={S1:2,S2:3,S10:2}` in `RedirectPatchSet._validate` + subtarget tests rewrite
- prior finding: `handoffs/P2DEBT-T2-IMPL-REVIEW-grok.md` CE8

## VERDICT: **CE8 CLOSED**

三項全綠：(1) 原反例 + S1/S10 arity fail-closed；(2) 完整 manifest 不誤殺；(3) V7 hermetic 不回歸。

---

## 1) §B8 閉合複驗 — 原 CE8 反例 + S1/S10 arity

命令：venv python 內聯腳本（repo cwd），對 `RedirectPatchSet`：`pop` 一 subtarget installer → `activate(tmp)`；斷言 raise / count / residual。

`MIN_INSTALLER_ARITY = {'S1': 2, 'S2': 3, 'S10': 2}`（runtime confirmed）

### 1a) 原反例：pop S2.save_report (index 0) → activate()

```text
--- CE8_ORIG_pop_S2_save_report ---
  installers_before: 3
  installers_after: 2
  min_arity: 3
  activated: False
  exc_type: RedirectCompletenessError
  exc_msg: incomplete seam: S2 requires at least 3 installers, got 2
  activation_count: 0
  active_is_none: True
  installed_ids: []
  production_identity_unchanged: True  # ICReporter.save_report is production fn
  PASS: True
```

對比 review 時（fix 前）：`CE8_ACTIVATE_SUCCEEDED_WITH_S2_MISSING_SUBTARGET True` + `activation_count 1`。  
**現在反轉：activate 被拒、activation_count==0、無殘留 patch。**

### 1b) S1 arity：pop `_resolve_filtered_path` (index 0)

```text
--- S1_pop__resolve_filtered_path ---
  installers_before: 2
  installers_after: 1
  min_arity: 2
  activated: False
  exc_type: RedirectCompletenessError
  exc_msg: incomplete seam: S1 requires at least 2 installers, got 1
  activation_count: 0
  installed_ids: []
  production_identity_unchanged: True
  PASS: True
```

### 1c) S10 arity：pop lgb `_resolve_model_path` (index 0)

```text
--- S10_pop_lgb__resolve_model_path ---
  installers_before: 2
  installers_after: 1
  min_arity: 2
  activated: False
  exc_type: RedirectCompletenessError
  exc_msg: incomplete seam: S10 requires at least 2 installers, got 1
  activation_count: 0
  installed_ids: []
  production_identity_unchanged: True
  PASS: True
```

**判定 (1): PASS** — 原 CE8 洞已閉；S1/S10 同構 arity 生效。

---

## 2) 反向可證偽 — 完整 manifest 仍能 activate（不誤殺）

同一 process、gate 先確認 `activation_count==0` 後：

```text
POLARITY: full complete manifest activate
  activated: True
  activation_count: 1
  installed_ids: ['S1', 'S10', 'S11', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9']
  installed_count: 11
  wrappers_installed: {'S1._resolve_filtered_path': True, 'S2.save_report': True, 'S10.lgb': True}
  all_wrapped: True
  activation_count_after_deact: 0
  active_after_deact: True
  PASS: True
```

**判定 (2): PASS** — arity gate 不誤殺完整 manifest。

---

## 3) 代跑 V7 hermetic（不回歸）

```bash
bash scripts/run_ic_persist_hermetic.sh --set V7 > /tmp/t2-ce8-v7.log 2>&1; echo RC=$?
```

原文摘要（log 尾）：

```text
RC=0
================ 133 passed, 8 skipped, 281 warnings in 20.34s =================
DIGEST_DIFF_EMPTY[V7]=1
```

**判定 (3): PASS** — 133 passed + `DIGEST_DIFF_EMPTY[V7]=1` + `RC=0`。

---

## 總判定

| 項 | 結果 |
|----|------|
| 1a 原 CE8 反例 (pop S2.save_report) | PASS → raise + count=0 + no residual |
| 1b S1 arity | PASS |
| 1c S10 arity | PASS |
| 2 完整 manifest activate | PASS（不誤殺） |
| 3 V7 hermetic | PASS 133p + DIGEST=1 + RC=0 |

### **CE8 CLOSED**

原 review 宣稱的 false-green（缺 subtarget 仍 activate）已以 fail-closed arity 修復並本輪獨立複驗；正反極性皆可證偽。

---

```
ASSUMPTIONS_VERIFIED: MIN_INSTALLER_ARITY runtime; pop-S2/S1/S10 activate raises RedirectCompletenessError; production identity unchanged on fail; full manifest activates 11 seams; V7 hermetic 133p+DIGEST=1
TESTS_RUN: inline CE8 reverify script PASS (3 mut + 1 polarity); bash scripts/run_ic_persist_hermetic.sh --set V7 → RC=0, 133 passed, 8 skipped, DIGEST_DIFF_EMPTY[V7]=1
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯寫本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: DONE
```
