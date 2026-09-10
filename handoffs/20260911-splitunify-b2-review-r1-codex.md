不可進 B2c：CODEX-R1-P1-01、CODEX-R1-P1-02、CODEX-R1-P1-03。
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
## Verdict
不可以進 B2c；修正三個 P1 並補上述 mutation/oracle coverage 後重審。
