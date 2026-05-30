# Handoff

**Agent**: Claude Code | **Time**: 2026-05-30 | **Branch**: main

## 正在做
無（本 session 完成 rolling skew/kurt 數值爆炸修正 L1–L4 + preprocessing 測試對齊）

## 最新（Rolling Skew/Kurt 爆炸修正，2026-05-30）

**根因**（實測確認，推翻所有先前假設）：
- L3 rolling skew/kurt 在 **原生 12h 序列**（HT-TRENDMODE 二元 0/1）計算，再前向填充到 1h index
- `rolling_skew_kurt`（增量 Pébay 滑動窗口）在**窗口從「含幾個 0」滑進「全 1」的瞬間爆炸**
- `_pebay_remove` 移除最後一個 0 時 catastrophic cancellation → m2 殘留 ~1e-25
- 舊絕對守衛 `m2 < 1e-30` 攔不住 → `m3/m2^1.5 → 2.6e+32`
- 確認推翻：非 parallel/cache 問題、非資料版本不一致

**修正 L1–L4（全部雙模式 CGSA + non-CGSA 驗證）**：
1. **L1 kernel（核心）**：`_compute_skew/_compute_kurt` 換成尺度相對守衛 `m2 ≤ 1e-12 × Σx²`（SciPy 同結構，1e-10 price / 1e20 volume / 報酬類 mean≈0 全正確；保留真實 fat-tail）
2. **L2 輸出衛生**：`if not isfinite: return NaN`（只攔 inf/overflow，不 clip 有限值）
3. **L3 快取+測試**：清 numba `__pycache__/*.nbc/.nbi`；`test_numba_rolling.py` 新增 6 個回歸測試（choppy→constant、1e-10/1e20 尺度、單離群值、determinism）
4. **L4 Pipeline 把關**：`compute_all` 一次算低基數欄位集合（`skip_higher_moments_max_cardinality: 2`，config 可調），4 個 skew/kurt 產出點共用，二元欄不輸出 skew/kurt 但保留 mean/std。CGSA / non-CGSA / numba / pandas fallback 4 路徑一致

**測試**：43 passed (test_numba_rolling)、197 passed 全 preprocessing suite

**資料重生成**：磁碟上 52 個 `|mean|>1e20` / 1107 個 `|mean|>1e10` L3 Skew/Kurt 特徵仍為舊爆炸值，需使用者觸發完整 feature pipeline 重跑後消失。

**副修**：3 個 preprocessing 測試對齊現行程式碼（fast-ADF 繞過了 monkeypatch 的 adfuller / log 字串改寫）。

## 踩坑提醒（本次新增）
- `rolling_skew_kurt` 的退化守衛必須是**尺度相對**（`m2/Σx²`），絕不用絕對門檻；pandas 在 1e-10 尺度會誤殺，我們的實作更正確
- numba `parallel=True` + `prange` 跨 window 的浮點 reordering 是非確定性來源（P4 已改成 sequential `range`，勿回退）
- L3 Skew/Kurt 對二元/低基數 L1 特徵（如 HT-TRENDMODE）本質退化，Layer 4 gate 在源頭阻斷，`skip_higher_moments_max_cardinality: 2` 控制
- fast-ADF（`FFACT_USE_FAST_ADF`，預設 1）繞過 statsmodels `adfuller`；測試需 `monkeypatch.setenv("FFACT_USE_FAST_ADF", "0")` 才能 patch adfuller

## 待辦
- **使用者觸發**：feature pipeline 重跑後在 Feature Table `Mean ↓` 確認頂端無 `|mean|>1e10` 特徵
- （既有）large_trade_ratio fail-fast + warmup 誤判（RUN_COMPARISON_20260521 §3.2/3.3）

## 阻塞
- （無）

## 前次完成（資料品質 Dashboard 重設計，2026-05-29）
- P0 coverage bug、P0 cache 失效、P1 誠實分類（warmup_only_high_nan/real_problem）、P3 group_breakdown
- 前端 types.ts、DataQualityDashboard 新增 tradeoff chart + group NaN stacked bar

## 前次完成（NaN 處理三 step，2026-05-28）
1. Cascade Blacklist（CDL_PATTERN_ALL + HT_DCPHASE 5 入口）
2. L7 Dead Feature Drop（frame path，`nunique<2` OR `valid_count<100`）
3. ADF Safe-Skip Whitelist（47 patterns，bypass 嚴格 I(0)）
- 179 tests pass；decoupling Phase 4.6.2 PASSED

## 不變的規則
- `momentum/` 絕不 import `api/`（7 Decoupling Rules）
- NaN ratio **不**是欄位品質指標；絕不以 NaN ratio 作為 drop 條件
- 退化守衛必須尺度相對；fat-tail 有限值不 clip
