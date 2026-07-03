# fracdiff max_lag 修復 — Manifest（扁平 ID，coverage_check 對象）

> 日期：2026-07-03 | Brief：`docs/FRACDIFF_MAXLAG_EPIC_BRIEF.md`
> 下游：`docs/FRACDIFF_MAXLAG_SPEC.md` / `docs/FRACDIFF_MAXLAG_TODO.md`
> 每個 ID 必須在 SPEC 中落點（Task 或 §N 標 N/A+理由），coverage_check.sh 機檢。

## A — production 修復（命中 (a)(d)）

- **[A-1]** `feature_preprocessor.py` `_apply_fractional_differencing` 的 max_lag
  預設分支改為 calibration-derived：`min(max(2, calibration_bars//10), 252)`
  （calibration_bars 預設 500 → max_lag=50），禁止任何 `len(df)` 依賴；
  config 顯式正值覆蓋行為保留不變。
- **[A-2]** `feature_config.py` `FractionalDifferencingConfig` 新增顯式
  `max_lag: int = 0` 欄位（0=auto→[A-1] 推導），schema/序列化影響面盤點。
- **[A-3]** `warmup_window.py` max_lag fallback（未設時取 252）與 [A-1] 的
  一致性決議：改為同一推導或保留保守值，二擇一並附理由（warmup 只影響
  預熱長度、寧可保守，不影響值正確性——SPEC 內定案）。
- **[A-4]** `_d_star_cache.py` 失效行為確認：fracdiff_hash 已含 max_lag →
  修後舊 cache 自動 miss 重算；驗證無需手動清理、無舊值污染路徑。
- **[A-5]** 全 repo 掃描：d* 搜尋/transform 路徑除 [A-1] 外不得殘留其他
  `len(df)`→max_lag 耦合（含 `_slow_path_parallel.py` metadata 傳遞鏈）。

## B — 測試（防假綠 + P1-FF-6 併入）

- **[B-1]** 移除 `test_ff_fullchain_truncation_mr.py` 兩個 fracdiff xfail 標記
  （`test_fracdiff_truncation_invariant`、`test_fracdiff_tail_perturbation_invariant`），
  修後實跑轉綠；斷言本體（d* 相等、atol≤1e-8、exact NaN mask）一字不得放寬。
- **[B-2]** mutation 探針（可證偽性）：monkeypatch Task 1.1 resolver seam
  使 max_lag 回到 `len(df)//10`，[B-1] **兩測試各自**必轉紅（serial+parallel
  皆實測）；紅不了 = 測試無效。
- **[B-3]** P1-FF-6 d* cache key mutation 探針（對準 v3 真實 guard）：
  path symbol / path TF / fracdiff_hash 之 max_lag 成分 / fracdiff_hash 之
  calibration_bars 成分 / payload row_count / payload time_range /
  strong_value_fp（既有測試已覆蓋者引用標不重複）→ 各對應隔離/失效測試
  必紅（章程 B1）；`data_fingerprint` 為 legacy 路徑不做（SPEC §N）。
- **[B-4]** 快 unit 測試：max_lag 推導函式對 len(df)∈{510,590,600,5000}
  全部回傳同值 50（calibration_bars=500 時）；calibration_bars 覆蓋與
  config 顯式覆蓋各一例。

## C — 值守恆簽核（三方，真實 kline）

- **[C-1]** 改前/改後對照（真實 `data_cache/feature_klines/kline_cache.h5`，
  run contract 見 SPEC §G：MR 同款 config、獨立空 d\* cache、全欄 digest oracle）：
  非 fracdiff 特徵全欄 digest 不變（值/NaN/數量/schema/index）；fracdiff 特徵
  變更「僅」可由窗寬變化解釋（改前 code 顯式 pin max_lag=50 跑出的值 ≡ 改後
  auto fresh-cache 跑出的值，全欄 digest 一致；G1 實際推導 max_lag 記入 receipt
  不硬編 60）。
- **[C-2]** 三方獨立簽核：Claude + Codex + Composer 各自檢 [C-1] 證據與
  方法論，至少一腿 adversarial 式獵漏（非確認式），三方都 PASS 才過。
- **[C-3]** slow 全鏈 receipt：fracdiff MR 套件實跑 passed 留 receipt；
  跑後 `./scripts/restore_golden_inventory.sh` + 清 pytest 舊輪次。

## D — 文件與治理

- **[D-1]** ROADMAP（P1 節收斂）+ HANDOFF 更新；
  `docs/FEATURE_STATEFUL_PARAM_AUDIT_FINAL.md` 若載 max_lag 語意需同步。
- **[D-2]** 管線留痕：雙家族 adversarial 檔 + reconcile 雙戳記 + review 檔
  全數 register-output 進 audit log，隨 commit 入庫。

## 排除（明列不做）

- d\* 持久化 / 固定參考 d\*（productionization epic，另立案）。
- 其他 preprocessing 層（winsor/rank/zscore/gaussian）任何行為變更。
- FF preset 盤點（另一 epic）。
