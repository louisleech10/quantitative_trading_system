FF-STAT SPEC v34 r15 codex review；本輪為唯讀審查，執行依 brief-kind=review。

## CODEX-R15-P1-01

**斷言**: v34 將欄集合 delta 的 sha256 與使用者核可紀錄的 sha256 比對當作機械核可鍵，但沒有定義 delta 的 canonical bytes；同一語意的 delta 只因 JSON key／array 順序不同即可得到不同 digest，因此核可 gate 不具可重現性。

**碼證**: `docs/FFSTAT_SPEC.md:76,119` 只要求 delta sha256、before/after 欄集合、逐欄 reason 與核可紀錄，未定義 UTF-8、key 順序、array 排序、JSON separators 或 newline；`tests/_golden/ffstat/contract.json:40-45` 也沒有 delta serialization contract。實跑 `venv/bin/python` 的純序列化 probe（真實資料前置條件為 `BTCUSDT/12h` 1,696 根）輸出：`default equal_bytes=False equal_sha=False`；同一 probe 加 `sort_keys=True,separators=(',',':')` 輸出 `equal_bytes=True equal_sha=True`。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:119
MUTATION: 對同一真實 BTCUSDT/12h 欄集合 delta 只交換 JSON object key 與 diff row 順序，分別對 raw bytes 算 sha256，再以其中一個 digest 寫入 approval record；未定 canonical bytes 時兩份等價 delta 產生不同 digest，機械比對會拒絕同一語意或依 writer 表示法漂移。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#85cbf4c2b7c1; tests/_golden/ffstat/contract.json#aca54b48eb3c; momentum/FeatureEngineering/preprocessing/calibration.py#31d5e03e39e6

修法：把 delta digest 的輸入固定為一個 canonical byte contract：欄名按 UTF-8 byte 排序且去重，before/after 陣列與 diff 陣列按明確 key 排序，JSON object 使用 `sort_keys=True`、`ensure_ascii=False`、`separators=(',', ':')`，newline 是否存在也明定；空 delta 固定為 `[]`，approval record 使用同一 canonical bytes。可行性證據是上述 probe 已在相同語意的兩個 key 順序上重現 raw hash 不同，並在指定排序與 compact encoding 後重現 bytes/hash 相同；現有 `calibration.py:71-74` 已示範欄名以 UTF-8 byte 排序後 hash 的可行模式。修補前，§G 的使用者核可機械閘不能作為決定性收批依據，故阻擋 v34 定案。

## CODEX-R15-P2-01

**斷言**: v34 的固定 selector 已消除任意挑選子集的方向性問題，但「移除一個指標參數實例」及其 tie-break 的 parameter value 沒有可機械解析的 schema；default `AtomicIndicatorConfig` 同時含 periods、multi-output combos、無參數 recursive/cumulative/pattern 指標，兩個 selector 可產生不同移除清單與 config digest 而都符合目前文字。

**碼證**: `docs/FFSTAT_SPEC.md:83` 只寫「K 最大之一个指標參數實例」與「指標名與參數值字典序」；`momentum/FeatureEngineering/feature_config.py:298-308` 的十個 category model 既含 `CategoryConfig` 也含 microstructure/entropy/tail-risk model。隔離複本以真實 `data_cache/feature_klines/kline_cache.h5` 執行 selector 前置 probe 輸出：`ROWS_12H 1696`、`ATOMIC_CATEGORY_FIELDS 10`、`L1_MAX_K_PROXY 2051`、`ESTIMATE_MAX_WARMUP_12H 2051`、`FULL_CAPACITY_TEST_WITH_F0 False`；default 中可見 `MACD`/`MACDEXT` 的 triple combos，以及 `MAMA`、`SAREXT`、`HT_PHASOR`、`HT_SINE`、`KLINGER_VOLUME_OSC` 等沒有 parameter value 的指標。`warmup_lookup.py:80-84` 的查詢介面也只接受單一 `(indicator, period)`，無法由現行文字自行決定 combo、null parameter 或多輸出閉包。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#85cbf4c2b7c1; momentum/FeatureEngineering/feature_config.py#d7e5a9fb2df2; momentum/FeatureEngineering/atomic/warmup_lookup.py#31d5e03e39e6

可行修法：定義 selector item 的 canonical schema，例如 `(category, indicator, parameter_kind, canonical_parameter_json)`；明確規定 periods/ema_periods 各值、每個 combo、無參數指標的 `null`、cumulative/pattern family 及 multi-output 元件各自是何種 instance，並定義移除一個 instance 時 L2–L6 的依賴閉包與 F_max 重算。最後以 canonical selector input、removal list、subset config bytes 共用 digest。可行性證據是現有十個 model fields 與 default config 已能列出全集，真實切片已能固定 rows/K 前置條件；這是補齊 selector 輸入語法與依賴語意，不需跑全設定 FF 或改數值。此 finding 不單獨阻擋 v34，但未補齊前 12h 收斂對證仍可能因實作者選法不同而不可重現。

### 必答

1. **(1a)** 本家 r14：`CODEX-R14-P1-01` 尚未閉合，但其「SPEC 定案後、實作派工前再同步 manifest」的延後理由成立；`CODEX-R14-P1-02` 已由 v34 §C／Task 2.3 ⑦ 的 delta、reason、approval record 與 digest gate 覆蓋；`CODEX-R14-P2-01` 的原始「任意子集」反例已由固定 selector 取代，但本輪 P2-01 是該 selector 的新可執行性殘留；`CODEX-R14-P2-02` 已由 caller-specific thresholds 與 29/30、99/100 邊界覆蓋。交叉核對之 `COMPOSER-R14-P1-01` 亦已由 Task 2.3 ③ 與 §G② 同步收窄。**(1b)** v34 diff、`docs/FFSTAT_SPEC.md:4,76,83,119` 逐字核對；`docs/manifests/FFSTAT.json:9-15,84` 仍是舊 gate，故 P1-01 的原始 mutation 在實作派工前仍可重現，但不是 v34 新增的缺陷。

2. **(2a)** 有：P1-01 是新的 deterministic contract 缺口；P2-01 是 selector instance／依賴閉包未定義。**(2b)** 以真實 `BTCUSDT/12h` HDF5 slice 讀得 1,696 rows，default 前置計算得 K proxy 2,051；同一 delta 的兩種 JSON key 順序 probe 得 raw sha 不同、canonical sort 後相同。未跑全設定 FF run，亦未把 proxy 宣稱為 selector 完成驗收。

3. **(3a)** selector「必終止且保留 recursive」本輪未能證成，也沒有以受控真實 slice 否證；只確認 default 全設定的 `K=2051` 已使 `2051+0+500 > 1696`，真實 `F_max` 仍須 A run 產生。delta sha256 可重現之 assumed 不成立於現行 SPEC contract。**(3b)** selector probe 輸出 `ROWS_12H=1696`、`L1_MAX_K_PROXY=2051`、`FULL_CAPACITY_TEST_WITH_F0=False`；serialization probe 輸出 `default equal_sha=False`、canonical sort 輸出 `equal_sha=True`。

4. **(4a)** ①命中為 selector contract 的 P2 歧義，沒有足夠證據升為 P0/P1 的非單調反例；②未命中 v34 新文案矛盾：現行 L3 `effective_n` 已是 non-NaN count，與「只計穩定後有限值」在只延長開頭 NaN 的模型下相符，但現行 NaN-rate denominator 尚待實作；③命中為流程風險而非本輪 blocking finding：Task 2.3 ⑦ 定了 approval record 欄位與 digest 比對，沒有定 writer/provenance，實作派工前須明確綁定「已取得使用者核可」事件，不能只由主委自填原話。**(4b)** ① `docs/FFSTAT_SPEC.md:83` 與 `feature_config.py:298-308`；② `momentum/FeatureEngineering/operators/rolling_aggregator.py:820-825` 的 `df.isna().mean()`／`(~df.isna()).sum()` 與 `momentum/FeatureEngineering/utils/dead_feature_filter.py:44-90` 的 `notna().sum()`；③ `docs/FFSTAT_SPEC.md:119` 的 approval record 規定，未見 writer/provenance contract。

5. **(5a)** 否，不能以 `VERDICT: proceed` 定案。**(5b)** 唯一擋定案的 P0/P1 是 `CODEX-R15-P1-01`；P2-01 與 approval writer/provenance 風險須在實作派工前補成可執行 contract，但不另列 blocking ID。

ASSUMPTIONS_VERIFIED: L7 `find_dead_columns` 的 `notna().sum()`／`nunique(dropna=True)` 已由實際檔案核對；真實 HDF5 的 BTCUSDT/12h rows=1696、AtomicIndicatorConfig fields=10、default warmup estimate=2051 已實跑；selector 終止／非空 recursive survivor 未驗證；delta canonical sha256 assumed 已被 serialization probe 否證。
TESTS_RUN: 隔離 `/tmp/ffstat-r15-Vew4HN` 內 `bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → `TEMPLATE PASS` rc=0；真實 HDF5/config/warmup probe → rc=0、上述 rows/K 輸出；serialization mutation probe → raw key permutation `equal_sha=False`、canonical sort `equal_sha=True`；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260926-ffstatauto-x-review-r14/synth.md` → rc=1（review brief 不適用 STAMP-BLOCKED，僅記錄）；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r15-codex.md --family codex --round-id c0f1fd73-81d7-40d8-918f-5335bd8c940d` → `COMPLETENESS PASS(single)` rc=0。
FAILURES_SEEN: `rm -rf /tmp/ffstat-r15-Vew4HN` 被環境 rm-f policy 拒絕；依 brief 未改寫命令或繞過。隔離複本的 pandas HDFStore probe 讀得 0 keys，後以既有 HDF5 layout 的 `h5py` 只讀 probe 重跑並取得真實 rows；一次在無 git metadata 的隔離複本執行 git diff 只得到 usage，未作驗收依據。
SCOPE_CHANGES: none；未改 code、SPEC、manifest、templates、CLAUDE.md、git 或 data_cache；只新增本交件與狀態交接檔。
NUMERIC_OR_SCHEMA_IMPACT: 未實作任何數值或 schema 變更；本輪只指出 delta canonical serialization 與 selector input schema 尚未定義。
TMP_CLEANUP: `/tmp/ffstat-r15-Vew4HN` 保留，因指定 `rm -rf` 被環境拒絕；`/tmp/claude-501` 未觸碰。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r15-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R15.md

VERDICT: blocked
BLOCKED-BY: CODEX-R15-P1-01
CLOSED: CODEX-R14-P1-02,CODEX-R14-P2-01,CODEX-R14-P2-02
STATUS: DONE
