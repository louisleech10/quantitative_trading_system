# GOVB0-B3 Code Review — COMPOSER

**task-id**: GOVB0-B3-REVIEW  
**受審 commit**: `18cfdd2`（B3 本體；HEAD `9e91aef` 無 governance 程式差異）  
**reviewer**: COMPOSER（獨立 adversarial；禁改碼）  
**日期**: 2026-08-05

## Verdict：需修補後派工

B3 詞法契約／引號感知／排除機制整體設計可接受，且多數 fail-open 修復（E-3、RECURSE）有語料與 mutation 背書。但 **`_gate_lex.sh` 8KiB 截斷引入一條可重現的真派工 fail-open**（舊版 BLOCK、新版 ALLOW），依 brief 判定基準屬 **BLOCKING**，本輪不得進 B4。

`FINDINGS_COUNT: 2`（BLOCKING: 1，MAJOR: 1）

---

## §0 前提宣告

### fact-verified（本 reviewer 實跑）

| 項目 | 命令 | 結果 |
|---|---|---|
| 語料 A 條數 | `grep -c '^{' tests/governance/fixtures/gate_invariance_corpus.txt` | **30** |
| flips fixture 機械一致 | `python3 scripts/extract_phase2_expected_flips.py --check` | **OK rows=29** rc=0 |
| 排除 mutation | `pytest tests/governance/test_gate_deny_fields.py::test_01_invariance_exclude_nonflip_mutation -q` | **1 passed** rc=0 |
| 契約 11 項語料 | `pytest tests/governance/test_gate_lexical_contract.py::test_20_contract_22_coverage_and_direction -q` | **1 passed** rc=0 |
| Task 2.1 轉向 | `pytest tests/governance/test_gate_decision.py -q` | **6 passed** rc=0 |
| 全套 governance | `pytest tests/governance -q`（導 `/tmp/govb0_full_gov.log`） | **751 passed** rc=0（255s） |
| latency（OUT-OF-SCOPE 主題，僅解 750/751 差） | `pytest tests/governance/test_debt_gate.py::test_gate_check_latency_under_100ms -q` | **1 passed** rc=0 |

### 751 vs 750 差值（brief 要求確認）

- **collect 總數**：`pytest tests/governance --collect-only -q` → **751 tests collected**（本機 HEAD）。
- **實作者「750 passed」**：commit `18cfdd2` 訊息寫「734→750 passed；**1 failed** 為 latency」⇒ **750 passed + 1 failed = 751 collected**。
- **主委「751 passed」**：latency 在完整 `audit.log` 上已綠（本 reviewer 實跑 1 passed），故 **751/751 全綠**。
- **結論**：非新增幽靈測試；差值 = 當時 **latency 單次失敗** vs 現在通過。

### assumed 攻擊結果

| 假設 | 結論 | 證據 |
|---|---|---|
| 排除清單只來自 TODO 機械抽取、無手加 | **成立** | `--check` rc=0；29 行皆對應 `TEST-2.x` bullet + 方向標記；`test_01_phase2_flips_fixture_matches_todo` 通過 |
| 抽取窮舉所有轉向敘述 | **部分不成立** → MAJOR-01 | `TEST-2.1-RECURSE` 等寫「六條皆 BLOCK」無「由 ALLOW 轉 BLOCK」字樣，抽取器略過；目前語料 A 未含該六條故 invariance 仍綠，但未來若進 A 且未補清單會靜默紅 |
| 契約 11 項語料 B 各有 TP/TN | **成立** | `test_20_contract_22_coverage_and_direction` 通過；語料 B 契約 1–10 各 ≥2 條（見 `gate_decision_corpus.txt`） |

---

## 逐項核對表

### 標的 1 — 排除機制

| # | 判定 | 摘要 |
|---|---|---|
| 1a | **PASS** | fixture 可由 `extract_phase2_expected_flips.py --check` 重現；無手編漂移 |
| 1b | **PASS（附 MAJOR 殘留）** | 現行 TODO 內「由 X 轉 Y／維持 Z」均已抽到；絕對態敘述（RECURSE）未抽 → 見 MAJOR-01 |
| 1c | **PASS** | 反向斷言 1/2 在 `test_01_invariance_decision_trace`；mutation `test_01_invariance_exclude_nonflip_mutation` 實跑通過 |

### 標的 2 — fail-open 精準化

| # | 判定 | 摘要 |
|---|---|---|
| 2a | **PASS（抽樣 13 向量）** | 見下方 VERIFY 表；E-3／RECURSE／OUTSIDE 等真派工仍 BLOCK |
| 2b | **PASS** | `echo "codex exec x"` → ALLOW（契約 1）；`git commit -m "x"; codex exec y` → BLOCK（引號外分號） |
| 2c | **PASS** | 未閉合引號／heredoc FC 五向量／nest attack 測試全綠 |
| **2-regression** | **FAIL** | 8KiB 截斷後綴真派工 → **BLOCKING-01** |

**VERIFY 2a 抽樣（`bash scripts/gate_check.sh`，無 token，rc 直接取）**

| 契約 | 探針命令 | rc | 預期 |
|---|---|---|---|
| 1 TN | `pgrep -fl 'codex exec\|cursor-agent\|grok '` | 0 | ALLOW ✓ |
| 2 TP | `eval "codex exec x"` | 2 | BLOCK ✓ |
| 2 TP | `out=$(codex exec x)` | 2 | BLOCK ✓ |
| 3 TP | `bash -c "codex exec x"` | 2 | BLOCK ✓ |
| 2 TP | `true && codex exec x` | 2 | BLOCK ✓ |
| 1b TP | `echo start; grok -m grok-4.5 -p "x"` | 2 | BLOCK ✓ |
| 1 TN | `git commit -m "x; codex closure review"` | 0 | ALLOW ✓ |
| 2 TP | `git commit -m "x"; codex exec y` | 2 | BLOCK ✓ |
| 6 FC | `echo "codex exec x"`（僅引號內） | 0 | ALLOW ✓ |
| 10 TP | `cat <<EOF\ncodex exec x\nEOF\ncodex exec y` | 2 | BLOCK ✓ |
| **截斷** | `python3 -c "print('x'*8200)"` + `; codex exec hi` | **0** | **應 BLOCK ✗** |

### 標的 3 — Task 2.0／2.1 本體

| # | 判定 | 摘要 |
|---|---|---|
| 3a | **PASS** | 契約 1–10 各 TP+TN；`test_20_contract_22` 通過 |
| 3b | **PASS** | `test_20_proto_parity_26` 通過；3 條具名差異（scratchpad/porcelain/find）已文件化 |
| 3c | **PASS** | `test_21_1b_multiline_four` 4/4；`_gate_lex_preprocess` Pass2 跨行狀態機（非行內 sed） |
| 3d | **PASS** | `test_20_heredoc_failclosed_five` + `test_20_heredoc_allowlist_ok` + `test_20_heredoc_nest_attack` 互補 |
| 3e | **PASS** | `test_debt_gate.py` 僅補 `_gate_lex.sh` 複製；`test_family_registry.py` 釘 `_gate_lex.sh` executor drift — 最小必要 |
| 3f | **PASS** | 見 §1 測試品質（mutation 11 項、語料 sha256、invariance 雙向斷言） |

### §1 必查 11 類（範本）

| 類 | 結果 |
|---|---|
| 1 矛盾/互斥 | 無（主委語料 A vs TODO 翻轉已由排除機制解；設計已文件化） |
| 2 漏項/E2E | 無（B3 scope 內） |
| 3 不可測 | 無 |
| 4 quant 假設 | 無 |
| 5 過度工程 | 無（單一 `_gate_lex.sh` 合理） |
| 6 OOM/並行 | 無 |
| 7 Cache | 無 |
| 8 API/相容 | 無 |
| 9 測試品質 | 無 blocking 缺口；8KiB 截斷未測到 → BLOCKING-01 |
| 10 Agent 可執行 | 無 |
| 11 短命工 | 無（排除清單與 lex 為 Phase 2 永久基礎設施） |

---

## COMPOSER-R12-P0-01

**斷言**: `_gate_cmd_is_dispatch` 在指令長度 >8192 時截斷掃描字串，使**舊版會 BLOCK 的真派工**（前綴填充 + `; codex exec …`）在新版變成 **ALLOW（fail-open）**。

**碼證**:
- `scripts/_gate_lex.sh:291-303`：`local _max_lex=8192` + `head -c "$_max_lex"`
- RECHECK:
```bash
python3 -c "pad='x'*8200; import json,subprocess,os; cmd=pad+'; codex exec hi'; p=json.dumps({'tool_name':'Bash','tool_input':{'command':cmd}}); subprocess.run(['bash','scripts/gate_check.sh'],input=p,env={**os.environ,'GATE_DIR_OVERRIDE':'/tmp/govb0-gate-dir-composer'}).returncode"
# 現行 → 0 (ALLOW)
bash scripts/gate_check.sh <<< "$(python3 -c "import json; print(json.dumps({'tool_name':'Bash','tool_input':{'command':'x'*8200+'; codex exec hi'}}))")" ; echo rc=$?
# 現行 rc=0；pre-Phase2 snapshot rc=2（本 reviewer 對照實跑）
```

**來源摘要**: scripts/_gate_lex.sh#86ffda54b321

[BLOCKING] 信心度=High。委員 prompt 可達數十 KB；攻擊者可在前 8KiB 填無害內容、尾端放 `; codex exec …` 繞過 PreToolUse。brief 明文：舊擋新放之真派工一律 BLOCKING。

**修法**:
1. **首選（fail-closed）**：取消截斷；改以單次 awk 流式掃描或分塊掃描，保留「命令位置」語意且 O(n) 而非 O(n²) 拼接。
2. **次選**：截斷時若末尾未見完整 shell 句法且長度被截 → `return 0`（BLOCK），勿靜默 ALLOW。
3. **測試**：新增語料 B TP + mutation——截斷邏輯 revert 後該條須轉 ALLOW（證偽）。

---

## COMPOSER-R12-P1-01

**斷言**: `extract_phase2_expected_flips.py` 只辨識「由 BLOCK 轉 ALLOW／維持 …」等方向標記，**未覆蓋** TODO 中以絕對態寫法的行為變更（如 `TEST-2.1-RECURSE`「六條皆 BLOCK」、`TEST-2.2-REGRESS`「兩條須 BLOCK」），未來若這些命令進語料 A 且 Phase 2 改動判定，**不會自動進排除清單**。

**碼證**:
- `docs/GOVB0_FRICTION_TODO.md:336-337`（RECURSE 六條，無「由 ALLOW 轉」字樣）
- `scripts/extract_phase2_expected_flips.py:128-131`（無方向標記則 `continue`）
- 現況安全：`gate_invariance_corpus.txt` 無 `bash -c "codex exec` 等 RECURSE 條目（`grep` 0 命中）；`test_01_invariance_decision_trace` 仍綠

**來源摘要**: scripts/extract_phase2_expected_flips.py#f4f54dabbefe

[MAJOR] 信心度=High。不阻斷當前 invariance，但削弱「清單窮舉 TODO 轉向」前提；B4+ 若語料 A 擴充可能再次撞主委式矛盾。

**修法**: 抽取器增第三類「絕對態＋命令列舉」（`皆 BLOCK`／`須 BLOCK` + 反引號命令），或要求 TODO 一律用「由 X 轉 Y」格式；並加測試：RECURSE 六條若模擬進 A 必須在 flips 或明確 `maintain`。

---

## 出場判準核算

| 條件 | 值 |
|---|---|
| findings 總數 | **2**（≤5 ✓） |
| BLOCKING | **1**（需 0 ✗） |
| 可進 B4 | **否** — 須先修 COMPOSER-R12-P0-01 並補回歸測試 |

---

## 收尾

- **產出**: `handoffs/20260805-govb0-b3-review-composer.md`
- **/tmp 清理**: 嘗試移除 `govb0_*` worktree／log 遭環境權限阻擋（`Permission denied`）；**未改動 `/tmp/claude-501`**
- **誤觸**: review 中曾誤跑 `extract_phase2_expected_flips.py`（無 `--check`），已 `git checkout -- tests/governance/fixtures/phase2_expected_flips.txt*` 還原

---

ASSUMPTIONS_VERIFIED: 語料 A=30；flips --check OK；invariance/mutation/lexical/decision 測試實跑通過；751=750+latency 單次失敗解釋成立；8KiB fail-open 對照 snapshot 實證  
TESTS_RUN: `pytest tests/governance -q` → 751 passed rc=0；加點測試見 §0 表  
FAILURES_SEEN: none（測試全綠；判定邏輯 fail-open 為行為缺陷非測試失敗）  
SCOPE_CHANGES: none（read-only review）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）

STATUS: DONE
