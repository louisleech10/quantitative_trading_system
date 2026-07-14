# IC1C-B3 Code Review — Codex (2026-07-14)

task-id: IC1C-B3 | reviewer: codex | scope: HEAD diff 的 B3 UI/docs/baseline、`tests/conftest.py` 裁決與 RESULT

## Verdict

APPROVE。Task 3.1 的 UI 註記、文件契約與 G-NEW2 零 schema/payload 證據成立；無 blocking。

## Findings

1. `NetICChart` 四態均顯示 per-rebalance、未年化、禁跨 timeframe 直比，chart tooltip 同文；build 與 8 個 Vitest 通過。
2. API 文件與實作一致：typed request=`net_ic`、engine/module=`net_ic_analysis`；SKIPPED/GROSS_ONLY/COST_ENABLED 精確鍵集合、conditional union、成本域與 enabled 缺值 422、Deep/Analyze 兩入口 override reject 均對上 model/service/tests。
3. G-NEW2：HEAD 與工作樹 `.result` canonical sha 同為 `98a4e56b...`；刪 `git_head` 後整份 JSON sha 同為 `275fa643...`。故檔案 sha 變因確為 lineage `2133c77...`→`04ac6fb...`，feature/summary/payload 未變；現檔 sha sidecar 校驗通過。
4. **擴 scope 核可**：正式授權 `tests/conftest.py` 的全域 `Binance Client.ping` stub，理由為 TODO r7/B2-B3 Gate 離線可 collect/run 的必要 enabler。它只替換 ping；現有真 Binance 測試仍呼叫 `get_klines`/download，且全 repo 無直接 ping oracle，未發現 mask 真連線驗收。未來新增 ping 契約測試須明示 opt-out/隔離；B3 RESULT 的 `SCOPE_CHANGES:none` 應以本授權更正解讀。
5. full-suite 20 個 deep-analysis ERROR 是 redirect process-global lock 的順序污染：同檔及相關 86 tests serial 重跑全綠，且 B3 production diff 不碰 redirect。歸屬既有 test-infrastructure/order-dependence，非 IC1C B3 回歸；另票修 fixture lifecycle，不能把單跑綠解讀為 full-suite gate 綠。
6. NON-BLOCKING：`docs/API_SPECIFICATION.md` 有 5 處 Markdown 行尾空白；不影響契約/渲染，後續整理即可。

ASSUMPTIONS_VERIFIED: Frozen SPEC/TODO reconcile 已核可；HEAD 是 B2 baseline；現有 live-network tests 的實際呼叫面已 grep/讀檔確認。
TESTS_RUN: related pytest `86 passed`; Vitest `8 passed`; Next build exit 0；grep per_rebalance=3；`shasum -c g_new2.sha256` OK；HEAD/current result 與 del(git_head) sha 比對相等；`git diff --check` 僅 docs 5 處 trailing whitespace。
FAILURES_SEEN: B3 receipt full-suite 44 failed/32 errors，含 20 redirect order-dependent errors；本 reviewer 定向重跑未重現。
SCOPE_CHANGES: 核可 `tests/conftest.py` 單檔擴 scope（r7 offline enabler）；review 僅新增本檔。
NUMERIC_OR_SCHEMA_IMPACT: none；G-NEW2 result byte-equivalent，僅 git_head lineage 改變。
OUTPUT: handoffs/IC1C-B3-CODEREV-codex.md
CODE-REVIEW: APPROVE(0 BLOCKING)
