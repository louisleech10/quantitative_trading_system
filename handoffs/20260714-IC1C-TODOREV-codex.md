# IC1C-TODOREV Codex adversarial review
## Verdict：有根本缺陷需修補；目前不可派工
VERIFY: `sed -n '1,151p' docs/IC1C_NETIC_SPEC.md`; `sed -n '1,122p' docs/IC1C_NETIC_TODO.md`; `rg -n '"net_ic"|net_ic_analysis' momentum/Analysis/ic_reporter.py tests/momentum/test_export_formats.py`。摘要：Frozen SPEC/TODO 全文已讀；現行 reporter 仍輸出/alias `net_ic`，export fixture 仍固化舊 schema。
## Findings（挑戰前提優先）
ADV-CODEX-1 [BLOCKING][High] 證據：SPEC §T 公式僅為 `(bps/10000)×turnover`，§U 只裁非有限 turnover→SKIPPED；TODO Task 1.1 卻新增 `max(0.0,turnover)`，Task 1.3 又要求負 turnover clamp。反例：上游污染產生 turnover=-0.2 時被靜默改成 0，成本拖累看似合法且資料錯誤消失。RECHECK：搜尋 `max(0.0,turnover)|負 turnover clamp`。修法：不得自行發明；先由 Frozen SPEC 裁定負值應 reject 或 SKIPPED，再加具名測試/probe。
ADV-CODEX-2 [BLOCKING][High] 證據：SPEC §C 自稱「完整 consumer manifest」，明列 `ic_reporter.py`、service NaN 轉換、route、export tests；TODO Tasks/修改檔案未處理 reporter/export，卻在末尾聲稱 7/7 覆蓋。實跑 rg 顯示 reporter:150/209/631-634 與 `test_export_formats.py:73-74` 仍有 `net_ic`。反例：engine 全樹無舊鍵但 CSV export 仍公開 `net_ic` alias，M1 的 analyzer-only oracle仍綠。RECHECK：上述 rg。修法：逐 consumer 建 Task、red-on-break 測試與 gate；未需改者逐項寫明證據。
ADV-CODEX-3 [BLOCKING][High] 證據：SPEC §U 指定常數位置 `test_net_ic_schema_profiles.py::SCHEMA_*`；TODO Phase 1 改放 `test_net_ic_analyzer.py`，且追溯仍稱 §U 已覆蓋。反例：下游/驗收按 Frozen 路徑 import oracle 時檔案不存在。RECHECK：`rg -n 'test_net_ic_schema_profiles|test_schema_profiles' docs/IC1C_NETIC_*`。修法：依 SPEC 建 dedicated schema-profile test，或先正式修訂 Frozen SPEC。
ADV-CODEX-4 [BLOCKING][High] 證據：TODO B1 的 Task 1.2 驗收是 T2 `test_net_ic_e2e_unavailable`，但 B1 Gate 只明跑 T1+T3；`mutation_probe_check.sh` 只選 `-k test_mutation_`，不會執行該 E2E。反例：`_run_net_ic` 繼續傳錯資料，T1/T3與 mutation probes 全綠，B1仍可放行。RECHECK：比對 TODO 64、80 行及腳本的 pytest selector。修法：B1 gate 明跑 T2 的具名 E2E並證離線可 collect。
ADV-CODEX-5 [BLOCKING][High] 證據：TODO Task 2.2 同時要求 input `min=0.1, step=0.1`，驗收卻用 `grep -n "useState(5)\|0.1" NetICChart.tsx` 要求零命中。反例：完全正確的 min/step 實作必被 gate 判紅。RECHECK：`rg -n '0\.1|grep -n' docs/IC1C_NETIC_TODO.md`。修法：以 AST/RTL 測試鎖定「缺 turnover 不得代入數值」，靜態檢查只匹配舊 fallback 表達式。
ADV-CODEX-6 [BLOCKING][High] 證據：SPEC §U/M10 宣告 `cost_bps` 三層合法域；TODO Task 1.1/2.1 的 validator 都只在 `cost_enabled=True` 時驗值。反例：`cost_enabled=False,cost_bps=NaN` 可穿過 config/API/analyzer，與「合法域=有限」及 M10 三層聲明不一致。RECHECK：以三個 model/constructor 各測 `{False, NaN}`。修法：非 None 時一律驗域；enabled 時另驗不得 None，M10 每層覆蓋 enabled true/false。
ADV-CODEX-7 [BLOCKING][High] 證據：G-NEW 僅寫 `script --new` 後列口頭比對，G-NEW2 在 B2/B3 Gate 只有名稱，無產出路徑、獨立 verifier、可執行命令或 failure oracle。反例：腳本直接複製 G-NEW 為 G-NEW2、完全不走 API，文件仍可聲稱「API 傳導等值」。RECHECK：`rg -n 'G-NEW2|--new' docs/IC1C_NETIC_TODO.md`。修法：列 artifact/meta/hash、API 入參7bps→engine artifact、feature byte diff 的獨立命令與預期 stdout/exit；gate 實跑該命令。
ADV-CODEX-8 [BLOCKING][High] 證據：TODO §0 規定驗證一律真-kline、禁新合成 fixture；Task 0.1 卻「人工構造 turnover 缺/gross_ic NaN」，且 G-OLD oracle只是由同一腳本同時寫 JSON+checksum。反例：人工樣本或空/錯 JSON 連同新 checksum 一起生成，`shasum -c` 與兩次決定性都綠。RECHECK：TODO 16、35、40 行。修法：skipped case 必由真資料衍生且標 lineage；另建獨立內容 validator（樣本來源、row/key counts、必含路徑、fixture/git hash），禁止 producer 自證正確。
ADV-CODEX-9 [MAJOR][High] 證據：Task 2.2 邊界承諾 empty/loading/error、API 422表單錯誤、全 SKIPPED 空態，但 T4 只具名 wiring/probe，無各狀態可見 UI oracle；Task 3.1 只 grep `per_rebalance`，註解/隱藏字串亦通過。反例：元件永遠 spinner或文字只在註解，build/grep仍綠。RECHECK：TODO 100-116 行。修法：RTL 逐態 render/assert visible text，422互動測試，tooltip可見性測試。
## 被當成事實的未驗證假設
TODO 假設負 turnover 可安全歸零、producer checksum 可證 baseline 真實性、以及「同名 Task=100% SPEC 覆蓋」；前三者已由 ADV-CODEX-1/8/2 反例推翻。現行 `net_ic_proxy` caller 僅測試則經 `rg` 初核成立，但執行前仍須全 repo（含動態 getattr/export）複驗。
## 十類檢查摘要
矛盾/互斥：1,3,5,6,8；漏項/端到端：2,7,9；不可測驗收：4,7-9；quant：1,6；過度工程：無；OOM/並行：本 scope 無新增；cache：N/A；API/型別/相容：2,6,9；測試品質：2-9；Agent 可執行性：2,4,5,7-9。§RISK/§A/§C/§G/§P/§V/§R/§N 皆有實質文字，但 TODO 的 G-NEW2 與部分 UI gate 為邏輯空殼。
ASSUMPTIONS_VERIFIED: Frozen/reconcile 標記存在；SPEC/TODO 全文及相關現行 caller/export/mutation selector已實讀實查。
TESTS_RUN: read-only review；未跑產品測試。上述 VERIFY/RECHECK 為靜態可重跑命令。
FAILURES_SEEN: none（審查 finding 非測試失敗）。
SCOPE_CHANGES: none；只新增本 handoff。
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）。
TODO-REVIEW: REJECT(8 BLOCKING)
