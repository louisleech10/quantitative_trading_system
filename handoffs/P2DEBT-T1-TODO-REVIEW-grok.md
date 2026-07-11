# P2DEBT-T1 TODO R1 — Adversarial Review (grok)

- **task-id**: `p2debt-t1`
- **TODO**: `handoffs/P2DEBT-T1-TODO-DRAFT-R1.md`
- **SPEC**: `handoffs/P2DEBT-T1-SPEC-DRAFT-R3.md`（雙戳記前提：grok R2 + codex R3；本審不重審 SPEC 本體）
- **日期**: 2026-07-11
- **審查者**: grok
- **模式**: adversarial TODO-vs-SPEC；唯讀 + tmp；未讀其他 reviewer 之 TODO 產出

---

## 1) 100% SPEC 覆蓋追溯

| SPEC 來源 | 內容 | TODO 落點 | 判定 |
|-----------|------|-----------|------|
| §P Task 1.1 | B4×3 遷移 + `test_gate_adversarial_rejects_uppercase_verdict` | Task 1.1 項 1.1.1–1.1.4 | **OK** |
| §P Task 1.2 | B5×5 遷移 + `test_b5_spec_missing_risk_hit_fails` | Task 1.2 項 1.2.1–1.2.6 | **OK** |
| §P Task 1.2b | `docs/VERIFY_GATE_SPEC.md`：`RISK-HIT: b` + 2× 真實 FACT-RECEIPT（含 `^echo` mutation 錨） | Task 1.2b 項 1.2b.1–1.2b.4 | **OK** |
| §P Task 1.3 | R7 `VERDICT`→`Verdict` | Task 1.3 項 1.3.1 | **OK** |
| §V ① | 缺 RISK-HIT 必 FAIL | §V 表 + 1.2.5 | **OK** |
| §V ② | `VERDICT:` 全大寫必 FAIL | §V 表 + 1.1.4 | **OK** |
| §V ③ | canonical 無 FACT-RECEIPT 必 FAIL（與 present 成對） | §V 表 + 1.2.2 / 1.2.3 | **OK** |
| §V 章程 | suite 9→0；真實路徑回歸；plain 禁令；mutation N/A | Phase Gate / Final Acceptance / §0 | **OK** |
| §C 硬邊界 | 禁 `scripts/`；scope 4 檔；防假綠；禁 tmp 取代真實路徑；canonical；派工前快照 diff | §0 + Final Acceptance | **OK** |
| §V 殘餘風險 | D-1 不解析值；receipt 不驗真偽 | §0 殘餘風險 + Task 1.1 邊界 | **OK** |
| §R | 單 commit message | Final Acceptance 建議 commit | **OK** |
| 附錄修法清單 | 4 檔摘要 | 附錄速查 | **OK** |

**漏項 / 扭曲**：無 BLOCKING 級漏項或 oracle 扭曲。遷移字串、斷言保留語、B 案 receipt 命令與 SPEC R3 一致（含 mutation `^echo` + `$*`）。

---

## 2) 驗證命令抽樣（read-only，≥3）

### R1 — 基線 suite（TODO 基線）

```bash
venv/bin/python -m pytest tests/governance -q --tb=no
```

**VERIFY 摘要**: `9 failed, 140 passed, 1 warning in 55.29s`（與 TODO 基線 9/140 一致）

### R2 — 9 紅目標子集 node id

```bash
venv/bin/python -m pytest \
  tests/governance/test_verify_gate_b4.py \
  tests/governance/test_verify_gate_b5.py::test_b5_spec_command_output_fact_receipt_missing_fails \
  tests/governance/test_verify_gate_b5.py::test_b5_spec_fact_receipt_missing_fails \
  tests/governance/test_verify_gate_b5.py::test_b5_spec_fact_receipt_present_passes \
  tests/governance/test_verify_gate_b5.py::test_b5_spec_pending_confirmation_passes \
  tests/governance/test_verify_gate_b5.py::test_b5_existing_verify_gate_spec_still_passes \
  tests/governance/test_verify_gate_redteam.py::test_r7_gate_task_id_appends_committee_dispatch \
  -q --tb=line
```

**VERIFY 摘要**: `9 failed, 8 passed`；失敗與 TODO 目標一致（b4×3 + b5×5 + r7×1）。正測 GOOD/PENDING 現紅原因為 `§RISK 缺 RISK-HIT`；`existing_verify_gate_spec` 為 RISK-HIT + 2× FACT-RECEIPT；R7/B4 pass 路徑為 `缺 Verdict 行（D-1）`。

### R3 — D-1 Verdict 大小寫 + gate.sh L207

```bash
echo "VERDICT: APPROVED" | grep -qE 'Verdict[[:space:]]*[:：]' && echo MATCH || echo NO_MATCH
echo "Verdict: APPROVED" | grep -qE 'Verdict[[:space:]]*[:：]' && echo MATCH || echo NO_MATCH
sed -n '205,210p' scripts/gate.sh
```

**VERIFY 摘要**: `VERDICT:` → `NO_MATCH`；`Verdict:` → `MATCH`；源碼 L207 `grep -qE 'Verdict[[:space:]]*[:：]'` + 錯誤字串 `缺 Verdict 行…（D-1 拒發）`。與 TODO §0 / 1.1.3–1.1.4 一致。

### R4 — B 案 receipt 錨 + 現行生產路徑 fail

```bash
grep -n 'Task)' scripts/gate_check.sh
grep -n '^echo "→ 跑 mutation 探針: pytest -k test_mutation_' scripts/mutation_probe_check.sh
bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md; echo exit=$?
```

**VERIFY 摘要**:
- `37:  Task)`
- `74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"`
- `TEMPLATE FAIL`：缺 `RISK-HIT` + 2× fact-scope `FACT-RECEIPT`（gate_check / mutation 兩行）；`exit=1`

與 TODO 1.2b 鎖定字串一致。

### R5 — 遷移後 fixture 語意（tmp only，對齊 TODO 1.2.x）

| fixture | 預期 | 實跑 |
|---------|------|------|
| canonical 無 receipt + RISK-HIT + 待確認：無 | rc=1，stdout 含 `FACT-RECEIPT` | **PASS**（rc=1，列 `§A fact-scope 缺 FACT-RECEIPT`） |
| canonical 有 receipt + RISK-HIT | rc=0 `TEMPLATE PASS` | **PASS** |
| 缺 RISK-HIT、canonical+receipt 齊 | rc=1，stdout 含 `RISK-HIT` | **PASS** |
| PENDING 僅 RISK-HIT | rc=0 | **PASS** |
| VERIFY_GATE_SPEC tmp + 三錨點（B 案字面） | rc=0 | **PASS**（`TEMPLATE PASS`） |

### R6 — 解耦

```bash
grep -r "from api\." momentum/ | wc -l
```

**VERIFY 摘要**: `0`（與 TODO Final Acceptance 一致）

---

## 3) 弱化 / scope creep 檢查

| 檢查 | 結果 |
|------|------|
| 是否改 `scripts/` 或指示放寬 gate/template | **無** — §0 / 各 Task「不可做」明禁 |
| 是否弱化 `returncode` / 刪 `FACT-RECEIPT` / skip | **無** — 明確禁止 `in (0,1)`、skip、刪斷言 |
| 是否用 tmp 取代 `docs/VERIFY_GATE_SPEC.md` 回歸 | **無** — 1.2.6「測試不變」+ §0 禁令 |
| 是否把 plain `- 已確認:` 當 fact-scope 證據 | **無** — 1.2.1–1.2.3 強制 canonical 粗體 |
| 是否把 uppercase `VERDICT` 留在 pass fixture | **無** — 1.1.3 改 `Verdict`；1.1.4 專測 uppercase；grep 守門 |
| scope 是否超出 §C 四檔 | **無** |
| 是否「修」D-1 值解析（REJECTED 當拒因） | **無** — 邊界寫明勿加誤斷言 |

**結論**：TODO 未弱化 SPEC；若干處加嚴（1.1.1 要求 combined **不含** `缺 Verdict 行`；1.1.4 VERDICT 僅出現於負例）。

---

## 4) 執行端可讀性（cold-start）

| 維度 | 判定 |
|------|------|
| §0 全域約束可單獨遵守 | **是** — scope / 禁令 / 檢查器語意 / 殘餘風險一頁 |
| 每 Task 有檔+函式+精確字串變更 | **是** — 表格式遷移對齊 SPEC §P |
| 每項有可執行驗收命令 + 預期 | **是** — 單測 node id + suite gate |
| 依賴拓撲 | **是** — 單 batch B1；1.2.6 明示須 1.2b 後 |
| 派工 prompt 可複製 | **是** |
| 是否需回讀 SPEC 重推 | **否**（TODO 自稱冷啟動可開工；本審同意：關鍵字串與 oracle 已內嵌） |

殘餘摩擦（非 BLOCKING）：1.1.4 新測未明示 `try/finally` 清理 `handoffs/` 檔（既有 b4 模式有 finally）；Phase Gate 部分行寫裸 `pytest` 而非 `venv/bin/python -m pytest`（Final Acceptance 有 venv）。

---

## 5) Findings

### BLOCKING

**無。**

### MINOR

#### G-TODO-M1 — Task 1.2b.1 中間驗收命令易誤導
- **證據**: TODO 1.2b.1 驗證欄：`bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md 2>&1 | grep -q 'RISK-HIT'` 並寫「不再報缺 RISK-HIT」。
- **問題**: 補上 `RISK-HIT` 後，fail 訊息只剩 FACT-RECEIPT 兩行，**stdout 可能不再含字串 `RISK-HIT`**，`grep -q 'RISK-HIT'` 反而 false。正確中間條件是「不再出現 `§RISK 缺 RISK-HIT`」；閉合應以 1.2b.4 `TEMPLATE PASS`+exit 0 為準（該項正確）。
- **影響**: 執行端若只跑 1.2b.1 中間命令可能誤判；不阻最終驗收。
- **信心度**: High
- **RECHECK**: 只加 RISK-HIT 後跑 template_check，確認訊息集合。

#### G-TODO-M2 — Phase Gate 命令前綴不一致
- **證據**: Phase 1 測試表用裸 `pytest …`；Final Acceptance / 各 Task 閉合用 `venv/bin/python -m pytest`。
- **影響**: 無 venv activate 時可能指錯直譯器；非語意弱化。
- **信心度**: High
- **RECHECK**: `which pytest` vs `venv/bin/python -m pytest`。

#### G-TODO-M3 — 1.1.2 驗收敘述「小寫比對」略過寬
- **證據**: TODO 1.1.2「combined 含 provenance 或 committee_dispatch（小寫比對）」；源碼為 `"provenance" in combined.lower() or "committee_dispatch" in combined`（後者**未** lower）。
- **影響**: 敘述微失真；TODO 同時寫「保留原斷言」，實作若抄源碼則無害。
- **信心度**: High

#### G-TODO-M4 — 1.1.4 新測未點名 cleanup
- **證據**: 1.1.4 允許寫 `handoffs/20990101-B4-UPPER-VERDICT-COMPOSER.md`；同檔既有測試用 `try/finally unlink`。
- **影響**: 冷啟動可能留殘檔於 handoffs/；建議 tmp 路徑或 finally（非 SPEC 缺口）。
- **信心度**: Medium

---

## 6) 10 類快掃（template V13 對照）

| # | 類 | 結果 |
|---|-----|------|
| 1 | 矛盾 | 無（SPEC↔TODO 字串/oracle 一致） |
| 2 | 漏項 | 無 |
| 3 | 不可測 | 無（命令+rc+字串 oracle） |
| 4 | quant 假設 | N/A（治理 fixture） |
| 5 | 過度工程 | 無（單 batch fixture 遷移） |
| 6 | OOM | N/A |
| 7 | cache | N/A |
| 8 | API/相容 | N/A |
| 9 | 測試品質 | §V 三負例+回歸真實路徑已落 TODO |
| 10 | Agent 可執行 | 可冷啟動；MINOR 見上 |

**被當成事實的未驗證假設**: 無新增。TODO 基線與檢查器語意經本審實跑核實（R1–R6）。

---

## 7) 總結

TODO R1 對 R3 SPEC 為**完整、可派工**之執行清單：§P 全 Task、§V 三負例、§C 三禁令與 B 案錨點皆可追溯；驗收命令可執行且抽樣通過；未發現斷言弱化或 `scripts/` scope creep。MINOR 不阻 Frozen / 派工。

RECONCILE-STAMP APPROVED (p2debt-t1 TODO R1, grok, 2026-07-11)

Verdict: APPROVE
