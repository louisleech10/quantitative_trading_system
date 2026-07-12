# P2DEBT-T2 IMPL REVIEW — composer (adversarial)

- task-id: `p2debt-t2-impl-review-composer`
- role: independent dual-family code review (author=codex; no self-review)
- date: 2026-07-12
- scope: ticket-2 redirect only; **read-only** (only this file written)
- brief: `handoffs/P2DEBT-T2-IMPL-REVIEW-BRIEF.md`
- receipt anchor: `handoffs/run_receipts/20260712T003131Z-p2debt-t2-impl-final6.json` (exit 0)

## VERDICT: **BLOCK**

final6 hermetic body is green (all `DIGEST_DIFF_EMPTY=1`, V6 `V6_NO_NEW_RED=1`, C-5 V7 leak closed), but **SPEC/TODO 宣稱的 S1–S11 subtarget fail-closed 契約是假的**：缺 S2 `save_report` installer 仍可 `activate()`，而 `test_missing_subtarget_refuses_activate` 從未呼叫 `activate()` 故假綠。這與 C-5「漏一寫點直到 digest 才抓」同類；外層 digest 可信，內層 manifest 完整性 gate 不可信。

---

## Counterexamples attempted (falsifiable)

### CE8 — PRIMARY BLOCKING: subtarget mutation 不拒絕 activate（獨立重現）

**契約**（SPEC §SEAM / `test_missing_subtarget_refuses_activate` 命名）：S1/S2/S10 任一 subtarget installer 缺失 → `activate()` 必須 `RedirectCompletenessError` 且 `activation_count==0`。

**測試實際行為**（`tests/momentum/Analysis/test_ic_persist_redirect_unit.py:70-89`）：

1. monkeypatch `_build_manifest` 並 pop 一個 installer
2. 只呼叫 `resolve_all()`
3. 斷言 installer 數量 + `get_activation_count()==0`（activate 未呼叫，恆真）
4. **從未呼叫 `activate()`**

**本輪反例腳本**（repo cwd, venv python）：

```text
# pop S2.save_report (index 0), then activate
CE8_ACTIVATE_SUCCEEDED True
S2_installer_count 2
activation_count 1
```

`RedirectPatchSet._validate` 僅要求 `installers` 非空 + ID 集合 == S1..S11；**S2 剩 2/3 method patch 仍視為完整 seam 並成功 activate**。S1（`_resolve_filtered_path` / `_persist_outputs`）、S10（lgb/xgb）同型。

**為何 BLOCK**：C-5 正是「manifest 宣稱完整、實際漏一 caller 寫點」；CE8 證明同類回歸可再次通過 unit matrix，只能靠 V* digest 兜底。

**修復門檻**（author，非本 review）：

- `_validate` / `activate` 強制 per-seam installer 最小 arity（S1≥2, S2≥3, S10≥2）
- 改寫 subtarget tests：`pop → pytest.raises(RedirectCompletenessError): activate() → activation_count==0`

---

### CE-DISABLE — mutation canary 對「瞬時寫入+清理」假綠（獨立重現）

**手法**：`IC_PERSIST_REDIRECT_DISABLE=1` 時 `get_active_redirect()` 強制 `None`（即使 `_ACTIVE` 已 set），wrapper 全 pass-through。

```text
wrote_prod_mid True
digest_changed_while_file_existed True
digest_after_cleanup True   # pre == post
```

搭配 `IC_PERSIST_REDIRECT_DISABLE=1 pytest …::test_save_and_load_roundtrip`：**1 passed, DIGEST_UNCHANGED=1**（測試內 `unlink` 清掉 production 檔）。

`test_mutation_redirect_disabled_caught` 用 `chdir(work)` + 改 `production_prefix` 到 sacrificial cwd，**不驗 repo `data_cache` 污染**；`MUTATION_CANARY=1` 只證明 redirect 邏輯可被 DISABLE 關掉，不保證 hermetic 會紅。

**判定**：非當前 final6 洩漏；但 mutation 協議對「寫後即刪」路徑無效。外層 digest 仍為主 fence（C-5 已證）。

---

### CE1 — spy 不攔 raw FS；digest 可證偽（獨立重現）

active redirect 下直接 `Path("data_cache/models/…").write_bytes(...)`：

| 層 | 結果 |
|---|---|
| `ctx.spy.violations` | `[]` |
| production 檔存在 | **True** |
| `digest_data_cache()` 新 key | **True** |

probe 寫入 `models/_composer_review_probe.pkl` → `diff_detected True`, `new_key {'models/_composer_review_probe.pkl'}`（已清理）。

**判定**：spy 非 FS fence；digest oracle **可證偽**（與 C-5 敘事一致）。非 live bypass（測試應走 resolver/helper）。

---

### CE-cwd — 相對路徑 + 非 repo cwd 跳過 rewrite（潛在）

`chdir(/tmp/othercwd)` + active redirect + `_redirect_path(Path("data_cache/features/x.h5"))` → 等於輸入、resolve 落在 `othercwd/data_cache/…`，不進 sacrificial root。

現行 V1–V7 自 repo root 跑 → **非 live**。C-2/C-3 家族潛在坑；golden Run C 已用 symlink+chdir 犧牲根設計避開。

---

### CE5 — golden A/B/C sha256

`normalize()` 剝 `filtered_features_path` / `report_paths` / mtime（路徑無關）。

| 案例 | 結果 |
|---|---|
| A/B/C 三跑 | `hashes[0]==hashes[1]==hashes[2]`（本輪 V5 重跑通過） |
| Run C OFF | chdir `work/` + symlink `feature_klines`；`before==after` digest |
| 改 payload 欄位 | hash 變（設計意圖） |

**判定**：鎖 **normalized 語意**，非 path byte；搭配 `DIGEST_DIFF_EMPTY[V5]=1` 可接受票 2 目標。

---

### V6 nodeid gate

未重跑全 V6（~5min）；引用雙戳 receipt：

- 正向：`handoffs/P2DEBT-T2-P1-POLARITY-grok.md` → `V6_NO_NEW_RED=1`, `DIGEST=1`, `RC=0`
- 反向：刪基線一行 `test_full_analysis` → `NEW_RED` 含該 nodeid, `RC=1`
- final6：`DIGEST_DIFF_EMPTY[V6]=1` + 23 pinned nodeids（`tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt`）

**判定**：機械 gate **可證偽**；票 2 未引入新紅（C-4 已獨立確認）。

---

### S1–S11 接縫（C-5 後）

| Seam | 狀態 |
|---|---|
| S1 | C-5 補 `_persist_outputs` + `_RedirectingReporter`；`test_s1_orchestrator_report_literals_redirect` 正向 |
| S2 | 三 method wrapper |
| S3/S7 | `_resolve_filtered_path` |
| S4/S8 | module `Path` → `_redirect_path`（覆蓋 S5/S6 宣告目標） |
| S5/S6/S9/S11 | installer no-op；靠 S4 或 helper（`get_active_redirect_root`） |
| S9/S11 | inventory 計數防 bypass（`_export_fixture_filtered_path`×2, `_create_e2e_factory`×8） |
| S10 | `_resolve_model_path`；bad payload 改寫 redirect root（C-5） |

**live V7 殘留繞過**：本輪未找到（`test_save_and_load_roundtrip` + roundtrip 後 `PROD_CLEAN`）。**manifest 完整性契約**：CE8 FAIL。

S5/S6 no-op + S4 Path patch：讀 `ic_analysis_service.py` L976/L1260/L1321，皆用模組級 `Path` → S4 有效。

---

### asyncio.to_thread

`test_to_thread_polluter_writes_under_redirect` 通過；gate 為 process-global `_ACTIVE` + `RLock`，非 TLS。與 SPEC R4 一致。

---

## Review checklist (brief)

| 焦點 | 結果 |
|---|---|
| 寫入導向犧牲根；讀寫同根 | **是**（現行 wiring + C-5 後） |
| 殘留 C-5 型繞過寫點 | final6 scope **未發現 live leak**；CE8 證明 partial seam 可 silent activate |
| digest oracle 可證偽 | **是**（CE1 + C-5 史實 + final6 全 DIGEST=1） |
| golden A/B/C sha256 鎖行為 | **是**（normalized payload；路徑 key 刻意剝離） |
| V6 nodeid gate | **可證偽**（P1 polarity 雙向 PASS） |
| S1–S11 接縫完整性 | **FAIL**（CE8 + probe 同構假陽性 + S9/S11 unit 字串 tautology） |
| commit scoping | 見下 |

---

## Commit scoping（混雜 freeze 腳本）

| 檔案 | 票 2 hunk | 票 5 hunk | 建議 |
|---|---|---|---|
| `tests/fixtures/gen_ic_run_selector_baseline.py` | import + `run_with_manual_redirect()` | 無 | **整檔入 T2** |
| `tests/golden/ic_phase1_contract/freeze_baseline.py` | redirect wrapper | 無 | **整檔入 T2** |
| `tests/golden/ic_phase1_1a_cut1/freeze_baseline.py` | redirect import/wrapper | `h5_existing` 短路；`config_override` False；meta | **`git add -p` 只取 redirect hunks** |
| `tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py` | redirect wrapper | `h5_existing`；override True；command 路徑修正 | **同上 split** |
| `baseline_*.json`, `l65/test_inventory.txt` | — | 純票 5 | **禁入 T2 commit** |

票 2 與票 5 freeze 語意（854d444 flag-off provenance）**不可同一 commit**。

---

## Tests run this review

```text
venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_persist_redirect_unit.py \
  tests/momentum/Analysis/test_ic_persist_redirect_inventory.py -q
→ 46 passed

venv/bin/python -m pytest tests/momentum/Analysis/test_ic_persist_redirect_unit.py::test_mutation_disable_redirect_internal -q
→ 1 passed

bash scripts/run_ic_persist_hermetic.sh --set V5 → DIGEST_DIFF_EMPTY[V5]=1, HERMETIC_RC=0 (~279s)

# adversarial scripts (CE8, CE-DISABLE, CE1 digest probe): independently reproduced
# final6 full --set all: cited receipt only (not re-run)
```

---

## What is solid (do not regress)

1. Hermetic digest 外層 gate — C-5 實錘；本輪 CE1 再證可證偽
2. C-5 修法：S1 `_persist_outputs`、bad-payload 同根、S10 redirect-root 容許
3. V6 baseline ⊆ gate + P1 雙極性
4. Inventory 靜態 S9/S11 + 16-caller 集合
5. `run_with_manual_redirect` generator bracket
6. process-global gate 跨 `to_thread`

---

## Required before APPROVE

1. **修 CE8**：per-seam installer arity + subtarget tests 必須 `activate()` 並 expect raise
2. 建議：probe 改真寫入或降 SPEC 語意為「path-shape only」
3. 建議：S9/S11 unit 假字串 mutation 改 inventory 式源碼掃描或刪除
4. 修後重跑 unit + V7 digest（codex 修 / grok 跑）

在 (1) 落地前，「S1–S11 完整性」unit gate 不可信；僅外層 digest 可信。

---

```
ASSUMPTIONS_VERIFIED: CE8 activate-with-missing-S2-subtarget; CE-DISABLE transient write+digest clean; CE1 digest detects probe file; V5 hermetic DIGEST=1@本輪; roundtrip PROD_CLEAN; final6 log lines cited
TESTS_RUN: unit+inventory 46p; mutation unit 1p; V5 hermetic RC=0 DIGEST=1; adversarial CE scripts; final6 not re-executed
FAILURES_SEEN: none in pytest; CE8 is design false-green not pytest red
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: handoffs/P2DEBT-T2-IMPL-REVIEW-composer.md
```

STATUS: DONE
verdict=BLOCK
