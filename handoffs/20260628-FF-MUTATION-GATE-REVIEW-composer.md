# Adversarial Review — Mutation Gate Mechanism (Composer)

**審查對象**: commit `0d377e6` — `docs/TEST_DESIGN_CHARTER.md` §B1.1/B1.2/B1.3 + B1-驗收紀律、`scripts/mutation_probe_check.sh`  
**審查者**: Composer (adversary, 作者不自審)  
**日期**: 2026-06-28  
**實測環境**: macOS bash 3.2.57, pytest 8.4.2, `venv/bin/python`

---

## 結論

**機制可用，但須補強（非 BLOCKING 推翻，屬 P1 硬化項）。**

相對「pytest 全綠 + diff grep」是實質升級：dogfood 已證能抓「整檔缺探針」；全 skip / 全 xfail / 整批 N/A 會被 `collected=0` 或 `rc≠0` 擋住。  
但 **B1.1 宣稱的「基線綠→變異紅→原斷言 pytest.raises」目前幾乎全靠作者自律 + adversarial 目檢**，腳本只驗「有名、有跑、有綠」，**擋不住空心探針**。B1.2 oracle 獨立性章程寫得誠實（腳本註明不驗），應維持 adversarial 必問，可加低成本 WARN 啟發式。

**建議**: B1 atomic 批次可繼續用此閘；合併前須補 P1（探針結構靜態檢查 + N/A 錨點收緊）；長期接入 `gate_check.sh` 或 CI 受審路徑 hook，否則仍靠驗收紀律。

---

## A. 漏洞清單（假綠仍能過閘）

### A-1. 空心探針 `assert True` — **已實測可過**

| 欄位 | 內容 |
|------|------|
| **攻擊法** | 每檔放 `def test_mutation_hollow(): assert True`，主測試照常寫或寫弱斷言。 |
| **反例** | `/tmp/test_hollow_plain.py` → `bash scripts/mutation_probe_check.sh` → **PASS**（1 passed）。 |
| **修法** | 腳本增 **規則 1.5（靜態）**：`test_mutation_*` 函式體須含 `pytest.raises`（或 `np.testing.assert` 包在 raises 內）；禁單行 `pass`/`assert True`/`1/0` 偽 raises。章程 §B1.1 加一句：「探針須 import/call 同檔至少一個非 mutation 測試函式，或 inline 重跑其斷言路徑」。 |

### A-2. 偽自證 `pytest.raises` — **已實測可過**

| 欄位 | 內容 |
|------|------|
| **攻擊法** | `def test_mutation_fake():` 內 `with pytest.raises(ZeroDivisionError): 1/0`，與待測模組無關。 |
| **反例** | `/tmp/test_fake_raises.py` → **PASS**。 |
| **修法** | 靜態檢查：探針內須出現待測模組 import（`TALibWrapper`/`VolumeIndicatorEngine` 等）或同檔被測符號；可選 AST 驗 `raises` 區塊內含 `assert_allclose`/`assert_array_equal` 等。 |

### A-3. 無基線綠、未綁底層測試 — **已實測可過**

| 欄位 | 內容 |
|------|------|
| **攻擊法** | 探針只做「無關斷言必紅」，不先跑基線、不呼叫 `test_*` 主體。 |
| **反例** | `/tmp/test_no_baseline.py` → **PASS**。現網 `test_atomic_differential.py::test_mutation_wrapper_source_close_to_open_fails` 亦用 `assert not np.allclose` 而非 `pytest.raises`，與 §B1.1 文字不完全一致但仍過閘。 |
| **修法** | 章程明確兩種合格模式：(a) 基線綠→注入→`pytest.raises(AssertionError)` 重跑原斷言；(b) 注入後獨立 oracle 斷言必與基線分離且須先有一行「未注入時主斷言會過」的註解+結構化標記 `# MUTATION-BASELINE: <fn>` 供腳本 grep。 |

### A-4. 探針命名繞過 `-k mutation` — **已實測可過**

| 欄位 | 內容 |
|------|------|
| **攻擊法** | 真邏輯放 `test_atr_removed_fails`（不含 mutation 子字串），檔內再放空心 `test_mutation_stub`。規則 1 見 `test_mutation_*` 即放行；規則 2 只跑 stub。 |
| **反例** | `/tmp/test_wrong_name_probe.py`（含會 fail 的 `test_atr_removed_fails`）→ **PASS**（僅 stub 被跑）。 |
| **修法** | 規則 2 改 `pytest -k "test_mutation_"`（或 `--collect-only` 數 `test_mutation_` 開頭節點）；規則 1 要求**每個** `def test_`（非 mutation）須被至少一個 `test_mutation_*` 在 docstring 標 `# MUTATION-COVERS: test_foo`（機械對帳）。 |

### A-5. B1.2 oracle 自指 — **機器未驗（章程已誠實標明）**

| 欄位 | 內容 |
|------|------|
| **攻擊法** | 探針用 `build_talib_input_semantics` 同時改 `TALIB_INPUT_SEMANTICS` 與 wrapper，或 oracle 從 `list_indicators()` 衍生；閘仍綠。C1-2 類假綠可復現。 |
| **反例** | 現網 C1-2 修後探針用獨立 `arrays_from_dataframe` + talib，屬好範本；但機制本身不擋自指。 |
| **修法（低成本啟發式，WARN 非 FAIL）** | 對 `test_mutation_*` 掃描：(1) 是否讀 `_*_MAP`/`list_indicators` 同時當 expected；(2) 是否 `from ...talib_wrapper import` 的私有欄位出現在斷言右側；(3) 是否缺少 `talib.`/`scipy.`/`tests.references` 任一獨立 oracle 痕跡。輸出 `ORACLE-SELF-REF WARN` 供 adversarial 必問，**不宣稱機器證獨立**。章程 §B1.2 保留「adversarial 標準必問」為主閘。 |

### A-6. N/A 豁免在批次路徑下可濫用 — **已實測可過**

| 欄位 | 內容 |
|------|------|
| **攻擊法** | 在受審目錄新增 P0 檔，docstring 內嵌 `# MUTATION-PROBE: n/a — fake smoke`（非行首 `#` 註解），不寫 `test_mutation_*`。同目錄其他檔有真探針 → 規則 2 仍 `6 passed` → **整批 PASS**。 |
| **反例** | 暫增 `tests/feature_engineering/atomic/test_adversary_na_leak.py`（已刪）→ `mutation_probe_check.sh tests/feature_engineering/atomic/` → **PASS**。單檔 N/A-only 仍 FAIL（`collected=0`），故「整批 n/a」擋得住；**混批假 N/A 擋不住**。 |
| **修法** | N/A 僅接受**行首** `^[[:space:]]*# MUTATION-PROBE: n/a —`（排除 docstring）；或要求 N/A 檔**不得**含 `def test_`（純 fixture/helper 檔才可 N/A）。 |

### A-7. 閘未接入 fail-closed gate — **流程洞**

| 欄位 | 內容 |
|------|------|
| **攻擊法** | 實作者不跑腳本，驗收方只看 pytest 全綠（違反 B1-驗收紀律但無機械後果）。 |
| **反例** | `scripts/gate_check.sh` / `gate.sh` **無** `mutation_probe_check` 引用；僅 charter 與派工 prompt 要求。 |
| **修法** | FF P0 路徑列入 preflight/postflight 或 `gate.sh dispatch` 子檢查；至少 `tests/feature_engineering/atomic/` 硬編在 B1 完成批驗收腳本。 |

---

## B. 誤擋清單（擋正當測試）

### B-1. 契約/純 smoke 檔若被納入路徑會 FAIL — **可接受但需紀律**

| 欄位 | 內容 |
|------|------|
| **情境** | `test_failopen_contract.py`、`test_split_contract.py` 等契約測試無探針 → 規則 1+2 皆 FAIL。 |
| **評估** | 章程定位「受審路徑 = 聲稱正確性批次」；對 contract 檔誤用全目錄掃描會誤擋。**非設計 bug**，但須文件化：只對 SPEC 標 P0 目錄跑閘；契約檔加行首 `# MUTATION-PROBE: n/a — contract only, §0 smoke`。 |
| **假探針風險** | 中等：開發者可能為過閘寫 A-1 空心探針而非正確 N/A。N/A 模板應寫進 §B1.1 範例。 |

### B-2. N/A 逃生口對單檔 correctness 不夠 — **反而防濫用**

| 欄位 | 內容 |
|------|------|
| **情境** | 單檔僅 N/A、無 `test_mutation_*` → `rc=5` / `collected=0` → FAIL。 |
| **評估** | 正確；不能靠 N/A 獨逃。誤擋風險低。 |

### B-3. 路徑含空格 — **實測 OK**

| 欄位 | 內容 |
|------|------|
| **情境** | `"/tmp/test path with spaces"` + `test_mutation_ok` |
| **反例** | **PASS**（`"$@"` 引號正確）。 |

### B-4. `collected` 解析與 xfail/skip — **部分邊界已擋**

| 欄位 | 內容 |
|------|------|
| **全 skip** | `/tmp/test_all_skip.py` → `1 skipped`, `collected=0` → **FAIL** ✓ |
| **全 xfail** | `/tmp/test_all_xfail.py` → `1 xfailed`, 無 `N passed` → `collected=0` → **FAIL** ✓ |
| **混合** | `1 passed, 1 xfailed` → grep 取 `1 passed` → PASS（合理） |
| **殘餘風險** | 若 summary 行含多個 `N passed`（罕見 plugin 輸出），`head -1` 可能取錯；建議改 `tail -1` 解析最終 summary 行，或 `pytest --tb=no -q` 後讀 `$?` + `--collect-only -q` 單獨數探針數。 |

### B-5. bash 3.2 — **相容**

| 欄位 | 內容 |
|------|------|
| **實測** | macOS 預設 bash 3.2 可跑；用 `[[:space:]]`、`read -r`、heredoc 分檔列表，無 bash 4+ 語法。`set -u` 已開。 |

---

## C. 腳本邏輯逐行審查 (`mutation_probe_check.sh`)

| 行 | 觀察 | 嚴重度 |
|----|------|--------|
| 24-25 | `venv/bin/python` → `python` fallback 合理；未檢查 pytest 是否存在（失敗時訊息靠 pytest）。 | LOW |
| 31-42 | 目錄用 `find ... -name 'test_*.py'`；不跟 symlink、不排 `__pycache__` 旁檔，足夠。路徑含換行極罕見未處理。 | LOW |
| 44-56 | 規則 1：`def test_` 存在才要求探針；純 helper 檔跳過 ✓。N/A grep 過寬（見 A-6）。 | MED |
| 54-56 | `files` 變數 trailing newline + heredoc 讀取：實測正常；空行 `continue` ✓。 | OK |
| 59 | echo 用 `$*` 僅顯示，不影響執行。 | OK |
| 60 | `"$@"` 正確引號傳 pytest。 | OK |
| 63 | `grep -oE '[0-9]+ passed' \| head -1`：全 xfail/skip 時得 0 → fail ✓；見 B-4 殘餘風險。 | LOW |
| 64-68 | `rc≠0` 與 `collected=0` 分開訊息；但 N/A-only 單檔兩條都觸發時訊息重複（規則 1 已 exempt 則只見 rc=5）。 | LOW |
| 70-76 | 有 fail 時 exit 1；全過 exit 0。無 `set -e` 刻意控制流程 ✓。 | OK |
| — | **未驗探針內容**（A-1~A-4 根因）。 | HIGH |
| — | **未接入 gate_check**（A-7）。 | MED |

---

## D. 章程條文對照

| 條文 | 評估 |
|------|------|
| **§B1.1** | 意圖正確；與腳本能力有 gap（宣稱自證，機器只驗存在+綠）。建議加「探針結構最低要求」並與腳本規則 1.5 對齊。 |
| **§B1.2** | 誠實標 oracle 靠 adversarial；C1-2 反例清楚。建議加 WARN 啟發式清單，不過度承諾機器驗證。 |
| **§B1.3** | 內容正確；腳本**不**驗 cache reset，仍靠探針綠間接推論。可接受，adversarial 抽樣讀 `clear()`/`initialize()` 即可。 |
| **B1-驗收紀律** | 「親跑看真紅真綠」是必要補丁；腳本單獨不足以代驗收。應在 RESULT 模板強制貼 `mutation_probe_check` 輸出 + 至少一則手動 `--lf` 探針紅截圖/日誌。 |

---

## E. 優先修補建議（按 ROI）

1. **P0（本批可做）**: 規則 2 改 `-k "test_mutation_"`；N/A 改行首錨點（堵 A-6）。
2. **P1（下一 commit）**: 規則 1.5 靜態掃描空心/偽 raises（堵 A-1/A-2）；docstring 範本 + contract N/A 範例（減 B-1 假探針）。
3. **P2**: oracle 自指 WARN 啟發式（A-5）；`gate.sh` / postflight 接入（A-7）。
4. **維持人工**: B1.2 完整 oracle 審計、B1-驗收紀律親眼看紅。

---

## F. 實測摘要

```text
# 現網 dogfood
bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/
→ PASS, 6 passed, 53 deselected

# 攻擊向量（皆在 /tmp 或暫增後刪除）
hollow assert True          → PASS (A-1)
fake raises 1/0             → PASS (A-2)
misnamed + stub             → PASS (A-4)
docstring N/A in batch      → PASS (A-6)
all skip / all xfail        → FAIL (collected=0) ✓
N/A-only single file        → FAIL ✓
path with spaces            → PASS ✓
```

---

ASSUMPTIONS_VERIFIED: 攻擊向量以本機 bash 3.2 + venv pytest 實跑確認；atomic 目錄為 HANDOFF 聲稱之 dogfood 路徑；gate_check 無 mutation 引用以 grep 確認。  
TESTS_RUN: `bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/` PASS；多組 /tmp 攻擊腳本見 §F。  
FAILURES_SEEN: none（審查任務，未改產品碼）。  
SCOPE_CHANGES: none（僅寫本 review 檔）。  
NUMERIC_OR_SCHEMA_IMPACT: none。

STATUS: DONE
