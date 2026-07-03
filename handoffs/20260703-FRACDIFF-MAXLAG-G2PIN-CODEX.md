# fracdiff max_lag G2 pin 斷路器 — Codex 腿

task-id: fracdiff-maxlag-g2pin-codex-20260703
date: 2026-07-03
scope: read-only analysis; only this file written

## 1. 事實 6 實碼驗證

結論：事實 6 成立。現行 HEAD 的 `config_override["preprocessing"]["fractional_differencing"]["max_lag"] = 50` 會在 Pydantic schema 解析後被丟棄；`FeaturePreprocessor` 收到的 dict 不含 `max_lag`，讀值點回到 `len(df)//10` auto 分支。

解析鏈行號：
- `momentum/factories.py:234-249`: `create_feature_factory()` 建立 `ConfigManager()` + `AdapterRegistry()`，回傳 `FeatureFactory(config_manager, registry)`。
- `momentum/FeatureEngineering/feature_factory.py:237-252`: `generate_features()` 先呼叫 `_resolve_config(config_override)` 產生 `FactoryConfig` 並計算 cache hash。
- `momentum/FeatureEngineering/feature_factory.py:275-292`: `_generate_features_impl()` 再呼叫 `_resolve_config(config_override)`；實際 pipeline 使用這份 `FactoryConfig`。
- `momentum/FeatureEngineering/feature_factory.py:3673-3686`: `_resolve_config()` 一般路徑直接走 `self._config_manager.get_merged_config(config_override)`。
- `momentum/FeatureEngineering/config_manager.py:90-100`: `get_merged_config()` 將 default/user/API override deep-merge，然後 `FactoryConfig.model_validate(merged)`。
- `momentum/FeatureEngineering/feature_config.py:183-191`: `FractionalDifferencingConfig` 欄位只有 `enabled/d_range/adf_threshold/weight_threshold/precision/apply_to/cache_d_star`，沒有 `max_lag`，且未設 `ConfigDict(extra="allow")`。
- `momentum/FeatureEngineering/feature_config.py:231-245`: `PreprocessingConfig.fractional_differencing` 型別是 `FractionalDifferencingConfig`。
- `momentum/FeatureEngineering/feature_config.py:461-490`: `FactoryConfig` 本身 `extra="allow"`，但這只保留 FactoryConfig 層未知鍵；nested `FractionalDifferencingConfig` 仍依自身預設 extra 行為忽略未知鍵。
- `momentum/FeatureEngineering/feature_factory.py:2745-2747`: 交給 preprocessor 前使用 `config.preprocessing.model_dump()`；已被丟棄的 nested key 無法再出現。
- `momentum/FeatureEngineering/feature_factory.py:2625-2639`: `_run_layer6_5_preprocessor()` 將該 dict 傳給 `FeaturePreprocessor(...)`。
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:130-145`: `FeaturePreprocessor.__init__()` 設 `self.fracdiff_config = self._config.get("fractional_differencing", {})`。
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:3193-3200`: fracdiff 讀 `self.fracdiff_config.get("max_lag", 0)`；缺 key 時 `max_lag <= 0`，改用 `min(max(2, len(df)//10), 252)`。

實測命令：
```bash
source venv/bin/activate && python - <<'PY'
from momentum.FeatureEngineering.config_manager import ConfigManager
cm = ConfigManager()
config = cm.get_merged_config({
    "preprocessing": {"fractional_differencing": {"enabled": True, "max_lag": 50}}
})
frac_model = config.preprocessing.fractional_differencing
frac_dump = config.preprocessing.model_dump()["fractional_differencing"]
print("has_attr_max_lag", hasattr(frac_model, "max_lag"))
print("model_dump_keys", sorted(frac_dump.keys()))
print("model_dump_max_lag", frac_dump.get("max_lag", "<missing>"))
print("extra", getattr(frac_model, "__pydantic_extra__", None))
PY
```

實測輸出摘要：
```text
has_attr_max_lag False
model_dump_keys ['adf_threshold', 'apply_to', 'cache_d_star', 'd_range', 'enabled', 'precision', 'weight_threshold']
model_dump_max_lag <missing>
extra None
```

推論：現行 HEAD 的 production config 路徑沒有有效 pin escape hatch；2026-06-29 直接餵 dict 給 `FeaturePreprocessor` 的 pin 實驗不等價於 `create_feature_factory().generate_features(config_override=...)` 路徑。

## 2. G2 產法裁決

裁決：選 A，但縮窄為「實例 dict 層注入 + 強防呆斷言 + 報告明確標記 non-production config-path workaround」。不選 B/C。

理由：
- G2 的目的不是證明現行 config schema 可 pin，而是產出「修前計算邏輯、唯一差異為 fracdiff 讀值點收到 `max_lag=50`」的 byte oracle。A 能隔離到 `FeaturePreprocessor.fracdiff_config` 這個 production 讀值 dict，避免混入 Task 1.2 的 schema commit。
- B 會把 G2 變成「HEAD + schema fix」而非 strict pre-fix baseline。雖然 Task 1.2 預期不動數值演算法，但它會改 config hash、model dump、schema 序列化面，新增一層需要簽核的變因。
- C 會弱化 §G 條件 1。它可作修後 sanity 對照，但不能取代「修後預設 vs 修前 pin=50」這個直接證明。

建議 A 的具體形態：
- 只在 freeze script 的 G2 run 內 patch `FeaturePreprocessor.__init__` wrapper：呼叫原始 `__init__` 後，在同一實例的 `self.fracdiff_config["max_lag"] = 50` 注入。
- wrapper 只在 G2 context manager 作用域內生效，G1/G1-repeat 不可共享。
- 不 patch `feature_preprocessor.py:3198-3200` 的計算邏輯，不 patch `_get_weights_ffd`、cache hash builder 或 transform 路徑。
- G2 receipt 必寫：`pin_method=preprocessor_instance_fracdiff_config_injection`，並列出非 production config path 的原因：現行 Pydantic schema drops key。

必加防呆：
- G2 run 後檢查所有 d* payload 的 `max_lag == 50`。
- G2 run 後檢查所有 d* payload 的 `fracdiff_hash != G1`，且 hash 中解析/記錄的 max_lag 與 G1 實際值不同。
- G1 vs G2 的 fracdiff 欄 digest 必不同；非 fracdiff 欄 digest 必相同。
- patch context 結束後跑一個輕量 assertion：新建或下一個 preprocessor 沒有殘留 `max_lag=50` 注入，避免污染 G1-repeat 或後續修後 run。

主要風險：
- A 不是 production config path，§G 文字若不改會讓後續驗收誤讀成「現行 code + config_override pin」。
- dict 注入若打到未使用實例或被後續 copy 覆蓋，會靜默失效；上面的 payload/digest 斷言是 hard gate。
- 若 G2 使用 CGSA streaming 或 L7 raw 路徑，需確認所有 `FeaturePreprocessor(...)` 建立點都經 wrapper；`feature_factory.py:2235-2242`、`:2635-2668`、`:3197-3200` 都是候選實例化路徑，wrapper 在 class `__init__` 層比單一 callsite 更穩。

## 3. 挑戰 Claude 腿等價論證

Claude 腿的核心「dict 注入與 config 路徑若通會交付的東西在 `self.fracdiff_config.get("max_lag", 0)` 讀值點 byte 級等價」大方向成立，但有四個漏洞需要補：

1. 等價邊界只覆蓋 fracdiff 讀值點，不覆蓋 config hash / cache key。production config path 若 schema 支援 `max_lag=50`，`FeatureFactory._compute_config_hash()` 會經 `config.model_dump(by_alias=True)` 將 `max_lag` 納入 feature cache key（`feature_factory.py:3696-3724`）。dict 注入發生在 config hash 之後，不會改 feature store cache key。G2 必須 `force_regenerate=True` 且用獨立輸出/空 cache，不能依賴 feature cache key 隔離。
2. 等價邊界不覆蓋 metadata/config_used。若 receipt 或 parquet metadata 讀的是 `FeatureGenerationResult.config_used` 或 `effective_preprocessing_config`，它可能仍不含 `max_lag=50`，除非腳本另外從 d* payload 記錄 resolved max_lag。因此 §G 不能要求「config_used 顯示 pin 生效」作為 A 的證據。
3. 「factory 建好後、generate 前，把 preprocessor 的 dict 注入」這句操作上不精確；preprocessor 是 generate 途中才建立的，不是 factory 建好時已存在。實作應為 `FeaturePreprocessor.__init__` wrapper 或在 factory callsite 附近攔截 newly-created instance。
4. 若 patch 到 `self._config["fractional_differencing"]` 但 `self.fracdiff_config` 已經綁到舊 dict/copy，或反過來只 patch 外部 config dict 而不是實例使用的 dict，會失效。應明確 patch `self.fracdiff_config`，並用 `assert self.fracdiff_config.get("max_lag") == 50` 在 wrapper 內 fail-fast。

因此：A 可接受，但只能在文件中稱為「pre-fix calculation-path pin baseline」，不能稱為「pre-fix config-path pin baseline」。

## 4. SPEC §G 文字修改建議

建議把 §G 第 30-31 行改成下列語意：

```markdown
- run contract（可重現，寫死）：真實 kline `data_cache/feature_klines/kline_cache.h5`，BTC+ETH × 1h；config 來源 = `ff_truncation_mr_helpers._fracdiff_mr_config_payload()`（calibration_bars=500）；窗長 = `_fracdiff_window_bars(...)`（≥600，與 MR 同款）。G1/G2/修後跑各用獨立輸出路徑、`force_regenerate=True`、獨立空 d* cache。
  (G1) 現行 code 預設（auto→len 耦合，receipt 記錄實際推導 max_lag，不硬編 60）。
  (G2) 現行 code 的計算路徑 + G2-only `FeaturePreprocessor.__init__` wrapper，在 preprocessor 實例的 `fracdiff_config["max_lag"] = 50` 注入。這不是 production config path；使用原因是現行 `FractionalDifferencingConfig` 會丟棄未知 `max_lag`。G2 的語意是「pre-fix calculation-path pin=50 baseline」，不是「config_override pin baseline」。
```

建議在 §G cache 隔離段補：

```markdown
- G2 防呆斷言：所有 d* payload 必須 `max_lag==50`；G2 `fracdiff_hash` 必須不同於 G1；G1 vs G2 fracdiff 欄 digest 必須不同；非 fracdiff 欄 digest 必須相同；patch context 結束後不得污染 G1-repeat/修後 run。任一不滿足即 G2 pin 未生效，Task 0.1 FAIL。
```

建議在 §A 已驗證事實補一條：

```markdown
- `config_override.preprocessing.fractional_differencing.max_lag` 在現行 HEAD 會被 `FactoryConfig.model_validate()` 的 nested `FractionalDifferencingConfig` 丟棄；`FeaturePreprocessor` 收到的 `fractional_differencing` dict 不含 `max_lag`，production config path 無法 pin max_lag。證據：`feature_config.py:183-191,231-245,461-490`；`config_manager.py:90-100`；`feature_factory.py:3673-3686,2745-2747,2625-2639`；runtime probe 輸出 `has_attr_max_lag False` / `model_dump_max_lag <missing>`。
```

建議同步 TODO Task 0.1 驗證欄：

```markdown
- 驗證：兩 receipt 檔存在且載上列欄位；G2 receipt 必載 `pin_method=preprocessor_instance_fracdiff_config_injection`；所有 G2 d* payload `max_lag==50`；G1 vs G2 fracdiff 欄 digest 不同、非 fracdiff 欄 digest 相同；G1 記錄的實際推導 max_lag 落檔（不硬編 60）。
```

## 5. 收尾欄位

ASSUMPTIONS_VERIFIED: 已驗證 `config_override` 經 `ConfigManager.get_merged_config()`/`FactoryConfig.model_validate()` 後 nested `fractional_differencing.max_lag` 被丟棄；已核對 `create_feature_factory` → `generate_features` → `_resolve_config` → `_preprocessing_config_dict` → `FeaturePreprocessor` → read site 行號。
TESTS_RUN: `source venv/bin/activate && python - <<'PY' ...` runtime probe；pass，輸出顯示 `has_attr_max_lag False`、`model_dump_max_lag <missing>`。
FAILURES_SEEN: none
SCOPE_CHANGES: none; only wrote this handoff file
NUMERIC_OR_SCHEMA_IMPACT: none from this read-only analysis; conclusion implies Task 1.2 schema necessity is higher because current config path cannot pin `max_lag`
