# Reconcile — 20260926-ffstatauto-x-review-r15

**來源** 20260926-ffstatauto-x-review-r15-codex.md, 20260926-ffstatauto-x-review-r15-composer.md　|　**roster** codex,composer

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| delta 雜湊缺逐位元組框架（codex）：v34將欄集合delta的sha256與 | P1 | CODEX-R15-P1-01 | 採納（Task 2.3 ⑦ 定死 canonical bytes：欄集合＝欄名 UTF-8 位元組升序去重、以 `\n` 連接之 UTF-8 位元組；delta＝物件 `{"added":[…],"removed":[…],"reasons":{欄名:原因}}`，陣列依欄名 UTF-8 位元組升序，`json.dumps(delta, sort_keys=True, ensure_ascii=False, separators=(',', ':'))` 之 UTF-8 位元組、無結尾換行；空 delta＝`{"added":[],"removed":[],"reasons":{}}`；核可紀錄存同一 digest；加鍵序與列序置換不變 digest 之負例） | code-contract |
| delta 雜湊缺逐位元組框架（composer）：v34Task2.3⑦／§G①要求欄集合 | P1 | COMPOSER-R15-P1-01 | 採納（同上一列） | code-contract |
| 選擇器實例語法未定：v34的固定selector已消除任意挑 | P2 | CODEX-R15-P2-01 | 採納（§G⑦：實例＝`(category, indicator, parameter_key, canonical_parameter_json)`——清單型參數之每個值、多參數組合之每個組合〔JSON 陣列〕、無參數指標為 `null`；實例 K＝倍數表以該實例最大週期查得之值，無參數者取表內登記值；每步移除全部 K 等於當前最大值之實例〔免 tie-break〕，其衍生之 L2–L6 欄隨設定消失；F_max_tf 每步以 A run 實測；終止時若不含任何 recursive 實例 ⇒ blocked 收據；選擇器輸入全集、移除清單與子集設定位元組共用一 sha256） | code-contract |

**核可紀錄寫入者（兩家必答 4 皆列程序風險、未立 ID）**：v35 於 Task 2.3 ⑦ 明寫誠實邊界——核可紀錄由主委於使用者以阻塞式提問作答後寫入，記使用者逐字原話、session id 與提問之 delta digest；機器只能驗 digest 一致，無法驗原話真偽，以原話與 session 供稽核。

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R15-P1-01

**斷言**: v34 Task 2.3 ⑦／§G ① 要求欄集合與 delta 之 sha256 機械比對，但未定義與 v13 `calibration_source_sha256` 同級之逐位元組框架（欄名排序、diff 陣列序、JSON 鍵序、UTF-8）；同一語意 delta 兩次序列化可得不同 digest，核可 gate 與 CODEX-R14-P1-02 修法在 SPEC 層仍不可重現。

**碼證**: `docs/FFSTAT_SPEC.md:119` ⑦ 只寫「改前與改後欄集合之 sha256…及 delta 之 sha256」，未釘死序列化；對照 `tests/_golden/ffstat/contract.json:40-45` 對校準域有 `calibration_source_sha256` 鍵但無 column-set-delta 欄位定義。`/tmp/ffstat_r15_wd/probe_r15.py`（repo 根執行）→ `DELTA_SHA {"unsorted_keys_differ": true, "sort_keys_stable": true, "spec_defines_sort_keys": false}`：同一 before/after/diff 物件，`json.dumps` 鍵序不同則 sha256 不同，`sort_keys=True` 才穩定。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:119
MUTATION: 對同一組欄集合 delta 先以 `{"before":[...],"after":[...],"diff":[...]}` 寫收據算 sha256，再以鍵序 `diff,after,before` 重寫同一內容算 sha256；若測試只比對「本次收據內自算 digest」而 SPEC 未定框架，兩份收據可一過一紅或雙過但 digest 不一致，機械核可失效。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#85cbf4c2b7c1; tests/_golden/ffstat/contract.json#aca54b48eb3c; handoffs/reconcile/20260926-ffstatauto-x-review-r14/synth.md#1ad38ffc4589

**修法**: 在 Task 2.3 ⑦ 或 `contract.json` 增 column-set-delta 位元組契約（建議：欄名 UTF-8 升序後以 `\n` 連接再 sha256；diff 陣列依 `col` 升序；整份收據 `json.dumps(..., sort_keys=True, separators=(',',':'), ensure_ascii=False)` 後 sha256），並在測試加「鍵序 permute 不變 digest」負例。可行性：`calibration_source_sha256` 已有逐位元組先例；probe 已證 `sort_keys=True` 可消除鍵序漂移；不需全 FF run、秒級單測可覆蓋。

---

