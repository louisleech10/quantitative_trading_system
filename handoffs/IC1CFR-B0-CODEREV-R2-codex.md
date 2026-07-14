# IC1CFR-B0 Code Review R2 — Codex

- task-id: `IC1CFR-B0`; verdict: **CLOSED / APPROVE（0 BLOCKING）**。
- scope: 唯讀掃退修；唯一產出為本檔。

## 原 BLOCKING 閉合

1. **CLOSED — fail-open**：隔離擷取實檔 `_parse_pytest_failed_nodeids` 與 `collect_pytest_failed_nodeids`，monkeypatch pytest 為 `returncode=3`、stdout/stderr 無 nodeid；實跑輸出 `CASE1_EXIT 1`，stderr 含 `returncode=3` 與 `no failure/collection nodeids parsed`。`check_nodeids()` 無機會把空集合當子集 PASS。
2. **CLOSED — regex 誤截**：實檔 parser 反例 `ERROR tests/a.py::test_x` → 僅 `tests/a.py::test_x`；`ERRORS` block 的 `collecting tests/d.py::test_z` 不產 file-only；真 `ERROR tests/b.py` / `ERROR collecting tests/c.py` → 分別收 `tests/b.py` / `tests/c.py`。逐行 `if "::" in line: continue` 與 block 分支排除成立。
3. **CLOSED — baseline 重建**：`wc/awk/sort` → 77 行、77 unique、77 含 `::`、0 file-only、已排序。三個誤收 file path 均不存在；新增 golden nodeid 存在。集合反算為舊 79＝76 test-level＋3 file-only，與 79→77（移除 3、新增 1）精確一致。
4. **CLOSED — 凍結產物未被動**：退修派工時間 01:40；`before.json`、`before.sha256`、`factory_allowlist.txt` mtime 均 01:08，早於派工且彼此一致。現 SHA256 分別 `c72dd1d…d3ff`、`44621d…721b`、`83f663…3ef`；canonical 內容仍為首輪已獨立驗過的 `2b6489da…512ca`。只有 script 01:42、nodeids 01:59、RESULT 02:01 為退修後時間。

## Delta / receipts

- delta 聚焦 `scripts/ic1cfr_stopgap_freeze.py:530-617` 的 rc 保留、空解析 fail-close、兩處 collection 排除 `::`，以及 nodeid baseline/RESULT；未見 runtime (`momentum/ api/ frontend/`) 變更。
- `python3 -S` AST 直接解析/執行實檔 parser 反例：上述矩陣 PASS；fail-close monkeypatch：exit 1 PASS。
- `awk` + `sort -c` + 集合算術：77/77/0、79→77 PASS。
- 未重跑 15 分鐘全 suite；重建全跑 receipt 為 RESULT CMD E：pytest rc=1，45 failed/1496 passed/18 skipped/32 errors，parser=77、file-only=0。此輪以集合與 parser 反例獨立複核該 receipt。

ASSUMPTIONS_VERIFIED: 原 1 BLOCKING 的兩個根因與四個指定反例均以實碼/實檔複驗 CLOSED。
TESTS_RUN: isolated actual-function probes PASS；baseline wc/awk/sort/set arithmetic PASS；artifact stat/shasum PASS。
FAILURES_SEEN: `python3 -m py_compile` 因系統 pyc cache 路徑權限被拒；改用不寫檔的 AST parse/compile 驗證，PASS。
SCOPE_CHANGES: none；產出 `handoffs/IC1CFR-B0-CODEREV-R2-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: none（review only）。
STATUS: DONE
CODE-REVIEW-R2: APPROVE
