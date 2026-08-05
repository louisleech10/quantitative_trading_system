# GOVB0-IMPL-B3 — grok 實作收尾

family: grok  
task-id: GOVB0-IMPL-B3  
brief: `handoffs/20260805-GOVB0-IMPL-B3-BRIEF.md`  
時間: 2026-08-05

## 狀態

**STATUS: BLOCKED** — 語料 A INVARIANCE 因預期 2.1-FP 翻轉（pgrep）無法全綠；需擴大 scope 才能合規收斂。

實作本體（Task 2.0 契約＋Task 2.1 判定）已落地並經 targeted 測試；**未**自行改語料 A / 未弱化 INVARIANCE 斷言（brief 硬禁）。

## 正在做 / 完成

| 項 | 狀態 |
|---|---|
| Task 2.0 契約 11 項語料 B ≥22 條 | 完成（50 JSON 列） |
| 語料 B `.sha256` sidecar | 完成 |
| `scripts/_gate_lex.sh` 詞法單一實作 | 完成 |
| `gate_check.sh` Bash 路徑 source＋LEGACY 逃生 | 完成 |
| `test_gate_lexical_contract.py` / `test_gate_decision.py` | 完成 |
| TEST-2.0-MUT-11（11 項）＋ MUT-ALLOWLIST | 完成（pytest 實跑 pass） |
| TEST-2.1-*（FP/E3/RECURSE/OUTSIDE/1B/MUT） | 完成 |
| 語料 A INVARIANCE 全綠 | **未過**（見阻塞） |

## 改動檔

| 檔 | 說明 |
|---|---|
| `scripts/_gate_lex.sh` | **新** 詞法契約：heredoc 七條、跨行引號 awk、命令位置擴充、`-c`/`eval` 遞迴≤3、fail-closed |
| `scripts/gate_check.sh` | Bash 延遲 source lex；env 前綴剝除收窄（避免 `out=$(codex…)` 誤剝）；LEGACY 路徑保留 |
| `tests/governance/fixtures/gate_decision_corpus.txt` | 占位 → 真實語料 B（50 條） |
| `tests/governance/fixtures/gate_decision_corpus.txt.sha256` | **新** sidecar |
| `tests/governance/test_gate_lexical_contract.py` | **新** TEST-2.0-* |
| `tests/governance/test_gate_decision.py` | **新** TEST-2.1-* |
| `tests/governance/test_debt_gate.py` | hermetic 複製清單加 `_gate_lex.sh` |
| `tests/governance/test_family_registry.py` | `_gate_lex.sh` 釘入 `_DRIFT` / `_CONSUMER_FILES` |

未 commit、未 push。未碰 `data_cache/`、未做 Task 2.2+。

## 1) 契約 11 項 → 語料 B 對照（各 ≥1 TP＋TN）

| 契約 | TP 例 | TN 例 |
|---|---|---|
| 1 引號內分隔符 | `echo start; grok -m …` | `pgrep -fl 'codex exec|…'` |
| 1b 跨行剝引號 | 真多行 `codex exec` | commit 多行訊息含 codex |
| 2 命令位置 | `out=$(codex exec x)` 等 | `cat sp_codex.txt` |
| 3 -c/eval 遞迴 | `bash -c "codex…"` | `bash -c 'echo hello'` |
| 4 引號路徑 | `"/my dir/codex" exec` | `"/my dir/otherbin" exec` |
| 5 路徑形狀 | `/opt/…/codex exec` | `./scripts/cx_run.sh`（2.4 完整前 ALLOW） |
| 6 未閉合 | `echo "codex…` | `echo "hello"` |
| 7 unquoted -c | `bash -c codex` | `bash -c echo` |
| 8 遞迴深度 | depth2 / depth-over | depth2 echo |
| 9 跳脫 | 尾隨 `\` fail-closed | `echo "a\"b"` |
| 10 heredoc | 後接派工／FC 五向量／nest attack | body 不掃／allowlist delim |

## 2) 語料 B vs B2 占位

- B2：1 行 placeholder JSON  
- B3：50 條契約＋2.1 轉向；sha256=`9fcb8d91838bcec4f65b3e2f8f9c89d45b0259161db14e8020dbd35c28fd30c2`

## 3) 原型③ 26 條 parity

- 家族／`-c`／E-3 命令位置：**與 proto3 一致**  
- **具名差異 3 條**（Task 2.2 才收窄 claude 子字串；B3 維持 `claude[^|]*(-p|--print)`）  
  - `scratchpad + rev-parse` / `.claude + porcelain` / `find -print`：proto3=ALLOW，本實作=BLOCK  

## 4) 語料 A 基線與完工

**VERIFY:b3-baseline-invariance**（動工前）  
`pytest tests/governance/test_gate_deny_fields.py -q` → **22 passed**

**完工後同一命令**（核心子集實跑）  
`pytest tests/governance/test_gate_deny_fields.py -q` → **21 passed, 1 failed**  
- 唯一失敗：`test_01_invariance_decision_trace`  
- **index 16**（0-based）=`pgrep -fl 'codex exec|cursor-agent|grok '`  
  - snapshot: `(2, dispatch)` → 現行: `(0, '')`  
  - 即 TEST-2.1-FP 預期轉向；**其餘 29 條 trace 與 snapshot 一致**

## 5) 分支對照／覆蓋

- `_decision_branches_from_gate_check` 仍可由 LEGACY 段＋字面錨機械導出  
- `test_01_corpus_a_covers_decision_branches` **PASSED**  
- family 清單：`_gate_lex.sh` 已釘 `_DRIFT`

## 6) Mutation 實跑

```
pytest tests/governance/test_gate_lexical_contract.py::test_20_mut_11_contract_reverts \
       tests/governance/test_gate_lexical_contract.py::test_20_mut_allowlist_turns_fc_allow -q
→ 2 passed  rc=0
```

11 契約項各自翻轉（c1…c10）＋ allowlist FC 至少一條 ALLOW：見該兩測通過。

## 7) git / pytest / golden

```
git diff --stat（tracked）:
 scripts/gate_check.sh                              |  32 +-
 tests/governance/fixtures/gate_decision_corpus.txt | 282 +-
 tests/governance/test_debt_gate.py                 |   1 +
 tests/governance/test_family_registry.py           |   3 +-
 + untracked: scripts/_gate_lex.sh, corpus .sha256, 兩測試檔
```

```
pytest tests/governance -q   # 全套曾跑
→ 3 failed, 745 passed in 987.95s
  FAILED test_01_invariance_decision_trace   # pgrep 2.1-FP（本批）
  FAILED test_gate_check_latency_under_100ms # cold~287ms；snapshot 同環境~203ms，皆>100ms（大 audit 34k 行）；非本批改判定路徑之 Task cold 回歸（Read allow ~45ms 與 snapshot 同級）
  FAILED test_no_unpinned_family_list_line   # 已修（釘 _gate_lex.sh）；全套當時未含後修
```

```
bash scripts/restore_golden_inventory.sh
git status --short tests/golden/
→ （空）
```

## 阻塞（需 Claude / 使用者擴大 scope）

### BLOCKING-1：語料 A 含 Phase-2 FP 向量

- **證據**：INVARIANCE index16 pgrep `(2,dispatch)→(0,'')`  
- **brief**：翻轉 ⇒ 停下；**禁改語料 A 換綠**  
- **提案**（擇一，需核准）：  
  1. 自語料 A **移除** pgrep 列（改只留語料 B / TEST-2.1-FP）  
  2. INVARIANCE 改為「Phase-0 觀測欄位」範圍，或排除具名 2.1-FP id  
- 未自行改 TODO / 語料 A / 既有 INVARIANCE 斷言

### 次要：latency 門檻 vs 真實 audit 體積

- 實測 cold 以 2MB audit 為準 >100ms（snapshot 亦 >100ms）  
- 與本批詞法（Task 路徑不 source awk）無直接因果；**未**放寬門檻

## 設計決策（本批）

1. 詞法獨立 `_gate_lex.sh`，Bash 才 source → 避免 Task cold 解析巨 awk  
2. env 前綴值限簡單字面，避免 `out=$(codex…)` 被 R1 剝成 `exec x)`  
3. 超大 cmd（>8KiB）只掃前綴 → 4MB audit 邊界測不卡死  
4. claude 子字串**不**在本批收窄（留給 2.2）；proto3 TN 三條具名差異  
5. `GATE_LEGACY_DECISION=1` 緊急回舊一線性判定  

## 踩坑

1. macOS awk `towc` 中文失敗 → preprocess/extract 一律 `LC_ALL=C`（禁 export）  
2. `out=$(codex…)` 被 env-strip 誤傷  
3. 突變只 copy `gate_check.sh` → 缺 `_gate_lex.sh`；改 fallback `scripts/_gate_lex.sh`（cwd=repo）  
4. 家族 regex 須保留 `(codex|…)[[:space:]]` 字面供 `_DRIFT` 釘死  

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: 語料 A pgrep 動工前 BLOCK（snapshot=現行）；改後 ALLOW；其餘 A 條目 (rc,kind) 不變；proto3 26 條可跑；契約 1b 需跨行 awk 非 sed
TESTS_RUN: baseline deny_fields 22 passed；完工 deny_fields 21p/1f（INVARIANCE）；decision+lexical 14 passed；mut-11+allowlist 2 passed；full governance 745p/3f（含 latency/unpinned 當下態）；restore golden → tests/golden 空
FAILURES_SEEN: 4MB O(n²) hang→8KiB cap；Unicode awk→LC_ALL=C；env-strip 誤傷 cmdsub；mut 缺 lex file→fallback；allowlist mut 邊界→放寬 token 收集
SCOPE_CHANGES: 提案擴大：語料 A 移除 pgrep 或調整 INVARIANCE（未自改）；test_debt_gate/family_registry 最小同步（_gate_lex 釘檔）
NUMERIC_OR_SCHEMA_IMPACT: gate 判定對 quote/E-3/-c 路徑改變（預期）；audit schema 未改；產品數值未動
```

STATUS: BLOCKED — 語料 A INVARIANCE 因 2.1-FP pgrep 翻轉；需核准擴大 scope（移出 A 或調整 INVARIANCE 範圍）後方可標 DONE
