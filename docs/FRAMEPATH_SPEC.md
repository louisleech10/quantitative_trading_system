# FRAMEPATH — 刪除非 CGSA 舊引擎（frame）與舊特徵 h5 讀寫鏈 — SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260928-framepath-x-consult-r1/synth.md`（去留查證）、`handoffs/reconcile/20260928-framepath-x-consult-r2/synth.md`（偵察）　|　日期：2026-10-08　|　對應 TODO：docs/manifests/FRAMEPATH.json（SPEC 凍結後生成）
> 版本：v15（審查 r14 修補，基準 HEAD 6e07e0ad）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（全票排序第 5 步，`docs/TICKET_ORDER.md`）。
- **命中高風險原則**：(a) 刪除位於 Feature Factory 正式生成之共用函式內之分支，誤刪即改變 CGSA 輸出；(b) 跨 momentum／api／scripts／tests／frontend；(c) 四 Phase、刪除碼難以事後由行為察覺；(d) 特徵為 IC／ML 之上游。
- RISK-HIT: a,b,c,d
- 屬 CLAUDE.md「行為不變型重構」：CGSA 輸出於 §G 比對域內改前／改後須逐位元一致；適用三方數據正確性簽核鐵律（Claude＋`scripts/governance_families.json` 之 `active_stampers`）。

## §A 假設與待使用者確認
- **已驗證事實**（7 條 FACT-RECEIPT）：
  - FACT-RECEIPT: `grep -rn "_cgsa_enabled" momentum api scripts | grep -v __pycache__` → 印出定義 2（`feature_factory.py:1200`、`multi_tf_generator.py:1916`）、呼叫 11（feature_factory.py:555,1234,2084,2171,2895,3389,4468,4880；multi_tf_generator.py:95,1874,1895）（主委 實跑 2026-10-08）
  - FACT-RECEIPT: `grep -rl FFACT_USE_CGSA tests | wc -l` → 印出 `31`；`grep -rl FFACT_USE_CGSA api frontend/src run_api.py config` → 印出空（主委 實跑 2026-10-08；codex、grok 獨立重跑同值）
  - FACT-RECEIPT: `find . -name "*_factory.h5" -not -path "./.git/*" | wc -l` → 印出 `0`；`grep -o '"hdf5_relative_path": "[^"]*"' data_cache/features/registry.json | sed 's/.*\.//' | sort | uniq -c` → 印出 `11 ""`、`29 json"`（主委 實跑 2026-10-08）
  - FACT-RECEIPT: `grep -rn "save_factory_output" momentum api scripts | grep -v __pycache__` → 印出定義 `feature_storage.py:2420` 與唯一呼叫 `feature_factory.py:4595`（frame L7 分支內）（主委 實跑 2026-10-08）⇒ CGSA 從不寫 `*_factory.h5`，`_try_load_cache`（:4687，首步讀 `load_factory_output`）對 CGSA 恆不命中。
  - FACT-RECEIPT: `grep -rn "_load_features_df" api momentum | grep -v "def _load_features_df"` → 印出空（主委 實跑 2026-10-08）⇒ `FeatureBrowserService._load_features_df` 之 `.h5` 分支生產零呼叫者。
  - FACT-RECEIPT: 兩次同設定 CGSA 生成（`tests/feature_engineering/ffstat_helpers.stat_payload` 單週期）→ `base_fingerprints` 3632/3632 欄值 hash 全等、manifest 檔 bytes 不等（composer 實跑 2026-10-08，見偵察 r2 synth）
  - FACT-RECEIPT: `grep -n "FFACT_USE_CGSA" momentum/FeatureEngineering/memory_budget.py` → 印出 `178:    "FFACT_USE_CGSA",` 屬 `NON_ARM_FFACT_KEYS`；`_compute_config_hash` 不讀環境變數（主委 實跑 2026-10-08）⇒ 刪該鍵不改 config hash。
- **待使用者確認**：待確認：無
- **已確認結果**：2026-09-28 使用者裁定刪除 frame 產生路徑與舊特徵 h5 讀取、不再花時間在 frame 測試（逐字：「若是frame都不需要，那不就不要花時間在任何跟frame有關的部份和測試上？」「舊的h5什麼的也可以刪除，這樣可以專注在把現行的模組做好吧？」）；2026-10-02 使用者定案全票排序（FRAMEPATH＝第 5 步，FF-NAME＝第 6 步）。

## §C 約束
- 解耦 7 條；不弱化 NaN／inf gate、不擅改 CGSA 輸出大小；`kline_cache.h5`、`data_cache/hdf5_cache/`、IC 服務內部 h5、IC `*_filtered.h5` 匯出、case 特徵 h5（`FeatureStorage.load_features_from_hdf5`／`save_features_to_hdf5`）**不在本票**；不得以副檔名全域禁止 h5。
- `hdf5_path`／`hdf5_relative_path` 欄名不改（CGSA 下承載 manifest `.json` 路徑；改名屬跨棧 DTO，不在本票）。
- 驗收母體不得含 frame 臂（`FFACT_USE_CGSA=0`、canonical legacy-*、batch2d frame 對照）。
- 本機 8 GB：真實資料重測試一律單組串行；委員審碼期間不跑重型生成；禁跑多週期全史生成。
- 不新增 manifest 快取命中行為（見 §N）；不改欄名、不加命名世代鹽（屬 FF-NAME）。
- 共用路徑注意：`FeatureFactory._combine_layers` 現行呼叫之 context 字面共六種（主委 `grep -o 'context="[a-z0-9_]*"'` 於 feature_factory.py／multi_tf_generator.py，2026-10-08）：`layer3_input`（feature_factory.py:2063）、`layer4_input`（:2180、:2182）為 CGSA 所用，保留；`layer6_5_input`（:572）、`layer7_final`（:4484）、`multi_tf_layers`（multi_tf_generator.py:1532）、`multi_tf_legacy_merged`（:1584）皆在 frame 碼內，刪 frame 後零呼叫者；`_combine_layers` 改為 context 白名單（`layer3_input`、`layer4_input`），其餘一律具名拒絕，守住「CGSA 不做全欄合併」。L3 `feature_factory.py:2084` 之串流條件改寫後，其後非串流分支（:2126 起）保留給 `in_memory` 級距；`feature_naming.tag_timeframe`、`FeatureFactory._timeframe_tagged_name` 服務 CGSA，保留；L3 `persist_mode == "in_memory"` 之非串流分支為 CGSA in_memory 級距所用，保留。

## §G Golden / Baseline
- **feature/kline 條件**：真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture；三方數據正確性簽核。
- **凍結時機**：Phase 1 任何生產碼改動之前，於 HEAD 6e07e0ad 以 `scripts/freeze_framepath_baseline.py`（新）凍結至 `tests/_golden/framepath/cgsa_fingerprint.json`；manifest 排除鍵清單唯一來源＝`tests/_golden/framepath/compare_domain.json`（新），與處置表同於 TODO 階段凍結、sha256 入 manifest；排除鍵只准時間戳、計時、絕對路徑、暫存 uuid 類非語意鍵，驗證器拒絕排除 `run_status`、`quality_status`、`failure_reasons`、`feature_names`／欄名序列、`config_hash` 與 `COMPLETENESS_FIELD_NAMES` 任一欄。
- **記憶體**：唯一指標＝phys_footprint 行程樹峰值；唯一取樣來源＝`momentum/FeatureEngineering/memory_guard.py` 之 `_Readings`（根＝該格生成行程，逐成員 footprint、(pid,start) 去重、同一時刻加總、讀不到之存活成員列入 `failed`），間隔 0.1 秒、自該格開始至結束；凍結與比對入口見 `ICFA_GUARD_READINGS_FILE`（`memory_guard.READINGS_ENV`，守護單元測試之注入接縫）已設即具名拒跑，收據每筆讀數記 `injected`；每格峰值 < 2 GB；任一讀數 `failed` 非空、`injected` 為真、無讀數、或峰值 ≥ 2 GB ⇒ 該格 FAIL（凍結與改後皆驗）；C6 須至少一筆讀數之成員含根以外行程（證明平行 worker 被取樣），否則 FAIL；收據記峰值、讀數筆數與秒數。量測語意與正式記憶體守護同一取樣器，本閘用途＝確認測試格規模，不作輸出正確性判準。
- **設定矩陣**（`stat_payload` 級精簡指標、短窗）：C1 單週期平穩化開；C2 單週期平穩化關；C3 多週期主週期＋一個較長次週期（`FFACT_MULTI_TF_PARALLEL=0`）平穩化開；C4＝C1 於 `FFACT_L3_PERSIST_MODE` 之 streaming 與 hybrid 各一；C5＝C1 同 work dir 第二次生成（resume 命中）；C6＝C3 同參數但 `FFACT_MULTI_TF_PARALLEL=1`；C7＝C1＋`persist=False`；C8＝C1＋`FFACT_L3_PERSIST_MODE=in_memory`；C9＝C3＋`allow_partial_timeframes=True`，於真實 kline 副本刪除 `<symbol>/<次週期>` 之 data dataset、刪後讀回確認缺失，並於該格子行程啟動前（kline storage 建構前）在其環境將 `LEGACY_KLINE_CACHE_DIR` 指向空之受控目錄防止補回 ⇒ 該次週期缺載、`run_status=partial`；收據記有效 legacy 目錄與刪後讀回結果（兩者為本格前置條件，不成立 ⇒ 拒跑）；比對域＝`run_status`、`quality_status`、`failure_reasons`、`skipped_timeframes` 與 `momentum/FeatureEngineering/feature_storage.py` 之 `COMPLETENESS_FIELD_NAMES` 所列全部欄（於結果 metadata 與 manifest 兩處皆比），加上其餘週期之指紋。週期取值由 `stat_payload` 參數給定，不寫死於比對器。
- **baseline 內容**：每格之公開輸出欄名序列 sha256、欄數、列數、時間索引 sha256；逐欄 NaN／inf mask sha256 與 float32 值位元 sha256（沿用 `ffstat_helpers.base_fingerprints`／`public_fingerprints` 之 parquet 枝）；平穩化決策表 sha256；manifest 經 `compare_domain.json` 篩選後之 canonical JSON sha256；run_status、各週期 completeness 與失敗／降級原因；生成路徑收據（L3 落地模式、多週期 serial／parallel、L6.5 CGSA 臂）。C7 無落盤 parquet 者以回傳結果與 completeness metadata 為比對對象。
- **通過條件**：改後同設定重跑，上列每項逐項相等（無容差：同碼路徑、同資料、已實測可重現）；任一不等 ⇒ 列出設定格、欄名、項目 ＝ FAIL。

## §P Phase 與依賴

### Phase 1 — 刪 frame 產生路徑（依賴：無；Task 1.1 先於 1.2–1.5）

**Task 1.1 — 凍結 CGSA 指紋基準**
- 目標：改前凍結 §G 基準與比對器。　檔案：`scripts/freeze_framepath_baseline.py`（新）、`tests/_golden/framepath/cgsa_fingerprint.json`（新）、`tests/_golden/framepath/compare_domain.json`（新）、`tests/feature_engineering/test_framepath_invariance.py`（新）　既有 caller：新建無 caller。
- 改法：凍結腳本於 HEAD 6e07e0ad 跑 C1–C9 並寫 JSON（含 `head_commit`、每格 phys_footprint 行程樹峰值、讀數筆數與秒數）；測試以同設定重跑並逐項比對；`compare_domain.json` 列 manifest 排除鍵（時間戳、計時、絕對路徑、暫存 uuid）之封閉集合，未列者一律納入比對。
- **驗證**：`pytest tests/feature_engineering/test_framepath_invariance.py` 於 HEAD 綠；mutation（暫存工作樹，不提交）：M1 `feature_naming.tag_timeframe` 少標一週期、M2 `_combine_layers` 對 `layer4_input` 回傳空表、M3 L7 落盤前改 float64、M4 manifest 新增未登記鍵 ⇒ 各自紅，收據 `handoffs/run_receipts/<date>-framepath-b1-mutation.txt`。
- **邊界**：C5 resume 與 C1 之 fingerprint 相等；C1–C8 任一格 `run_status` 非 complete、或 C9 之 `run_status` 非 partial 或其 skipped／failed 週期不含該次週期 ⇒ 凍結腳本拒寫並具名報錯；任一格記憶體 FAIL ⇒ 拒寫。
- **存活至**：收案後保留（作為 FF-NAME 前之 CGSA 不變基準；FF-NAME 改名時依其 SPEC 重凍）。
- **覆蓋風險**：無。
- 不可做：不得把 frame 臂列入任何格；不得以容差替代逐位元；不得在比對器內硬寫週期或標的。

**Task 1.2 — 單週期與 L3／L4／L6.5／L7 分派改為唯一 CGSA**
- 目標：刪環境分派與單週期 frame 尾段。　檔案：`momentum/FeatureEngineering/feature_factory.py`（`_cgsa_enabled` 定義與其 8 呼叫點、`generate_features` 單週期尾段 :569–597、`_layer6_5_preprocessing` 之記憶體分支 :3413–3420、`_layer7_validate_and_persist` 非 CGSA 體 :4484–4617、`_combine_layers` 之環境判斷、`_prepare_cgsa_registry` 之環境早退、`run_ic_first` :2895–2898 之環境守衛）　既有 caller：`generate_features`、`MultiTFGenerator`、`run_ic_first`、API 生成服務。
- 改法：分派點一律走 CGSA；`self._cgsa_registry is None` 之處改為拋具名例外（新類別，定義於 feature_factory.py，訊息含 symbol／timeframe／呼叫點）；`_combine_layers` 改 context 白名單（`layer3_input`、`layer4_input`），白名單外一律拋同一具名例外；L3 串流條件改為 `persist_mode in {"streaming","hybrid"}`，其後非串流分支原樣保留給 `in_memory`；`FFACT_USE_CGSA` 於生產碼零讀取；同批整檔刪除 `scripts/fix_spec_v1_to_v1_1.py`（歷史 SPEC 改寫腳本，非生成路徑，內含兩處無 context 之 `_combine_layers` 呼叫）。
- **驗證**：Task 1.1 不變測試綠；新測 `tests/feature_engineering/test_framepath_cgsa_only.py`：registry 為 None 呼叫 L3／L6.5／L7 分派點各拋具名例外；`_combine_layers` 對白名單外之六種以上 context 字面（含 `layer6_5_input`、`layer7_final`、`multi_tf_layers`、`multi_tf_legacy_merged`、任意字串）拋具名例外、兩白名單照常 concat；AST 掃描 momentum／api／scripts 全部 `_combine_layers(` 呼叫之 context 字面 ⊆ 白名單（非字面引數亦判 FAIL）；設 `FFACT_USE_CGSA=0` 之生成仍產 CGSA manifest 且無 `*_factory.h5`。
  `ASSERT pytest tests/feature_engineering/test_framepath_cgsa_only.py WHEN state=after THEN rc=0`
  mutation：把任一分派點之具名例外改回 `pass`／舊分支 ⇒ 該測紅。
- **邊界**：`FFACT_USE_CGSA=0` 殘留於使用者環境 ⇒ 無作用（不報錯、不分派）；`persist=False` 生成 ⇒ 走 CGSA raw pipeline 且 completeness 照寫。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不得保留「registry 為 None 時之記憶體後備」；不得改 CGSA 分支內任何計算。

**Task 1.3 — 刪多週期 legacy 組裝與 frame 列對應**
- 目標：`generate_multi_tf` 唯一進入 `_generate_multi_tf_cgsa`。　檔案：`momentum/FeatureEngineering/timeframe/multi_tf_generator.py`（`_cgsa_enabled`、`_generate_multi_tf_legacy` 與其專用 helpers（含 `multi_tf_layers`／`multi_tf_legacy_merged` 兩處 `_combine_layers` 呼叫）、`MultiTFGenerator._combine_layers`（:1873，repo 內零呼叫者）、`_apply_timeframe_tag` 之 registry 為 None 側）、`feature_factory.py:391–404`（`_legacy_native_row_maps`）、`momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:226`（`set_no_start_calibration` 之 `native_maps` 參數與 `_no_start_native_maps` 之消費邏輯）　既有 caller：`FeatureFactory.generate_features`（多週期）、`_attach_calibration`。
- 改法：刪除上列；`set_no_start_calibration()` 改無參數；其消費端刪 row-map 分支（CGSA 原生子實例路徑不變）。
- **驗證**：Task 1.1 C3、C6、C9 綠；`grep -rn "_legacy_native_row_maps\|_generate_multi_tf_legacy\|_no_start_native_maps\|multi_tf_legacy_merged\|multi_tf_layers" momentum` → 0。
- **邊界**：多週期 parallel 與 serial（`FFACT_MULTI_TF_PARALLEL`）皆經 CGSA；次週期資料不足之既有 partial 語意不變（既有 `tests/test_cgsa_multi_tf.py` 之 missing lower TF 測試綠）。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不得統一或改寫週期標記規則（屬 FF-NAME）。

**Task 1.4 — 死碼掃除**
- 目標：Task 1.2／1.3 後零呼叫者之函式一併刪除。　檔案：`feature_factory.py`、`multi_tf_generator.py`、`feature_preprocessor.py`。
- 改法：以 AST 掃描列出三檔內之 def 與其 repo 內（momentum／api／scripts／tests）引用數，零引用且非公開入口者刪除；結果寫收據 `handoffs/run_receipts/<date>-framepath-dead-scan.txt`（前／後兩份）。
- **驗證**：後掃描收據 `handoffs/run_receipts/<date>-framepath-dead-scan.txt` 之「零引用且未具名保留」計數 == 0；具名保留項每項附理由；mutation：於暫存工作樹加回一個零引用 def ⇒ 計數 == 1。
- **邊界**：只被已刪測試引用者視為零引用；被保留之 CGSA 測試引用者保留。
- **存活至**：收案後保留。
- **覆蓋風險**：Phase 2 會刪 `feature_storage.py` 寫讀端；本 Task 不碰 `save_factory_output`／`load_factory_output`（屬 Task 2.1）。
- 不可做：不得刪 CGSA 仍呼叫者；不得順手重構。

**Task 1.5 — 治理清單與測試遷移（產生路徑）**
- 目標：刪 frame 產生後之測試同批遷移，Phase 1 結束時受影響測試全綠。　檔案：`momentum/FeatureEngineering/memory_budget.py:178`（刪 `FFACT_USE_CGSA` 列）、`tests/feature_engineering/test_icfirstalign_memory.py`（掃描對齊）、受影響測試檔（處置表＝`tests/_golden/framepath/test_disposition.json`，新）、`tests/_golden/prered/allowed_red.json`（FRAMEPATH 列與 EXPECTED）、`tests/_golden/ffstat/nan_propagation_classes.json`（`_generate_multi_tf_legacy` 條目）。
- 改法：**處置表於 TODO 階段凍結**——TODO 起草時於 HEAD 6e07e0ad 產出 `tests/_golden/framepath/test_disposition.json`，作為 TODO manifest 之契約 JSON，與 TODO 一同經三家審查與戳記，其 sha256 記入 manifest；實作期不得增改（需增改 ⇒ 回 TODO 重審）。內容涵蓋 Phase 1–3 全部受影響檔：受影響檔母體＝HEAD 中含 `FFACT_USE_CGSA`、`_cgsa_enabled`、`_generate_multi_tf_legacy`、`_legacy_native_row_maps`、`load_factory_output`、`save_factory_output`、`_factory.h5`、`_factory_meta.json`、`_try_load_cache`、`_load_hdf5_features`、`register_hdf5_for_browse`、`multi_tf_legacy_merged`、`multi_tf_layers`、`multi_symbol_c3`、`batch2d/control`、`hdf5_path`、`hdf5_relative_path`、`.h5` 任一字面之 `tests`、`frontend/src`、`scripts` 檔，另加 `tests/governance/test_prered_allowed_red.py`（其 `EXPECTED` 須同步刪 FRAMEPATH 列），並排除 `scripts/fact_keys.json`（治理事實鍵生成源，各批收尾同步現況，由 Task 4.1／4.2 之 `gen_fact_key_blocks.sh` 檢查與文字掃描約束）（清單寫入處置表檔頭）。處置表由五部分組成——nodeid 表、操作表與三個頂層清單 `new_files`、`fact_key_rows`、`ignored_baseline`（schema 見驗證⑤⑥），nodeid 表與操作表每列必填 `phase`∈{1,2,3}：(i) nodeid 表——以該母體於 HEAD 之 `pytest --collect-only -q` 為母體，每個 nodeid 標 `keep`、`delete`（附理由）或 `rename:<新 nodeid>`，`delete`／`rename` 列必填其操作列 id；(ii) 操作表——每列有唯一 id、`phase`、`path`、操作種類、HEAD 摘錄雜湊、frame 依據說明（供 TODO 審查逐項核對）與所涵蓋之 nodeid 集合（可為空，如 helper；`delete-file` 須含該檔全部 HEAD nodeid）。操作種類封閉為六種，各限定可用之副檔名與摘錄雜湊算法：`delete-node`（限 `.py`；檔＋AST 節點路徑：函式、模組層 dict 項、模組層 set／list／tuple 元素、import 別名、parametrize 元素、函式內敘述；雜湊＝節點 span 經正規化之 AST sha256）、`rename`（限 `.py`；舊名→新名；雜湊同 `delete-node`）、`rewrite`（限 `.py`；整個函式改寫；必附理由、「須保留之原斷言」清單〔HEAD 行號與正規化 AST 雜湊〕與改寫後函式全文〔源碼與正規化 AST 雜湊〕；雜湊同 `delete-node`）、`delete-json-path`（限 `.json`；JSON Pointer；雜湊＝目標子樹 canonical JSON〔鍵排序、固定分隔〕sha256）、`replace-file`（限非 `.py`、非 `.json`，如 `.sh`、`.ts`、`.tsx`；雜湊＝HEAD 整檔 sha256，另記凍結之新檔全文與其 sha256）、`delete-file`（任一副檔名；`path` 限單一檔案，刪目錄須逐檔各列一筆且涵蓋該目錄於 HEAD 之全部檔案；雜湊＝HEAD 整檔 sha256）；frame 對 CGSA 之比對斷言以 `delete-node` 列出；非 factory 用途之 h5（kline、case、IC fixture、generic mock）不列操作即為保留；`scripts/capture_full_golden_baseline.py`、`scripts/compare_with_full_golden_baseline.py` 之去留於本表定案。實作照表執行：frame 對照臂刪除，有效意圖以 CGSA 斷言承接；`test_failopen_manifest::test_persist_false_generate_features_metadata` 改驗 CGSA `persist=False`，轉綠同批刪 allowed_red FRAMEPATH 列並同步 EXPECTED。
- **驗證**：新測 `tests/feature_engineering/test_framepath_disposition.py`（秒級，不跑被測測試）：記本批已執行集合 E＝處置表中 `phase` ≤ 本批 Phase 之列：⓪`test_disposition.json` 之 sha256 等於 manifest 所記戳記值；每列有合法 `phase`；任一操作列之 `path` 於 HEAD 為目錄 ⇒ 紅；`scripts/fact_keys.json` 出現於母體或操作表 ⇒ 紅；每個操作列之種類與其 `path` 副檔名相容（依上列限定），不相容即紅；①HEAD 母體與現行 collect 之差集恰等於 E 中 `delete` 之 nodeid 與 `rename` 之舊 nodeid，且 E 中每個 `rename` 之新 nodeid 現行存在；②**逐檔期望值比對（單一規則，不分副檔名）**：對「母體 ∪ 操作表所列 path」之每個檔 F——E 中有 `delete-file`(F) ⇒ F 現行須不存在；否則 F 現行須存在且等於期望值：`.py`＝HEAD 版（`git show 6e07e0ad:<path>`）套用 E 中 F 之 `delete-node`／`rename`、以凍結全文代入 E 中 `rewrite` 函式、再經下列正規化之整個模組 AST，與現行經同一正規化之 AST 逐節點相等；`.json`＝HEAD 版 `json.load` 套用 E 中 F 之 `delete-json-path` 後之 canonical 序列化，與現行之 canonical 序列化相等（E 中 F 無操作 ⇒ 與 HEAD 位元組相等）；其餘副檔名＝E 中有 `replace-file`(F) ⇒ 現行 sha256 等於凍結值，否則與 HEAD 位元組相等；③E 中每個 `rewrite` 之「須保留之原斷言」其正規化 AST 皆出現於凍結之改寫後全文內（TODO 階段自檢）；④處置表內部一致：nodeid 表每個 `delete`／`rename` 所指操作列存在且其 nodeid 集合含該 nodeid，反之每個操作列之 nodeid 集合中每個 nodeid 於 nodeid 表標 `delete`／`rename` 且指回該列；每列之摘錄雜湊等於以其種類所定算法對 `git show 6e07e0ad:<path>` 重算之值，算不出即紅；⑤新增檔（範圍 R＝`momentum`、`api`、`scripts`、`tests`、`frontend/src`）：(a)`git diff --name-status --diff-filter=A 6e07e0ad -- <R>` 與 `git ls-files --others --exclude-standard -- <R>` 之聯集須 ⊆ 處置表 `new_files` 中 `phase` ≤ 本批之 path；(b)`git ls-files --others --ignored --exclude-standard -- <R>` 之檔案級結果，過濾為副檔名 ∈ {`.py`, `.json`, `.ts`, `.tsx`, `.sh`} 且不在 `__pycache__/` 下者，須等於處置表 `ignored_baseline`（TODO 階段於乾淨 HEAD 工作樹以同一命令與同一過濾凍結）；⑥`scripts/fact_keys.json` 與 HEAD 版之 canonical JSON 差異只准落在處置表 `fact_key_rows` 所列之列，其餘列須相等；三清單之封閉 schema：`ignored_baseline`＝排序後不重複之 repo 相對路徑字串陣列；`new_files` 每項＝{`path`（repo 相對、唯一、落於 R）、`phase`∈{1,2,3}、`task`（本 SPEC Task 編號，該 Task 須以「（新）」或「新測」列出此 path，或為該 Task 處置表 `rename` 新函式所在之新檔）}；`fact_key_rows` 每項＝{`row_id`（`scripts/fact_keys.json` 列之識別字欄，唯一）、`phase`}，只准本票之 ROADMAP 列、HANDOFF 列與 §N 所建之欄名殘留列；驗證器拒收未知欄位、非字串、重複項、越界 `phase`、`path` 不在 R、`row_id` 不在上列三種；⑦既有檔改動範圍：`git diff --name-status -M 6e07e0ad -- tests scripts frontend/src` 之每個舊路徑與新路徑皆須屬於「母體 ∪ 操作表所列 `path` ∪ `new_files`」，否則紅；`scripts/fact_keys.json` 不由⑦裁決，只由⑥判其列級差異（`momentum`、`api` 之生產碼改動不在本閘，由 Task 1.2–2.3 之驗收、Task 1.1 CGSA 不變基準與審碼承擔）；正規化只做下列封閉形態之剝除，鍵一律限字面 `"FFACT_USE_CGSA"`：(a) `monkeypatch.setenv`／`monkeypatch.delenv` 以該鍵為第一引數之敘述；(b) `os.environ["FFACT_USE_CGSA"] = …`、`del os.environ[…]`、`os.environ.pop("FFACT_USE_CGSA", …)` 敘述；(c) 任一 dict 字面（含 `patch.dict(os.environ, {...})`、`@pytest.mark.parametrize` 之元素、helper 參數）中該鍵之項；(d) 任一呼叫之關鍵字引數 `FFACT_USE_CGSA=…`（含 `prepare_env`／`prepare_stat_env` 等 helper）；剝除後留下之空 dict／空敘述一併正規化為無。上列以外之任何差異（含 `FFACT_MULTI_TF_PARALLEL` 等其他鍵、ids、fixture 引用、斷言）皆判不等。mutation：刪一條未登記測試 ⇒ ①紅；把一條 `keep` 測試之斷言改為 `assert True` ⇒ ②紅；把 decorator 中 `FFACT_MULTI_TF_PARALLEL` 之 `"0"` 改 `"1"` ⇒ ②紅；把模組層 path registry（如 `tests/test_multi_tf_generator.py` 之 `_PATH_ENV`）之 `FFACT_MULTI_TF_PARALLEL` 改值、或刪一個未列於操作表之 path key ⇒ ②紅；刪處置表所列之 frame 路徑鍵或 frame 專用 helper／import ⇒ ②綠；改處置表任一位元組 ⇒ ⓪紅；新增一個不在 `new_files` 之 `tests/feature_engineering/unlisted_probe.py`（含另加 ignore 規則使其被忽略）⇒ ⑤紅；R 外新增 `docs/` 文件 ⇒ ⑤不判；新增被既有 `*.bak` 規則忽略之檔 ⇒ ⑤(b)不判；於既有被忽略目錄下新增 `.py` ⇒ ⑤(b)紅；改名一個母體外之 `tests/_fixtures/` 檔 ⇒ ⑦紅；照表 `delete-file` 一個關鍵字母體外之 golden 檔 ⇒ ⑦綠；只改 `fact_key_rows` 允許之列 ⇒ ⑥⑦綠；`new_files` 列一個 Task 未標「（新）」之 path 或 `fact_key_rows` 列他票之列 ⇒ ⑤⑥前之 schema 檢查紅；改 `fact_keys.json` 中非 `fact_key_rows` 之一列描述 ⇒ ⑥紅；`rename` 之測試改了 fixture 呼叫或輸入資料 ⇒ ②紅；實作之 `rewrite` 函式與凍結全文有任何差異（含改 fixture、輸入資料、保留斷言改 `assert True`）⇒ ②紅；表外刪 `allowed_red.json` 一列或改 `nan_propagation_classes.json` 一鍵 ⇒ ②紅；照表刪已列之 JSON Pointer ⇒ ②綠；nodeid 表標刪一個未被任何操作列涵蓋之 nodeid ⇒ ④紅；把 `delete-json-path` 之摘錄雜湊填錯 ⇒ ④紅；對 `.json` 列 `delete-node` 或對 `.sh` 列 `delete-node` ⇒ ⓪紅；改 `BatchProgressPanel.test.tsx` 一條斷言或改 `scripts/prune_dead_feature_runs.sh` 一行而無 `replace-file` 列 ⇒ ②紅；處置表列 `delete-file`(`tests/_golden/batch2d/control.json`) 而實作未刪 ⇒ ②紅；Phase 1 批提前執行 `phase=2` 之列 ⇒ ①或②紅；改 `FIXED_ENV` 之非 `FFACT_USE_CGSA` 鍵 ⇒ ②紅；改 decorator 非 env 參數 ⇒ ②紅；只刪 decorator 中 `FFACT_USE_CGSA` 鍵或 helper 之該關鍵字引數 ⇒ ②綠。何者可刪、何者改名、何者須改寫及其須保留之斷言，由 TODO 審查定案（三家逐項核處置表）；實作期⓪–⑦機械確認照表執行。受影響測試檔明列路徑跑綠（真實資料者單組串行）。
- **邊界**：參數化測試之 frame 參數值刪除須於 nodeid 表標 `delete` 並於操作表列對應 parametrize 元素；只剝 `FFACT_USE_CGSA` 之測試不列操作、nodeid 標 `keep`；每批收尾以該批 E 跑⓪–⑦，Phase 3 收尾 E＝全表。
- **存活至**：收案後保留（`test_disposition.json` 為刪除審計紀錄）。
- **覆蓋風險**：無（處置表於 TODO 階段一次涵蓋 Phase 1–3，各 Task 只照表執行）。
- 不可做：不得放寬既有 CGSA 斷言換綠；不得以檔為單位宣稱已覆蓋。

### Phase 2 — 刪 factory h5 讀寫鏈（依賴：Phase 1）

**Task 2.1 — storage 與生成快取**
- 目標：刪 factory h5 寫讀端與只讀它的生成快取。　檔案：`feature_storage.py`（`save_factory_output`、`save_metadata_json`、`load_factory_output`）、`feature_factory.py`（`_try_load_cache`、:460–465 快取查詢、`_last_generation_from_cache` 與其消費 :346、:353）　既有 caller：`generate_features`、`FeatureLibrary`。
- 改法：整刪；`force_regenerate` 參數保留（仍傳入 `_cgsa_force_fresh`）；CGSA resume（`_prepare_cgsa_registry`）不變。
- **驗證**：Task 1.1 全格綠（含 C5 resume）；`grep -rn "load_factory_output\|save_factory_output\|_try_load_cache\|_last_generation_from_cache" momentum api` → 0。
- **邊界**：base_path 下手放一個 `*_factory.h5` ⇒ 生成忽略之、照常 CGSA 生成；`force_regenerate=True` 與 False 結果 fingerprint 相等。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不新增 manifest 快取命中（§N）。

**Task 2.2 — FeatureLibrary 與 coverage**
- 目標：讀者只走 V2。　檔案：`momentum/FeatureEngineering/feature_library.py`（:205–215 無 hash 之 h5 後備）、`momentum/Analysis/coverage_analyzer.py`（`_resolve_feature_file_path`、h5py 讀取與 legacy 掃描分支）　既有 caller：IC 服務 FeatureLibrary 後備、coverage API。
- 改法：V2 manifest 找不到 ⇒ `FeatureNotFoundError`（訊息不提 HDF5）；coverage 只走 V2／FeatureReader。
- **驗證**：既有 V2 讀取測試綠；新斷言：只有 `*_factory.h5`、無 V2 run 之 base_path ⇒ `FeatureLibrary.load` 拋 `FeatureNotFoundError`、coverage 回傳該 symbol 無資料而非讀 h5；mutation：還原後備 ⇒ 紅。
- **邊界**：有 V2 run 且同時有 `*_factory.h5` ⇒ 只讀 V2；`config_hash` 明給但缺 artifacts ⇒ 既有錯誤訊息不變。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不動 `load_features_from_hdf5` 族。

**Task 2.3 — API 舊 h5 分支**
- 目標：API 對 factory h5 具名拒絕，CGSA manifest 路徑不變。　檔案：`api/services/feature_factory_service.py`（:305 非 `.json` 之 stats warmup 分支、`_load_task_context` :4692 非 `.json` 分支、`_load_hdf5_features_df` :4790、:5264、:5298、:5797 之 h5 後備；:5572 `kline_cache.h5` 不動）、`api/services/feature_browser_service.py`（`.h5`／`.hdf5` 分支與 `_load_hdf5_features`、`_find_dataset_group`）、`api/routes/feature_factory.py:628`（`register_hdf5_for_browse` 保留，非 `.json` 路徑具名拒絕）　既有 caller：Feature Explorer 之 browse／schema／rows／CSV 路由、批次結果登錄。
- 改法：非 `.json` 之 task 路徑 ⇒ service 拋 `ValueError`（訊息含「舊 factory h5 已不支援」與路徑）；`/browse/register` 與其他受影響 route 於 broad `except Exception` 之前加 `except ValueError` → HTTP 400（對齊同檔 browse route 既有模式）；`_start_stats_cache_warmup` 若刪後無呼叫者則刪，否則保留。
- **驗證**：新測 `tests/api/test_framepath_api_h5.py`：register／task context／schema／selected rows／CSV 對 `.h5` 皆 `status_code == 400` 且 body 含該訊息與路徑；同檔以 CGSA manifest fixture 斷言 feature list、selected rows、CSV 匯出成功（200）。mutation：刪 route 之 `except ValueError` ⇒ register 回 500、測試紅。
  `ASSERT pytest tests/api/test_framepath_api_h5.py WHEN state=after THEN rc=0`
  既有 `tests/api/test_feature_browser_routes.py`、`tests/api/test_feature_browser_service.py` 依處置表遷移。
- **邊界**：`hdf5_path` 為空字串之舊 registry 列（11 筆）⇒ 既有行為不變；`.JSON` 大寫副檔名 ⇒ 與現行判定一致。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不改 `hdf5_path` 欄名；不動 kline／case／IC h5。

**Task 2.4 — 前端與 h5 讀取測試處置**
- 目標：前端敘述與測試處置同步。　檔案：`frontend/src/lib/types.ts`（`hdf5_relative_path` 註解改述為 manifest 路徑）、`frontend/src/store/featureFactoryStore.ts`（若有 `.h5` 專屬文案或分支）；h5 讀取相關測試（`tests/test_feature_storage_validator_factory.py`、`tests/momentum/test_coverage_analyzer.py`、`tests/feature_library/test_phase*.py`、`tests/feature_engineering/ffstat_helpers.py` 之 `*_factory.h5` 枝、`tests/feature_engineering/test_icfirstalign_icfirst.py` 之 h5 fixture、`tests/feature_engineering/test_failopen_consumer.py` 之 `load_factory_output` mock）依 `test_disposition.json`（TODO 階段已凍結）執行處置　既有 caller：無新增。
- 改法：前端只改註解／文案；測試依處置表遷移或刪除。
- **驗證**：前端有改 ⇒ `npm run build` 與受影響 vitest 綠；Task 1.5 處置測試綠。
- **邊界**：前端欄名讀取不變；無 `.h5` 專屬分支 ⇒ 前端零改動並於收據記 grep 結果。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不改 DTO 欄名。

### Phase 3 — 腳本與 golden（依賴：Phase 2）

**Task 3.1 — 腳本逐檔處置**
- 目標：腳本不再呼叫已刪路徑。　檔案與處置：`scripts/freeze_batch2d_baseline.py`（刪 control／frame run，只留 CGSA）、`scripts/golden_multi_symbol_c3.py`（退休刪檔：其產物 `tests/fixtures/golden/multi_symbol_c3/` 在 tests／momentum／api 零讀者，主委 `grep -rln "multi_symbol_c3" tests momentum api` 2026-10-08 → 空）、`scripts/icfirstalign_preic_diff.py`（刪 `=0` 舊臂；無剩餘用途則刪檔）、`scripts/profile_v6v7_comparison.py`（刪 `=0` 前優化臂；無剩餘用途則刪檔）、`scripts/profile_gate3_to_4_full.py`（刪「可用 FFACT_USE_CGSA=0 關閉」說明）、`scripts/freeze_failopen_baseline.py`／`scripts/verify_cgsa_pipeline.py`／`scripts/l65_native_tf_profile.py`／`scripts/profile_l65_native_tf_groups.py`／`scripts/profile_multi_tf_baseline.py`（只刪 env 設定與印出）；`scripts/capture_full_golden_baseline.py`、`scripts/compare_with_full_golden_baseline.py`（去留於處置表定案）　既有 caller：`scripts/*.sh` 與文件引用。
- 改法：照處置表（Task 1.5，TODO 階段凍結）中 `phase=3` 之 scripts 操作逐檔執行；刪檔者同批刪其引用。
- **驗證**：受影響腳本 `python -m py_compile` rc=0；`grep -rn "FFACT_USE_CGSA\|_factory\.h5\|_factory_meta\.json\|save_factory_output\|load_factory_output" scripts --include=*.py` → 0；Task 1.5 之⓪–⑦以 E＝`phase` ≤ 3 跑綠（scripts 之整模組 AST 比對同測試檔）。
- **邊界**：刪檔之腳本若被 `scripts/*.sh` 或文件引用 ⇒ 同批刪引用或改指向；只改 env 之腳本行為不變。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不得跑 `freeze_*` 全量重凍（只做靜態處置）。

**Task 3.2 — frame 產出之 golden**
- 目標：驗收母體不含 frame 產物。　檔案：`tests/_golden/batch2d/control.json`（刪）、`tests/fixtures/golden/multi_symbol_c3/baseline.parquet`、`tests/fixtures/golden/multi_symbol_c3/config.json`、`tests/fixtures/golden/multi_symbol_c3/env_snapshot.json`（三檔各一筆 `delete-file`，零讀者）　既有 caller：batch2d 對照測試。
- 改法：照處置表刪 control.json 及其 frame 對照斷言、multi_symbol_c3 三檔與其 py 引用；文字引用之現況改寫歸 Task 4.1。
- **驗證**：Task 1.5 處置測試綠；`git diff --stat 6e07e0ad -- tests/_golden/batch2d/cgsa_baseline.json tests/_golden/failopen/baseline.json` 為空；`grep -rn "multi_symbol_c3\|batch2d/control" tests momentum api scripts --include=*.py` → 0。
- **邊界**：刪除前再跑一次讀者 grep，若出現讀者 ⇒ 停下回 SPEC；歷史凍結快照之 env 記錄不重凍。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不重簽 batch2d「不得相等」oracle；不修改兩份 CGSA 凍結快照。

### Phase 4 — 文件、事實鍵與收案（依賴：Phase 3）

**Task 4.1 — 現況文件同步**
- 目標：現況文件不再描述 frame／factory h5。　檔案：`docs/ARCHITECTURE.md`（legacy feature HDF5 相容敘述）、`docs/FF_FAILOPEN_FROZEN_TESTS.md`（non-CGSA L7 列）、`docs/plan/feature-factory-optimization/plan.yaml`（fallback 文案）、`docs/DEVELOPMENT_GUIDE.md`（若有）、`scripts/fact_keys.json`（RM-FRAMEPATH／HP-FRAMEPATH 狀態，經 `bash scripts/gen_fact_key_blocks.sh --write`）、`docs/ROADMAP.md`、`HANDOFF.md`、`docs/FFNAME_SPEC.md`（只加一行 pointer：Task 2.1 frame 臂、2.2 HDF5 世代閘已因本票失去對象，待第 6 步重寫刪除）　既有 caller：無。
- 改法：只改現況段；已收案 SPEC 之沿革不改寫；本票於 `scripts/fact_keys.json` 之 ROADMAP 列與 HANDOFF 列票名改為不含 `FFACT_USE_CGSA`、`_factory.h5` 等字面之穩定名（如「FRAMEPATH：刪除 frame 舊引擎與舊特徵 h5 讀寫鏈」），舊名只留沿革。
- **驗證**：`grep -rn "FFACT_USE_CGSA\|_factory\.h5\|load_factory_output" docs/ARCHITECTURE.md docs/DEVELOPMENT_GUIDE.md docs/FF_FAILOPEN_FROZEN_TESTS.md` → 0；`bash scripts/gen_fact_key_blocks.sh` 檢查模式 rc=0。
- **邊界**：plan.yaml 之 acceptance 條目若為歷史凍結 ⇒ 改為標註「FRAMEPATH 已刪」而非刪行；FFNAME_SPEC 只加 pointer、不改其 Task 正文。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不改已收案 SPEC 之正文。

**Task 4.2 — 收案總檢**
- 目標：機械確認刪淨與不變。　檔案：無新增　既有 caller：無。
- 改法：跑下列檢查並寫收據 `handoffs/run_receipts/<date>-framepath-close.txt`。
- **驗證**：`grep -rn "FFACT_USE_CGSA\|_cgsa_enabled\|load_factory_output\|save_factory_output\|_factory\.h5\|_legacy_native_row_maps\|_generate_multi_tf_legacy\|_try_load_cache" momentum api scripts frontend/src tests` 之命中只含 `tests/_golden/batch2d/cgsa_baseline.json`、`tests/_golden/failopen/baseline.json`（歷史凍結 env 快照）、`tests/_golden/framepath/`（本票基準與處置表）、`scripts/fact_keys.json` 之「以下為沿革」之後字串與 Task 1.2／2.2／2.3 之負向測試字面；`grep -rln "multi_symbol_c3\|batch2d/control\|golden_multi_symbol_c3\|fix_spec_v1_to_v1_1" momentum api scripts frontend/src tests docs/ARCHITECTURE.md docs/DEVELOPMENT_GUIDE.md docs/FF_FAILOPEN_FROZEN_TESTS.md docs/ROADMAP.md docs/plan/feature-factory-optimization/plan.yaml docs/FFNAME_SPEC.md` 之命中只含 `scripts/fact_keys.json` 與 `docs/ROADMAP.md` 中「以下為沿革」之後字串、`tests/_golden/framepath/`；`grep -n "FFACT_USE_CGSA\|_factory\.h5\|load_factory_output" docs/ROADMAP.md docs/plan/feature-factory-optimization/plan.yaml docs/FFNAME_SPEC.md` 之命中只准為：「以下為沿革」之後字串、plan.yaml 同行帶「FRAMEPATH 已刪」標註者、`docs/FFNAME_SPEC.md` 之 Task 2.1／2.2 段（待第 6 步重寫）；`bash scripts/gen_fact_key_blocks.sh` 檢查模式 rc=0；`bash scripts/check_decoupling.sh` 之紅燈數不多於 HEAD 6e07e0ad；Task 1.1 不變測試全格綠；allowed_red 無 FRAMEPATH 列。
- **邊界**：命中清單出現上列以外之檔 ⇒ FAIL 並回到對應 Phase。
- **存活至**：收案後保留。
- **覆蓋風險**：無。
- 不可做：不跑 `pytest tests/governance` 全套（本票未動共用治理控制流）。

## §V 驗證策略與邊界測試目錄
- **mutation**：Task 1.1（M1–M4）、1.2、1.5、2.2 各附可證偽 mutation，收據入 `handoffs/run_receipts/`；引 `docs/TEST_DESIGN_CHARTER.md`。
- **測試層級**：Golden 對照（Task 1.1，真實資料、單組串行）＋單元（具名例外、處置表、API h5 拒絕）＋既有 CGSA 測試回歸（明列路徑）。全部可獨立 `pytest tests/...`，不需 run_api.py。
- **防假綠**：每批 diff 既有測試斷言；刪除之測試必登記 `test_disposition.json`，不得放寬 CGSA 斷言。
- **三方簽核**：Phase 1、Phase 2 收批前，Claude＋三家各自獨立確認 Task 1.1 收據之比對域與結果（資料正確性簽核）。
- **邊界目錄**：resume（C5）、多週期 serial（C3）與 parallel（C6）、L3 streaming／hybrid（C4）與 in_memory（C8）、`persist=False`（C7）、次週期不足 partial（C9）、殘留環境變數、手放舊 h5、空 `hdf5_path`、大寫副檔名、白名單外 combine context。
- 每批收尾：`bash scripts/restore_golden_inventory.sh`；列本批暫存（pytest-of-louis、中斷測試殘留、委員 /private/tmp 副本）與刪除指令交使用者。

## §R 回退
- 每 Phase 獨立 commit，可單獨 `git revert`；Phase 2 依賴 Phase 1，回退 Phase 1 前先回退 Phase 2。Task 1.1 不變測試紅 ⇒ 該批不得提交。不設 feature flag（本票目的即刪除切換開關）。

## §N N/A 登記
- 殘留：manifest 型生成快取命中（CGSA 同 config 已有 complete run 時直接回傳、不重算）— `為何現在不做: needs-research:失效條件（kline 增量、校準封包、config hash 外之環境）與 FFSTORE 儲存設計之關係`；觸發：FFSTORE 票 SPEC 起草時納入評估；登記處：docs/ROADMAP.md RM-FFSTORE 列。現況 CGSA 恆不命中 `_try_load_cache`，本票刪除後行為不變。
- 殘留：`hdf5_path`／`hdf5_relative_path` 欄名改為 manifest 語意之名 — `為何現在不做: blocked-by:跨棧 DTO（api/models、frontend/src/lib/types.ts、registry.json 既存 40 筆）改名須另立相容遷移，與本票刪除無依賴`；觸發：下一次動 FeatureRegistry schema 之票；登記處：docs/ROADMAP.md 新列（Task 4.1 建）。
- 殘留：FF-NAME SPEC 之 Task 2.1 frame 臂、Task 2.2 HDF5 世代閘刪除 — `為何現在不做: user-ruling:2026-10-02 全票排序 FF-NAME 為第 6 步，其 Task 0＝SPEC 重寫`；觸發：第 6 步開工；登記處：docs/ROADMAP.md RM-FFNAME 列。
- 殘留：repo 外自訂 base_path 下可能存在之既存 `*_factory.h5` 檔（repo 內實測 0 個）— `為何現在不做: user-ruling:2026-08-05 使用者定「面向未來不溯及既往」（遇舊資料不合新規預設封存非遷移）＋2026-09-28 刪除舊特徵 h5 讀取裁定`；觸發：無（本票不追蹤 repo 外檔；收案白話閘交使用者 `find <base_path> -name "*_factory.h5"` 查核與刪除指令）；登記處：docs/ROADMAP.md 本票列。
