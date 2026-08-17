# GAP-1 B1 code review — Codex R10
task-id: 20260817-GAP1-B1-REVIEW-R10; family: CODEX; commit: 7093d00f

## Verdict：需修補後進 B2

## CODEX-R10-P1-01
**斷言**: 缺少真實 kline 時，`test_returns_contract.py` 會把核心資料正確性測試靜默變成綠色 skip，故「111 passed」不是可攜的 B1 gate。
**碼證**: `tests/momentum/Analysis/strategy_validation/test_returns_contract.py:39-41` 以 `pytest.importorskip`／`pytest.skip` 放過缺檔；本機 focused pytest → `111 passed`，但無資料分支不會失敗。RECHECK: 在沒有 `data_cache/feature_klines/kline_cache.h5` 的驗證環境跑同一 pytest 並加 `-rs`，目前會出現 skip 而 rc=0。
**來源摘要**: tests/momentum/Analysis/strategy_validation/test_returns_contract.py#e656f2c3a2a4
[MAJOR] 信心度=10/10；真實資料測試的缺席不能被當成通過。修法：資料是本票必要前置時用 `pytest.fail`／明確 preflight fail-closed；若另設可選整合測試，B1 gate 必須明確要求資料存在且 skip 不得算通過。

## CODEX-R10-P1-02
**斷言**: mutation probe 沒有檢查 baseline 與 post-restore pytest rc，故既有紅或還原後紅都可能被誤報為全部 mutation 通過。
**碼證**: `scripts/gap1_b1_mutation_probe.sh:74-76`、`:103-107` 只 `echo "$?"`，沒有非零分支；本輪實跑五條皆 rc=1、post-restore rc=0，但這只證明本次結果，未證明腳本 fail-closed。RECHECK: 將 baseline 或還原後 pytest 置為非零再執行 probe，預期腳本應非零；現行腳本沒有該 gate。
**來源摘要**: scripts/gap1_b1_mutation_probe.sh#99c8e1c2d94e
[MAJOR] 信心度=10/10；腳本的兩個已修缺陷（backup 還原未追蹤檔、SyntaxError mutant）確實已擋住，但末段「全綠」自檢仍是空殼。修法：捕獲 baseline/post-restore rc，任一非 0 立即退出；保留現有 rc=1 且 `FAILED>=1` 判準。

## CODEX-R10-P1-03
**斷言**: `StrategyBacktestObjective` 在 timeframe 已指定、注入 engine 接受新 kwargs 但回傳缺 `annualization` 時，會無錯誤把 objective Sharpe 算回 730。
**碼證**: `momentum/Optimization/objectives/strategy_backtest.py:130-135` 使用 `annualization.get("periods_per_year", 730)`；可執行 injection probe 輸出 `returned=6.583962285857072`, `expected_730=6.583962285857072`, `expected_8760=22.807514388443547`, `silent_730=True`。RECHECK: 以同一 probe 或測試一個接受 `**kwargs`、回傳無 annualization 的 engine，`timeframe="1h"` 應現行無例外且回 730。
**來源摘要**: momentum/Optimization/objectives/strategy_backtest.py#e2d35ca3506b
[MAJOR] 信心度=10/10；A1-19 的「不支援 kwargs 就 TypeError」只覆蓋一類 engine，未封住 kwargs 相容但 metadata 缺失的數值錯誤。修法：`self.timeframe is not None` 時要求 annualization 存在、source=`resolved` 且 periods_per_year 合法，否則 fail-loud；timeframe=None 的 legacy 730 fallback 可保留並明確標示。

## CODEX-R10-P2-04
**斷言**: `IBacktestEngine` Protocol 仍只宣告四個舊參數，未宣告 objective 在 timeframe 路徑傳入的 `timeframe`／`risk_free_rate`，介面契約與實作行為已漂移。
**碼證**: `momentum/core/protocols.py:132-138` 的 `run_backtest` 沒有兩個 optional kwargs；`strategy_backtest.py:115-125` 卻動態傳入。既有 `StubBacktestEngine`／`DummyBacktestEngine` 也仍是舊簽名，現行相容行為靠條件分支而非 Protocol。RECHECK: 用靜態型別檢查或逐一檢查 `IBacktestEngine` 實作簽名，會看見新 engine contract 未被宣告。
**來源摘要**: momentum/core/protocols.py#f39ba5fbe938
[MINOR] 信心度=9/10；目前 production `VectorizedBacktest` 路徑可運作，故不把它誤列為當前 runtime failure。修法：後續允許擴大 scope 時更新 Protocol 與所有實作／test doubles；B1 因 brief 白名單只允許既有測試加斷言，不在本輪越界修改。

## CODEX-R10-P3-05
**斷言**: A1-19 已成為實作依據，但 TODO 與新 package docstring 仍只列 A1-18／A1-15，追溯文字不一致。
**碼證**: `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md:311-337` 新增 A1-19；但 `docs/GAP1_STRATEGY_OVERFIT_TODO.md:5,42,520,525` 與 `momentum/Analysis/strategy_validation/__init__.py:4` 仍寫舊範圍。RECHECK: `rg -n 'A1-1\.\.A1-(15|18)|A1-19'` 可重現混用。
**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#961bb34c1515
[MINOR] 信心度=10/10；不影響本次 runtime，但會讓後續執行端漏讀 canonical 落點修訂。修法：下一個允許的文件同步變更統一標為 A1-19。

## 段 A — 契約符合度（逐 Task）
Task 1.1：符合。`momentum/core/frequency.py:18,39-41` 只讀 `TIMEFRAME_SECONDS`，未知直接 `UnknownTimeframeError`；re-export identity 實跑為 `same_object True`，沒有第二張 timeframe→秒表。Task 1.2：符合，`n<2`／非有限／`std(ddof=1)==0` 全回 NaN＋非 ok；skew、kurtosis、Mertens variance 都以 per-period 值計算，formula 與 §G 一致。Task 1.3：annualization 是平行 metadata、早退有填、既有測試 diff deletion lines=0；但見 P1-03 與 P2-04。Task 1.4：bar_count 非 ok、default_730／缺欄 fail-closed、hash 綁 equity/trade fields；標準 engine 的 `+1` 年數換算見段 D。

## 段 B — A1-19 決定複核
canonical 搬到 `momentum/core` 是架構上正確的 lower-level pure primitive，不是單純為過閘：輸入常數本來在 core，且 decoupling baseline 實跑 `BASELINE OK`；re-export 目前不漂移。沒有更好的第三案需要採用，永久放寬 Strategy→Analysis allowlist 反而較差。條件式 kwargs 不打折指定 timeframe 的傳遞鏈，因為該分支實跑且五條 mutation 通過；但 Protocol 應後續補齊（P2-04），且 kwargs-compatible 缺 metadata 的可執行反例使「不會隱性 730」不成立（P1-03）。

## 段 C — 測試品質與可證偽性
`bash scripts/gap1_b1_mutation_probe.sh` 實跑 rc=0：baseline 72 passed；§V-8/15/5/10/13 分別轉紅 rc=1，FAILED=8/5/7/1/1；post-restore 72 passed，且無 mutant 殘留。兩個 brief 指定的舊缺陷已修好，但 probe rc gate 仍缺（P1-02）。既有兩測試檔只新增、未刪斷言；`test_sharpe_ratio_diverges...` fixture 實際 default Sharpe=`1.577786126886036`、hourly=`5.465611470487859`，skip 分支本輪未遮蔽斷言。`test_returns_contract.py` 的缺資料 skip 是實質假綠（P1-01）；no-trades 測試除不 crash 外仍驗 n_obs/status/finite ppy，未單獨列 finding。

## 段 D — 數值正確性
`sharpe.py:88` 使用 `std(ddof=1)`，`:96` 為 `(1-skew*sr_pp+(kurtosis-1)/4*sr_pp**2)/(n_obs-1)`；focused suite 與 §V-10 numeric mutation 均通過。`TIMEFRAME_SECONDS` 全鍵計算：`1m=525600`、`5m=105120`、`15m=35040`、`1h=8760`、`4h=2190`、`12h=730`、`1d=365`，皆整除無 round 偏差。真實 kline 回測驗證 `equity_len=1500`、`bar_returns_size=1499`、`bar_size_plus_one=1500`、`relation_holds=True`；因此本票正常 engine 路徑的 `+1` 正確，未列 finding。

## 被當成事實的未驗證假設（§0）
- `fact-verified`: focused suite `111 passed`、decoupling rc=0、五條 mutation rc=0；上述輸出均由本輪實跑取得。
- `assumption disproved`: A1-19 所稱 fail-loud 覆蓋所有不支援 engine 不成立；kwargs-compatible／缺 annualization 反例見 P1-03。
- `bounded assumption`: `bar_returns.size+1 == len(equity_curve)` 已在真實 engine 驗證，但只對該 engine 的有限、首值有效 invariant 成立；本輪沒有把任意 malformed equity 宣稱已驗證。

ASSUMPTIONS_VERIFIED: commit 7093d00f、TODO FROZEN R3、A1-19、白名單 diff、111-test suite、decoupling、五條 mutation、real-kline 1500-bar +1 關係均已核對。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/momentum/Strategy/test_vectorized_backtest.py tests/momentum/Optimization/test_strategy_backtest_enhanced.py -q` → 111 passed；`bash scripts/gap1_b1_mutation_probe.sh` → rc=0；`python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → rc=0；rounding/import/hash/real-kline probes 如上；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-b1-review-codex.md --family codex` → rc=0，`COMPLETENESS PASS(single)`、5 個 canonical ID、格式合規。
FAILURES_SEEN: none in accepted baseline or mutation run; one exploratory one-line probe had a syntax error before rerun, no repository change；completeness checker earlier曾被 PreToolUse gate 暫時擋下，寫檔後重跑已 rc=0。
SCOPE_CHANGES: none; only `handoffs/20260817-gap1-b1-review-codex.md` is produced; code/SPEC/TODO/commit/push untouched; existing unrelated dirty files preserved.
NUMERIC_OR_SCHEMA_IMPACT: no implementation or output schema change; review identifies a hidden-730 numeric path and stale Protocol/documentation metadata.
HANDOFF_OUTPUT: handoffs/20260817-gap1-b1-review-codex.md
COMPLETENESS_CHECK: rc=0; `COMPLETENESS PASS(single)`，5 個 canonical ID，格式合規。
STATUS: DONE
