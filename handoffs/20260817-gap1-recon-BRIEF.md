# GAP-1 偵察：DSR/PBO/MinBTL 策略層防過擬合（N 帳本＋落點＋契約）

brief-kind: consult

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。
本輪輪次=R1。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md`、`handoffs/GAP1-KICKOFF-SEED.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 `reconcile_stamps_check.sh`。
- 本任務是**偵察（read-only）**，不是 code review 某個 diff。**禁改碼、禁寫測試**；只產你自己的 consult 報告檔。
- 每一條結論都要附**可獨立重現的證據**（file:line、grep 指令與輸出、實跑 receipt）。無證據的斷言請標 `UNVERIFIED`。
- 種子檔 `handoffs/GAP1-KICKOFF-SEED.md` 之「設計要點」是**候選**、非裁決；歡迎逐條推翻。

## 任務背景（為什麼做這件事）
票＝`docs/IC_QUANT_GAP_REGISTRY.md` #1：**DSR（Deflated Sharpe Ratio）／PBO（Probability of Backtest
Overfitting, CSCV 法）／MinBTL（Minimum Backtest Length）** 三件套，Bailey & López de Prado 系列。
現況：因子層已有 FDR／HAC 多重檢定防線（IC 主線 epic 已上線），**策略層裸奔**——
「試了 N 個策略挑最好的那個」這件事在平台上沒有任何檢定擋著。
本偵察產出將餵給 SPEC 起草（Claude），SPEC 再交三家 adversarial。

## 審查標的（今天的碼，不是文件的轉述）
- 策略/回測面：`momentum/Strategy/vectorized_backtest.py`、`momentum/Strategy/performance_metrics.py`（`sharpe_ratio()` at :77）、`momentum/Optimization/`（`optuna_optimizer.py`、`objectives/strategy_backtest.py`、`result_analyzer.py`、`trial_comparison.py`、`checkpoint_manager.py`）
- 既有驗證模組（ML 孤島，是否可複用）：`momentum/Analysis/model_validation/`（`combinatorial_purged_cv.py`、`walk_forward_validator.py`、`cv_validator.py`、`oot_validator.py`）
- 報酬序列產出面：`momentum/Analysis/prediction_analyzer.py`（`np.cumsum` at :154-155）、`momentum/Analysis/factor_return_analyzer.py`（`sharpe_ratio` at :263）、`momentum/Analysis/long_short_analyzer.py`、`momentum/Analysis/expectancy_calculator.py`
- 契約/報告面：`momentum/Analysis/contracts/ic_report_contract.json` ＋ `validate_report_against_contract`；`scripts/ic_wiring_check.sh`
- API/服務面：`api/routes/optimization.py`（`n_trials` 欄位 at :48-49、:130）、`api/services/xgboost_task_service.py`、`api/services/xgboost_batch_service.py`、`api/services/optimization_task_service.py`、`api/services/optimization_output_service.py`
- 測試紀律：`docs/TEST_DESIGN_CHARTER.md`、`tests/momentum/helpers/ichc_run.py`

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: repo 目前**沒有任何** DSR/PBO/CSCV/MinBTL 實作 → `grep -rn "deflated\|DSR\|PBO\|CSCV\|MinBTL\|min_btl" --include="*.py" momentum api` 零命中（2026-08-17 實跑）
fact-verified: `momentum/Analysis/model_validation/combinatorial_purged_cv.py` 存在但屬 ML 孤島，未接 IC/策略選擇流程 → `docs/IC_QUANT_GAP_REGISTRY.md`「IC 主路徑切分現狀」節明載
fact-verified: `api/routes/optimization.py:48` 有 `n_trials`（1–10000）欄位；Optuna 為現行超參搜尋器 → 該檔實讀
fact-verified: `momentum/Analysis/prediction_analyzer.py:154-155` 用 `np.cumsum(strategy_returns)`（單利累加，非複利 `cumprod`）產權益曲線 → 該檔實讀
assumed: 「嘗試次數 N」在平台上目前**沒有任何機器化的統一帳本**，只有零散的 Optuna trial 數與批次任務筆數 ← 請直接攻這條，逐個計數面查證
assumed: 三件套只吃「報酬序列 ＋ N」，不需碰特徵層，因此可做成獨立的 `momentum/Analysis/` 新模組而不改回測引擎 ← 可能錯（若報酬序列來源不統一或不可信），請驗證
assumed: `ic_report_contract.json` 可經擴 `report_sections` 承載三關結果（沿用 ICHC capability status 契約），不需新契約檔 ← 請驗證是否語意錯位（IC 報告 vs 策略報告是兩個產物）
assumed: MinBTL→PBO→DSR 的三關順序（資格→選法→冠軍）是正確的產品順序 ← 若你認為某關該獨立或順序有誤，請提出

## 必答（逐條 verdict，附證據）
1. **N 帳本盤點（本票最難點）**：列出平台上**所有**可能構成「嘗試次數」的計數面（Optuna trials、XGBoost 批次、strategy/優化 checkpoint、IC 因子篩選次數、前端重複送單…），逐個標：位置（file:line）／是否已持久化／能否機器讀／能否被繞過（漏記路徑）。給出**可 fail-closed 的 N SoT 設計建議**（含「N 不可知」時的誠實態度：拒答還是標 unknown？）。
2. **報酬序列輸入契約**：策略層報酬序列究竟由誰產、什麼頻率、單位（比例/百分點/對數）、是否已扣成本/滑價、NaN/空態語意？多個產出點（`vectorized_backtest` vs `prediction_analyzer` vs `factor_return_analyzer`）是否語意不一致？`prediction_analyzer.py:154` 的 `np.cumsum` 是否構成本票**前置修復**（若是，是 BLOCKING 還是可並行）？
3. **落點與複用**：三關應落在哪（新模組路徑建議）？`model_validation/combinatorial_purged_cv.py` 能否直接供 PBO 的 CSCV 分割複用，或必須另寫（附為什麼——purging/embargo 語意是否與 CSCV 的 S 塊組合相容）？現有 `performance_metrics.sharpe_ratio()`（:77，`periods_per_year` 預設 730）能否作 DSR 的觀測夏普輸入，年化慣例是否與 DSR 公式假設相容？
4. **產出契約與可見性**：三關結果進哪個產物、schema 怎麼標 status（`available`/`unavailable`/`degraded`）？需不需要前端 wiring（`ic_wiring_check.sh` 是否會自動盯到）？「不合格」（MinBTL 未達）在 UI 上必須怎麼**擋住而非只是標註**？
5. **測試策略（禁自造 golden）**：DSR/PBO/MinBTL 公式可用哪些**第三方對照**驗（López de Prado 公開實作、論文解析案例、已知數值）？逐條給出可驗的具體案例與期望值來源。另列本票該有的統計檢定清單（對照 `docs/TEST_DESIGN_CHARTER.md`），並指出哪些測試「改壞會 FAIL」（mutation 可證偽）。
6. **scope 建議**：三件套是否應一次做完？若須分期，切法與理由（哪一關單獨上線就有真實防護價值、哪一關沒有 N 帳本就沒意義）。
7. 偵察結果是否足以進 SPEC 起草？有無 **BLOCKING**（例如報酬序列不可信、N 根本無法誠實記帳而使 DSR 變裝飾品）？

## Time-box 與範圍紀律
- 優先序＝必答 1（N 帳本）＞ 2（輸入契約）＞ 3（落點/複用）＞ 其餘。查不完的具名列「未查」清單，**不當阻塞**。
- **不受理範圍**：治理機制與流程（本票是量化實作）、前端樣式細節、IC 效能優化（另有 epic）、registry #2–#6 其他票的內容。
- 提醒：本票**不是**「把 ML 孤島接上 IC 主線」（那是 registry #2）；勿把 walk-forward/CPCV 接線需求塞進本票，除非你能證明 DSR/PBO 缺它就不成立。

## 產出
canonical 四欄 findings + 必答 1–7 的逐條 verdict + **Verdict**（可進 SPEC／BLOCKING 清單／scope 建議）。**禁改碼**（只產 consult 檔）。收尾清 /tmp workdir（保留 claude-501）。
