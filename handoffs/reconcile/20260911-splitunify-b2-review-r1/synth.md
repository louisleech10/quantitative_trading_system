# Reconcile — 20260911-splitunify-b2-review-r1

**來源** 20260911-splitunify-b2-review-r1-codex.md, 20260911-splitunify-b2-review-r1-composer.md, 20260911-splitunify-b2-review-r1-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併——**不可進 B2c**，三條 P1 皆為真實正確性缺口且 codex 已實跑證明。

三家 verdict：codex「不可進 B2c：`CODEX-R1-P1-01`／`P1-02`／`P1-03`」；
composer「可進」（零 findings sentinel）；grok「可進」（2 條 P2）。
依「看碼證不數人頭」採 codex——它**實跑**餵了三種 malformed 輸入並印出「沒有 raise、
輸出看起來正常」的結果，那是最強的碼證形態；另兩家沒有做這類負向注入。

主委自產版另存 `handoffs/20260911-splitunify-b2b-claude-selfreview.md`。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **H1 `event_keys` 與 `manifest` 未強制 ID 對齊** | P1 | CODEX-R1-P1-01 | **採納**。`split_projection.py:211-238` 逐列採 `event_keys`，只在建 clusters 時用到 `manifest` ⇒ 餵**另一批** manifest 也會產出看起來成功的 assignment（codex 實跑 `manifest_id_mismatch` 接受 `foreign`）。這是「兩個輸入各說各話而沒人對帳」的形態。修法：投影前做 **exact ID set 對帳**——`set(event_keys.event_id) == set(manifest.table.event_id)`，不等即 fail-closed；並在 docstring 明訂**不接受 subset**（要子集就先自己裁 manifest，別讓函式猜）。 |
| **H2 多 symbol guard 只看基數、不看相等** | P1 | CODEX-R1-P1-02 | **採納**。`:186-196` 只檢查 `len(symbols) > 1 or len(plan_symbols) > 1` ⇒ 單一 ETH 事件配單一 **BTC** plan 會靜默通過並產出 ETH 的 train/test（codex 實跑證明）。這正是本票 C-2 要擋的「錯誤邊界歸屬」，只是換一種形狀。修法：要求 plan symbol **非空且與 event symbol 之 exact set 相等**，任一缺漏或不一致在支援性判定**之前**就 fail-closed。 |
| **H3 malformed feature index 未 fail-closed** | P1 | CODEX-R1-P1-03 | **採納**。兩類：①**混合單位** index（部分秒、部分毫秒）——我的守衛是 `np.all(abs < 1e11)`，混合時 `all` 為 False ⇒ 直通；②**負 positional row index**——numpy 會回捲，靜默取到尾端的列。codex 實跑 `mixed_seconds_entry_accepted` 與 `negative_row_index_accepted` 皆輸出 train assignment、無 raise。修法：逐元素確認**單一時間單位**、finite／非 NaT、且 row index 落在 `0 <= i < len(index)`、無重複；新增 `M-SU-18`／`M-SU-19`。**這是資料完整性閘，不是放寬輸入的選項**（codex 逐字）。 |
| **H4 秒守衛門檻是第二份 policy** | P2 | CODEX-R1-P2-04、GROK-R1-P2-01、CLAUDE-R1-P2-01（**三方獨立命中**） | **採納**。`split_projection._index_as_ms` 手寫 `1e11`、`split_preview._as_ms` 用具名 `_MS_MAGNITUDE_FLOOR`；改一支另一支不會紅。grok 另指出**零值／混合量級語意已分歧**。🔴 這是我在「消滅兩份真相源」的票裡自己種下的第二份真相源。修法：抽出共用的 vector／scalar 單位 validator（住 `split_preview`），兩端共用；加一條 cross-source 測試把門檻綁在一起。 |
| **H5 mutation 覆蓋不足＋cluster oracle 循環相依** | P2 | CODEX-R1-P2-05、GROK-R1-P2-02 | **採納，且 oracle 那半是最痛的一條**。🔴 `test_splitunify_derive.py:318-342` 拿 `split_events` 當 oracle，但**抽出後 `split_events` 自己就是呼叫 `build_time_clusters`** ⇒ 該測試已變成**同義反覆**，我的重構把一條真回歸測試變成了空的。修法：改為**獨立 frozen oracle**（凍結 expected clusters JSON）。mutation 補 `M-SU-14`..`M-SU-20`：14＝`test_start_ms` 誤減 embargo（🔴 需新增「`label_end` 在 canonical test start **前 1ms**」的 train fixture——現有 exact-equal fixture 仍會 purge ⇒ **假綠**，grok 之 `>= test_start_ms - 1` 同指）、15＝重複 `event_level`／移除 `validate="1:1"`、16＝plan-symbol mismatch、17＝manifest ID mismatch、18＝混合單位、19＝負 row index、20＝`>=`→`>`（既有單測會紅但 harness 未登錄）。 |
| **H6 `tier_min_test_events` 責任邊界未定** | P3 | CODEX-R1-P2-04（附帶） | **採納**。純函式簽名沒有這個參數，預設寫死 `1`；非預設門檻要由誰傳、在哪一批決定，B3 接線時須明訂。列入 SPEC Task 3.1 之實作要點。 |
| **H0 composer 判可進、無 finding** | P3 | COMPOSER-R1-P3-00 | **記錄，但被 codex 覆蓋**。composer 逐項核對必答 1–7、主委兩項自查與 A-2 code fence 後判無 P0/P1/P2。⚠️ 這**不表示 composer 審得不夠**——H1／H2／H3 三條要**主動餵 malformed 輸入**才看得見，讀碼對照契約看不出來（契約本身沒寫「要檢查身份」）。⇒ 教訓寫進下一輪 brief：**code review 的必答要明確要求負向注入**，否則三家可能都只做正向對照。 |
| **H7 效能與 `insufficient_events_in_test` 語意（已答）** | P3 | CODEX 之必答 4／5 回覆 | **記錄，不改**。codex 實跑 **10k 事件 derive = 0.029247s** ⇒ 我 brief 之「我沒查的」第 1 條（效能）**已被否證為非問題**。`insufficient_events_in_test` 用 projected global `n_test`，codex 判「在單 symbol fail-closed 路徑等價」；我自評傾向現在就改逐 symbol，但三家皆未認為必要 ⇒ **維持現狀並在 `R-1`（per-symbol 支援）之殘留註明「屆時須一併改回逐 symbol」**。 |

### 主委之自我記帳

H5 的 oracle 循環相依是**我的重構造成的**：抽出共用函式那一刻，原本「新實作 vs 舊實作」
的比對就變成「新實作 vs 呼叫新實作的東西」。我當時只看到 567 passed 就過去了——
**測試變綠不等於測試還在測東西**。我另外寫的 A/B 探針（`20260910T182032Z-splitunify-clusters-ab`）
才是真的非循環比對，但它是探針不是測試，不會擋回歸。

H1／H2／H3 三條的共同形態是：我把 fail-closed 寫在「數量」上（幾個 symbol、幾個 plan），
而沒寫在「身份」上（哪一個 symbol、哪一批 manifest、哪些列）。codex 用負向注入把三個都打穿。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: `derive_event_split_from_plans` 未強制 `event_keys.event_id` 與 `manifest.table.event_id` 完全 keyed 對齊，會對另一批 manifest 產生看似成功的 assignment。
**碼證**: `split_projection.py:211-238` 逐列採 event_keys，僅在 `:236-238` 以 manifest 建 clusters；實跑 `manifest_id_mismatch` 接受 `foreign`。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#ab39bc4bf68c,docs/SPLITUNIFY_SPEC.md#3e39458b00e4
答1=是：`:201-207` 先處理空 test，再做 set/membership，`:221` 是精確 `>=` 且只 purge train；答3=helper `:130-142` 以 event_id merge、`validate="1:1"`，重複 event_level 實跑為 MergeError，但 derive 直入重複 event_keys 仍會重複輸出；答4=12 keys `:280-293` 通過測試，avg 為 raw cluster rows/distinct clusters，insufficient 以 projected global n_test，在單 symbol fail-closed 路徑等價；答5=抽取後兩路共用 `build_time_clusters`，10k derive=0.029247s。修法：投影前 exact ID set/keyed join fail-closed，並明訂 subset 政策。
## CODEX-R1-P1-02
**斷言**: multi-symbol guard 只檢查各自 symbol 集合的 cardinality，未檢查 plan symbol 與 event symbol 相等；錯誤 plan symbol 可靜默通過。
**碼證**: `split_projection.py:186-196`；實跑單一 ETH event keys 配單一 BTC plans，輸出仍為 ETH 的 train/test assignments，未 raise。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#ab39bc4bf68c,docs/SPLITUNIFY_SPEC.md#3e39458b00e4
修法：要求 plan symbol 非空且與 event symbol 的 exact set 相等；任一缺漏或不一致即在支援性判定前 fail-closed。此為錯誤邊界歸屬，阻擋 B2c。
## CODEX-R1-P1-03
**斷言**: projection 對兩類 malformed feature index 未 fail-closed：混合 seconds/ms index 及負 positional row index 都可被接受並產生錯誤 assignment。
**碼證**: `split_projection.py:76-92,198-207`；實跑 `mixed_seconds_entry_accepted` 與 `negative_row_index_accepted` 均輸出 train assignment、無 raise。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#ab39bc4bf68c,momentum/core/split_preview.py#278b28b30c6e
修法：逐元素確認單一時間單位、finite/NaT 與 row index `0 <= i < len(index)`，並拒絕 invalid/duplicate positions；新增 M-SU-18/M-SU-19。這是資料完整性 gate，不是放寬輸入的選項。
## CODEX-R1-P2-04
**斷言**: `_index_as_ms` 複製 `_as_ms` 的 `1e11` unit policy，形成第二份 arithmetic/policy seam；目前未見合法 homogeneous input 的數值差異，但日後門檻漂移可使投影與 boundary normalization 分歧。
**碼證**: `split_projection.py:76-92` 對照 `split_preview.py:54-81`；兩處各自實作 numeric magnitude guard，projection 不能直接重用 seconds-semantics 的 scalar normalizer。
**來源摘要**: momentum/Analysis/event_samples/split_projection.py#ab39bc4bf68c,momentum/core/split_preview.py#278b28b30c6e
答2=沒有第二份 answer-window/embargo arithmetic；共用 `build_time_clusters` 正確，但 unit policy 是重複。應抽共同 vector/scalar validator 或鎖定 cross-source boundary tests；此外 default `tier_min_test_events=1` 未由純函式 signature 傳入非預設 threshold，B3 需明確責任邊界。
## CODEX-R1-P2-05
**斷言**: mutation harness 尚未覆蓋關鍵 near-boundary、keyed-input 與獨立 oracle，現有 cluster regression 還與被抽取 helper 循環相依。
**碼證**: `test_splitunify_derive.py:318-342` 以已改寫的 `split_events` 作 oracle；mutation script 現有 M-SU-1..7,12,13，均可殺 mutant 但未含下列邊界。
**來源摘要**: tests/momentum/Analysis/test_splitunify_derive.py#4d7eacec7fd5,handoffs/20260911-splitunify-b2b-mutate.py#4521c58f2e9e,momentum/Analysis/event_samples/event_split.py#f9dbcfd3c9d6
答6=需補 M-SU-14（`test_start_ms` 誤改成減 embargo；新增 label_end 在 canonical test start 前 1ms 的 train fixture，原測試 exact-equal 仍會 purge、因此現有 fixture 會假綠）、M-SU-15 duplicate event_level/移除 `validate=1:1`、M-SU-16 plan-symbol mismatch、M-SU-17 manifest ID mismatch、M-SU-18 mixed unit、M-SU-19 negative row、M-SU-20 `>=`→`>`（既有單測會紅但 harness 尚未登錄）；cluster expected output 應改為獨立 frozen oracle。答7=不可以＋P1-01/P1-02/P1-03。
## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–7、主委兩項自查與 A-2 code fence 後無 P0/P1/P2 finding；可進 B2c（golden 五組）。

**碼證**: 兩段式 `split_projection.py:201-234` 對 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md:80-87`；`build_event_keys` merge `split_projection.py:130-132`；抽出 `event_split.py:51-66,160-161`；pytest derive 24/24、mutation UNCOVERED=0、回歸 652 passed（命令見 §0 表）。

**來源摘要**: docs/GAP3_EVENT_SPEC_AMENDMENTS.md#fed0430bf187;docs/SPLITUNIFY_SPEC.md#3e39458b00e4;momentum/Analysis/event_samples/split_projection.py#ab39bc4bf68c;momentum/Analysis/event_samples/event_split.py#f9dbcfd3c9d6

[NON-BLOCKING] 信心度=High。核對依據＝必答 1（A-2 四條機械對照）／必答 3（keyed join 三層防護）／必答 5（byte-identical + 652 回歸）之碼證；主委「複製非抽出」已改為共同呼叫且測試證實；M-SU-4/6/7 fixture 升級後 mutation 全覆蓋。殘差：`_index_as_ms`／`_as_ms` 漂移（必答 2）、`tier_min` 待 B3（必答 4）、10k 效能（brief 成本）——均列為後續，不擋 B2c。

---

## GROK-R1-P2-01

**斷言**: `split_projection._index_as_ms` 與 `split_preview._as_ms` 是兩份獨立的秒級門檻守衛（前者手寫 `1e11`、後者用 `_MS_MAGNITUDE_FLOOR`），且零值／混合量級語意已分歧；改其一不會令另一側測試變紅。

**碼證**: `momentum/core/split_preview.py:51-80`（`_MS_MAGNITUDE_FLOOR=1e11`；`if as_int and abs(as_int) < floor` ⇒ **0 放行**）；`momentum/Analysis/event_samples/split_projection.py:87-91`（字面 `1e11`；`np.all(|v|<1e11)` ⇒ **`[0]` raise**；混合 `[1.7e12, 1.7e9]` **整段放行**）。VERIFY: 本輪探針 stdout 摘要：`as_ms(0)=0`／`index_as_ms([0]) RAISE`／`index_as_ms(mixed)=[1700000000000, 1700000000]`。RECHECK: 同上三案＋確認 `_index_as_ms` 源碼不含 `_MS_MAGNITUDE_FLOOR`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#735445c7ccfc

[MAJOR] 信心度=High。失敗模式：日後只改一邊門檻或放寬混合陣列，B2a 邊界 ms 與 B2b 投影集合用不同單位閘，秒級 FF `timestamps.parquet` 可能一邊 raise 一邊靜默錯 1000 倍。修法：`_index_as_ms` 改 import／共用 `_MS_MAGNITUDE_FLOOR`；混合量級改 fail-closed（任一元素像秒即 raise）；補對測「改 floor ⇒ 兩側同紅」。不擋 B2c，但應進殘留或 B2c checklist。

---

## GROK-R1-P2-02

**斷言**: 現有答案窗 mutation／fixture 擋得住「整段刪除第一段」（M-SU-13）與「`>=`→`>`」（單元測），但擋不住「`>= test_start_ms - 1`」與「改讀已同步的 `time_bounds[0]`」——這兩類在 H1 對齊 fixture 上維持全綠，卻會在毫秒級或 bounds 漂移的真實輸入上錯 purge。

**碼證**: `test_splitunify_derive.py:112-118`／`:152-159`（`label_end`∈{`cutoff+H1`, `test_start`}）；`handoffs/20260911-splitunify-b2b-mutate.py` MUTANTS 無 `>=`→`>`、無 `time_bounds` 替換。VERIFY 探針：`label_end=test_start-1` 時正確碼不 purge、`-1` mutant 會 purge；`_plans` 下 `time_bounds[0]==index[test_rows[0]]` 恆真。RECHECK: 加一筆 `label_end_ms=test_start_ms-1` 的 train 事件斷言仍在 `assignments`；另造 `time_bounds[0]=test_start+H1` 且 `row_index` 不變，斷言仍 purge `label_end==true_test_start`。

**來源摘要**: tests/momentum/Analysis/test_splitunify_derive.py#4d7eacec7fd5

[MAJOR] 信心度=High。失敗模式：實作被改成微偏的答案窗比較或改信 `time_bounds` 時，B2b 綠、B2c golden 若仍用同形 H1 fixture 也綠，直到非對齊真實批才露出 OOS／過度 purge。修法：mutate 表加 M-SU-14‥16（見必答 6）；B2c G-5.4 至少含 `test_start-1` 與 bounds 錯位各一案。不擋開工，擋的是「以為 mutation 已封死答案窗」的過度自信。

---

