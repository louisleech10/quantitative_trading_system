# GAP-1 B1 實作 code review（R10）— COMPOSER

**task-id**: `20260817-GAP1-B1-REVIEW-R10` | **family**: composer | **brief**: `handoffs/20260817-gap1-b1-review-BRIEF.md`
**審查標的**: commit `7093d00f`（B1 Task 1.1–1.4）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁 commit**

**VERIFY（本輪實跑）**:
- `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/momentum/Strategy/test_vectorized_backtest.py tests/momentum/Optimization/test_strategy_backtest_enhanced.py -q` → **111 passed** rc=0
- `bash scripts/gap1_b1_mutation_probe.sh` → **MUT_RC=0**（§V-8/15/5/10/13 各 1+ FAILED；post-restore 72 passed）
- `python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → **BASELINE OK** rc=0
- §V-9 手動 mutate（`bar_count` 改回 `status="ok"`）→ `test_bar_count_is_not_applicable_with_named_reason` **1 failed** rc=1（探針未自動化此條）
- `available_years` +1：真實 kline 回測 `len(equity_curve)==1500`、`bar_returns.size==1499`、`bar_returns.size+1==eq_len` ✓
- `_ann_fixture` sharpe_ratio **1.578**（非零；`test_sharpe_ratio_diverges` 之 skip 路徑本 seed 不觸發）
- `TIMEFRAME_SECONDS` 全 7 鍵 `round(365*24*3600/secs)` 與 exact 差 **0.00e+00**

---

## Verdict：需修補後進 B2

段 A–D 契約與數值核心**達標**；A1-19 兩項架構決定**可接受**（見段 B）。唯一需補：`gap1_b1_mutation_probe.sh` **未納入 TODO 要求的 §V-9**（Task 1.4／Phase B1 Gate），與 receipt 宣稱之五條清單（§V-5/8/10/13/15）亦與 Gate 行不一致——測試可證偽性存在但**自動化自證缺口**（見 `COMPOSER-R10-P1-01`）。補一條 probe mutant（`bar_count` 或 `default_730` 接受）即可進 B2；**非**根本缺陷需重作。

**BLOCKING**：無。**MAJOR**：1（P1-01）。**MINOR**：0。

---

## 段 A — 契約符合度（Task 1.1–1.4）

| Task | 結論 | 要點 |
|------|------|------|
| **1.1** | **符合** | `resolve_periods_per_year` 未知一律 `UnknownTimeframeError`（`frequency.py:39-40`）；僅 `TIMEFRAME_SECONDS` 單表；`available_years` 為唯一 bar→年推導處。 |
| **1.2** | **符合** | 退化七情形全 NaN+`status!="ok"`；`skew`/`kurtosis`/`sr_estimator_variance` per-period；Mertens 公式 `(1-γ3·SR+(γ4-1)/4·SR²)/(T-1)` 與 §G 一致（`sharpe.py:96`）；`value_annualized` 僅展示。 |
| **1.3** | **符合** | `metrics: Dict[str,float]` 未汙染；`annualization` 平行 metadata；早退亦填；`git show 7093d00f -- tests/` 兩檔**僅追加**斷言、無放寬/刪除。 |
| **1.4** | **符合（probe 缺口除外）** | `bar_count`→`not_applicable`；`default_730`/缺欄→`annualization_unresolved`；`source_artifact_hash` 綁 equity+trades；`trade_level.periods_per_year` 用 `available_years(n_bars=len(equity))`（實作 `bar_returns.size+1`＝equity 長度，見段 D）。 |

**1.1 vs 1.3 邊界**：`vectorized_backtest._resolve_annualization` 對未知 timeframe **落 `default_730`**（Task 1.3 邊界②），與 1.1 API 之 raise **不矛盾**——DSR 路徑經 `extract_period_returns` 仍 fail-closed。

---

## 段 B — A1-19 兩項決定複核

### B1 — canonical 落點 `momentum/core/frequency.py` + re-export

| 子題 | 結論 |
|------|------|
| **(a) 架構正確 vs 過閘** | **架構正確**。純常數推導、輸入 `TIMEFRAME_SECONDS` 已住 core；`Strategy→Analysis` 確實觸發 R2（brief 已附 rc=1）。放 core 比 manifest allowlist 永久放寬跨域代價小。 |
| **(b) 雙路徑漂移** | **低風險、可管理**。`strategy_validation/frequency.py` 僅 re-export `__all__` 三符號；`vectorized_backtest` 直呼 `momentum.core.frequency`（更嚴）。漂移場景＝只改 core 忘更新 re-export doc——可加 CI import 雙路徑 smoke（建議 B2 前順手，非阻擋）。 |
| **(c) 第三案** | 改 manifest allowlist（主委已否決）或 Protocol 注入對純函式過重；**維持 A1-19**。 |

### B2 — objective 條件傳 `timeframe`/`risk_free_rate`

| 子題 | 結論 |
|------|------|
| **(a) 傳遞鏈打折？** | **否（在 GAP-1 作用域內）**。`timeframe is not None` 時鏈路完整且有 `test_objective_forwards_timeframe_to_engine`／`test_objective_sharpe_matches_direct_engine`；`None` 時契約本即 `default_730` 顯式 metadata，非靜默。 |
| **(b) 應改 Protocol？** | **B1 不必**。全量更新 `IBacktestEngine`+替身會動白名單外測試檔；A1-19 條件傳遞是相容性取捨，已測「有則傳、無則舊形狀」。B4 wiring 前可再評估 Protocol 擴充。 |
| **(c) 隱性 730 反例** | **DSR 路徑無**。`extract_period_returns` 對 `default_730`/缺欄一律 `annualization_unresolved`；給 `timeframe` 而引擎不支援仍 `TypeError`。`timeframe=None` 之 730 為 Task 1.3 明示邊界，非隱性。 |

---

## 段 C — 測試品質

- **五條 mutation（§V-5/8/10/13/15）**：本輪重跑 rc=0；每條 rc=1 且 FAILED≥1；post-restore 全綠；無 MUTANT 殘留。**探針自檢非空殼**（cp 備份還原 + grep + baseline）。
- **§V-9**：**未納入探針**（見 P1-01）；手動 mutate 可轉紅。
- **`test_sharpe_ratio_diverges` skip**：`_ann_fixture` seed=20260817 下 sharpe≈1.58≠0，skip **不觸發**；§V-13 mutation 已鎖 rf 敏感性。
- **`test_returns_contract` kline skip**：無 `data_cache` 時多數用例 skip，但 `test_missing_annualization_field_is_fail_closed` 仍跑；屬專案「真實 kline、禁合成 fixture」政策，**非 B1 假綠**；CI 若要硬 gate 需另議資料供應（超出 B1）。
- **`test_no_trades_yields_zero_obs_without_crash`**：除不 crash 外仍斷言 `n_obs==0`、`status=="ok"`、`periods_per_year` 有限——邊界①合理，非廉價綠燈。

---

## 段 D — 數值正確性

- **Mertens**：與手算/scipy 一致，`test_mertens_estimator_variance_hand_formula` atol=1e-12。
- **`resolve_periods_per_year`**：1h/4h/12h/1d 及 1m/5m/15m 全鍵整除，`round` 無偏差。
- **`available_years` +1**：`equity_curve` 長 N ⇒ `pct_change().dropna()` 得 N-1 條 bar return ⇒ `n_bars=N` 須 `bar_returns.size+1`；與 TODO「`n_bars=<equity 長度>`」及 `test_trade_level_periods_per_year_matches_trades_per_year`（`len(equity_curve)/8760`）一致。**主委不確定點已澄清：+1 正確。**

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪 |
|------------|------|------|
| 111 passed | fact-verified | **覆核 rc=0** |
| decouple BASELINE OK | fact-verified | **覆核 rc=0** |
| mutation 五條全轉紅 | fact-verified（§V-5/8/10/13/15） | **覆核 rc=0** |
| 既有兩測試檔只加不減 | assumed→**verified** | `git show 7093d00f` diff 僅 `+` 區塊 |
| A1-19 架構正確 | assumed→**verified** | 段 B 結論 |
| `+1` 換算正確 | assumed→**verified** | 段 D 實跑 |

---

## Findings（canonical）

## COMPOSER-R10-P1-01

**斷言**: `scripts/gap1_b1_mutation_probe.sh` 未自動化 TODO Task 1.4／Phase B1 Gate 要求的 **§V-9** mutation（接受 `bar_count` 或 `default_730`），與 commit receipt 宣稱「五條全轉紅」及 Gate 行 `§V-5／8／9／10／13` 不一致，留下 mutation 自證缺口。

**碼證**: `scripts/gap1_b1_mutation_probe.sh:78-101` 僅 §V-8/15/5/10/13；`docs/GAP1_STRATEGY_OVERFIT_TODO.md` Task 1.4 驗證欄「mutation §V-9 轉紅」、B1 Gate「§V-5／8／9／10／13」。本輪手動 mutate `returns_contract.py` 使 `bar_count` 回 `status="ok"` → `pytest …::test_bar_count_is_not_applicable_with_named_reason` **1 failed** rc=1。RECHECK：在探針末加 §V-9 mutant（如把 `_REASON_T_SEMANTICS_INFLATES` 分支改 `status="ok"`）並斷言 rc=1。

**來源摘要**: scripts/gap1_b1_mutation_probe.sh#99c8e1c2d94e

[MAJOR] 信心度=High。會怎麼失敗：未來 regress 接受 `bar_count`/`default_730` 時，現行探針仍綠，違反 TODO「新測試須 mutation 自證」精神。修法：探針增 §V-9（可選保留 §V-15 並更新 Gate 文案統一為六條或明確取捨）。測試本體已可證偽，故非 BLOCKING。

---

## §1 必查（11 類摘要）

1. 矛盾：無（Gate 行 vs 探針清單見 P1-01）。2. 漏項：§V-9 探針。3–11：其餘無阻擋項。

STATUS: DONE
