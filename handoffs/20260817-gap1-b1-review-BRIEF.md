# GAP-1 B1 實作 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap1-b1-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–D 之敘述是「請你查證的問句與我的待攻假設」，
> 不是主委的 operational 結論；實際結論在委員產出與收斂檔
> `handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md`（含各家實跑 rc）。
> 檔頭之 `fact-verified:` 三條則附有主委實跑命令。

brief-kind: review

## 審查標的（commit `7093d00f`；`git show 7093d00f --stat` 可看全貌）
- 新模組：`momentum/core/frequency.py`（canonical）、`momentum/Analysis/strategy_validation/`
  （`__init__.py`／`frequency.py`(re-export)／`sharpe.py`／`returns_contract.py`）
- 既有檔改動（白名單內）：`momentum/Strategy/vectorized_backtest.py`、
  `momentum/Optimization/objectives/strategy_backtest.py`
- 測試：`tests/momentum/Analysis/strategy_validation/{test_frequency,test_sharpe,test_returns_contract}.py`
  ＋既有兩檔**只加不改**：`tests/momentum/Strategy/test_vectorized_backtest.py`、
  `tests/momentum/Optimization/test_strategy_backtest_enhanced.py`
- mutation 探針：`scripts/gap1_b1_mutation_probe.sh` ＋ receipt
  `handoffs/run_receipts/20260817T170000Z-gap1-b1-mutation.log`
- 契約來源：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（**FROZEN R3**）Task 1.1–1.4 ＋
  `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md` A1-1..**A1-19**（衝突以延伸檔為準）

## 本輪任務（四段皆必答）
**段 A — 契約符合度（逐 Task）**：Task 1.1／1.2／1.3／1.4 之實作是否**逐條**滿足 TODO 之
「實作要點／不可做／邊界／驗證」？特別查：
- 1.1：未知 timeframe 是否**一律 raise**（禁回 730）；是否**沒有**第二份 timeframe→秒對照表。
- 1.2：退化四情形是否全數 NaN＋status 非 ok（**禁** 0.0）；`skew`／`kurtosis`／`sr_estimator_variance`
  是否**全部** per-period；`value_annualized` 是否**只**用於展示。
- 1.3：`metrics: Dict[str, float]` 型別是否未被污染；`annualization` 是否為平行 metadata；
  早退路徑是否也填；**既有斷言是否一條都沒被放寬或刪除**（請 `git show 7093d00f -- tests/` 逐行看）。
- 1.4：`bar_count` 是否一律非 ok；`default_730`／缺欄是否 fail-closed；`source_artifact_hash` 是否真綁輸入。

**段 B — 🔴 A1-19 兩項實作期決定之複核（本輪重點，我自己下的決定，請攻）**：
1. **canonical 實作搬到 `momentum/core/frequency.py`、原路徑改 re-export**。
   我的理由：`momentum/Strategy/` → `momentum/Analysis/` 命中 canonical Rule 2，
   `check_decoupling_imports.py` fail-closed（實跑 rc=1、2 筆 NEW）；`momentum.core.*` 是 scanner 之
   結構性豁免，且本函式是純常數推導、其輸入 `TIMEFRAME_SECONDS` 本就住 core。
   **請答**：(a) 這是架構上正確，還是「為了過閘而搬」？(b) re-export 會不會造成**兩個 import 路徑**
   之後漂移（TODO 寫 A 路徑、實作在 B 路徑）？若會，修法為何（收斂成單一路徑？在 re-export 加 gate？）
   (c) 有無更好的第三案（我否決過「改 manifest allowlist」——理由是會永久放寬 Strategy→Analysis）。
2. **objective 只在 `timeframe is not None` 時才傳 `timeframe`／`risk_free_rate` 給 engine**。
   我的理由：`IBacktestEngine` 其他實作（含既有測試替身）簽名未含這兩參，無條件傳會使既有路徑
   **18 failed**（實跑）；給了 timeframe 而引擎不支援 ⇒ 仍 `TypeError`（fail-loud），不靜默退回 730。
   **請答**：(a) 這算不算「條件式行為」而使 SPEC 之「傳遞鏈必須明列」打折？
   (b) 是否應改為更新 `IBacktestEngine` Protocol＋測試替身簽名（那會動到既有測試檔，白名單只允許「加斷言」）？
   (c) 有無**可執行反例**使目前寫法在真實路徑上退回隱性 730 而不報錯？

**段 C — 測試品質（可證偽性；本專案禁廉價綠燈）**：
- 五條 mutation（§V-5／8／10／13／15）之 receipt 是否可信？**請自己重跑**
  `bash scripts/gap1_b1_mutation_probe.sh`（約 1 分鐘，會自我還原）並回報你的 rc 與 FAILED 數。
- 探針本身之兩個已修缺陷（`git checkout` 還原不了未追蹤檔；註解插進括號 ⇒ SyntaxError 使 rc=2）
  現行版是否真的擋住？（腳本末段有「還原後無 mutant 殘留且全綠」自檢——請確認它不是空殼。）
- 新測試有無**廉價綠燈**：例如 `test_no_trades_yields_zero_obs_without_crash` 這種只驗不 crash 的、
  或 `pytest.skip` 用在會掩蓋真失敗處（`test_sharpe_ratio_diverges_by_sqrt_ratio_with_zero_rf` 有
  `if default == 0.0: skip`——這是否讓該斷言可能永遠不執行？請實際檢查該 fixture 下 sharpe 是否非零）。
- `test_returns_contract.py` 讀真實 kline；若檔案不存在會 `skip` ⇒ 在無資料機器上整檔靜默跳過。
  這是否構成假綠？修法？

**段 D — 數值正確性（本票命中 (a)(d)）**：
- Mertens 估計量變異數之實作 `(1 - γ3·SR + (γ4-1)/4·SR²)/(T-1)` 是否與 §G 逐字一致（含 `ddof=1`）。
- `resolve_periods_per_year` 用 `round(365*24*3600 / secs)`：`1h`→8760、`4h`→2190、`12h`→730、`1d`→365
  是否皆整除無誤差？有無 timeframe 會因 `round` 產生偏差（請列出 `TIMEFRAME_SECONDS` 全部鍵之計算值）。
- `returns_contract` 之 `trade_level.periods_per_year = n_trades / available_years`：
  `available_years` 用 `n_bars = len(equity_curve)`（我用 `bar_returns.size + 1`）——這個 +1 是否正確？
  equity_curve 長度與 bar 數之關係請自行驗證後回答（**這是我最不確定的一處，請務必查**）。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`（V13）之 §0／§1／§3 與 canonical 四欄格式。
ID＝`## <FAMILY>-R10-P<0-3>-<NN>`，**本輪輪次=R10**。零 findings 用 sentinel `## <FAMILY>-R10-P3-00`（body 須實質）。

## ⚠️ 前置說明
- **禁改碼、禁改 SPEC／TODO／延伸檔、禁 commit／push**；只產你自己的 review 檔。
- 可自由**跑測試**（`venv/bin/python -m pytest …`）與 mutation 探針；跑完請貼 rc。
- 既有紅 2 條（`tests/momentum/Optimization/test_model_hyperparam_enhanced.py`）與本批無關
  （主委以 stash 驗證過），**勿**列為本批 finding。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/momentum/Strategy/test_vectorized_backtest.py tests/momentum/Optimization/test_strategy_backtest_enhanced.py -q` → **111 passed**（Claude 實跑）
fact-verified: `python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → `BASELINE OK`（無新增違反）
fact-verified: mutation 五條全轉紅 rc=1（receipt 見上）
assumed: 既有兩測試檔之斷言只被新增、未被放寬 ← 請逐行 diff 驗
assumed: A1-19 兩項決定為架構上正確而非為過閘取巧 ← 請攻
assumed: `available_years(n_bars=len(equity_curve))` 之 `+1` 換算正確 ← 請攻（主委自承不確定）

## Time-box
優先序＝段 B（A1-19 決定）＞ 段 D（數值）＞ 段 C（測試品質）＞ 段 A（契約符合度）。
**不受理**：使用者裁決、TODO 已 Frozen 之契約本身（要改請走延伸檔提案並說明為何非改不可）、
前端、治理機制、B2–B4 尚未實作之部分。

## 產出
Verdict（可進 B2／需修補後進 B2／有根本缺陷需重作）＋段 A–D 各段結論＋canonical findings。
收尾清 /tmp workdir（保留 claude-501）。
