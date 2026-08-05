# GOVB0-B3-UNBLOCK — grok 解阻塞收尾

family: grok  
task-id: GOVB0-B3-UNBLOCK  
brief: `handoffs/20260805-GOVB0-B3-UNBLOCK-BRIEF.md`  
時間: 2026-08-05

## 狀態

**STATUS: DONE** — 語料 A INVARIANCE 改為「排除 Phase2 預期翻轉後仍相等」；排除清單自 TODO **機械抽取**（禁手挑）；語料 A 條目未刪。

## 1) 預期翻轉清單 — 抽取邏輯與產出

| 項 | 路徑 |
|---|---|
| 抽取腳本 | `scripts/extract_phase2_expected_flips.py` |
| 清單 | `tests/governance/fixtures/phase2_expected_flips.txt` |
| sidecar | `tests/governance/fixtures/phase2_expected_flips.txt.sha256` |

**抽取規則（可重跑）**：
1. 掃 `docs/GOVB0_FRICTION_TODO.md` 驗證 bullet：`` `TEST-2.*`（…） ``
2. 略過 `mutation`／`MUT` 列（「轉回」非產品轉向）
3. 辨識方向標記：`由 BLOCK 轉 ALLOW`／`由 ALLOW 轉 BLOCK`（含「全／全部／N條全」前綴）與 `維持 BLOCK|ALLOW`
4. 自方向標記**之前**抽反引號命令（含 markdown 雙反引號 `` nested ` ``）
5. 寫 TSV：`kind\ttest_id\tfrom\tto\tcommand`；sha256 sidecar 同步

```
python3 scripts/extract_phase2_expected_flips.py
# → rows=29 flip=21 maintain=8
# sha256=f4f54dabbefe0c89ea4782474ad7529251d1757f24d771809e1ae891eee397cf
python3 scripts/extract_phase2_expected_flips.py --check  # rc=0
```

**機械無法抽取（散文／無 由X轉Y 樣式）— 明說、未手挑**：
| 列 | 原因 |
|---|---|
| `TEST-2.1-RECURSE`「六條皆 BLOCK」 | 無「由 X 轉 Y」樣式 |
| `TEST-2.1-1B`「4/4 通過」 | 無方向標記 |
| `TEST-2.2-REGRESS`「兩條須 BLOCK」／散文「由 BLOCK 退化」 | 非產品「由 X 轉 Y」清單句；屬回歸護欄敘述 |

## 2) TEST-0.1-INVARIANCE 改後 + 反向斷言

改檔：`tests/governance/test_gate_deny_fields.py`

| 測試 | 行為 |
|---|---|
| `test_01_phase2_flips_fixture_matches_todo` | `--check` 重抽 == fixture + sha |
| `test_01_invariance_decision_trace` | 語料 A 排除 flip 清單命中後 (rc,kind) 相等；反向1+2 |
| `test_01_invariance_exclude_nonflip_mutation` | 錯誤排除非 flip 條 → 反向1 轉紅 |

**反向1**：每個被排除的語料 A 條目必須命中 `kind=flip` 清單（禁靜默排除）。  
**反向2**：清單中每一條 flip：
- 若命中語料 A → **必須**在語料 B 有對應且 snapshot→current 依 from→to 翻轉
- 若命中語料 B → 必須確實翻轉
- 若 A、B 皆無 → residual（未來 Task 尚未進語料 B；**不得**用於排除 A）

**實跑**：
```
pytest tests/governance/test_gate_deny_fields.py::test_01_phase2_flips_fixture_matches_todo \
       tests/governance/test_gate_deny_fields.py::test_01_invariance_decision_trace \
       tests/governance/test_gate_deny_fields.py::test_01_invariance_exclude_nonflip_mutation -q
→ 3 passed  rc=0
```

本批語料 A 僅 **pgrep** 一條被排除（TEST-2.1-FP）；其餘 29 條 trace 與 snapshot 相等。

## 3) 排除清單 mutation 實跑 rc

```
pytest tests/governance/test_gate_deny_fields.py::test_01_invariance_exclude_nonflip_mutation -q
→ 1 passed
mut_rc:0
```

## 4) 語料 A 條數未減少

| 證明 | 結果 |
|---|---|
| JSON 條數 | **30**（`grep -c '^{' …/gate_invariance_corpus.txt`） |
| pgrep 仍在 | line 58 仍含 `pgrep -fl 'codex exec|cursor-agent|grok '` |
| `git status --short` 該檔 | **無改動**（未刪、未改語料 A） |

## 5) 兩個既有失敗逐條說明

| 測試 | 本批？ | 說明 |
|---|---|---|
| `test_gate_check_latency_under_100ms` | **否** | 全套實跑 cold_ms≈283.8、audit **34468 行 / 2.0MB**。snapshot 同環境亦 >100ms（B3 收尾已記 ~203ms）。**未放寬門檻**。根因＝`audit.log` 體積 → **P1-6 線 C（第 0.5 批）**，本批不修。 |
| `test_no_unpinned_family_list_line` | 已修（B3 本體） | 釘 `_gate_lex.sh` 入 `_DRIFT` / `_CONSUMER_FILES`。本輪實跑 `unpin_rc:0`（1 passed）。 |

## 6) test_debt_gate / test_family_registry 改動逐行

**`tests/governance/test_debt_gate.py`**（+1 行）  
- hermetic 複製清單在 `"gate_check.sh",` 後加 `"_gate_lex.sh",`  
- 原因：B3 的 `gate_check.sh` Bash 路徑 `source` 同目錄 `_gate_lex.sh`；缺檔會使 hermetic 探針失真。最小同步。

**`tests/governance/test_family_registry.py`**（+1 行於 `_DRIFT`；`_CONSUMER_FILES` 加一名）  
- `_DRIFT` 增：`("_gate_lex.sh", "grok|agy)[", "executor_clis", {"claude"})`  
- `_CONSUMER_FILES`：`"gate_check.sh"` 旁加 `"_gate_lex.sh"`  
- 原因：家族 CLI 正則熱路徑移入詞法模組；不釘會 `test_no_unpinned_family_list_line` 紅。最小同步。  
- **未改既有斷言本體**（只擴充釘檔清單）。

## 7) git / pytest / golden

```
git diff --stat（tracked，含 B3 本體累積）:
 scripts/gate_check.sh                              |  32 +-
 tests/governance/fixtures/gate_decision_corpus.txt | 282 +-
 tests/governance/test_debt_gate.py                 |   1 +
 tests/governance/test_family_registry.py           |   3 +-
 tests/governance/test_gate_deny_fields.py          | 225 +-
 + untracked: scripts/_gate_lex.sh, extract_phase2_expected_flips.py,
   phase2_expected_flips.txt{,.sha256}, gate_decision_corpus.txt.sha256,
   test_gate_decision.py, test_gate_lexical_contract.py
```

```
pytest tests/governance -q
→ 1 failed, 750 passed in 1056.23s  EXIT:1
  FAILED test_gate_check_latency_under_100ms  # 非本批；見 §5
  （INVARIANCE 全綠；unpinned 全綠）
```

```
bash scripts/restore_golden_inventory.sh   # restore_rc:0
git status --short tests/golden/
→ （空）
```

## 排除機制殘留（誠實邊界，非手挑）

1. **residual flips**（在清單、尚未進語料 B）：TEST-2.2-FP4×4、TEST-2.2-PIPE、TEST-2.3-PREFIX5 中 4 條（ellipsis／字面微差）、TEST-2.4-DIRECT×3、TEST-2.4-COMMITTEE。B4 補語料 B 後反向2 自動納管。  
2. **反向2 對 residual 不 hard-fail**（避免 B3 被未實作 Task 卡死）；但 **A 排除路徑**強制「必須在 B 且翻轉」— 目前僅 pgrep 走此路徑且已綠。  
3. 若主委要求「清單每一條（含未進 B）皆 hard-fail」，需 B4 語料齊全後再開——**未自行放寬為手挑刪條**。

## 清 /tmp

- 已清本 task 的 `/tmp/govb0_*` log／workdir 意圖；**保留** `/private/tmp/claude-501` 與 `/tmp/claude-501`。  
- 未 `git checkout`／`restore`／commit／push；未碰 `data_cache/`。

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: TODO 由X轉Y 可機械抽取 21 flip+8 maintain；語料 A 30 條未刪且含 pgrep；排除後 INVARIANCE 綠；mutation 反向1 紅路徑 rc=0（斷言通過）；unpinned 釘 _gate_lex rc=0
TESTS_RUN: extract --check rc=0；deny_fields 25p；invariance+mut+fixture 3p；unpin 1p；full governance 750p/1f (latency only)；restore golden → tests/golden 空
FAILURES_SEEN: none new for unblock path；latency 既有（audit 34k 行）
SCOPE_CHANGES: 本批新增 extract 腳本+flips fixture+INVARIANCE 改寫；未改語料 A；未做 B4+
NUMERIC_OR_SCHEMA_IMPACT: 無產品數值；gate 判定仍為 B3 詞法結果；audit schema 未改
```

STATUS: DONE
