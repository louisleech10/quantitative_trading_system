# FF-STAT SPEC v36 審查 r17 — CODEX

task-id: 20260926-FFSTATAUTO-X-REVIEW-R17  
family: codex  
brief-kind: review  
標的：`git diff bf591b73 3130de9b -- docs/FFSTAT_SPEC.md`；r16 reconcile `handoffs/reconcile/20260926-ffstatauto-x-review-r16/synth.md`。本輪唯讀；探針只在 `/tmp/ffstat_r17_work.JhZCov` 使用真實 `data_cache/feature_klines/kline_cache.h5`，未跑全設定 FF。

## CODEX-R17-P1-01

**斷言**: v36 把固定選擇器的實例數×輸出欄數鎖到 `ConfigManager._estimate_indicator_params`，但目前 L1 生成路徑沒有同樣的多軸展開；因此 default config 的 selector 不是必然驗得過，就是會把未實際生成的欄納入移除計算，無法形成可收斂且可重現的 subset。

**碼證**: `docs/FFSTAT_SPEC.md:85` 要求以 L1 實際展開為單一來源、並斷言總數等於 `_estimate_indicator_params`。`momentum/FeatureEngineering/config_manager.py:626-702` 卻將 `stddev`、`nbdev`、`matype`、`acceleration×maximum` 與 `ema_periods×atr_multiplier` 相乘；`momentum/FeatureEngineering/atomic/trend_indicators.py:110-147` 只展開 `params`／`combos`／`periods`，`momentum/FeatureEngineering/atomic/volatility_indicators.py:27-56,155-184` 對自訂 Keltner 等路徑另行固定計算。真實 `/BTCUSDT/12h/data`（全長 1,696 根；探針切片 128 根）之 default config probe rc=0：BBANDS `resolved_output_count=24` 對 `estimate_indicator_params=120`、STDDEV `11` 對 `22`、VAR `11` 對 `22`、MA `9` 對 `45`、SAR/SAREXT 各 `1` 對 `9`、Keltner `0` 對 `36`、ADOSC `1` 對 `9`；這些是 source multiplicity 之前的參數／輸出投影差異。
CODE-ANCHOR: momentum/FeatureEngineering/config_manager.py:693
MUTATION: 在真實 BTCUSDT/12h default config 保留 BBANDS 的 periods 與 stddev 軸，讓 selector 依現行 L1 `_resolve_params` 只產生 periods×3 欄，卻依 `_estimate_indicator_params` 記錄 periods×stddev×3；若仍產生通過收據，便證明等式沒有檢出生成／估算漂移。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#e99f34daf19a; momentum/FeatureEngineering/config_manager.py#83186309c248; momentum/FeatureEngineering/atomic/trend_indicators.py#da5496d9968a; momentum/FeatureEngineering/atomic/volatility_indicators.py#1c29d88164df; momentum/FeatureEngineering/atomic/parameter_generator.py#c8ab99f90a45

修法：把參數展開、輸出欄數與 custom-derived indicator 的投影收斂成一個無副作用 canonical expansion function；L1 七類 engine、固定選擇器與 `_estimate_indicator_params` 都只消費這個 projection。projection 必須明列 Cartesian 軸、combo 預設值、輸出數與 source 依賴；不能只把目前不一致的兩個計數相加。若依 v36 的 BBANDS／Keltner 等軸真正擴大 L1 生成，欄數與輸出大小會改變，須在實作前明確核准；若要保持現有 schema，則 canonical projection 必須反映現有生成欄並同步調整 estimator，不能靜默混用兩套語義。

可行性證據：`ParameterGenerator.generate_combos` 已在 `momentum/FeatureEngineering/atomic/parameter_generator.py:72-84,116-237` 提供無資料的 combo 解析，`TALibWrapper.compute_batch` 已提供輸出名與 batch 邊界；本輪在真實 128 根切片上以同一 default config 實跑 projection probe，已得到上述可反駁的 per-indicator 差異，故可以先以純函式單測逐指標相等，再接入 selector，不需要 full FF 或合成資料。

## CODEX-R17-P2-01

**斷言**: v36 的「倍數表登記之週期型鍵取最大值」仍未封閉每個 combo／特殊指標的鍵映射；現行表只有 ULTOSC 的一般條目，ADOSC 是 cumulative special case，且找不到 STOCH 條目，因此同一 canonical parameter dict 仍不能從規格與現行表唯一推出 K。

**碼證**: `docs/FFSTAT_SPEC.md:85` 只引用「倍數表登記之週期型鍵」，沒有給出封閉的 indicator→key projection。`momentum/FeatureEngineering/atomic/parameter_generator.py:133-160` 將 STOCH 解析為 `fastk_period`、`slowk_period`、`slowd_period` 及兩個 matype；`:227-232` 將 ULTOSC 解析為三個 `timeperiod` 鍵。現行 `momentum/FeatureEngineering/atomic/warmup_table.yaml:340-348` 有 ULTOSC，`:367-381` 將 ADOSC 列為 cumulative-diff-EMA special case，沒有 STOCH 條目。真實 12h static selector probe rc=0 回報 `rows_12h=1696`、`enabled_definition_count=137`、`resolved_instance_count=649`；以目前表與 K proxy 走到 `static_steps=131`、`terminal_remaining=0`、`terminal_recursive=0`，且 `missing_warmup_table_indicators` 包含 STOCH。這是 selector 的 fail-closed／K 投影缺口，非 full A-run 結果。
CODE-ANCHOR: momentum/FeatureEngineering/atomic/parameter_generator.py:133
MUTATION: 將同一 STOCH combo 的 `fastk_period`、`slowk_period`、`slowd_period` 任一值替換，若沒有明確的 STOCH 表條目與鍵映射而仍可計出相同且可核准的 K-removal receipt，即表示 K projection 未封閉。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#e99f34daf19a; momentum/FeatureEngineering/atomic/warmup_table.yaml#d1fbdeae67c8; momentum/FeatureEngineering/atomic/parameter_generator.py#c8ab99f90a45; momentum/FeatureEngineering/config_manager.py#83186309c248

修法：在同一 canonical projection 中為每個啟用 indicator 封閉週期鍵集合與 special-case 規則；至少明確記錄 STOCH 三個 period 鍵的 max、ULTOSC 三個 period 鍵的 max、ADOSC 的 cumulative burn-in／slow-period 規則。缺條目或鍵集合不完整時，在計算 K 前直接輸出 blocked receipt，不產生部分移除清單；這也要與 §G 的倍數表完整性 fail-closed 共用同一投影。

可行性證據：現有 `ParameterGenerator` 已產生上述 resolved dict，`warmup_table.yaml` 已能分辨 ULTOSC 與 ADOSC 兩類；本輪 static probe 已在真實 HDF5 layout 上實際列出缺表集合與 terminal blocked 狀態，補成封閉 mapping 可由現有純資料輸入驗證，不需要改變數值計算。

**必答**

1. **(1a)** `CODEX-R16-P1-01` 已閉合：v36 `docs/FFSTAT_SPEC.md:78` 將 `reasons` 收窄為 `nan_rate_rule`／`stable_samples_below_min`，並要求未知值在 digest／approval 前拒收；原 r16 的 `constant_rule` 反例不再符合契約。`CODEX-R16-P2-01` 只部分閉合：v36 已補 resolved dict、Cartesian 軸、combo defaults、canonical key 與 estimator equality，但本輪 P1 的實跑仍證明現行 L1 path 尚未共享同一展開投影，K mapping 亦留在本輪 P2。
2. **(1b)** r16 P1 以文字核對即可重播：保留完整 delta、digest 與 approval，只把 reason 改成未列舉字面，會在 v36 的 closed enum gate 前拒收；未再重開 R1–R7。r16 P2 的原始「參數軸與 parameter_key 未唯一化」已補文字，但現行 default config 的 BBANDS／MA／Keltner／SAR 等 per-indicator count 差異，使其不能宣稱完全閉合。
3. **(2a)** 本輪新增 `CODEX-R17-P1-01`（生成投影與 estimator 對證不可通過）及 `CODEX-R17-P2-01`（週期鍵到 K 的映射未封閉）。兩者都由 v36 新增的 §G⑦ 條款與現行生成／warmup 表的交界暴露；沒有把既有 R1–R7 裁定重新列為 finding。
4. **(2b)** 可重現序列是：載入真實 `/BTCUSDT/12h/data` 的 1,696 根 → 取前 128 根與 default merged config → 依各 L1 engine 現行 resolve／output path 計數 → 對照 `_estimate_indicator_params`；probe rc=0 且得到 BBANDS 24/120、STDDEV 11/22、MA 9/45、Keltner 0/36。另一個 selector probe 只做 static K proxy，得到 131 步後 terminal empty；依 brief 未跑 full FF 或新的 minute/hour generation check。
5. **(3a)** 「selector 必終止且終止子集非空」不是已保證的 compound assumption：有限實例集合在每步移除當前最大 K，故 removal 過程可終止；但 v36 自己規定 terminal 無 recursive 時輸出 blocked，並未保證 survivor 非空。真實資料為 1,696 根；本輪 proxy 的 `initial_max_k=2051`、`static_steps=131`、`terminal_remaining=0`、`terminal_recursive=0` 只能證明目前表／projection 組合會觸發 fail-closed，不能冒充 A-run。
6. **(3b)** 「L1 parameter expansion 與 estimator 純函式相等」為假：真實切片結果已列於 P1；差異發生在 source multiplicity 之前。因而 v36 的 equality acceptance 目前不能通過，這是 P1，而不是用 proxy 結果推導出的額外 P0。
7. **(4a)** ①未命中本輪 blocking finding：未量 default full-config 的每步 A-run `F_max` 總步數／秒數；§G⑦ 的 full acceptance run 仍受 brief 的 stop discipline 豁免，不能據未測量升級。②命中本輪 P2：STOCH 無表條目、ADOSC 為 special case、ULTOSC 未明列 key projection。③命中本輪 P1：per-indicator resolved expansion 與 `_estimate_indicator_params` 不一致。
8. **(4b)** ①由本輪未執行 full A-run 的紀錄支持；②由 `warmup_table.yaml:340-381`、`parameter_generator.py:133-160,227-232` 與 selector probe output 支持；③由 `config_manager.py:626-702`、trend／volatility resolve code 與 real-kline projection probe output 支持。
9. **(5a)** 本版不能 `proceed`。
10. **(5b)** 唯一阻擋裁決的 P0/P1 是 `CODEX-R17-P1-01`；`CODEX-R17-P2-01` 不單獨阻擋，但在 selector 實作前需補齊。

ASSUMPTIONS_VERIFIED: 已核對 HANDOFF、CLAUDE、r17 brief、r16 reconcile、R1–R7 ruling、v36 diff；已讀真實 `/BTCUSDT/12h/data` rows=1696；已實跑 default L1 expansion probe、static selector probe、spec template check；未宣稱 full FF、A-run F_max 或新的 minute/hour generation check 已驗證。
TESTS_RUN: `bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → `TEMPLATE PASS` rc=0；`cd /tmp/ffstat_r17_work.JhZCov && PYTHONPATH=. /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe_r17.py > /tmp/ffstat_r17_probe_v5.out 2>&1` → rc=0，rows_full=1696、rows_probe=128，輸出 P1 所列差異；`cd /tmp/ffstat_r17_work.JhZCov && PYTHONPATH=. /Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe_selector_r17.py > /tmp/ffstat_r17_selector.out 2>&1` → rc=0，enabled_definition_count=137、initial_max_k=2051、static_steps=131、terminal_remaining=0、terminal_recursive=0；`git status --short -- momentum api scripts tests docs templates config` → 與 review 前 baseline 相同；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r17-codex.md --family codex --round-id 11260afc-9ffe-47ee-9842-a14d274903b7` → `COMPLETENESS PASS(single)` rc=0。
FAILURES_SEEN: 初版隔離 probe 因把 Keltner 當成 TALib 參數指標、又假設 pattern engine 有 `_resolve_params` 而 rc≠0；未改 repository，調整 probe 對 custom-derived／pattern path 的處理後 v5 rc=0。收尾明確 `rm -rf`／`rm -f` 命令被環境安全政策拒絕，未改寫成替代清理形式；`claude-501` 維持存在。未遇其他 PreToolUse hook block。
SCOPE_CHANGES: none；未改 code、SPEC、manifest、templates、CLAUDE.md、git 或 `data_cache/`；只新增本輪交件檔，並將狀態追加到既有 r17 status handoff。
NUMERIC_OR_SCHEMA_IMPACT: 本輪沒有實作數值或 schema 變更；P1 修法若讓多軸真正進入 L1，欄數／輸出大小可能改變，交件只標記此風險，未擅自選邊或改動。
TMP_CLEANUP: 已嘗試移除本輪明確建立的 `/tmp/ffstat_r17_work.JhZCov` 與 `/tmp/ffstat_r17_*` output，但環境拒絕 `rm -rf`／`rm -f` style command；未改寫指令，故這些暫存仍在。`/tmp/claude-501` 已確認存在且未觸碰。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r17-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R17.md

VERDICT: blocked
BLOCKED-BY: CODEX-R17-P1-01
CLOSED: CODEX-R16-P1-01
STATUS: DONE
