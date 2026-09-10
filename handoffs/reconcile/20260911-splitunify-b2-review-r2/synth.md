# Reconcile — 20260911-splitunify-b2-review-r2

**來源** 20260911-splitunify-b2-review-r2-codex.md, 20260911-splitunify-b2-review-r2-composer.md, 20260911-splitunify-b2-review-r2-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併——**不可進 B2c**；六條合併後全數為「輸入不變式未驗證」，一次修完即可。

三家 verdict：codex「不可進：`P1-01`／`P1-02`／`P1-03`」、grok「不可進：`P1-01`／`P1-02`」、
composer「可進」（其兩條標 P2）。**主委自產版亦判「不可進」**
（`handoffs/20260911-splitunify-b2b-r2-claude-selfreview.md` 之 `CLAUDE-R2-P1-01`）。
⇒ 四方中三方判不可進，且 codex／grok／主委在**同一條**（索引不變式）獨立收斂。

🔴 **本輪的方法論驗證**：我在 R2 brief 必答 2 明確要求「**主動餵 malformed 輸入**，
不要只讀碼」——這一改，composer 也做了負向注入並找到兩條（R1 它是零 finding）。
⇒ R1 之 H0 記的教訓（「brief 必答要明確要求負向注入」）**當輪就見效**。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **I1 `feature_index` 不變式未驗（未排序／重複）** | **P1** | GROK-R2-P1-01、CODEX-R2-P1-02（後半）、CLAUDE-R2-P1-01（**三方獨立收斂**） | **採納**。`test_start_ms = index_ms[test_rows[0]]` 假設索引**時間遞增**；反序時它不再是測試段最早時刻 ⇒ 答案窗比較用到錯的邊界，且**完全靜默**。重複時間戳則讓集合成員判定失去唯一性。⇒ 共用 validator 補**嚴格遞增**檢查（`np.diff > 0`，一併涵蓋重複）。放在 `assert_epoch_ms_array` 內，`holdout_boundary` 與投影兩端同時受惠。 |
| **I2 NaN 在數值型索引被靜默轉成 0** | **P1** | GROK-R2-P1-02、COMPOSER-R2-P2-01 | **採納**。`astype("int64")` 把 `NaN` 變成 **0**（或未定義值）⇒ `feature_cutoff_ms=0` 的事件可能被誤判為 train。DatetimeIndex 之 NaT 我已擋，**數值型的 NaN 沒擋**——同一個洞的另一半。⇒ `assert_epoch_ms_array` 在 cast **之前**驗 finite。 |
| **I3 `event_keys.event_id` 重複未擋** | **P1** | CODEX-R2-P1-01 | **採納**。H1 我只做了「集合相等」，**集合會吃掉重複** ⇒ 同一個 event_id 出現兩次仍與 manifest 集合相等，然後被重複計數／重複輸出 assignment。⇒ 補唯一性檢查（`event_keys` 與 `manifest.table` 各自都要）。 |
| **I4 `row_index` 非整數 float 被靜默截斷** | **P1** | CODEX-R2-P1-02（前半）、COMPOSER-R2-P2-02 | **採納，並推翻我自己的裁定**。我在 `CLAUDE-R2-P3-04` 判「維持現狀，型別錯誤非資料品質問題」——**三家有兩家判該擋**，且理由更好：`0.5 → 0` 是**靜默改變歸屬**，不是型別噪音。依「分歧採較嚴版」採納。⇒ `assert_positional_rows` 在 cast 前驗整數性。 |
| **I5 事件時間戳／答案窗完整性未驗** | **P1** | CODEX-R2-P1-03、GROK-R2-P2-04、CLAUDE-R2-P2-03 | **採納**。`label_end_ms < label_start_ms`（反轉窗）與 test 側的 NaT／NaN 都可產生 assignment。上游 `alignment.py:192` 有閘，但投影是**公開純函式**，B3 以外的 caller 不受保護。⇒ `event_keys` 欄位驗證時一併驗 finite 與 `label_start_ms <= label_end_ms`。 |
| **I6 `bucket_ms <= 0` 未擋** | P2 | CODEX-R2-P2-04、GROK-R2-P2-03、CLAUDE-R2-P2-02（**三方獨立收斂**） | **採納**。負值產出負向 `time_cluster_id`；`bucket_ms == 0` 目前「有擋」是**巧合**（靠 pandas `IntCastingNaNError`），上游換行為就靜默失效。⇒ `time_cluster_bucket_ms` 出口加 `bucket > 0` 並給本票語意的訊息。 |
| **I0 composer 判可進** | P3 | COMPOSER 之 Verdict | **記錄**。composer 判 H1–H5 逐條閉合、其兩條標 P2 不擋 B2c。被 codex／grok／主委覆蓋——但它**這一輪做了負向注入**並找到 I2／I4 的一半，與 R1 的零 finding 相比是實質進步，證明 brief 之必答寫法有效。 |

### 共同形態（六條合一）

六條全部是**同一類**：我把 fail-closed 寫在「有沒有給」（缺欄、缺 plan、缺 symbol）上，
沒寫在「給的東西是否滿足不變式」（遞增、唯一、finite、整數、正數、區間有序）上。
⇒ 修法統一為**兩支共用 validator 的強化**（`assert_epoch_ms_array`、`assert_positional_rows`）
＋ `event_keys` 欄位驗證擴充 ＋ `time_cluster_bucket_ms` 正值檢查，
並補 `M-SU-21`..`M-SU-26` 各自對應一條不變式。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P1-01
**斷言**: H1 未閉合：exact ID set 對帳未拒絕重複 `event_keys.event_id`，會重複計數/輸出 assignment。
**碼證**: `split_projection.py:214-225,244-270` 只比 set 後逐列輸出；實跑 `duplicate_event_id => ACCEPT assignments=3, purged=2, assignment_ids=['e_train_ok','e_test','e_train_ok']`。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#afba86ba4a18;docs/SPLITUNIFY_SPEC.md#3e39458b00e4
P1／High；應在 projection 對帳前要求 `event_keys.event_id` 唯一並 fail-closed，否則 H1 身份完整性仍可被重複列穿透。
## CODEX-R2-P1-02
**斷言**: H3 未閉合：`assert_positional_rows` 先 `dtype=int` 靜默截斷非整數 float，且 feature index 未驗 sorted/unique。
**碼證**: `split_preview.py:89-109`；實跑 `row_index_nonintegral_float => ACCEPT assignments=2,purged=2`、`feature_index_unsorted => ACCEPT assignments=0,purged=1`、`feature_index_duplicate => ACCEPT assignments=1,purged=0`。
**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff;momentum/Analysis/event_samples/split_projection.py#afba86ba4a18
P1／High；先驗原始 dtype/整數性、`feature_index` 單調遞增且唯一，再做 positional/時間投影，避免錯列被當成合法 boundary。
## CODEX-R2-P1-03
**斷言**: event-key timestamp/interval 完整性未 fail-closed；test-side 的 NaT 與 `label_end_ms < label_start_ms` 可產生 assignment。
**碼證**: `split_projection.py:170-172,244-267` 僅檢欄且只在部分分支轉 int；實跑 `label_end_NaT_test_side => ACCEPT assignments=2,purged=2`、`label_start_NaT_test_side => ACCEPT assignments=2,purged=2`、`label_end_before_label_start_test_side => ACCEPT assignments=2,purged=2`。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#afba86ba4a18;docs/SPLITUNIFY_SPEC.md#3e39458b00e4
P1／High；逐事件驗 finite/non-NaT、整數毫秒與 `label_start_ms <= label_end_ms`，不應因事件落 test 而跳過 malformed input。
## CODEX-R2-P2-04
**斷言**: `bucket_ms` 負值未拒絕，cluster 可產生負 ID；此為不擋 B2c 的 P2。
**碼證**: `event_split.py:39-65` 無正值 guard；實跑 `bucket_ms=0 => RAISE IntCastingNaNError`，`bucket_ms=-3600000 => ACCEPT cluster IDs [-472223,-472292,-472297,-472293]`。
**來源摘要**: momentum/Analysis/event_samples/event_split.py#f9dbcfd3c9d6;tests/golden/splitunify/clusters_oracle.json#8a9f3f733edd
P2／Medium；補 `bucket_ms > 0` 的明確 ValueError；不擋 B2c，因零值已 raise 且本輪 oracle/mutation 另有獨立覆蓋。
必答1：H1 未閉合（P1-01）；H2 閉合；H3 未閉合（P1-02）；H4 閉合；H5 閉合。
必答2：已擋：feature_index NaT→ValueError、cutoff NaN→ValueError、缺 event_id→ValueError、錯型→ValueError、manifest 缺 decision_at_ms→KeyError、bucket 0→IntCastingNaNError；未擋：test-side NaT、float row、負 bucket、反向 interval、unsorted/duplicate index（上述碼證為實跑 stdout）。
必答2續：H1/H2/H3 負向身份測試與 `pytest ...test_splitunify_derive.py` 重跑均驗；未擋項即 P1-01..03，非讀碼推定。
必答3：刪掉 `len(symbols)>1` 正確；plan symbol 非空、train/test 相等、event symbol exact-set 相等三道守衛後，無多 symbol 反例；mutation M-SU-2/M-SU-3/M-SU-16 均 rc=1。
必答4：oracle 獨立；JSON 手推 `472222/472223` 與 `1/0.5`，可抓 bucket 換算及權重公式錯；targeted 35 passed，15 mutants `UNCOVERED=0`。
必答5：不可以＋CODEX-R2-P1-01／P1-02／P1-03；非阻擋 P2-04 留後續。
TESTS_RUN: derive 重跑 `35 passed`；mutation 單獨重跑 `UNCOVERED=0`、C0 rc=0；回歸指定集合 `703 passed`；decoupling stdout `R2=1 R3=17 R4=3`（基線值，rc=1）。
FAILURES_SEEN: 首次 derive 曾報 2 failures，立即單獨/完整重跑皆 35 passed；第一次 mutation 與第二支併發造成不可信中間結果，無併發第三次為 UNCOVERED=0；restore script rc=128（sandbox 禁 `.git/index.lock`），inventory 無 diff。
SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: review only，未改碼/測試/規格/schema/output。
Verdict: 不可進 B2c：CODEX-R2-P1-01／CODEX-R2-P1-02／CODEX-R2-P1-03；P2-04 不擋 B2c。
STATUS: DONE
## COMPOSER-R2-P2-01

**斷言**: `assert_epoch_ms_array` 對含 `NaN` 的 float64 時間戳陣列不 fail-closed，cast 後帶 `RuntimeWarning` 仍放行，derive 可產出 assignment。

**碼證**: `split_preview.py:67-71`（`np.asarray(arr, dtype=int64)` 無 finite 檢查）；實跑 `nan_derive: PASS_THROUGH warnings=['invalid value encountered in cast']`。RECHECK: 同上 inline 探針。

**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff

[MAJOR] 信心度=High；失敗模式：上游 NaN 污染 index 時投影不 raise，membership 集合含垃圾 ms 值。修法：在 `assert_epoch_ms_array` 加 `np.isfinite` gate。**不擋 B2c**（H3 主項混合單位／負 index 已閉合；NaN 為殘差邊界，建議 B2c checklist 或 B3 接線前補測）。

## COMPOSER-R2-P2-02

**斷言**: `assert_positional_rows` 接受 float `row_index`（`dtype=int` 截斷），derive 不 raise。

**碼證**: `split_preview.py:95`；實跑 `float_row_derive: PASS_THROUGH n_assign=2`（`row_index` 為 `float64` 的 train plan）。RECHECK: 建 `SplitPlan(row_index=np.asarray(train.row_index, dtype=float), ...)` 呼叫 derive。

**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff

[MINOR] 信心度=Medium；失敗模式：`2.9` 截成 `2` 可能錯位。修法：`np.issubdtype(..., np.integer)` 或拒非整數 float。**不擋 B2c**。

---

## GROK-R2-P1-01

**斷言**: `feature_index` 非時間遞增時，`test_start_ms = index_ms[test_rows[0]]` 與集合成員所用時間戳一併錯位，答案窗／train·test 歸屬會靜默算錯且不 raise。

**碼證**: `split_projection.py:240` `test_start_ms = int(index_ms[test_rows[0]])`；`:238-239` `train_ms`/`test_ms` 由同一（可能未排序）陣列索引。VERIFY 探針 `Q2_unsorted_chair_reverse`：反序 index＋原 positional plans → `test_rows0_ms=1700090000000`、`earliest_among_test_rows=1700000000000`、`mismatch=True`，且 `e_train_ok` 的 `split_label` 變成 **`test`**。RECHECK: 同上反序注入；修後應在正規化後 `np.all(np.diff(index_ms) > 0)` 失敗即 raise。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#afba86ba4a18

[BLOCKING] 信心度=High。與 R1 H3 同族：資料完整性閘只擋了單位／負索引，沒擋單調性。修法：在 `assert_epoch_ms_array`（或投影入口）加**嚴格遞增**檢查，一併擋重複時間戳（探針 `Q2_dup_ts` 目前未擋）。`holdout_boundary` 同源假設亦應共用此閘。**擋 B2c。**

---

## GROK-R2-P1-02

**斷言**: 數值型 `feature_index` 含 NaN 時不被 fail-closed；`assert_epoch_ms_array` 以 `astype("int64")` 把 NaN 變成 **0**，可使 `feature_cutoff_ms=0` 的事件被誤判為 train。

**碼證**: `split_preview.py:70-71` 非 integer dtype → `np.asarray(..., dtype="int64")`（RuntimeWarning: invalid value encountered in cast）。VERIFY：train 列位置寫入 NaN 後，`cutoff=0` 事件 → `split_label=train`；同事件在潔淨 index 上 → purged。RECHECK: `feature_index` 含 `np.nan` 必須 raise（建議 `np.isfinite` 全真），不得 cast。

**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff

[BLOCKING] 信心度=High。DatetimeIndex 的 NaT 已擋，但數值 NaN 旁路仍開——同一「時間戳必須是合法 epoch ms」不變式。**擋 B2c。**

---

## GROK-R2-P2-03

**斷言**: `bucket_ms < 0` 時 `build_time_clusters` 不擋，會產出負向 `time_cluster_id`；`bucket_ms == 0` 僅靠 pandas `IntCastingNaNError` 巧合擋住。

**碼證**: `event_split.py:59-60` `decision_at_ms // bucket` 無 `bucket > 0` 檢查。VERIFY：`bucket_ms=-1` → `NO_RAISE`、`time_cluster_id=-1700000000000`；`bucket_ms=0` → `IntCastingNaNError`。RECHECK: `time_cluster_bucket_ms` 出口加 `bucket > 0`。

**來源摘要**: momentum/Analysis/event_samples/event_split.py#f9dbcfd3c9d6

[MAJOR] 信心度=High。不擋 B2c（非 H1–H5 回歸；屬 Q2 新洞），但應與 P1 同批修，避免巧合閘失效。

---

## GROK-R2-P2-04

**斷言**: `label_end_ms < label_start_ms` 的反轉答案窗不被投影擋下，會當正常事件進入 assignments／purged 邏輯。

**碼證**: `split_projection.py:244-267` 只讀 `label_end_ms` 做 `>= test_start_ms`，無 `label_start <= label_end` 檢查。VERIFY：`label_end = cutoff - H1` → `NO_RAISE` 且進 assignments。上游 `alignment.py` 有閘，但本函式為公開純函式。RECHECK: 入口驗證 `label_start_ms <= label_end_ms`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#afba86ba4a18

[MAJOR] 信心度=High。不擋 B2c（可標「不擋 B2c」），建議與 P1 同批加欄位不變式。

---

## GROK-R2-P3-05

**斷言**: `row_index` 為 float 時 `assert_positional_rows` 經 `dtype=int` 截斷（0.5→0）後當合法列使用，不 raise。

**碼證**: `split_preview.py:95` `np.asarray(rows, dtype=int)`；探針 `Q2_float_rows`／`Q2_float_truncation_effect` → `NO_RAISE`，截斷後 `[0,1,2,3,4]`。RECHECK: 若要擋，需 `np.asarray(rows)` 後断言整數值（`np.can_cast`／`arr == arr.astype(int)`）。

**來源摘要**: momentum/core/split_preview.py#9001fe15b4ff

[MINOR] 信心度=High。同意主委「維持現狀」裁定；**不擋 B2c**。呼叫端型別錯誤，非資料品質主路徑。

---

