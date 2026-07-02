# GOV O3EXT + R7 — Implementation Code Review（Composer / 非實作者）

**Reviewer**: Composer 2.5 | **Implementer**: Codex | **Date**: 2026-07-03  
**SPEC**: `docs/GOV_O3EXT_R7_SPEC.md` | **TODO**: `docs/GOV_O3EXT_R7_TODO.md`  
**ADV 基線**: `handoffs/20260703-GOV-O3EXT-R7-ADV-COMPOSER.md` F1–F7（Frozen 後 closure 已 APPROVED）  
**審查範圍**: 未 commit diff — `scripts/gate.sh`、`scripts/verification_claim_check.py`、`scripts/verify_task_provenance.py`、`scripts/register_legacy_committee_files.sh`、`tests/governance/test_verify_gate_{r7ext,o3ext}.py`

---

## 方法

實讀 diff + SPEC/TODO；對照 ADV F1–F7 修法是否在**碼上**落地；隔離環境（`GATE_DIR_OVERRIDE` / `VERIFY_GATE_COMMITTEE_AUDIT_LOG`）實跑 F3 攻擊腳本、path-mismatch 探針、legacy 8 檔註冊、`pytest tests/governance/`；比對 B4 legacy provenance 回歸。

---

## ADV F1–F7 落地對照

| Finding | 落地狀態 | 碼上證據 |
|---------|----------|----------|
| **F1** 讀 committee audit log（非 verify_audit） | **落地** | `verification_claim_check.py` 新增 `_committee_audit_path()` + `COMMITTEE_AUDIT_ENV`；`o3ext` 測試 `test_committee_event_in_verify_audit_log_does_not_exempt` 反例綠 |
| **F2** raw bytes sha256；禁用 reconcile_body_hash | **落地** | `gate.sh` `_sha256_file`；`register-output` / legacy 腳本皆 raw sha256；未呼叫 `reconcile_body_hash.sh` |
| **F3** register-output 須先行 dispatch；拒 legacy-* | **落地** | `gate.sh` `_task_has_dispatch` + `legacy-*)` case；實測無 dispatch → exit 1；legacy task-id → exit 1 |
| **F4** JSON 經 json.dumps | **落地** | `gate.sh` `_append_committee_json_event` 用 `json.dumps`；`r7ext` fuzz 測試 `evil"\n` 單行合法 JSON |
| **F5** 欄位名 `output_path` | **落地** | 事件 schema、`verify_task_provenance`、測試 assert 皆 `output_path` |
| **F6** stamp-review 全鏈 | **落地** | `r7ext` `test_reconcile_full_chain_*` + pending 無 register 失敗；`verify_task_provenance._stamp_event_satisfies` 消費 `committee_output` |
| **F7** 新測試檔非空殼 | **落地** | `r7ext` 9 collected、`o3ext` 9 collected；全 governance **124 passed**（基線 106 + 18） |

---

## Findings

### B1 — [NON-BLOCKING] `register-output` 未綁定 dispatch 預告 `output_path`（R2 軟變體）

**信心度**: High  
**證據**: `gate.sh` `register-output` 只驗 `_task_has_dispatch`，不比對 dispatch 事件的 `output_path` 與註冊路徑。  
**反例（隔離環境實跑）**:

```bash
# dispatch 聲稱 output=A（pending）
bash scripts/gate.sh dispatch ... --task-id path-mismatch --output handoffs/20990703-PATH-MISMATCH-A.md
# register 實際走私 B
bash scripts/gate.sh register-output path-mismatch handoffs/20990703-PATH-MISMATCH-B.md  # exit 0
python scripts/verification_claim_check.py --files handoffs/20990703-PATH-MISMATCH-B.md   # exit 0
```

**評估**: ADV **F3** 目標是「無 dispatch 直接 register」→ 已封堵。path mismatch 需先有一次低門檻 `gate.sh dispatch`，仍留 audit 痕跡；SPEC/TODO 未明訂 register 路徑須等於 dispatch `--output`（pending 流程允許事後補檔）。建議 B3 或 follow-up：`register-output` 在 dispatch 已有非空 `output_path` 時強制路徑相等（pending 除外語義已覆蓋「先宣告後建檔」）。

---

### B2 — [NON-BLOCKING] Task 1.2 未改 `reconcile_stamps_check.sh` 本體

**信心度**: High  
**證據**: diff 無 `reconcile_stamps_check.sh`；W2 邏輯擴在 `verify_task_provenance.py`，shell 仍 `check-stamp` 委派。  
**評估**: 行為已閉合（`r7ext` 全鏈 + `test_delib_reconcile_still_passes_allowlist` 綠）；與 SPEC「修改檔案」字面偏差，架構可接受。

---

### B3 — [NON-BLOCKING] Task 3.1 文件增補不在本 diff

**信心度**: High  
**證據**: `docs/MULTI_AGENT_ORCHESTRATION.md`、`docs/VERIFY_GATE_SPEC.md` 無變更。  
**評估**: B1+B2 實作 review 不擋；B3 編排端收尾項。

---

### B4 — [NON-BLOCKING] 測試覆蓋缺口

| 缺口 | 說明 |
|------|------|
| 重複 `register-output` append | SPEC 邊界②要求 append-only；無專測（行為從 `_append_committee_json_event` 推斷） |
| legacy 腳本重複執行 | 同一 8 檔可多次 append `committee_output`；白名單仍拒第 9 檔 |
| `r7ext` F3 攻擊腳本 | 未逐字收錄 ADV 檔名，但 `test_register_output_requires_prior_dispatch_and_handoffs_path` 等價覆蓋 |

---

### B5 — [NON-BLOCKING] `reconcile_stamps_check.sh:59` 註解仍寫「2026-07-01 grandfather」

**信心度**: Medium  
**證據**: B4 已改 allowlist；註解未同步（本 diff 未觸該檔）。不影響執行。

---

## 審查要點逐項

### ① F1–F7 碼上落地（含 F3/F4）

- **F3**: 無 dispatch `register-output` → `ERROR: …找不到先行 committee_dispatch` exit 1；`legacy-*` → exit 1。走私鏈在**有** dispatch 後可完成（見 B1），符合 F3 closure 文本。
- **F4**: `json.dumps` 取代 `printf` 裸拼；fuzz 測試通過。

### ② `register_legacy_committee_files.sh` 白名單

- **8 檔硬編碼** + **8 組 sha256**（`expected_sha` case，L27–36）。
- 非白名單 → `ERROR: legacy whitelist 不含` exit 1（實測第 9 檔）。
- 8 檔齊套 + `VERIFY_GATE_COMMITTEE_AUDIT_LOG` 隔離 → `verification_claim_check.py --files <8>` exit 0。
- `task_id: legacy-gov-o3ext-r7`；主 `register-output` 拒 `legacy-*`（分工正確）。

### ③ checker 豁免不及 HANDOFF/docs

- `_is_committee_process_exempt`: 僅 `handoffs/` 前綴；`HANDOFF.md` 檔名拒絕；`check_unit` 仍擋 `root_handoff_status` / `commit_msg`。
- `o3ext`: HANDOFF 同 prose、docs 同 prose、錯 log（verify_audit）皆 exit 1；`redteam` R2 全綠。

### ④ `verify_task_provenance.py` W2/W3 與 B4 legacy

- `parse_committee_events` 收 `committee_output`；`find_dispatch_by_task` 限 `committee_dispatch`（ADV/W3 語義保留）。
- `check_stamp_provenance` 先 legacy allowlist → 再 `find_events_by_task` + `_stamp_event_satisfies`；`pending` fail-closed。
- **實測**: `reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md` exit 0；`test_verify_gate_b4.py` 11/11 綠。Codex「B4 legacy 相容」宣稱 **成立**。

### ⑤ 新測試可證偽

- 改壞 `register-output` 前置檢查 → `test_register_output_requires_prior_dispatch_*` 應紅。
- 改壞 committee log 來源 → `test_committee_event_in_verify_audit_log_does_not_exempt` 應紅。
- 改壞 hash 綁定 → `test_registered_handoff_process_file_hash_mismatch_fails` 應紅。
- `git diff tests/governance/` 既有檔：**無刪 assert**。

---

## TESTS_RUN

```text
# 隔離攻擊 / 探針
F3 no-dispatch register-output → exit 1
F3 legacy-* register-output → exit 1
path-mismatch dispatch A / register B → register 0, checker 0 (B1 記錄)
legacy 8-file register + checker → exit 0
legacy 9th file → exit 1

# pytest
pytest tests/governance/test_verify_gate_r7ext.py tests/governance/test_verify_gate_o3ext.py -v → 18 passed
pytest tests/governance/ -q → 124 passed
pytest tests/governance/test_verify_gate_b4.py -q → 11 passed
bash scripts/reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md → PASS
```

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: F3/F4 攻擊腳本隔離實跑；legacy 8+1 檔探針；path-mismatch 探針；B4 DELIB reconcile；governance 124 passed
TESTS_RUN: 見上 TESTS_RUN 節
FAILURES_SEEN: none（審查過程）
SCOPE_CHANGES: none（read-only review）
NUMERIC_OR_SCHEMA_IMPACT: governance audit 新增 committee_output 事件類型；無 quant 路徑影響
HANDOFF_NOT_UPDATED: read-only review；不覆写根 HANDOFF.md
```

---

## Verdict 摘要

| 類別 | 計數 |
|------|------|
| BLOCKING | 0 |
| NON-BLOCKING | 5（B1–B5） |

**F1–F7 修法均已碼上兌現**；F3 攻擊腳本（無 dispatch 直接 register）實測 exit 1；F4 fuzz 經 `json.dumps`；legacy 8 檔白名單+sha256 有效；checker 豁免域正確；W2/W3 B4 legacy 未放寬；新測試可證偽且全綠。殘餘 B1（register 路徑未綁 dispatch 預告）為 SPEC 未明訂的加固項，不阻 B1+B2 合併。

FINAL VERDICT: APPROVED — F1–F7 落地完整、隔離攻擊與 124 governance tests 通過；唯一值得跟進的硬化點是 register-output 與 dispatch output_path 綁定（NON-BLOCKING B1）。

STATUS: DONE
