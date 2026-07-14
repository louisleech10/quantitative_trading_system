# IC1C-B2 Code Review — Codex (2026-07-14)

範圍：`git diff HEAD` + `handoffs/IC1C-B2-RESULT.md`，對照 Frozen TODO Phase 2 / SPEC §U；RECONCILE 三家戳記機檢 PASS。

## BLOCKING findings
1. **B1 — G-NEW2 擅自削弱 Frozen oracle**：TODO:125 明定排除三注入 feature 後，G-NEW COST_ENABLED 與 API feature dict「逐鍵 sha256 等值」；`scripts/ic1c_freeze_baseline.py:1294-1308,1375` 另放行 `gross_ic`。既有 artifact 實查 4/4 非注入 feature 的 `gross_ic` 不等、其餘鍵等值，故完整 dict 全不等。來源路徑不同是有效設計發現，但只能回修 Frozen TODO/SPEC 或讓兩路使用同一 canonical IC 輸入，不得現場降 oracle。
2. **B2 — B2 Gate 無法依字面命令重現**：`pytest ... --collect-only`、mutation checker、`python scripts/ic1c_freeze_baseline.py --baseline new2` 均在 import `api.main` 時連 Binance 並以 `ConnectionError` 失敗；違反 TODO:124「離線可 collect/fixture 隔離」，且 RESULT 的 collect/probe/new2 PASS claim 在本環境不可重現。程序內先 stub `Client.ping` 後 27 tests 才全過。
3. **B3 — TS 並非 §U discriminated union / 精確 profiles**：`frontend/src/lib/types.ts:2459-2488` 用單一 interface（`status/value/reason` 與 feature/profile 欄皆 optional），可表示 `status:'ok', value:null, reason:'x'`、缺 capacity 子鍵及混合 profile；與 SPEC §U「TS 同構、唯一合法形狀、精確鍵集合」不符。
4. **B4 — T4 三態 oracle 未證 API 422 傳導**：`shows_error_on_422` 只是直接傳 `formError` prop，沒有讓 request builder/API client 回 422；且無 loading 態測試。元件有三態分支、page catch 會設 failed，但 Frozen TODO:122 要的是可證偽 wiring oracle，目前測試可在 API error 傳導壞掉時仍綠。
5. **B5 — 未授權 scope change**：`frontend/src/hooks/useFeatureFactory.batchDate.test.ts` 不在 TODO Task 2.2 修改清單；即使只是刪 unused callback args 且 build 所需，依執行合約仍屬越界，須 revert 或先取得擴 scope 核准/獨立票。

## 三處現場調適裁決與正向核對
- NaN/inf：**fail-closed 行為成立，測試分層調適本身不阻斷**。標準 JSON 無非有限 number；我以可表示字串 `"NaN"`/`"Infinity"` 經真 HTTP 驗證皆 422（含 disabled NaN），unit 亦覆蓋 float NaN/inf。建議把兩個字串案例納入 T2，避免「HTTP 未測」誤述。
- G-NEW2 gross 放行：**構成 BLOCKING 違規**（B1）；合理根因不能取代 Frozen 變更程序。
- eslint scope 外檔：**構成 BLOCKING scope 違規**（B5）；改動語意雖中性，授權仍缺失。
- 雙入口與繞道：Deep endpoint、Analyze endpoint、Analyze 的 nested `deep_analysis_config.config_override` 三路皆實測 422；`_build_deep_module_override` 是 base 先、typed 最後；7bps/§U runtime union patched-offline e2e 通過。
- 前端：`useState(5)`、scenario 常數與 `turnover ?? 0.1` 已清；Vitest 5/5、Next build 成功。m4/m7/m10 probes 在程序內隔離網路後全過，但正式 mutation gate 因 B2 collect error 仍 FAIL。

ASSUMPTIONS_VERIFIED: Frozen TODO:125 無 gross_ic 豁免；4/4 非注入 feature gross 不等/其餘鍵等值；HTTP NaN/inf 字串與三種 override 路徑皆 422；typed-last/union runtime/前端假值清除成立。
TESTS_RUN: stamp checker PASS；官方 collect FAIL(ConnectionError)；stub Client.ping 後 pytest 27 passed；官方 mutation FAIL(collection)；Vitest 5 passed；Next build PASS；官方 new2 FAIL(ConnectionError)；jq artifact comparison 4/4 full_equal=false。
FAILURES_SEEN: 離線 import Binance 導致三項字面 gate 失敗；G-NEW2 artifact 證實 gross_ic 4/4 差異。
SCOPE_CHANGES: reviewer 僅新增本檔；實作者越界檔見 B5。
NUMERIC_OR_SCHEMA_IMPACT: reviewer 無；B1 弱化數值傳導 oracle，B3 TS schema 過寬。
CODE-REVIEW: REJECT(5 BLOCKING)
