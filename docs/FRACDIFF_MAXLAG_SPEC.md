# fracdiff max_lag 截斷不變修復（併 P1-FF-6）— SPEC

> 來源 PLAN/診斷：`docs/FRACDIFF_MAXLAG_EPIC_BRIEF.md` + `docs/FRACDIFF_MAXLAG_MANIFEST.md` + 三腿檔 `handoffs/20260702-FF-DSTAR-GATE-{CLAUDE,CODEX,COMPOSER}.md`　|　日期：2026-07-03　|　對應 TODO：`docs/FRACDIFF_MAXLAG_TODO.md`

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（會改全部 fracdiff 特徵值）。
- **命中高風險原則**：(a) 數值正確性/資料品質（fracdiff 全欄值變更）；(d) ML/回測正確性（特徵值餵 IC/ML，截斷不變性是防偽護網基礎）。(b) 部分：`feature_config.py` schema、warmup_window 下游。
- 命中 (a)(d) → §G Golden 必填、雙家族 adversarial 必跑（大型鐵律 2026-06-09）。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（附驗證方式；各項含 .py 行號或 receipt 出處）：
  1. max_lag 預設分支 `min(max(2, len(df)//10), 252)` 位於 `feature_preprocessor.py:3198-3200`，僅當 config `max_lag<=0` 時觸發（本 session grep+Read 實證）。
  2. `FractionalDifferencingConfig`（`feature_config.py:183-191`）**無 max_lag 欄位** → production 預設永遠走 len(df) 耦合分支（本 session Read 實證）。
  3. d\* 搜尋 `_find_min_d` 用 `_calibration_series`（first-500 prefix，`feature_preprocessor.py:3699`）取值，但 `_get_weights_ffd(..., max_width=max_lag)`（:3734）吃外部傳入的 len(df)-derived max_lag（本 session Read 實證）。
  4. transform 路徑（serial `:3029-3059` 的 `max_width=max_lag`；parallel `_slow_path_parallel.py:128,145` 經 column_metadata 傳遞）同吃該 max_lag（本 session grep+Read 實證）。
  5. `_d_star_cache.py` 的 `fracdiff_hash` 含 max_lag（`:206-221,302-308`），payload 驗 `row_count`/`time_range`（`:421-426`）→ max_lag 改變後舊 cache 自動 miss（本 session Read 實證）。
  6. `warmup_window.py:292-295`：config max_lag<=0 時 fallback 252 當預熱基底（本 session Read 實證）。
  7. 失敗實錄：B2 回歸 receipt `20260702T042627Z-ff-b2-regression`（2 fracdiff failed；d\* mismatch `0.4844 vs 0.4688`）。pin `max_lag=50` 時 600→590 d\* 全同（檔載於 `handoffs/20260629-FF-B2-FRACDIFF-codex.md` 實測記錄）。
  8. `calibration_bars` 預設 500（`feature_preprocessor.py:175-187`）；fracdiff MR config 亦設 500。
  9. `lag_processor.py`/`parameter_generator.py` 的 max_lag 是 lag 運算子概念（吃 config sequence_length），與 fracdiff d\* 路徑無關（本 session grep 實證）→ 不在本 epic 範圍。
  10. **（2026-07-03 斷路器委員會補）** `config_override.preprocessing.fractional_differencing.max_lag` 在現行 HEAD 被 nested `FractionalDifferencingConfig` 靜默丟棄（無該欄位、無 extra=allow）→ **production config path 無法 pin max_lag**。runtime probe：`model_dump_max_lag <missing>`（出處：`handoffs/20260703-FRACDIFF-MAXLAG-G2PIN-CODEX.md` §1，解析鏈 `config_manager.py:90-100`→`feature_config.py:183-191,231-245`→`feature_factory.py:2745-2747`）。故 Task 1.2 非僅顯式化，是把幽靈逃生口變真。
- **待使用者確認**：無（定序與路由使用者 2026-07-02 已定；修向屬技術決策，三腿委員會已收斂 max_lag 解耦 len(df)，依 memory 技術決策委派委員會）。
- **已確認結果**：使用者 2026-07-03「開始 fracdiff epic/P1-FF-6 流程」+「中大型 Codex 執行、Composer review」。

## §C 約束（引用 + 本任務相關）
- 解耦 7 條（`grep "from api\." momentum/`→0 等）；不弱化 NaN/inf gate；不擅改輸出大小；優化優先序 1-3（跨tier/多symbol/資料品質）先於 runtime。
- 本任務共用路徑/下游：`feature_config.py`（schema 消費者：config_manager、warmup_window、native_tf_helpers、API 序列化）；`_d_star_cache`（cache 檔案相容性）；`ff_truncation_mr_helpers.py`（測試 helper，多測試共用）。
- **禁止**：放寬 [B-1] 兩測試任何斷言（d\* 相等、atol≤1e-8、exact NaN mask）；動其他 preprocessing 層行為；動 d\* 持久化（另 epic）。

## §G Golden / Baseline（高風險(a/d) 必填；adversarial 修訂版 2026-07-03）
- **run contract（可重現，寫死）**：真實 kline `data_cache/feature_klines/kline_cache.h5`，BTC+ETH × 1h；config 來源 = `ff_truncation_mr_helpers._fracdiff_mr_config_payload()`（calibration_bars=500）；窗長 = `_fracdiff_window_bars(...)`（≥600，與 MR 同款）；G2 僅覆寫 `fracdiff.max_lag=50`。輸出 parquet + digest json，路徑寫死於 TODO Task 0.1。
  (G1) 現行 code 預設（auto→len 耦合，**receipt 記錄實際推導 max_lag**，不硬編 60）；(G2) **現行 code 計算路徑 + G2-only `FeaturePreprocessor.__init__` wrapper 於實例 `fracdiff_config["max_lag"]=50` 注入**（§A.10：config path 會丟棄該鍵，故非 config-path pin；G2 語意=「pre-fix calculation-path pin=50 baseline」，receipt 記 `pin_method=preprocessor_instance_fracdiff_config_injection`）。
- **G2 pin 防呆斷言（缺任一=Task 0.1 FAIL，2026-07-03 委員會裁定）**：①G2 全部 d\* payload `max_lag==50`；②G2 `fracdiff_hash` ≠ G1；③G1 vs G2 fracdiff 欄 digest 必不同、非 fracdiff 欄必相同；④patch 作用域結束後 `__init__` 還原（不污染 G1/修後 run）。
- **D 增強（Composer）**：Task 1.2 落地後用真 config 路徑（顯式 max_lag=50）重跑 G2'，斷言 G2' digest == G2——同時驗證注入等價與 schema 修復生效（落 Task 1.2 驗證欄）。
- **oracle = 全欄 byte 級（禁抽樣 hash 作 PASS 依據）**：per-column 全量 `value_sha256` + `nan_mask_sha256` + dtype + index hash + feature 名稱/順序 schema hash。per-feature mean/std/nan_ratio 僅作人讀診斷，非 oracle。既有 `build_l65_golden_baseline.py` 的抽樣 hash 工具**不得**充當 byte 級比對（Composer 碼證 :275-308 為 13 row 抽樣）。
- **cache 隔離（防套套邏輯，Codex #2）**：G1/G2/修後三跑各用**獨立空 d\* cache 目錄**（或 `cache_d_star=False`）；receipt 必記：resolved max_lag、DStarCache 檔案路徑、payload fracdiff_hash、cache hit/miss 計數。修後跑必須是 **fresh 重算**證明推導正確，不得吃 G2 寫入的 cache。
- **通過條件（可證偽）**：
  1. 修後預設（fresh cache）vs (G2)：fracdiff 欄 per-column value/nan-mask sha256 **全欄一致**（證明變更純由窗寬造成）。
  2. 修後預設 vs (G1)：非 fracdiff 欄 per-column sha256 全欄一致 + row count/index 相等；fracdiff 欄允許且預期不同，diff 報告列 G1 實際 max_lag 與修後值 + 差異樣本（atol 報告用 1e-8 尺度，最多列 20 欄）。
  3. 任一超出 → 列出 feature + 實際 diff = FAIL，不 merge。
  4. **§G 為「同窗全量守恆」必要非充分**：截斷不變性由 [B-1] slow MR receipt 另證，兩者都過才簽核（Task 3.1 條件 4）。

## §P Phase 與依賴

### Phase 1 — production 修復（依賴：無）
**Task 1.1 — [A-1] max_lag 預設改 calibration-derived（含可測 seam，Codex #4）**
- 目標：d\*/transform 路徑 max_lag 與 len(df) 解耦。檔案：`feature_preprocessor.py` `_apply_fractional_differencing`（:3198-3200 分支）。
- 改法：新增**獨立 resolver 方法** `_resolve_fracdiff_max_lag(self) -> int`：config 顯式正值→原值；否則 `min(max(2, self._calibration_bars() // 10), 252)`。`_apply_fractional_differencing` 改呼叫該 resolver（production 唯一推導點，mutation 探針的 monkeypatch seam）。同步更新行內註解語意。
- 既有 caller/影響面：同函式內 cache 建構（:3207-3221）、serial/parallel 傳遞（值來源改變、介面不變）。
- 驗證：unit 測 len(df)∈{510,590,600,5000} 推導皆 50（calibration_bars=500）；顯式 config=37 時用 37；`grep -n "len(df)" feature_preprocessor.py` 確認 fracdiff 推導路徑零殘留。
- 邊界：①df=300（<calibration_bars）→ resolver 仍回 50，且 d\* 搜尋實際只用 300 bars（`_calibration_series` 取 min，:180-182）——短 df oracle：resolved max_lag==50、輸出 row count 不變、無例外、`size<w` 全 NaN 保護路徑（:3738-3739）行為記錄不弱化；②calibration_bars=800 → 80。**短於 calibration_bars 的截斷 MR 保證不在本 epic 範圍（§N 登記）**。
- 不可做：不改 `_get_weights_ffd`/卷積本體；不動 precision/adf_threshold 語意。

**Task 1.2 — [A-2] FractionalDifferencingConfig 顯式 max_lag 欄位**
- 目標：schema 顯式化，0=auto。檔案：`feature_config.py:183-191` 加 `max_lag: int = Field(default=0, ge=0)`。
- 影響面：`warmup_window.py:292`（model_dump().get 已相容）、config 序列化/前端 payload（新欄位有預設值，向後相容）。
- 驗證：pydantic round-trip 測試；舊 config dict（無 max_lag）載入不炸且值=0；**G2' 交叉驗證（D 增強）**：schema 落地後用真 config 路徑 pin=50 重跑 golden run contract，G2' digest == G2（證 §G 注入等價 + config 路徑修通）。
- 邊界：負值 config → `ge=0` ValidationError（fail-fast，不靜默視同 auto）；非 int 型別。
- 不可做：不加 preset 相關欄位（preset 盤點另 epic）。

**Task 1.3 — [A-3] warmup_window fallback 一致性**
- 目標：決議並落地。改法（本 SPEC 定案）：**保留 252 保守 fallback 不改**——warmup 只影響預熱長度非值正確性，寧可多熱；但加註解引用本 epic 說明為何與 [A-1] 推導不同。**行數不受影響論證（Codex NB#2）**：warmup base_windows 先含 calibration_bars≥500（`warmup_window.py:290`），故 252 fallback 不主導 trim；G2 顯式 50 與修後 auto 50 產出 row count/index 必相等——§G 條件 2 已含 row-count/index 相等斷言。
- 驗證：`pytest tests/ -k warmup_window` 全 passed（既有測試零修改，diff 為證）。邊界：config 顯式 max_lag>0 時 warmup 用顯式值（現行為，不變）。
- 不可做：不把 warmup 也改成 50（縮短預熱屬行為變更，超範圍）。

**Task 1.4 — [A-4]+[A-5] cache 失效確認 + 全路徑掃描（Codex #3 修訂：分兩案）**
- 目標：證明無殘留 len(df) 耦合、cache 失效語意精確。
- 改法：掃描 fracdiff/d\* 路徑（`feature_preprocessor.py`、`preprocessing/_slow_path_parallel.py`、`preprocessing/_d_star_cache.py`、`preprocessing/_native_tf_helpers.py`）所有 max_lag 來源；寫測試斷言修後同 config 下 fracdiff_hash 與 len(df) 無關（600 vs 590 hash ==）。
- **舊 cache 兩案分立**：(a) 修前 auto len-derived cache（max_lag=60 hash）→ 修後必 miss 重算；(b) 修前顯式 pin=50 cache → payload（row_count/time_range）與 per-column strong_value_fp 全符時**允許合法命中**（這是正確重用非污染），測試分開斷言，不得寫成「一切舊 cache 必 miss」。
- 驗證：兩案測試 pytest passed；grep 產物列入交接檔。邊界：cache 目錄不存在 → 正常建立。

### Phase 2 — 測試轉綠 + P1-FF-6 探針（依賴：Phase 1）
**Task 2.1 — [B-1] 兩 xfail 移除轉綠**
- 檔案：`tests/feature_engineering/test_ff_fullchain_truncation_mr.py:116-155` 移除兩個 `@pytest.mark.xfail`，斷言本體一字不改。
- 驗證：slow 實跑兩測試 passed（receipt 留檔）。防假綠：diff 斷言（`_assert_fracdiff_truncation_invariants`/`_assert_d_star_gate` 不得被改弱）。
- 邊界：xfail 移除後若紅 → 修 production 而非測試。

**Task 2.2 — [B-2] max_lag mutation 探針（Codex #4/#6 + Composer 修訂）**
- 目標：可證偽性。改法：monkeypatch **Task 1.1 的 `_resolve_fracdiff_max_lag` seam** 使其回傳 `len(df)//10` 等效值 → MR 必 FAIL（pytest.raises 包住）。
- **覆蓋兩 MR**：截斷 MR（600→590）與尾端擾動 MR 各一 mutation 檢查（或共用 mutant fixture 各跑一次），不得只證 d\* gate 單場景。
- **parallel 路徑**：另一 mutation case 強制 `n_jobs>1` 走 `_slow_path_parallel`（縮欄數控時長）實測 mutant 穿透，不得只用「參數同源」論證。
- 驗證：mutation 測試 pytest 單跑 passed（= 內部 `_assert_d_star_gate`/值斷言確實拋 AssertionError），serial+parallel 各≥1。邊界：monkeypatch 經 fixture 隔離不洩漏。

**Task 2.3 — [B-3] P1-FF-6 d\* cache key mutation 探針（Codex #5 + Composer 重設計：對準 v3 真實 guard）**
- 目標：cache 隔離護網可證偽。mutant 對準 **production v3 實際 guard**（`_d_star_cache.py`）：
  ①path symbol（:327-331，須構造「同 path 錯 payload」或跨 symbol 錯誤命中場景，**不重複** P1-FF-5 V5.2 path 測試）；②path timeframe；③`fracdiff_hash` 移除 **max_lag** 成分（本 epic 核心軸）；④`fracdiff_hash` 移除 **calibration_bars** 成分（:227）；⑤payload `row_count`（:421）；⑥payload `time_range`（:425）；⑦per-column `strong_value_fp`（:482-486、501-527——若 P1-FF-5/`test_d_star_col_fingerprint.py` 已覆蓋則引用檔名標「不重複」）。
  `data_fingerprint` 為 legacy no-col-values 路徑（:493-499）→ **N/A 登記不做 mutant**（理由：非 v3 production guard）。
- 驗證：≥6 個 mutant 各一測試（pytest.raises + match FAIL 訊息可辨識）+ `scripts/mutation_probe_check.sh tests/feature_engineering/test_dstar_cache_key_mutation.py` exit 0（章程 B1.1）。邊界：mutant 逐一開關互不遮蔽；誤命中須被**值斷言**抓到（非只 hash 斷言）。
- 不可做：不擴到 batch checkpoint/RunLease 污染面（B-5 defer 項，另批）；不動 production cache 邏輯。

**Task 2.4 — [B-4] 快 unit 推導測試**
- 如 Task 1.1 驗證欄所列，獨立快測（非 slow），CI 常跑。

### Phase 3 — 值守恆簽核 + 收尾（依賴：Phase 2）
**Task 3.1 — [C-1]+[C-2] 三方值守恆簽核（Composer 修訂：oracle 統一 + 條件 4）**
- 依 §G 四條通過條件產證據包（真實 kline，禁合成 fixture）：oracle = per-column 全欄 value/nan-mask sha256（canonical digest），per-feature 統計僅輔助——**任一 fracdiff 欄 digest 不同即 FAIL**，不存在「hash 相等即可」與「須 per-feature 統計」的雙軌。條件 4 = [B-1] slow MR receipt（截斷不變另證）。
- **float 並行穩定性前置**：同 config 同 n_jobs 連跑兩次 canonical digest 相同（可執行腳本/pytest 落在 Task 0.1 比對工具內）才進行對照。
- 簽核範圍：BTC+ETH × 1h（§G run contract）；Claude + Codex + Composer 獨立審，至少一腿 adversarial 式獵漏（主動構造反例：換 symbol/窗長試圖打破守恆）；三方 PASS 才過。
- 驗證：3 份簽核檔（handoffs/*.md）各載明 PASS/FAIL + 反例嘗試記錄 + receipt 引用（resolved max_lag、fracdiff_hash、cache hit/miss）。
**Task 3.2 — [C-3] slow 全鏈 receipt**
- fracdiff MR 套件實跑 passed；跑後 `./scripts/restore_golden_inventory.sh` + 清 pytest 舊輪次（留 pytest-current）。
**Task 3.3 — [D-1]+[D-2] 文件與留痕**
- ROADMAP/HANDOFF 更新；`docs/FEATURE_STATEFUL_PARAM_AUDIT_FINAL.md` max_lag 語意同步；全過程檔 register-output。

## §V 驗證策略與邊界測試目錄
- 層級：unit（推導函式、config schema）/ 整合（MR 全鏈 slow）/ Golden 對照（§G 三條）/ mutation（B-2/B-3 可證偽）。皆 `pytest tests/...` 可獨立跑。
- **防假綠**：diff 既有斷言（兩 MR、`_assert_d_star_gate`、mutation negative controls）不得放寬；mutation 探針證明紅得起來；驗收引用格式「檔載『…』(出處:receipt)」。
- 邊界目錄：短 df（<calibration_bars）✓Task1.1 / 全NaN 欄（既有 skip 路徑不變）✓Task1.4 / 舊 cache 檔載入兩案 ✓Task1.4 / 負值·非法 config ✓Task1.2 / 並發 parallel mutation ✓Task2.2 / `len(clean)<20` d\* 硬回 1.0（`feature_preprocessor.py:3701-3702`，行為不變記錄）✓Task2.4。
- 測試章程（`docs/TEST_DESIGN_CHARTER.md`）：B-2/B-3 屬 B1 類 mutation probe；oracle 分級——[C-1] 為 golden byte 級 oracle，[B-1] 為 metamorphic 不變量 oracle。

## §R 回退
- Phase 1/2/3 各獨立 commit，可單獨 revert；[A-2] schema 欄位有預設值、向後相容，revert 無 migration。
- 不設 feature flag：本修復是正確性修復，依「驗過就別預設關閉」原則直接生效；回退靠 revert（單點改動、confined 路徑）。Golden FAIL → 不 merge。

## §N N/A 登記
- §A 待使用者確認：無 —— 修向屬技術決策，三腿委員會已收斂且使用者已定序/定路由（見 §A 已確認結果）。
- feature flag（§R）：N/A — 理由如 §R；以 pin-config（顯式 max_lag）作為對照/逃生口，非預設關閉。
- 短於 calibration_bars（df<500）之截斷 MR 保證：N/A — 本 epic 只保證推導解耦與短 df 不炸/不弱化 NaN gate；短窗截斷不變量另議（Composer ④）。
- `data_fingerprint` mutation 探針：N/A — legacy no-col-values 路徑（`_d_star_cache.py:493-499`），非 v3 production guard（Codex #5）。
- 簽核範圍為 BTC+ETH × 1h 非 10 symbols × 3 TF：Golden byte 級對照成本受控取窄集；全量 10×3 於 epic 完成後「FF 定版重生成給 IC」時由使用者手動觸發覆蓋（Brief §7/§8 已同步修正，Composer B3）。
