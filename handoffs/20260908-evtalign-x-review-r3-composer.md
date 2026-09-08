brief-kind: review
task-id: 20260908-EVTALIGN-X-REVIEW-R3
family: composer
findings-round: R3
標的 commit: `efb16e4c`（B1 實作）；B0 scaffold＋golden 在 `097dae40`

---

## 被當成事實的未驗證假設（§0）

| 前提 | 裁定 | 覆核摘要 |
|---|---|---|
| 新測試 14 條 0 skip | **fact-verified** | `pytest tests/momentum/test_close_coterminalize.py tests/api/test_event_label_alignment.py -q -rs` → 14 passed, rc=0 |
| phase gate 1 mutation 8/8 | **fact-verified** | `bash scripts/evtalign_phase_gate.sh 1` → `GATE PASS: phase=1` |
| split golden 對證 | **fact-verified** | `handoffs/20260907-probe-split-baseline.py` → `與既有 golden 相同？ **True**` |
| stage0 裁切不改 oracle 抽樣 | **fact-verified** | `handoffs/20260908-probe-stage0-trim-oracle.py` → `逐鍵相同 = True` |
| baseline sha 未改碼 | **fact-verified** | `shasum -a 256 -c handoffs/20260908-evtalign-r3-baseline.sha` → 全 OK |
| 守衛 sha256 未動 | **fact-verified** | `test_guard_untouched_sha256_pinned` 在 14 條內通過 |
| close index 單調／唯一 | **fact-verified（推翻 brief 附錄疑慮）** | `_normalize_frame_time_index` → `_normalize_ic_time_index`（`:203-207`）與 feature 同套單調＋唯一檢查 |
| 截短化約為同尾（B） | **fact-verified** | `test_stage2_truncated_labels_equal_coterminal_labels_and_tail_nan_eq_lag` rc=0（真實 `create_label_generator()`） |
| K 線中段 gap 裁切行為 | **unverified** | brief `NOT_RUN`；本輪未構造 |
| tz-aware `asi8//10**6` 鍵 | **needs-research** | brief `NOT_RUN`；未實跑 |
| 端到端 API（`uat_samples/events_ok.json`） | **blocked-by** | 需後端＋K 線快取；本輪未跑 |
| brief 聲稱 golden 8 檔全綠 | **部分推翻** | 本輪 `pytest tests/momentum/Analysis/test_ichc_p2_golden.py::TestTG1Golden::test_feature_set_and_config_exact` → hash 斷言紅（`9fcdd0cb…` vs `c1616bdf…`）；**與 EVTALIGN diff 無交集**，疑環境／config 漂移，不歸因 B1 |

---

## 1a. R2 逐條 CLOSED／OPEN（COMPOSER 覆核；原提出方為準）

| R2 群集 | 原提出方 | COMPOSER 裁定 | 重跑／碼證摘要 |
|---|---|---|---|
| D1 `label_kind` 可偽造 | 三家 | **CLOSED** | `derive_label_kind(label_source)` 由 stage3 產生分支寫定；`None`/`unknown` raise；mutation `D2` 紅、`test_label_kind_missing_source_raises` 綠 |
| D2 `bars_after_target_end` 可偽造 | codex | **CLOSED** | 參數已不存在；`_coterminalize_close` 依 `feature_index[-1]`（`:240-252`）；R2 反例 E（`bars_after=0`）對新碼**不適用** |
| D3 close 污染 oracle 自洽 | codex | **CLOSED** | `validate_alignment` sha256 釘住；`EA-RESID-4` 保留；grok Case H 仍 `PASSES_SELF_FAILS_TRUE`（設計邊界，非新洞） |
| D4 `event_given` 三檢查抓不到平移 | 三家 | **CLOSED** | `validate_event_given` 逐值比對（`:400-406`）＋`event_owners` 綁 id；service `_assert_event_triple_bound`；grok Case I（rotation）在新契約下會紅（`test_event_values_shifted_by_one_row_raise`）；mutation `D1`/`D3` 紅 |
| D5 覆寫前仍跑 forward_return | grok | **OPEN** | **實作刻意保留** stage2 `:2951-2957` 之 `validate_alignment`；與 TODO Task 2.1 要點 3「事件模式覆寫前不驗」**字面矛盾**；見必答 4a/4b 與 `COMPOSER-R3-P1-01` |
| D6 Task 0.2 基線不足 | 三家 | **CLOSED** | golden v2 含 `split_row_fingerprint`＋`retained_event_ids`；probe sha256 `e378c706…` 對證 True |
| D7 excess／risk_adjusted 無 oracle | codex | **CLOSED** | B 不新增 raise；非 oracle 型別截短仍 fail-closed（`ORACLE_RETURN_KINDS` 僅 `log`/`simple`）；`EA-RESID-5` 登記 |
| D9 mutation ID 衝突 | codex | **CLOSED** | `evtalign_phase_gate.sh 1` → 8/8（7 紅＋C0 綠）、`UNCOVERED=0` |
| consult C2 兩呼叫點 | 三家 | **CLOSED** | stage0 `:2814`＋stage2 `:2935`；mutation `B2` 紅；spy 測試綠 |
| consult C4 D 為必要 | codex | **CLOSED** | D 與 B 同批已實作；e2e `test_e2e_event_path_reports_event_given_kind_and_consumed_labels` 綠 |
| D8／D10 | codex | **N/A** | 不在本批（B3/B4） |

**grok 反例腳本重跑**（`handoffs/20260907-evtalign-r2-grok-counterexamples.py`）：

| Case | R2 旗標 | R3 對新碼 |
|---|---|---|
| G `spoof_event_given` | LEAK_BYPASS | **已堵**：`label_source` 由產生者分支導出，非呼叫端 `label_kind` 參數 |
| I `event_value_rotation` | WRONG_JOIN_PASSES | **已堵**：`validate_event_given` 逐值比對 |
| J `event_precheck_excess_trunc` | MISBLOCK_DISCARDED_SCAFFOLD | **仍成立**：stage2 仍驗鷹架 ⇒ 見 D5 OPEN |
| H `polluted_close` | PASSES_SELF_FAILS_TRUE | **殘留**（`EA-RESID-4`，非本輪新引入） |

---

## 必答（成對 verdict）

### 2a. B 會不會漏（裁切後守衛通過但 label 含 look-ahead）

**生成路徑（stage2）主洩漏型態已關。** `_coterminalize_close` 在 `generate_returns_by_type` **之前**裁切（`:2935-2944`），且 `test_stage2_truncated_labels_equal_coterminal_labels_and_tail_nan_eq_lag` 證明截短与同尾逐位元組相同。

殘留邊界（非新 P0）：

1. **stage0 預載 labels**：裁切只動 oracle `close`，**不重生** HDF5 內 label；若磁碟 label 是用更長 K 線離線生成，理論上可與裁切後 oracle 自洽而仍含 look-ahead——`EA-RESID-4` 誠實邊界＋見 `COMPOSER-R3-P1-02`。
2. **close 品質**：污染 close 仍可使 L2 對自身 PASS（grok H）。
3. **中段 gap**：brief 標 `NOT_RUN`，本輪未否證。

非單調／重複 timestamp：**不會**——feature 與 close 皆經 `_normalize_ic_time_index` 強制單調唯一（推翻 brief 附錄「close 是否同樣強制」之未查聲稱）。

### 2b. B 會不會誤擋（合法情形改後被擋）

**截短＋`log`/`simple` 之原 R1 誤擋已修**（14 條內 truncated 測試綠）。`feature_index` 空 ⇒ raise（預期）。K 線尾早於 feature 尾 ⇒ no-op，交守衛（`:251-252` 註解）。未見新誤擋反例。

### 3a. D 會不會漏（通過 `validate_event_given`＋owners＋`_assert_event_triple_bound`）

**未能構造實質 bypass。** 整批平移（grok I）、值旋轉（`test_service_triple_bound_rotated_labels_raise`）、缺 owner／dup owner 皆有測試覆蓋。service 路徑必傳 `event_label_owners`（`:602`），`consumed_event_labels` 空則 `_assert_event_triple_bound` raise。

殘留：`event_owners=None` 時 orchestrator 仍可做值比對但 `consumed_event_labels={}`——**直連 orchestrator、不走 service 的 caller** 可缺 id 綁定；現行產品事件批皆走 service。tz-aware ms 鍵：`needs-research`（brief 未跑）。

### 3b. D 會不會誤擋（合法事件 run 被拒）

**未見。** 密集 event label（`test_event_given_dense_*`）、e2e la0 fixture、fallback `label_source=mainline_return_N` 跳過三元組回比（`:165-166`）皆綠。`float(src)!=float(val)` 精確比對：analyze 與回比之間無 `json.loads`/`model_dump`（`grep` 該區段無序列化）。

### 4a. 保留 stage2 `validate_alignment` 是否成立（刻意偏離 TODO 要點 3）

**部分成立、部分不成立。**

成立面：同一 K 線上，鷹架紅常反映資料品質問題，事件 label 亦建立在同一份 K 線；B 後鷹架與全域消費同一條序列，裁切已化約同尾；跳過會變成 `if 事件: skip validate` 的 §C-6 禁形狀。

不成立面：TODO Task 2.1 要點 3 仍寫「`event_label_value` ⇒ 覆寫前**不驗**」（`:165-169`），與碼**不一致**；事件 label 來自使用者 `event_label_values`，**不必**與 stage2 鷹架一致。grok Case J 仍描述「鷹架被擋、事件 label 其實可用」形態。

**裁定建議**：需 **user-ruling**——要麼改碼（事件＋`event_label_values` 時 skip stage2 守衛）、要麼改 TODO 明文記「刻意保留鷹架驗證」並接受 excess 等非 oracle 截短窗事件路徑可能被擋。

### 4b. 保留會否製造「驗了就丟」擋死？最小修法？

**會，具體情境**：`return_type∉ORACLE`（如 `excess`）＋截短 K 線＋合法 `event_label_values`；stage2 `:2951-2957` 對**即將被覆寫**的鷹架跑 `validate_alignment`（無 close oracle 時僅 Tier-1），可能在 stage3 覆寫前 raise；grok J 同型。

**最小修法（不違 §C-6）**：在 `_stage2_label_generation` 當**已知**下游 stage3 將以 `event_label_values` 覆寫時，**跳過**對鷹架之 `validate_alignment`（非 `if 事件模式` 空泛 skip，而是 `if event_label_values is not None` 且該序列不會被消費）；覆寫後仍走現行 `validate_consumed_label`/`event_given`。或：文件裁決接受此擋死為「同 K 線品質 gate」。

### 5a. mutation 集合夠不夠？列一種 8 條全綠的缺陷

1. **stage0 預載＋截短 K 線**：label 字节與「同尾預載」不等但 oracle 仍 PASS——8 條 mutation 皆未改 stage0 預載 label 內容或測試該對照（僅 stage2 生成路徑有 `test_stage2_truncated_*`）。見 `COMPOSER-R3-P1-02`。
2. （次要）`event_label_owners=None` 缺 id 綁定——無對應 mutation。

### 5b. 8 條紅的理由是否正確？

**是。** 逐條對照 `handoffs/20260907-evtalign-mutate.py`：`B1`/`B2`/`B3`/`D1`/`D2`/`D3`/`A4` 皆 `rc=1`（斷言失敗）；`C0` 註解-only `rc=0`。無 import／語法假紅。phase gate ① 亦驗 0 skip。

### 6. ≥10× 不必要複雜？`event_label_owners`＋`event_label_by_id` 可合一？

**無 ≥10×。** `owners` 為 `{epoch_ms: event_id}`（逐列綁定）；`by_id` 為 `{event_id: label_value}`（service 回比腿）。語意不同、同一迴圈產生（`:567-569`），合一成單一 nested dict 可省一行傳遞但可讀性未必更好——**不列 blocking simplify**。

### 7. 可合併進 B2 還是有 BLOCKING 必先改？

**可合併進 B2（Task 2.2）**，無新 P0。`COMPOSER-R3-P1-01`（D5 TODO／實作偏差）建議在 B2 前拿 **user-ruling** 或同步改 TODO；`COMPOSER-R3-P1-02`（stage0 預載 receipt）可進 B2 參數化測試。不構成 merge-blocking。

---

## COMPOSER-R3-P1-01

**斷言**: 實作保留 stage2 對鷹架之 `validate_alignment`，與 TODO Task 2.1 要點 3「事件模式覆寫前不驗」矛盾；在 `return_type∉ORACLE`＋截短 K 線＋合法 `event_label_values` 下，stage2 可在覆寫前 fail-closed，形成「驗了就丟」擋死（grok Case J）。

**碼證**: `ic_filter_orchestrator.py:2951-2957`（stage2 仍 `validate_alignment`）；`docs/GAP3_EVENT_ALIGNMENT_TODO.md:165-169`（覆寫前不驗）；`handoffs/20260907-evtalign-r2-grok-counterexamples.py` Case J → `MISBLOCK_DISCARDED_SCAFFOLD`。RECHECK: 事件路徑＋`return_type=excess`＋`N_CLOSE>N_FEAT`＋合法 `event_label_values` 跑 `_stage2`→`_stage3` 觀察是否在 stage2 raise。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#ad7b19170f9a; docs/GAP3_EVENT_ALIGNMENT_TODO.md#e2b6c6eebb68

[MAJOR] 信心度=High。非新洩漏，是 **TODO／實作／R2 D5 未閉** 之治理項。不修理由=`user-ruling`（brief 必答 4a 已請裁定）。修法見必答 4b。

---

## COMPOSER-R3-P1-02

**斷言**: B 的「截短化約為同尾」僅在 stage2 **生成**路徑有逐值測試；stage0 **預載** labels 在截短 K 線下未驗「磁碟 label 字节＝同尾預載」，mutation 8 條亦未覆蓋。

**碼證**: `test_stage2_truncated_labels_equal_coterminal_labels_and_tail_nan_eq_lag` 僅呼叫 `_stage2_label_generation`；stage0 `:2808-2821` 裁切 close 但不重生 HDF5 label；mutate 清單無「stage0 預載 label 漂移」項。RECHECK: 預載 labels（`N_FEAT` 行）+ reader `N_CLOSE` 跑 `_stage0_ingestion`，比對 label payload sha256 与同尾 reader `N_FEAT`。

**來源摘要**: tests/momentum/test_close_coterminalize.py#9c8aeb691151; momentum/Analysis/ic_filter_orchestrator.py#ad7b19170f9a

[MAJOR] 信心度=Medium。誠實邊界＋測試缺口，非已證實 prod 洩漏。不修理由=`needs-research`（需確認產品是否用「長 K 線離線 label + 短 feature」預載組合）。建議 B2 增 stage0 預載對照或登記 `EA-RESID` 若確認不存在該用法。

---

## §1 必查摘要

| 類 | 結果 |
|---|---|
| 1 矛盾 | D5：TODO 要點 3 vs 實作 → P1-01 |
| 2 漏項 | stage0 預載 receipt → P1-02；tz-aware → needs-research |
| 3 不可測 | mutation＋14 條＋gate 可執行；API e2e blocked-by |
| 4 quant | B 截短主徑封住；D 值綁定＋三元組封住旋轉 |
| 5 過度工程 | 無 |
| 6 OOM | 未改 hot path；110 格 `_assert_event_triple_bound` O(n_events) 可忽略 |
| 7 Cache | 未動 cache key |
| 8 API/相容 | forward_return 路徑無新報告鍵（§G-1 設計） |
| 9 測試 | 核心邊界有測；stage0 預載截短缺口 → P1-02 |
| 10 Agent | B+D 落地與 SPEC 大致一致，除 D5 |
| 11 短命工 | 無；D 為永久契約 |

---

## Verdict：可合併——R2 六 P0 形態已消除；D5（TODO 偏差／鷹架擋死）需 user-ruling 或同步改 TODO；無新 P0

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `pytest tests/momentum/test_close_coterminalize.py tests/api/test_event_label_alignment.py -q -rs` | 14 passed, 0 skip, rc=0 |
| `bash scripts/evtalign_phase_gate.sh 1` | `GATE PASS: phase=1` |
| `venv/bin/python handoffs/20260907-probe-split-baseline.py` | `與既有 golden 相同？ **True**` |
| `venv/bin/python handoffs/20260908-probe-stage0-trim-oracle.py` | `逐鍵相同 = True` |
| `shasum -a 256 -c handoffs/20260908-evtalign-r3-baseline.sha` | 全 OK |
| `venv/bin/python handoffs/20260907-evtalign-r2-grok-counterexamples.py` | 見 1a 表 |
| `pytest tests/momentum/event_samples/test_gap3_conditional_ic.py tests/momentum/Analysis/test_ichc_p2_golden.py -q` | 13 passed, **1 failed**（`test_feature_set_and_config_exact` hash 漂移，疑非本票） |

---

ASSUMPTIONS_VERIFIED: 驗收命令×5、grok 反例重跑、`_normalize_frame_time_index` 讀碼、stage2/stage3 流程讀碼
TESTS_RUN: 見 VERIFY
FAILURES_SEEN: `test_ichc_p2_golden.py::test_feature_set_and_config_exact`（本輪重跑，與 EVTALIGN diff 無關，未阻斷本輪裁定）
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）
產出檔: handoffs/20260908-evtalign-x-review-r3-composer.md

STATUS: DONE
