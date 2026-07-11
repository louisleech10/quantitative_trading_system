# P2DEBT-T1 Implementation Review (Grok)

**task-id**: p2debt-t1  
**reviewer**: grok  
**date**: 2026-07-11  
**scope reviewed**: `git diff` on `tests/governance/test_verify_gate_{b4,b5,redteam}.py` + `docs/VERIFY_GATE_SPEC.md`  
**mode**: adversarial, repo read-only except this file  

---

## (1) 防假綠 — 斷言未弱化/刪除/skip

### Diff 摘要（僅 fixture / 文件錨點；斷言極性保留）

| 檔 | 變更性質 | 既有 assert 極性 |
|----|----------|-----------------|
| `test_verify_gate_b4.py` | 3 fixture 補/改 `Verdict:`；**新增** uppercase 負例 | `rc==1` + reconcile/ADV；`rc==1` + provenance/committee_dispatch；`rc==0` + `GATE PASS` **皆保留** |
| `test_verify_gate_b5.py` | 4 fixture 補 `RISK-HIT` + canonical `- **已確認**：`；**新增** missing RISK-HIT 負例 | `rc==1` + `"FACT-RECEIPT" in stdout`（兩負例）；`rc==0`（present/pending/existing）**皆保留** |
| `test_verify_gate_redteam.py` | 1 行 `VERDICT`→`Verdict` | `rc==0` + `committee_dispatch` + hash **未動** |
| `docs/VERIFY_GATE_SPEC.md` | `RISK-HIT: b` + 2× FACT-RECEIPT | n/a（生產 SPEC） |

### 防假綠條款對照

| §C 條款 | 結果 | 證據 |
|---------|------|------|
| 禁 skip / 弱化 `returncode` | **PASS** | assert-only diff 無刪/改既有 `assert`；無 `pytest.skip` / `@pytest.mark.skip` / `returncode in (...)` |
| `test_b5_existing_verify_gate_spec_still_passes` 真實路徑 | **PASS** | 仍 `_run_template_check("spec", REPO_ROOT / "docs" / "VERIFY_GATE_SPEC.md")`（L421–423） |
| fact-scope 須 canonical，禁 plain 作唯一證據 | **PASS** | 遷移後 fact 負/正例皆 `- **已確認**：`；無 plain `- 已確認:` 作 fact-scope |
| 禁刪 `"FACT-RECEIPT" in stdout` | **PASS** | L292、L324 仍在 |
| uppercase `VERDICT` 不得為 pass 路徑唯一覆蓋 | **PASS** | `rg VERDICT:` 於 b4 **僅** L280 負例 `test_gate_adversarial_rejects_uppercase_verdict` |

**契約結論**：遷移改的是 **fixture 形狀**（對齊現行 D-1 / template_check 語意），不是把「應 FAIL 變 PASS」或刪 oracle。每條 migrated test 仍測原意圖：非 ADV→reconcile 拒、無 dispatch→provenance 拒、有 dispatch→GATE PASS、缺 FACT-RECEIPT→FAIL、有 receipt→PASS、pending→PASS、R7 audit 事件。

---

## (2) §V 三件套可證偽負例

| # | 測試 | rc oracle | message oracle | 存在+語意 |
|---|------|-----------|----------------|-----------|
| ① | `test_b5_spec_missing_risk_hit_fails` | `assert proc.returncode == 1` | `assert "RISK-HIT" in proc.stdout` | **OK** — fixture 有 canonical+receipt、**無** RISK-HIT 行 |
| ② | `test_gate_adversarial_rejects_uppercase_verdict` | `assert proc.returncode == 1` | `"缺 Verdict 行" in combined or "D-1" in combined` | **OK** — 內容 `VERDICT: APPROVED` |
| ③ | `test_b5_spec_fact_receipt_missing_fails` | `assert proc.returncode == 1` | `assert "FACT-RECEIPT" in proc.stdout` | **OK** — canonical DatetimeIndex **無** receipt |

Suite 實跑三測皆 **PASSED**（見下）。

---

## (3) 主驗收（本審親自重跑）

```text
$ venv/bin/python -m pytest tests/governance -q
======================= 151 passed, 1 warning in 51.35s ========================
EXIT:0
```

- **0 failed**；**151 passed**（基線曾 9 failed / 140 passed → 遷移後 +2 新負例 ≈ 151，合理）  
- 含 ①②③ 與 `test_b5_existing_verify_gate_spec_still_passes`、`test_r7_gate_task_id_appends_committee_dispatch` 全綠  

---

## (4) `docs/VERIFY_GATE_SPEC.md` FACT-RECEIPT 真偽（read-only 重跑）

| 文件宣告 | 實跑 stdout | 一致？ |
|----------|-------------|--------|
| `grep -n 'Task)' scripts/gate_check.sh` → `37:  Task)` | `37:  Task)` | **YES** |
| `grep -n '^echo "→ 跑 mutation 探針: pytest -k test_mutation_' scripts/mutation_probe_check.sh` → `74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"` | 同左 | **YES** |
| `- RISK-HIT: b` | `grep -n` → L10 | **YES** |
| `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` | `TEMPLATE PASS (spec): ...`；**rc=0** | **YES** |

無 stub / 無行號漂移。

---

## (5) scripts/ 未變更

```text
$ git diff --name-only scripts/
# (empty)
```

`git diff --name-only` 變更集僅四檔 whitelist：  
`docs/VERIFY_GATE_SPEC.md` + 三個 `tests/governance/test_verify_gate_*.py`。

---

## Findings

| 嚴重度 | 項 | 說明 |
|--------|----|------|
| none | — | 未見斷言弱化、skip、tmp 取代生產 SPEC、scripts 偷改、receipt 造假 |
| note（非阻） | D-1 不判 APPROVED/REJECTED | 與 TODO §0 殘餘風險一致；`Verdict: REJECTED` 僅為過 D-1 後測下游路徑 — 實作未誤加「因 REJECTED 被拒」斷言 |

---

## Structured summary

```
ASSUMPTIONS_VERIFIED: fixtures only; asserts preserved; 3 §V negatives assert rc!=0+oracle; FACT-RECEIPT cmds match stdout; scripts/ empty
TESTS_RUN: venv/bin/python -m pytest tests/governance -q → 151 passed, 0 failed, EXIT:0 (51.35s)
FAILURES_SEEN: none
SCOPE_CHANGES: none (4-file whitelist only)
NUMERIC_OR_SCHEMA_IMPACT: none (governance fixtures + SPEC anchors only)
```

Verdict: APPROVE
