# P2DEBT-T2 SPEC R2 REVERIFY — codex
Task-id: p2debt-t2 | Date: 2026-07-11 | Mode: read-only adversarial；未讀 grok re-verify；未跑 pytest body/collect-only

## Original findings re-check
- **B1 STILL-OPEN — full-set/驗收未閉合。** Receipt: `rg -l --glob '*.py' '\.(analyze|start_analysis|refilter)\(' tests | sort` 仍得 16 檔；`tests/api/test_ic_run_selector.py` 在集合內但 §COVERAGE A–F 無分類。ML 表列 5 個實際檔（R2 L94–99），V7 僅跑 FF + `Analysis/test_lightgbm_analyzer.py` + `Analysis/test_xgboost_protocol_methods.py`（L320），漏 `test_lightgbm_edge_cases.py` 與 momentum 根兩個 phase3 檔。GEN-01..04 雖入表，repo `rg 'IC_PERSIST_REDIRECT_ROOT'` 除 R2 自身為 0，Phase 4 的 env 契約無 consumer/seam。
- **B2 STILL-OPEN — seam/fixture 不可執行。** Receipt: R2 helper 明定 `monkeypatch,tmp_path`（L152–158），但現有 API polluter fixtures 是 session/session/module scope（`rg '@pytest.fixture|scope='`：analysis_api L69、export L65、deep L124）；顯式請求 function-scope fixture會 `ScopeMismatch`。S2/S4/S5/S6/S8 的「wrap 原函式後改函式內 local literal」沒有可注入參數；S8/S10 仍是 `wrap 或 monkeypatch` 二選一。plugin fixture 定義在 `..._plugin.py`（L191），Analysis/API 卻從另一模組 re-export（L189–190）。根層 `tests/test_feature_factory_e2e.py` 不在 momentum/API conftest scope，卻被要求 `usefixtures`。spy 有 production-prefix 斷言，但上述掛載/patch 點不足以使其覆蓋 production call path。
- **B3 STILL-OPEN — §V outer harness/mutation 不可證偽。** R2 L296–299 稱 `in-process importlib` 跑 pytest nodeid；importlib 不執行 pytest fixture/marker/nodeid，故不是包住 V1 suite 的 outer harness。L304–306 的 disabled redirect 要 production literal 寫入 `fake_prod`，卻未定義把 production root 映到 fake root 的機制；若用 redirect 做映射，並非「撤 redirect」mutation。per-file SHA256 oracle 本身正確，但沒有可執行 runner。
- **B4 STILL-OPEN — golden A/B 不是 redirect on/off oracle。** L223–227 的 A/B 兩次皆啟用 redirect；唯一無 redirect 的 Run C 被標「可選」。`normalize(result)` 與「豁免欄位」未具體定義；L234/V5 又要求 with/without receipt，與測試設計不一致。兩個既有 golden nodeid 的 `2 passed、0 skipped` 契約已補上，但不足以補此 oracle 缺口。
- **B5 STILL-OPEN — I1–I3 不可執行/不完整。** I1（L246）未定義如何從 isolation test 執行三個固定 nodeid並觀測跨 pytest run 的 install count，與失效的 in-process harness 同型；I2 受 B2 seam/scope 問題阻斷；I3 指定新檔 `test_ic_persist_redirect_inventory.py`（L248），但 §C allowed-new-files（L212）未包含它。正向條款「無 root autouse、禁 collect-grep」已閉合。
- **B6 CLOSED。** Receipt: R2 L6–19 有大任務白話 manifest/雙家族條款；L23–31 明列大小「大」及 `RISK-HIT: a,b`，與跨 IC/API/FF/ML/generator scope 一致。
- **M1 STILL-OPEN — §G/§V exit 仍矛盾。** V1 同時要求 `10 passed, 0 skipped` 又允許 perf 單一 skip（L314）；靜態計數為 oos 2 + e2e 5 + filter 1 + golden 2 = 10，perf skip 時只能是 9 passed/1 skipped。另 V3/V5 用 `pytest -q` 卻要求 stdout 的 `DIGEST_DIFF_EMPTY`/`ab_hash`（L316/L318）；pytest 預設 capture 下成功測試的 print 不出現在 stdout，SPEC 未加 `-s` 或 terminal reporter。

## New R2 problems
- **N1 BLOCKING — session-safe lifecycle 未設計。** API app/service 是 module globals且背景 task 跨 fixture setup；redirect 需 session/module scope 的 `tmp_path_factory` + 可 teardown patcher，R2 的 function fixture contract 無法安全覆蓋。
- **N2 BLOCKING — generator「文件化」不是 hermetic contract。** 生產碼禁止修改（L206/L214），pytest helper 又依賴 MonkeyPatch；GEN 腳本無可呼叫的 output-root API，故 env 名稱只是未實作假設。
- **N3 BLOCKING — 驗收未覆蓋宣稱的 ML 全家族。** §COVERAGE/Phase 2 宣稱 ML-01..06 全掛（L264–267），但唯一 ML 驗收 V7 漏 3 個 polluter 檔，外層 V3 又只聲稱跑 V1 子集。

ASSUMPTIONS_VERIFIED: 16-caller enumeration；split/oos stage7 stub；6 FF generate calls；5 ML polluter files；API fixture scopes；production hardcoded locals；fixture/conftest reachability；R2 §G/§V/§ISOLATION internal consistency
TESTS_RUN: read-only `rg`/`sed`/`nl`/`test -e`/`git status --short`；未跑 polluting pytest body或collect-only
FAILURES_SEEN: one shell quoting parse error during read-only rg probe；corrected with literal-safe rg，無檔案副作用
SCOPE_CHANGES: none；唯一產出 `handoffs/P2DEBT-T2-SPEC-REVERIFY-codex.md`
NUMERIC_OR_SCHEMA_IMPACT: none
Verdict: BLOCK — B1/B2/B3/B4/B5/M1 仍開；核心阻塞為 fixture scope/reachability、不可執行 outer harness/mutation、非 on/off golden oracle、generator 無 redirect consumer、ML 驗收漏檔
STATUS: BLOCKED — p2debt-t2 SPEC R2 尚未閉合，不附 RECONCILE-STAMP
