# FF-STAT SPEC v35 審查 r16 — CODEX

task-id: 20260926-FFSTATAUTO-X-REVIEW-R16  
family: codex  
brief-kind: review  
標的：`git diff f12e842e bf591b73 -- docs/FFSTAT_SPEC.md`；r15 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r15/synth.md`。本輪唯讀，探針只在 `/tmp/ffstat-r16-copy` 使用真實 `data_cache/feature_klines/kline_cache.h5`，未跑全設定 FF。

## CODEX-R16-P1-01

**斷言**: v35 只在散文中列出 `nan_rate_rule`｜`stable_samples_below_min`，沒有定義 `reasons` 出現第三種字面時必須拒收或輸出 blocked；因此一個有完整 reason、正確 digest、也有 approval 的未授權原因仍可通過目前列出的機械斷言。

**碼證**: `docs/FFSTAT_SPEC.md:77,120` 列出兩個原因並只測「差異欄缺原因」、digest mismatch、非空 delta 缺 approval 與置換不變，沒有 unknown-reason rejection。真實 `BTCUSDT/12h` HDF5 1,696 根之操作序列中，把一個完整 delta 的原因改成 `constant_rule`、依 v35 重新計 sha256 並寫入同一 digest 的 approval，探針輸出 `missing_reason_assertion=false`、`digest_match_assertion=true`、`approval_present_assertion=true`、`unknown_reason_rejection_rule_in_v35=false`。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:120
MUTATION: 以真實 BTCUSDT/12h 之非空欄集合 delta 將任一 `nan_rate_rule` 改為 `constant_rule`，保留每個差異欄都有 reason、重算 v35 digest 並把該 digest 寫入 approval；若現有四項機械斷言仍全通過，第三種原因即未被拒收。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#b4d89450c060; momentum/FeatureEngineering/utils/dead_feature_filter.py#d465c64126cd; scripts/governance_verdicts.json#877d4072399e

修法：在既有 delta 驗證中把 `reasons` 值明確收窄為該兩個字面；任一未知值在 digest／approval gate 前直接拒收並記 blocked，並補一個第三原因必紅的負例。這是收緊既有欄位契約，不新增平行機制。

可行性證據：上述真實資料操作序列已證明目前檢查集合不會因未知值而失敗；membership 檢查只遍歷既有 `reasons`，不改 v35 canonical bytes，且每次執行仍是秒級純資料驗證。故可在現有 delta validation/test 入口加入單一封閉集合判斷。

## CODEX-R16-P2-01

**斷言**: §G⑦ 雖補上 selector 四元組，仍未封閉 `parameter_key` 與所有預設參數軸的實例展開規則；實際預設設定的多軸指標可被展成不同數量的實例，進而得到不同 K-removal list、subset config 與共用 sha256。

**碼證**: `docs/FFSTAT_SPEC.md:84` 只明定 `periods`／`ema_periods`、明示 `combos`、無參數三種形狀，未說明 `BBANDS periods×stddev`、`Keltner ema_periods×atr_multiplier`、`SAREXT acceleration×maximum`、`MA periods×matype`、`STDDEV/VAR periods×nbdev` 的 `parameter_key` 與 Cartesian/非 Cartesian 展開。實作的既有參數盤點 `momentum/FeatureEngineering/config_manager.py:626-702` 明確將這些軸相乘；真實 default config probe 讀得 `STOCH` `[55,8,5]`、`ADOSC` `[21,55]`，而 `ParameterGenerator._combo_list_to_dict("stoch", [55,8,5])` 又解析成含兩個 matype 預設值的 dict，raw bundle 與 resolved bundle 的 digest 分別為 `1b5bcda1a3be26a14b9835104ea1a4a29bc1f52a1c57270e858aac92f4811d0b`、`f44d3611845ddd52b2619decbefe4456be7a016dd978b17b311dd37c9ae202f5`，不相等；HDF5 `BTCUSDT/12h` rows=`1696`。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#b4d89450c060; config/scan_config.yaml#0dc95e4f0a10; momentum/FeatureEngineering/config_manager.py#83186309c248; momentum/FeatureEngineering/atomic/parameter_generator.py#c8ab99f90a45; momentum/FeatureEngineering/feature_config.py#d7e5a9fb2df2

修法：在 selector 契約中列出每個參數軸的封閉 `parameter_key` 與唯一投影：combo 一律使用哪個 raw/resolved 形狀、period 與非 period list 是否取 Cartesian、預設值如何納入、十個 category model 如何展開，以及多輸出 indicator 的依賴閉包。selector、移除清單、subset config 都使用該同一投影後的 canonical object；這是補齊現有實例語法，不改數值或增加生成期檢查。

可行性證據：`config_manager.py:626-702` 已列出並可機械計數所有現有軸，`parameter_generator.py:72-84,116-160` 已有 combo 解析入口；同一真實 config 的 static selector probe 可在不跑 FF 下列出 `676` 個實例、`proxy_fmax=0` 時 `5` 個 K-only removal steps，故缺口是投影契約而非資料或記憶體不可行。

### 必答

1. **(1a)** `CODEX-R15-P1-01` 已閉合：v35 把欄名 UTF-8 byte 排序／去重、換行、delta object、`sort_keys`、`ensure_ascii=False`、compact separators、無結尾換行與置換不變負例都寫入。`CODEX-R15-P2-01` 的「任意子集／tie-break 未定」原始缺口也已由四元組、每步移除全部最大 K、無 recursive 時 blocked 覆蓋；本輪另發現其對實際多軸設定的展開殘留，列為 `CODEX-R16-P2-01`。**(1b)** 以原 P1 反例重跑：真實 1,696 根資料、欄名含非 ASCII、逗號、冒號、引號；鍵／陣列置換後 `same_semantics_bytes_equal=true`、`same_semantics_sha_equal=true`，不同 delta `different_delta_sha_equal=false`。原 P2 條文逐字核對成立，但多軸映射未被同一條文封閉。

2. **(2a)** 有兩個 v35 可重現的 contract 缺口：`CODEX-R16-P1-01` 的未知 reason 可穿過列出的 approval checks；`CODEX-R16-P2-01` 的多軸 selector instance 展開與 `parameter_key` 未唯一化。**(2b)** P1 的可執行 mutation 見該 finding；P2 以真實 default config 的 `BBANDS`／`Keltner` 等多軸盤點與 STOCH raw/resolved 操作序列重現不同實例投影，未跑全設定 FF。

3. **(3a)** §G⑦「12h selector 必終止且終止子集非空並含 recursive」判**不成立為已保證的強命題**：條文只保證每步移除目前最大 K，且明定無 recursive 時輸出 blocked；它沒有保證 survivor。真實資料 probe 的可驗數字為 12h=`1696`，現行 default warmup estimate=`2051`，全設定資格即不足；static K-only proxy（`proxy_fmax=0`）才得到 `instances=676`、`steps=5`、`terminal_remaining=670`、`terminal_recursive_like=210`、`elapsed_ms=0.483`，不能代替每步 A-run 的真實 F_max，因此未把 proxy 當成通過證據。**(3b)** `estimate_max_warmup_bars`／HDF5 probe 輸出 `2051`／`1696`；selector static probe 輸出上述 676／5／670／210；§G⑦ line 84 同時明列 no-recursive ⇒ blocked。

第二條 assumed「v35 bytes framework 使同語意 delta 同 sha 且不同 delta 不碰撞」判**成立**。**(3b)** 真實 HDF5 前置 rows=`1696`；special-name probe canonical bytes 為 `json.dumps(... sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')`，鍵／陣列置換後 bytes／sha 相等，不同 `added` 值 sha 不等。

4. **(4a)** ①未命中為本輪 blocking finding：未跑全設定 FF，static proxy 僅量得 5 個 K-only steps／0.483 ms，沒有可宣稱的 A-run 總耗時；既有條文把它留在驗收 run，不據缺測升級。②命中，對應 `CODEX-R16-P2-01`：MACD／STOCH／ADOSC 的顯式 combo 可取陣列最大值，但 BBANDS、Keltner、SAREXT、MA、STDDEV／VAR 的多軸實例與 `parameter_key` 仍未一義。③命中，對應 `CODEX-R16-P1-01`：第三原因的 digest／approval 處置沒有負例或拒收語義。

**(4b)** ① `probe_selector_steps.py` static output；② `config/scan_config.yaml:80-89,232-247,284-287,300-312`、`momentum/FeatureEngineering/config_manager.py:626-702`、`parameter_generator.py:116-160`；③ `docs/FFSTAT_SPEC.md:77,120` 與 unknown-reason mutation output。

5. **(5a)** 本版不可 `proceed` 定案。**(5b)** 唯一擋定案之 P0/P1：`CODEX-R16-P1-01`。`CODEX-R16-P2-01` 不單獨阻擋，但需在實作 selector 前補唯一展開契約。

ASSUMPTIONS_VERIFIED: 已核對 r15 synth、v35 diff、真實 HDF5 `BTCUSDT/12h` rows=1696；已實跑 v35 canonical delta special-character/permutation probe、unknown-reason mutation probe、default config/ParameterGenerator probe、static selector-step probe；未宣稱 selector A-run 或全設定 FF 已驗證。
TESTS_RUN: `bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → `TEMPLATE PASS` rc=0；`/Users/louis/Desktop/quantitative_trading_system/venv/bin/python probe_selector_contract.py` → rows_12h=1696、enabled_indicators=137；real-kline delta probe → same semantic bytes/sha equal、different delta sha unequal；unknown-reason probe → missing=false、digest_match=true、approval_present=true、unknown rejection rule=false；selector-step probe → instances=676、steps=5、terminal_remaining=670、elapsed_ms=0.483；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r16-codex.md --family codex --round-id 2f57c8ed-2b16-40ee-a55e-a4e0fcd59c04` → `COMPLETENESS PASS(single)` rc=0；git status baseline digest recorded before review=`fd5d5d59a3856032ccd8ce2ba7ab898448064950d07da2093d933fde0febdbbc`。
FAILURES_SEEN: 初次 HDF5 probe 只從 root key 尋找 BTCUSDT/12h，得到 `rows_12h=null`；未改寫驗證指令，修正隔離 probe 以實際 `/BTCUSDT/12h/data` layout 重跑，取得 1696。收尾指定 `rm -rf /tmp/ffstat-r16-copy` 與既有 `/tmp/ffstat_r16_wd` 各自被 PreToolUse／環境 rm-f policy 拒絕，未改寫指令或繞過；`/tmp/claude-501` 未觸碰。未跑 full FF，依 brief 與 8GB 限制。
SCOPE_CHANGES: none；未改 code、SPEC、manifest、templates、CLAUDE.md、git 或 data_cache；只寫本交件與必要狀態交接。
NUMERIC_OR_SCHEMA_IMPACT: 未實作任何數值或 schema 變更；finding 僅要求收窄既有 reason enum 與補齊 selector canonical projection。
TMP_CLEANUP: 已嘗試指定 `rm -rf /tmp/ffstat-r16-copy` 與 `rm -rf /tmp/ffstat_r16_wd`；環境拒絕 rm-f style command，未換寫法；`/tmp/claude-501` 保留。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r16-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R16.md

VERDICT: blocked
BLOCKED-BY: CODEX-R16-P1-01
CLOSED: CODEX-R15-P1-01,CODEX-R15-P2-01
STATUS: DONE
