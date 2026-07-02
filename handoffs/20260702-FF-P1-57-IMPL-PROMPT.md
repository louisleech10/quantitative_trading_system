# P1-FF-5/7 實作指派（Codex GPT-5.5 讀此檔執行；2026-07-02 使用者改派：Codex 實作、Composer review）

依三方定案 reconcile v2(codex+composer 內容 APPROVED):`handoffs/20260702-FF-P1-57-RECONCILE.md`。逐字讀該檔 §1-§4 + 三腿設計檔(DESIGN-CLAUDE/CODEX/COMPOSER)。真實 kline `data_cache/feature_klines/kline_cache.h5`,禁合成 fixture 當驗收。

## 交付(兩新檔 + 可選 helper)
- `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`(P1-FF-5)
- `tests/feature_engineering/test_ff_wrapper_path_correctness.py`(P1-FF-7)
- 可選 `tests/feature_engineering/ff_artifact_compare_helpers.py`

## P1-FF-5(照 reconcile §2)
分層:fast(order 三序 [A]/[A,B]/[B,A] 同 factory,canonical hash+抽 20 欄真值)、medium(A/B/A + L5 ref cache)、slow(solo(A) vs batch[B,A] 全鏈,`@pytest.mark.slow` + requires_kline)。不變量 V5.1 值/V5.2 d* 語義 map(非 byte)/V5.3 metadata/V5.4 路徑隔離;污染面覆蓋表 8+ 面各映射。探針 M5.1/M5.2/M5.3(v2 shape:正向偵測斷言在 raises 外)。

## P1-FF-7(照 reconcile §3)
V7.1 全 registry input semantics + direct-call differential + price_transform/MAVP/advanced;V7.2/7.3 **三層聯集** L2(polars vs pandas)/L3(numba vs pandas fallback)/L6.5(_transform_single 三分支 polars/numba_fast/serial + fracdiff on/off 互斥斷言);路徑證據=monkeypatch sentinel/counter 包各分支+反路徑 raise/計數 0(非 log)。V7.4 float16 誤差上界。探針 M7.1/M7.2。

## 驗證(鐵律:改完即交,勿硬撐慢測)
- **你只跑快測級**(fast tier + V7.2/7.3 小矩陣分鐘級) + py_compile/collect/mutation_probe_static;**慢測(FF5 slow 全鏈)你不跑**——標 marker 留編排端排隊(當前 mutation run 後序列,防 OOM)。
- 先單測快驗個別探針再全套(align oracle 教訓)。探針過 mutation_probe_static。
- 不動 production;不放寬既有斷言;測試副作用還原(golden inventory)。

## 收尾
寫 `handoffs/20260702-FF-P1-57-IMPL-codex.md`(逐 V/M 實作+新測試名;TESTS_RUN 明標 fast/skipped-slow;FAILURES/SCOPE)。禁「已驗/真紅」字樣。最後 STATUS: DONE 或 BLOCKED。
