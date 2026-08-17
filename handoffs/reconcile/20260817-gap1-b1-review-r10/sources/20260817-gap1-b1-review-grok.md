# GAP-1 B1 實作 code review / grok | task-id=20260817-GAP1-B1-REVIEW-R10

brief-kind=review；家族=GROK；輪次=R10；審查標的 commit `7093d00f`；禁改碼／禁 commit。

## Verdict：需修補後進 B2

Task 1.1–1.4 契約本體（頻率解析、typed Sharpe、annualization metadata、returns_contract 三語意）在
**VectorizedBacktest 真實路徑**上成立；mutation 五條本輪重跑全轉紅；111 pytest 全綠；既有測試斷言
**只加不改**。A1-19 之 **core 落點**為架構正確而非純過閘。

但 A1-19 第二項（objective 條件傳參）所主張的「給了 timeframe **不**靜默退回隱性 730」被
**可執行反例**推翻：`evaluate` 在 recompute metrics 時仍 `annualization.get("periods_per_year", 730)`，
引擎若接受 `**kwargs` 卻不寫 `annualization`，objective 會在已指定 `timeframe="1h"` 下靜默用 730。
此為 **MAJOR**，修補面積極小（fail-closed 當 `self.timeframe is not None`），建議 B2 開工前先補。

非根本缺陷、不需重作 B1。

---

## 段 A — 契約符合度（Task 1.1–1.4）

### Task 1.1 — **符合**
- `resolve_periods_per_year`：未知／`None`／`""`／`"1H"` 皆 raise `UnknownTimeframeError`；**無**第二份
  timeframe→秒表（唯一讀 `TIMEFRAME_SECONDS`）；無 default 參數。canonical 在 `momentum/core/frequency.py`，
  `strategy_validation/frequency.py` 為 re-export（A1-19，見段 B）。
- `available_years`：`n_bars / resolve_periods_per_year`；`n_bars<0`／非 int raise；`n_bars=0→0.0`。
- 測試參數化 `1h/4h/12h/1d` 與 §V 反向三年等值 `2.3232876712328765` 齊全。

### Task 1.2 — **符合**
- 退化四＋擴展（空／單點／NaN／inf／std=0／全零／常數）→ 數值欄 NaN、`status!="ok"`、
  `reason=="degenerate_returns"`；**禁** 0.0 相容模式（§V-5 本輪轉紅）。
- `skew`／`kurtosis(fisher=False)`／`sr_estimator_variance` 皆 per-period；`value_annualized` 僅
  `sr_pp*sqrt(periods)` 展示；moments 與 `periods_per_year` 無關（單位鎖定測試）。
- status 取 `contract_enum("capability_status")`，未複列枚舉。

### Task 1.3 — **符合（附段 B 之 MAJOR 缺口）**
- `run_backtest(..., timeframe=None, risk_free_rate=0.02)`；`BacktestResult.annualization` 平行 metadata；
  `metrics: Dict[str, float]` **未**被污染（型別與欄位分離）。
- 未知 timeframe → `source=default_730`（可機器判讀）；早退路徑亦填 annualization。
- 既有兩測試檔 diff：`git show 7093d00f --unified=0 -- tests/...vectorized... tests/...enhanced...`
  → **零非 context 刪行**（只加斷言）。fact 升級：brief assumed「未放寬」→ **本輪 verified**。
- objective 條件傳參見段 B；生產引擎路徑（`VectorizedBacktest`）傳遞鏈與數值分叉測試通過。

### Task 1.4 — **符合**
- `bar_count` → `status=not_applicable`、`reason=t_semantics_inflates_significance`（值仍回傳）。
- `default_730`／缺 `annualization` → `annualization_unresolved`、status 非 ok。
- `source_artifact_hash`：sha256(equity bytes + trade triples)；同結果跨語意相同、不同 backtest 不同。
- `trade_level.periods_per_year = n_trades / available_years(...)`；呼叫 Task 1.1 之 `available_years`。

---

## 段 B — A1-19 兩項實作期決定（本輪重點）

### B1. canonical → `momentum/core/frequency.py` + re-export

| 子問 | 結論 |
|---|---|
| (a) 架構正確 vs 過閘搬遷 | **架構正確**。函式是純常數推導；唯一輸入 `TIMEFRAME_SECONDS` 本就住 core；scanner 對 `momentum.core.*` 結構性豁免。Strategy→Analysis 直 import 命中 R2 是 TODO §0 未預見 R2 intra-momentum 的真實衝突，不是假問題。改 manifest allowlist 永久放寬 Strategy→Analysis **更差**。 |
| (b) 雙路徑漂移 | **有風險、目前低**。本輪 VERIFY：`core.resolve is reexport.resolve`（同一 function object）。Strategy 直 import core；測試／TODO 字面走 Analysis re-export。漂移會在有人「在 re-export 檔加邏輯」或「複製一份實作」時發生。 |
| (c) 第三案 | 維持 core canonical + 薄 re-export 為正解。可選強化：加 identity 測試（`is` 同一物件）作 gate；**不**建議改 Protocol 包一層純函式。 |

### B2. objective 只在 `timeframe is not None` 時傳 kwargs

| 子問 | 結論 |
|---|---|
| (a) 是否打折「傳遞鏈必須明列」 | **對 VectorizedBacktest 生產路徑不打折**（有 `test_objective_forwards_timeframe` + sharpe 同值 atol=1e-12）。條件傳參是對 `IBacktestEngine` 既有四參簽名的相容策略；A1-19 已文件化。 |
| (b) 是否應改 Protocol＋替身 | **長期應改**（簽名含 optional `timeframe`/`risk_free_rate`），但 B1 白名單只允許既有測試「加斷言」、改 Protocol 會牽動多替身——本批暫緩合理。 |
| (c) 可執行反例 → 靜默 730 | **有**。見 `GROK-R10-P1-01`：引擎 `**kwargs` 吞掉 timeframe、回傳無／空 `annualization` 時，objective 仍 `get(..., 730)`。A1-19 所稱「不支援 ⇒ TypeError」**只**覆蓋「簽名拒收 kwargs」；**不**覆蓋「接受後忽略」。 |

---

## 段 C — 測試品質

### Mutation 探針（本輪重跑）
```
VERIFY: bash scripts/gap1_b1_mutation_probe.sh
  baseline rc=0（72 passed）
  §V-8  rc=1 FAILED=8
  §V-15 rc=1 FAILED=5
  §V-5  rc=1 FAILED=7
  §V-10 rc=1 FAILED=1
  §V-13 rc=1 FAILED=1
  post-restore rc=0（72 passed；源碼無 return 730 / nan=0.0 / kurtosis/4 mutant 殘留）
  探針整體 rc=0
```
Receipt 可信：每條要求 `rc==1 且 FAILED>=1`（擋 rc=2 collection/SyntaxError）；備份用 `cp` 非 `git checkout`（修了未追蹤檔還原失敗）。

`grep MUTANT` 自檢字面偏空（mutant 從不插入該字串）；**實質閘**是 restore + 全綠 pytest，非空殼。

### 廉價綠燈檢查
- `test_sharpe_ratio_diverges_by_sqrt_ratio_with_zero_rf` 之 `if default==0.0: skip`：本輪用同 seed fixture 實跑
  `default sharpe ≈ -1.432`、`ratio ≈ 3.464101615137755 == sqrt(8760/730)` → **skip 未觸發**，斷言會執行。
- `test_no_trades_yields_zero_obs_without_crash`：不止不 crash，還斷言 `n_obs==0`、`status=="ok"`、`isfinite(ppy)`——邊界可接受（DSR 退化在 B3）。
- `test_returns_contract.py` 無 kline → `pytest.skip`：本機有檔且全跑；**無資料機器整檔靜默 skip** 有假綠殘留風險（見 P2）。本專案要求真實 kline 且本輪 111 passed 含該檔。

### 既有斷言
只加不改（見段 A）；與 brief assumed 一致並已升級 fact。

### B1 Gate pytest
```
VERIFY: venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ \
  tests/momentum/Strategy/test_vectorized_backtest.py \
  tests/momentum/Optimization/test_strategy_backtest_enhanced.py -q
→ 111 passed, rc=0
```

```
VERIFY: python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt
→ BASELINE OK（無新增違反）, rc=0
```

---

## 段 D — 數值正確性

### Mertens
實作：`(1.0 - skew * sr_pp + (kurtosis - 1.0) / 4.0 * sr_pp**2) / (n_obs - 1)`，`std(ddof=1)`。
與 TODO／§G 逐字一致。手算案例與 `test_mertens_estimator_variance_hand_formula` 一致（含錯誤形式 `γ4/4` 可證偽）。

### `round(365*24*3600 / secs)` — 全表
| tf | secs | exact | round | err |
|---|---:|---:|---:|---:|
| 1m | 60 | 525600 | 525600 | 0 |
| 5m | 300 | 105120 | 105120 | 0 |
| 15m | 900 | 35040 | 35040 | 0 |
| 1h | 3600 | 8760 | 8760 | 0 |
| 4h | 14400 | 2190 | 2190 | 0 |
| 12h | 43200 | 730 | 730 | 0 |
| 1d | 86400 | 365 | 365 | 0 |

`TIMEFRAME_SECONDS` **全部鍵**皆整除，`round` 無偏差。

### `available_years` 之 `bar_returns.size + 1`（主委不確定處）
**生產路徑正確。**

證據：
- `_calculate_equity_curve`：`equity = np.ones(len(prices))` → `len(equity_curve) == n_bars(prices)`。
- `_bar_returns`：`equity.pct_change().dropna()` → 長度 `n_bars - 1`（全 finite 時）。
- 故 `bar_returns.size + 1 == len(equity_curve)`。
- 真實 kline 1500 bars 實跑：equity=1500、bar_ret=1499、+1=1500；
  `trade_level.periods_per_year` 與 `n_trades/(len(equity)/8760)` 一致。

TODO 字面寫 `n_bars=<equity 長度>`；實作等價於該定義。空 equity 手造物件會變成 `0+1=1`（非生產路徑）；可改 `len(equity_curve)` 更貼字面，非正確性缺陷。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 本輪 |
|---|---|---|
| 111 passed（brief fact） | **fact 成立** | 重跑 111 passed rc=0 |
| BASELINE OK（brief fact） | **fact 成立** | 重跑 BASELINE OK |
| mutation 五條全紅（brief fact） | **fact 成立** | 重跑五條 rc=1 FAILED≥1；探針 rc=0 |
| 既有斷言未放寬（brief assumed） | **→ fact** | unified=0 diff 零刪除斷言行 |
| A1-19 core 落點架構正確（brief assumed） | **→ 成立** | 見段 B1 |
| A1-19「不靜默 730」（brief assumed） | **→ 推翻（有條件）** | 見 P1-01；僅 TypeError 路徑成立 |
| `+1` 年數換算正確（brief assumed） | **→ 成立（生產路徑）** | 見段 D |

---

## GROK-R10-P1-01

**斷言**: `StrategyBacktestObjective.evaluate` 在呼叫方已指定 `timeframe` 時，仍可能以 `annualization.get("periods_per_year", 730)` 靜默使用 730，只要引擎接受並忽略 kwargs 且不回填 `annualization`；A1-19「不靜默退回隱性 730」不成立。

**碼證**: `strategy_backtest.py:116-136` 條件傳 kwargs 後仍 `periods_per_year=int(annualization.get("periods_per_year", 730))`；A1-19 稱「不支援⇒TypeError、不靜默 730」；`IBacktestEngine` 僅四參。本輪 SwallowEngine（`**kwargs` 吞 timeframe、回 `annualization={}`）⇒ silent ppy=730。生產 VectorizedBacktest 主路徑仍正確。RECHECK: 建 SwallowEngine 後 `StrategyBacktestObjective(..., timeframe="1h")` 讀 recompute ppy。

**來源摘要**: momentum/Optimization/objectives/strategy_backtest.py#e2d35ca3506b

[MAJOR] 信心度=High。會怎麼失敗：優化目標在「已宣告 1h」下仍按 730 年化，冠軍排序／與 engine 直呼分叉被掩蓋。
修法（建議最小）：當 `self.timeframe is not None` 時，要求 `result.annualization` 為 dict 且 `source=="resolved"` 且含 `periods_per_year`，否則 raise；**禁止**在此分支 default 730。可加測試：SwallowEngine ⇒ 必須 raise。不阻擋 Task 1.1/1.2/1.4 契約本身；建議 B2 前小補丁。

---

## GROK-R10-P2-01

**斷言**: Task 1.1 存在兩個 import 路徑（`momentum.core.frequency` vs `momentum.Analysis.strategy_validation.frequency` re-export），目前同物件但無機械防漂移閘，後續若在 re-export 檔加邏輯會靜默分叉。

**碼證**: Strategy／returns_contract 直 import core；測試／TODO 字面走 Analysis re-export。VERIFY `core.resolve_periods_per_year is reexport.resolve_periods_per_year` → True（三名稱皆 is）；無測試鎖定 identity。RECHECK: `python -c "from momentum.core import frequency as c; from momentum.Analysis.strategy_validation import frequency as r; assert c.resolve_periods_per_year is r.resolve_periods_per_year"`。

**來源摘要**: momentum/Analysis/strategy_validation/frequency.py#e7bf1c0207ad

[MINOR] 信心度=High。修法：在 `test_frequency.py` 加 identity 斷言；或文件規定「新碼只許 import core，re-export 僅相容」。不需改 A1-19 落點結論。

---

## GROK-R10-P2-02

**斷言**: B1 mutation 探針未覆蓋 Task 1.4／§V-9 方向的 returns_contract mutant（例如 `bar_count` 改回 `status=ok` 或 `default_730` 改放行），該側只靠單元測試、無「改壞必紅」自證腳本。

**碼證**: `scripts/gap1_b1_mutation_probe.sh` 只 mutate frequency／sharpe／test_vectorized_backtest（§V-5／8／10／13／15）；TODO Task 1.4 與 B1 Gate 仍列 §V-9；單元測試 `test_bar_count_is_not_applicable_*`／`test_default_730_is_rejected` 有覆蓋故非裸奔。RECHECK: 暫時改 returns_contract 使 bar_count 回 ok 後跑 test_returns_contract（應紅）；確認探針未含此步。

**來源摘要**: scripts/gap1_b1_mutation_probe.sh#99c8e1c2d94e

[MINOR] 信心度=Medium。修法：探針加一條 mutate returns_contract（bar_count→ok）期望 FAILED≥1；或 TODO B1 Gate 明文「§V-9 完整版 defer B3」。不阻 B2。

---

## GROK-R10-P2-03

**斷言**: `test_returns_contract.py` 在 `data_cache/feature_klines/kline_cache.h5` 缺失時整檔 skip，無資料 CI／乾淨 checkout 會對 Task 1.4 呈假綠（0 failed / 全 skip）。

**碼證**: `test_returns_contract.py:40-41` `if not _KLINE.is_file(): pytest.skip(...)`；多數案例走 `_result()` 真實回測。本輪有檔且 111 passed 含該檔。RECHECK: 暫移 kline 後 `pytest .../test_returns_contract.py -q` 應見 skipped，再還原。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_returns_contract.py#e656f2c3a2a46a

[MINOR] 信心度=Medium。skip 優於造假；修法選一：GAP-1 標記下改 `pytest.fail`，或拆出不依賴 kline 的 fail-closed 案例。非 B2 阻擋。

---

## 11 類必查摘要

1. 矛盾/互斥：A1-19 與 objective 實作在「靜默 730」主張上不一致 → P1-01；其餘 Task 與延伸檔一致。
2. 漏項：B1 範圍內入口契約齊；§V-9 完整 mutation defer 需標明 → P2-02。
3. 不可測：核心皆有可執行驗證命令與 atol；mutation 有 rc。
4. quant 假設：Mertens／per-period 鎖定／bar_count 膨脹 T 處理正確。
5. 過度工程：無；core 落點反而比 allowlist 克制。
6. OOM/並行：無（純算術）。
7. Cache：無新 cache。
8. API/型別：`metrics` 型別未污染；Protocol 未更新（已知取捨）。
9. 測試品質：整體可證偽；見 P2-02／P2-03。
10. Agent 可執行性：TODO 可執行；A1-19 已補 R2 落點。
11. 必要性/短命工：無（B1 產物存活至全票完工）。

---

## 建議修補優先序（進 B2 前）

1. **必**：P1-01 — objective 在 `timeframe is not None` 時 fail-closed，禁 default 730。
2. **宜**：P2-01 identity 測試；P2-02 探針補 returns_contract mutant 或 TODO 明文 defer。
3. **可**：P2-03 無 kline 策略。

STATUS: DONE
