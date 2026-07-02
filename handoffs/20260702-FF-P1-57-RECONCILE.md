# P1-FF-5/7 測試設計 reconcile（三方收斂,Claude 綜合）

三腿:`20260702-FF-P1-57-DESIGN-{CLAUDE,CODEX,COMPOSER}.md`。兩委員獨立收斂點直接採納;分歧處列裁決+理由。Claude 版被兩家實質修正(三跑成本/污染面漏列/byte比對過粗),最終版以兩委員修訂為主幹。

## 1. 分層架構(兩家收斂,採納)
| Tier | 內容 | 成本 | 排程 |
|---|---|---|---|
| **fast**(PR gate) | FF5 快測 order 三序 `[A]/[A,B]/[B,A]` 同 factory(canonical hash+抽 20 欄真值,非只 hash);FF7.1 全 registry input semantics;FF7.2/7.3 小矩陣 | <5-8 分 | 隨時 |
| **medium**(requires_kline) | FF5 同 factory A/B/A + L5 reference cache 案例 | <20 分 | 排隊 |
| **slow**(receipt) | FF5 全鏈 **2 跑**:`solo(A)` vs `batch[B,A]`(B 先跑=最強污染序);`[A,B]` 僅 nightly 診斷不進主 gate | ~1h | mutation run/B2 後序列 |

## 2. P1-FF-5 不變量(修訂定案)
- V5.1 值:A 每特徵 parquet solo≡batch[B,A](容忍度沿 B2;float16 依 caveat)。
- V5.2 d*:比**語義 map**(有效 d_star 鍵值+metadata isolation 欄+path token+cross-context 必 miss),**不 byte 比整份 JSON**(computed_at/GC/value_aliases 非語義差異;Codex 挑戰成立)。
- V5.3 metadata:A manifest 行數/欄集/schema 一致。
- V5.4 路徑隔離(取代 Claude 版「不得出現 B 字串」過粗判):A 的 run dir/CGSA shard path/d-star payload/L7 artifact metadata 不得含 B context;manifest/checkpoint 合法記 batch symbols 不算違規。
- **污染面覆蓋表(兩家聯集,8+面)**:L5 `_reference_data_cache[(ref,tf)]`+IPC 注入、d* 磁碟路徑/payload、d* value_aliases 跨欄、同 factory `_d_star_cache_shared` 跨 TF、CGSA work_dir/shard、`FFACT_CGSA_WORK_DIR` env 固定目錄、L5 reference_symbol=B 案例、batch checkpoint/RunLease、類級 `INDICATOR_REGISTRY` 突變(歸 FF7 靜態 audit)→ 各自映射到上述 V/M(映射表沿 Composer §D3+Codex 補充)。

## 3. P1-FF-7(修訂定案)
- V7.1 **全 registry** input semantics(byte equality 級)+代表性 direct-call differential+price_transform policy+MAVP 特例+advanced 手刻引擎(Codex 矩陣);不靠「B1 清單 diff」抽樣(Codex 挑戰成立)。
- V7.2/7.3 多路徑等值 = **兩家層別聯集(v2 修訂,回應 Codex REJECT:原誤寫「收斂」漏 Composer 的 L6.5)**:
  - **L2**(Codex):Polars vs pandas persisted groups。
  - **L3**(兩家皆列):Numba `fused_rolling_stats`/streaming vs pandas fallback + persist callback。
  - **L6.5**(Composer):`FeaturePreprocessor._transform_single` 的 polars / numba_fast / serial 三分支,含互斥斷言(fracdiff off + polars_enabled→走 polars 且 numba_fast==0;fracdiff on→polars 必不走、走 `_apply_fractional_differencing_serial`)。
  - 路徑證據=monkeypatch sentinel/counter 包各分支+反路徑 raise/計數 0;fallback 允許/禁止兩模式各驗;log capture 僅輔助。
  - **裁決**:L2/L3/L6.5 各為獨立引擎邊界、各有 silent-fallback 風險,無一可省;兩腿只是各寫到自己讀到的層,非真分歧→取聯集。
- V7.4 float16/codec 誤差上界明示斷言(≤既有 caveat),超界紅。

## 4. Mutation 探針(章程 B1;v2 shape:正向偵測斷言在 raises 外;先單測快驗再全套)
- M5.1 d* cache path/payload 去 symbol 成分→V5.2 紅;M5.2 reference cache 毒化(A 拿到 B 的 ref)→V5.5 紅;M5.3 d* value_alias 跨欄錯配→V5.2b 紅。
- M7.1 swap wrapper 輸入欄→V7.1 紅;M7.2 patch 引擎選擇偽稱 polars 實走 pandas→sentinel 紅。

## 5. 交付檔
`tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`、`test_ff_wrapper_path_correctness.py`、共用 `ff_artifact_compare_helpers.py`(可選)。全部經 run_with_receipt;過 mutation_probe_static;副作用還原。

## 6. 分歧裁決紀錄
- 三跑 vs 兩跑:採兩家收斂「慢測 2 跑+快測三序」(Claude 原三跑全鏈成本過高,撤回)。
- [A,B] 地位:nightly 診斷(Codex),不進主 gate(Composer 同)。
- 已知邊界:並行 worker 共享 env(V5.7)列 optional nightly,不阻本批。

## v1→v2 修訂紀錄
v1:Composer APPROVED(sha 55691c03);Codex REJECTED——FF7 §3 誤寫「兩家收斂」只採 L2/L3,靜默漏 Composer 的 L6.5 矩陣。v2 已改為 L2+L3+L6.5 聯集並附裁決理由。body 變更→兩家重戳。

## 戳記
（委員各審本 reconcile v2+特別盯 Claude 綜合有無錯漏後 append
`RECONCILE-STAMP: <family> APPROVED 2026-07-02 sha256:<body-hash> task:<harness-task-id>`
或 `REJECTED — 理由`。append 前 `bash scripts/reconcile_body_hash.sh <本檔>`。）

RECONCILE-STAMP: composer APPROVED 2026-07-02 sha256:945123d3eca30d6c3a56b52c4f81b3e1c390fdd454fa6e28410b1db0f782c95c task:p1ff57-stamp-v2
RECONCILE-STAMP: codex APPROVED 2026-07-02 sha256:945123d3eca30d6c3a56b52c4f81b3e1c390fdd454fa6e28410b1db0f782c95c task:p1ff57-stamp-v2

## R7-emitter 缺口(待修,不阻本批)
reconcile_stamps_check 對本檔 provenance FAIL:task:p1ff57-stamp-v2 無 committee_dispatch 事件。
根因:gate.sh 的 _append_committee_dispatch 只在「高風險+有 --adversarial 實檔」分支觸發;
stamp-review 派工(risk low,無 --adversarial)不發事件→其授權的戳記無 provenance。
本檔兩家 APPROVED 為真(audit.log 有人類可讀派工紀錄可稽核)。
修向(另批,設計題):emitter 應對任何帶 --task-id 的委員派工觸發;但 stamp-review 的
output_path/hash 該記什麼(reconcile body_hash?)需設計,非 trivial。暫以 waived 派實作。
