# GAP-1 TODO（DRAFT）adversarial 審查 R1（含 SPEC R8 三項收回之 delta ＋ §N 殘留逐條攻）

brief-kind: review

## 審查標的
- **TODO DRAFT**：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（15 Task 四批；`template_check todo` PASS）
- **SPEC R8**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（定版；七輪 adversarial 收斂＋使用者白話閘裁決）
- 前一輪收斂：`handoffs/reconcile/20260817-gap1-x-review-r7/synth.md`
- 殘留登記：`docs/IC_QUANT_GAP_REGISTRY.md`「GAP-1 待補完登記」節（G1-R1..R8）

## 本輪任務（三段皆必答；缺一即 PARTIAL）
**A. TODO 完整審查**：照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0–§3 全 11 類＋§2 範本錨點／獵空殼。
重點：SPEC→TODO 抄寫漂移（每 Task 之函式簽名／欄位名／枚舉值／atol／驗證斷言是否與 SPEC 逐字一致）；
Task 間輸入輸出型別是否接得上（如 `LedgerReadResult` 欄位在 2.2／3.1／3.2／4.3 的用法一致）；
「執行端讀完即可寫碼」是否成立（缺偽碼／缺檔名／驗證是空話 ⇒ 空殼）；§B 批次依賴拓撲是否正確。

**B. SPEC R8 三項收回之 delta（🔴 委員從未審過；必逐項給 Verdict）**：
1. **Task 2.4 策略層 wiring 閘門**（SPEC:350；TODO Task 2.4）：W1–W4 規則之封閉集合是否可機械導出？
   `report.py` 字面比對之正則是否會誤判（如 section 名為其他字串子串）？rc 0/1/2 語意是否完備？
   mutation 兩條是否真能證偽？「四份治理白話檔同步」連動是否屬實（查 `scripts/plain_docs_sync_check.sh` 是否存在且會擋）。
2. **Task 3.4 `ml_pipeline` 回應附資格狀態＋警語**（SPEC:476；TODO Task 3.4）：`create_strategy_validation_reporter()`
   工廠是否符合解耦 R3／R1／R7；`for_study_trial` 用 `dataset_key=f"trial:{trial_number}"` 是否與 Task 2.2 之
   `dataset_key` 語意一致（今日必為 `n_unknown`——這是否讓該欄位在可預見期間**恆為降級**而無資訊量？若是，
   請答：這是 SPEC 之明知取捨（[A-裁決-降級]）還是缺陷）；`CreatePipelineResponse` 加 optional 欄位對
   `tests/test_phase6_end_to_end.py`／`tests/test_frontend_integration.py` 之既有斷言是否有破壞風險；
   任何例外吞為 `computation_failed` 是否會**掩蓋**真 bug（與「不弱化 gate」原則之關係）。
3. **Task 4.3 `UniverseProvenance` 欄位逐字**（SPEC:583；TODO Task 4.3）：五欄位（`selection_free`／`source`／
   `candidate_set_hash`／`candidate_count`／`declared_by`）是否與 SPEC 逐字一致；`check_universe_provenance` 三項驗證
   （集合相等／count 三方相等／canonical hash）是否仍可被 top-K 污染繞過（**附可執行反例**才算 BLOCKING）；
   `full_grid` 自洽仍 unverifiable 之裁決是否會使 PBO 在現況下**永遠**無 `ok` 路徑（若是，同上，答取捨或缺陷）。

**C. §N 殘留逐條攻「為何現在不做」（範本 §2 常設必答）**：SPEC §N（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md:660-694`）
共 8 項殘留（接線類 3 ＋ C1 繞過 ＋ API 硬擋 ＋ effective-N ＋ MinBTL 誤差 ＋ cumsum）。逐條檢查：
`為何現在不做:` 是否為 `blocked-by:`／`user-ruling:`／`needs-research:` 三值之一**且理由成立**
（依賴真的存在？裁決真的涵蓋？研究真的無公認方法？其實現在就能做？）；觸發條件是否可判定；
是否登記於 registry「GAP-1 待補完」（G1-R1..R8 對得上 8 項？）。
理由不成立／其實現在能做 ⇒ **MAJOR「殘留應收回為 Task」**附反證。8 項皆成立亦須逐條寫「成立＋一句為何」。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`（V13）。canonical ID `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，
**本輪輪次=R8**（GAP-1 之 R1–R6 已用於 SPEC 輪；本輪 session＝`review-r8`；勿重用）。四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`
（純 hex 緊接 `#`）。零 findings 時用 sentinel `## <FAMILY>-R8-P3-00`（body 須實質，禁空殼）。
段 B 三項與段 C 八項之逐項 Verdict 若無 finding，寫在 Verdict 段下之表格即可（不佔 finding ID）。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC／TODO、禁蓋戳記**；只產你自己的 review 檔（cx_run 指定之 output）。
- `review-r7` 之戳記另輪處理，**勿以「缺戳記」停工**（consult-r1／review-r1／r2／r4／r5／r6 已三家 APPROVED）。
- 「函式/檔案尚不存在」不是缺陷（本 TODO 為新模組 `momentum/Analysis/strategy_validation/`）。
- 實作者＝Claude 主委；你是三家 adversarial 之一，**不得**附和 TODO 框架（§0 相關性警告）。

## 本 brief 前提（逐條標）
fact-verified: `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → `TEMPLATE PASS`（Claude 實跑 2026-08-17）
fact-verified: TODO 引用之既有符號皆存在——`TIMEFRAME_SECONDS`（`momentum/core/constants.py`）、`contract_enum`／`load_report_contract`
（`momentum/Analysis/ic_config_schema.py:524,539`）、`MomentumConfig.results_path`（`momentum/core/config.py:326`）、
`create_ml_pipeline`／`CreatePipelineResponse`（`api/routes/ml_pipeline.py:125,100`）、`PerformanceMetrics(..., periods_per_year=730)`
（`momentum/Strategy/performance_metrics.py:20`）、`objectives/strategy_backtest.py:113` 為 `PerformanceMetrics(result.equity_curve, result.trades).calculate_all()`（Claude grep 2026-08-17）
fact-verified: `handoffs/reconcile/20260817-gap1-x-review-r7/synth.md` body sha256 `ad4c5c535461…`，戳記待補（`reconcile_stamps_check.sh` rc=1）
assumed: TODO 15 Task 對 SPEC 15 Task 之抄寫無語意漂移（追溯表 100% 只證「有對應」，不證「逐字一致」）← 請攻
assumed: R8 三項收回之 TODO 化（2.4／3.4／4.3）不引入新的解耦違規或既有測試破壞 ← 請攻
assumed: §N 8 項殘留之「為何現在不做」全部成立 ← 請逐條攻

## Time-box
優先序＝段 B（delta）＞ 段 C（殘留）＞ 段 A（全審）。**不受理**：使用者裁決本身（範圍 A／降級不硬擋／三值規則）、
前端樣式、治理機制設計、MinBTL 精確值、DSR「同一 V」修法、six 條 C1 生產 bypass 之關閉（已具名殘留）。
對「不受理」項只可作 MINOR 備註，不得作 BLOCKING。

## 產出
Verdict（可派工／需修補後派工／有根本缺陷需重作）＋ 段 B 三項逐項 Verdict 表 ＋ 段 C 八項逐條表 ＋ canonical findings。
收尾清 /tmp workdir（保留 claude-501）。
