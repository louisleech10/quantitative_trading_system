# FF Mutation Gate Adversarial Review — Codex

## 結論
**機制方向可用,但目前須補後才可當硬閘。**  
現版 `scripts/mutation_probe_check.sh` 能抓「完全沒有 `test_mutation_*`」的低階缺口,也能防「整批 n/a」靜默放行；但仍有 P0 假綠洞:空探針可 PASS、每檔只要一個探針即可遮住多個 correctness claim、`async def test_*` 檔可能被跳過。§B1.2 oracle 獨立性目前誠實標明為人工 adversarial,但可加低成本啟發式告警。

## 實測反例
- `EMPTY_PROBE_RC=0`: `/tmp/.../test_empty_probe.py` 內 `def test_mutation_empty(): assert True` 讓閘 PASS。
- `MANY_CLAIMS_ONE_PROBE_RC=0`: 同檔 2 個 correctness test + 1 個空 mutation probe 讓閘 PASS。
- `ASYNC_UNPROBED_WITH_OTHER_PROBE_RC=0`: 目錄內一個 `async def test_async_correctness_claim` 無探針,另一檔有空 probe,整批 PASS。
- `NA_ONLY_RC=1`: 單一純 N/A 檔會因 pytest rc=5 被擋。
- `NA_NO_REASON_WITH_OTHER_PROBE_RC=0`: N/A 行無理由,只要同批其他檔有 probe,可 PASS。
- `BASH_N_RC=0`: bash 語法檢查通過。

## A. 漏洞:假綠仍能過閘

### A1. 空探針可過閘
- 證據: `scripts/mutation_probe_check.sh:47` 只檢查 `def test_mutation_`; `:60-67` 只檢查 pytest pass 數。`def test_mutation_empty(): assert True` 會被當成有效探針。
- 攻擊法: 在 correctness 測試旁新增一個永遠 pass 的 `test_mutation_*`,完全不注入壞改、不呼叫原測試、不含 `pytest.raises`。
- 反例輸出: `1 passed, 1 deselected` 後 `MUTATION-PROBE PASS`。
- 修法: 章程補明「探針必須含 mutation marker + 反證上下文」,腳本加啟發式:每個 `test_mutation_*` 函式 body 至少命中 `pytest.raises|pytest.fail|monkeypatch|patch.object|mock.patch|setattr|clear\\(|initialize\\(` 等白名單 token,且不得只有 `assert True/pass`。這不是完整證明,但能擋空探針。

### A2. 每檔一個 probe 遮住多個 correctness claim
- 證據: §B1.1 說「每個正確性測試必附同檔 `test_mutation_*`」,但腳本 `:47-48` 是 file-level gate,不是 test-level mapping。
- 攻擊法: 同檔新增多個 correctness tests,只留一個和其中一條性質相關的 probe,其他 correctness claim 沒牙齒仍 PASS。
- 反例輸出: `MANY_CLAIMS_ONE_PROBE_RC=0`。
- 修法: B4 矩陣變成機械輸入,要求 `# MUTATION-PROBE-FOR: test_x,test_y` 或 test docstring marker,腳本檢查每個 claim function 有對應 probe；做不到時章程誠實降級為「file-level smoke gate,不等於每條 correctness claim 已 mutation-covered」。

### A3. Oracle 獨立性仍主要靠人,可加啟發式告警
- 現況: 腳本註解 `:18-19` 已誠實標明 B1.2 不由機器判斷。
- 攻擊法: `test_mutation_*` 裡仍使用被測 module 的 `list_indicators()`、`_INPUT_TYPE_MAP`、registry 或 wrapper 當 expected oracle；mutation 同步污染 source + oracle 後仍綠。
- 低成本補強: 腳本可掃描受審檔的 import 與 probe body,對「oracle 區域」出現 `from momentum.FeatureEngineering.atomic... import <被測函式/map/registry>`、`list_indicators(`、`INDICATOR_REGISTRY`、`_INPUT_TYPE_MAP`、`FeatureFactory` 等給 WARNING 或 fail-on-strict。這是 heuristic,不能取代 adversarial review；章程應明確寫「機器只做自指風險告警,最終靠 reviewer 判斷獨立 oracle」。

### A4. `-k mutation` 漏跑非 mutation 命名探針
- 證據: `scripts/mutation_probe_check.sh:60` 固定 `pytest -k "mutation"`；`test_atr_removed_fails` 這類語義探針不會被選中。
- 影響: 若章程允許非 `test_mutation_*` 命名,會漏跑；目前 §B1.1 明確要求 `test_mutation_*`,所以這點不是現版漏洞,但要避免未來命名漂移。
- 修法: 維持強命名規則,或改用 marker `@pytest.mark.mutation_probe` 並跑 marker。marker 比 `-k` 更不受函式/檔名語義影響。

### A5. N/A 不能整批濫用,但空理由可混過
- 證據: 全 N/A 檔會因 `pytest -k mutation` rc=5 被 fail,所以「整批 n/a」不能放行。可是 `:50` 只匹配 `MUTATION-PROBE: n/a`,不檢查同行理由；同目錄另有一個 probe 時,空理由 N/A 檔可 PASS。
- 攻擊法: 在多檔批次中,大部分 correctness test 檔標 `# MUTATION-PROBE: n/a`,只留一個空 probe 讓全批 PASS。
- 修法: N/A 行 regex 要求非空理由,例如 `MUTATION-PROBE:[[:space:]]*n/?a[[:space:]]*[-—:][[:space:]]*[^[:space:]].+`;另加統計輸出 `n/a files=N, probe files=M`,若 N/A 比例高於 0 或高於閾值,review 報告必列人工簽核。

## B. 誤擋:正當測試被擋

### B1. 純 smoke/contract 批次全 N/A 會被擋
- 證據: `NA_ONLY_RC=1`;規則 1 允許 N/A,但規則 2 仍要求整個輸入路徑至少有一個 passed mutation probe。
- 影響: 純邊界、smoke、contract 測試檔如果以單檔或全 N/A 目錄送審,即使不聲稱 correctness,也無法通過。
- 修法: 腳本分 mode: `--correctness` 要求至少一個 probe；`--allow-all-na` 只允許在非 correctness gate 使用,且輸出 `MUTATION-PROBE N/A ONLY` 非 PASS。或由調用端只把 correctness paths 傳給腳本。

### B2. `pytest -k mutation` 的 pass 計數容易給錯誤訊息
- 證據: skip probe 會 rc=0 且 `1 skipped`,腳本以 collected=0 fail,行為合理；但訊息寫「收集到 0 個 mutation 探針」不準確,實際是「0 passed」。
- 影響: debug 時會誤導為沒有收集,而不是全部 skip/xfail。
- 修法: 用 `pytest --collect-only -q` 或 `pytest --json-report`/`--co -q` 先列 nodeid,再跑精確 nodeid；pass/skip/xfail 分開統計。

## C. 腳本邏輯與 Bash 相容性

### C1. `async def test_*` 不被規則 1 視為測試
- 證據: `scripts/mutation_probe_check.sh:46` 只 grep `^[[:space:]]*def test_`,不含 `async def test_`。
- 攻擊法: 未來 API/WS async test 檔沒有 mutation probe,若同批其他檔有 probe,規則 1 跳過該檔,規則 2 由其他 probe 補 pass,整批 PASS。
- 修法: regex 改為 `^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+test_`；mutation probe 檢查同樣支援 async。

### C2. 文件/目錄路徑處理大致可用,但 newline 檔名不支援
- `find` 結果寫入 newline 字串,一般含空格路徑由 `read -r` 可保住；pytest 參數用 `"$@"` 正確。
- newline in filename 會壞,但 repo 測試檔不應使用此命名,可接受。

### C3. `venv/bin/python` fallback 合理,但未鎖定 repo root
- 腳本從 repo root 執行時 OK；從子目錄執行會找不到 `venv/bin/python` 而落到系統 `python`。
- 修法: 用 `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` 推 repo root,以 `"$REPO_ROOT/venv/bin/python"` 為優先。

### C4. `grep '[0-9]+ passed'` 不是 collected
- 證據: `scripts/mutation_probe_check.sh:63` 變數名 `collected`,實際取的是 passed 數。
- 影響: 對 skip/xfail 報錯語義不準；對「普通測試被 -k mutation 選中」也會把普通 pass 當 probe pass,但規則 1 通常會抓到無 `def test_mutation_` 的檔。
- 修法: 改名 `passed_count`;更好是直接從 pytest collection nodeid 中篩 `::test_mutation_`。

## 建議補丁方向
1. 腳本改為先 discovery: 用 AST 或 pytest collection 找出每個檔的 `test_*` / `test_mutation_*`,支援 `async def`。
2. 對每個 `test_mutation_*` 做最低 body heuristic,擋 `assert True/pass` 空探針。
3. 加 `MUTATION-PROBE-FOR` 或矩陣驅動,避免 file-level probe 遮住多個 correctness claim。
4. N/A 分支輸出獨立狀態,要求非空理由,全 N/A 只能在非 correctness mode 下通過為 N/A,不可顯示 PASS。
5. Oracle 獨立性在章程中誠實標明「人工必審 + 機器 heuristic warning」,不要宣稱完全機器強制。

## 收尾欄位
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、指定 prompt、commit 0d377e6 diff、`scripts/mutation_probe_check.sh`; 用 /tmp 最小 pytest 檔驗證空探針/多 claim 單 probe/async test/N-A/skip 行為。  
TESTS_RUN: `bash -n scripts/mutation_probe_check.sh` pass; 多組 `/tmp` 反例執行結果如上。  
FAILURES_SEEN: none, 反例是預期用於 review 的漏洞驗證。  
SCOPE_CHANGES: none, 只新增本 review 檔。  
NUMERIC_OR_SCHEMA_IMPACT: none。  
STATUS: DONE
