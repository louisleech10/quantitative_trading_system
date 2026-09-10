不可進 B2c：CODEX-R3-P1-01、CODEX-R3-P1-02。

# SPLITUNIFY B2b 定向確認 R3（codex）
task-id: 20260911-SPLITUNIFY-B2-REVIEW-R3  
family: codex  
review-object: commit `a8474406`；review-only，禁改碼。

## 必答 1：I1–I6

I1 **未閉合＋CODEX-R3-P1-01**：數值型 index 有嚴格遞增閘，但 `DatetimeIndex` 分支旁路；I2 **閉合**（finite/整數性於 cast 前驗證，M-SU-22）；I3 **閉合**（兩個 event_id 欄位各自驗唯一，M-SU-23）；I4 **閉合**（row_index cast 前驗整數，M-SU-24）；I5 **閉合**（三個事件時間欄 finite/整數毫秒、答案窗不反轉，M-SU-25）；I6 **閉合**（bucket_ms 正值閘，M-SU-26）。

## 必答 2：新一批負向注入（逐條實跑）

| 注入 | 結果與 stdout 摘要 |
|---|---|
| `symbol=None` | **未擋**：`PASS_THROUGH ... symbol=None ... n_symbols=0, per_symbol_n={}` |
| `symbol=""` | **已擋**：`ValueError: multi_symbol_projection_unsupported` |
| 混合 `str+None` | **未擋**：兩筆 assignment，含 `symbol=None`；`n_symbols=1` |
| 混合 `str+int` | **已擋**：`ValueError ... ['12345', 'ETHUSDT']` |
| 缺 `manifest.summary.n_events_raw` | **已擋但訊息裸**：`KeyError: 'n_events_raw'` |
| `time_bounds` 與 `row_index` 不一致 | **未擋例外且行為正確**：`split_label=train`；集合語意符合 C-4，非 finding |
| `feature_index` 全同值（數值） | **已擋**：`ValueError ... 時間戳非嚴格遞增 ... 重複（共 99 處）` |
| 超大 `bucket_ms=10**30` | **未擋＝合法**：`n_clusters=1`，weights `[0.3333333333333333]*3` |
| 單列 cutoff＝test 首根 | **未擋＝正確**：`split=['test'] purged=0` |
| 單列 cutoff＝train 末根 | **未擋＝正確**：`split=['train'] purged=0` |
| 反序 `DatetimeIndex` | **未擋＋算錯**：`actual_test_start_ms=1700090000000`、`earliest_test_ms=1700000000000`，`e_train_ok→test` |
| 重複 `DatetimeIndex` | **未擋**：`PASS_THROUGH assignments=2`；同值數值 index 則已擋 |
| reversed `test_plan.row_index` | **未擋＋算錯**：`reported_test_start_ms=1700356400000`、`true_test_start_ms=1700266400000`，`e_leak` 留在 `train`、`purged=[]` |

R2 既有九條重放：`venv/bin/python handoffs/20260911-probe-splitunify-negative-injection.py` → `未如預期者 = 0 / 9`、rc=0。

## 必答 3：`strictly_increasing` 的範圍

事件欄不套嚴格遞增是正確的：兩事件同一根 bar 實跑 `K two events same cutoff` → 兩筆 train assignment、weights `[0.5, 0.5]`，集合語意無洞。可是 `feature_index` 的 DatetimeIndex 旁路不是事件欄放寬造成的洞；它使 I1 只對數值 dtype 閉合，見 `CODEX-R3-P1-01`。

## 必答 4：可否進 B2c

**不可以＋CODEX-R3-P1-01、CODEX-R3-P1-02。**

## CODEX-R3-P1-01

**斷言**: `DatetimeIndex` 型 `feature_index` 未經嚴格遞增／去重驗證；反序時投影會靜默錯分，且 canonical `holdout_boundary` 同樣跳過此閘。

**碼證**: `split_projection.py:87-90` Datetime 分支直接回傳 `idx.asi8 // 10**6`；`:91-93` 的 `strictly_increasing=True` 只在非-Datetime 分支執行；`split_preview.py:222-226` 以 `not isinstance(index, pd.DatetimeIndex)` 跳過同一驗證。實跑 stdout：`L reversed DatetimeIndex: PASS_THROUGH actual_test_start_ms=1700090000000 earliest_test_ms=1700000000000 ... e_train_ok ... test`；`M duplicate DatetimeIndex: PASS_THROUGH assignments=2`。RECHECK：以同一反序／重複 DatetimeIndex probe 餵 `derive_event_split_from_plans` 與 `holdout_boundary`，兩者都應 raise。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#524f585c8d96;momentum/core/split_preview.py#75869791fe9f

[BLOCKING] 信心度=High；B3／生產特徵索引可為 DatetimeIndex，壞順序會令 `test_rows[0]` 不是最早 test 時刻，train event 可被錯標 test 或答案窗邊界錯位；若 B2c golden 只用數值 index 會假綠。修法：Datetime 轉毫秒後也走同一嚴格遞增 validator，並新增反序／重複 Datetime golden 與 mutation。

## CODEX-R3-P1-02

**斷言**: `assert_positional_rows` 只驗範圍／唯一性、不驗順序；reversed `test_plan.row_index` 會以最新 test row 當 `test_start_ms`，讓跨入實際 test 首根的 train event 留在 train。

**碼證**: `split_projection.py:264-277` 直接以 `index_ms[test_rows[0]]` 取邊界；`split_preview.py:121-154` 的 `assert_positional_rows` 沒有遞增檢查；canonical producer `holdout_test_row_index` 雖回傳 `arange`，投影入口未防範被改序的 plan。實跑 stdout：`O reversed test row_index: PASS_THROUGH reported_test_start_ms=1700356400000 true_test_start_ms=1700266400000 result=[{'event_id': 'e_leak', 'symbol': 'ETHUSDT', 'split_label': 'train'}] purged=[]`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#524f585c8d96;momentum/core/split_preview.py#75869791fe9f

[BLOCKING] 信心度=High；這是可具體造成 OOS leakage 的 boundary-input 變形，會在 B2c 未覆蓋的 plan 順序下使 B3 接線產出錯誤 train/test／purge 集合。修法：對 `test_plan.row_index` 驗證嚴格遞增（或在取首列前以獨立 canonical 順序驗證），並加入 reversed-plan negative golden。

## CODEX-R3-P2-03

**斷言**: `event_keys.symbol=None` 時 symbol 守衛被跳過，投影輸出 `symbol=None` 且 summary 的 symbol 計數為空，未 fail-closed。

**碼證**: `split_projection.py:214-216` 過濾 `None`；`:235` 只在 `symbols` 非空時比較。實跑 stdout：`A symbol=None: PASS_THROUGH ... assignments.symbol=None, n_symbols=0, per_symbol_n={}`；`C mixed str+None: PASS_THROUGH`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#524f585c8d96

[MAJOR] 信心度=High；不擋 B2c 合法 golden，但 B3 上游漏填 symbol 時會靜默形成不完整 summary。修法：把 None／缺值視為 invalid symbol，在 exact-set 守衛前 fail-closed。

## CODEX-R3-P3-04

**斷言**: `manifest.summary` 缺 `n_events_raw` 時雖會擋下，但 `_build_summary` 直接索引造成使用者看到無語意的裸 `KeyError`。

**碼證**: `split_projection.py:357-360` 直接讀 `manifest.summary["n_events_raw"]`；實跑 stdout：`E manifest.summary missing n_events_raw: BLOCKED KeyError: 'n_events_raw'`。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#524f585c8d96

[NON-BLOCKING] 信心度=High；此為錯誤可讀性與輸入契約診斷問題，不造成錯誤 OOS 數字，故不擋 B2c。修法：入口顯式檢查 summary 必填鍵並 raise 帶欄名／manifest context 的 ValueError。

## 三家分歧與判準

Grok R3 與本 review 依「可重現 malformed input 造成 OOS 邊界錯分＝P1」判定 Datetime 旁路為阻擋項；Composer R3 只將 `symbol=None` 列為 P2 並以合法 golden 不受影響為可進判準。Codex 另依同一碼證標出 reversed `test_plan.row_index`，因 probe 實際顯示 train leakage；判準看失敗模式與 stdout，不以家數表決。

ASSUMPTIONS_VERIFIED: I1 數值路徑閉合但 Datetime 路徑否證；I2–I6 閉合；事件欄重複合法；新一批注入逐項輸出如上；R2 九條全擋。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/test_splitunify_derive.py -q` → 43 passed, rc=0；`venv/bin/python handoffs/20260911-splitunify-b2b-mutate.py` → UNCOVERED=0、21 mutants rc=1、C0 rc=0；`venv/bin/python handoffs/20260911-probe-splitunify-negative-injection.py` → 9/9、rc=0；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` → PASS、rc=0；`bash scripts/check_decoupling.sh` → R2=1 R3=17 R4=3、既有違規 rc=1；`bash scripts/restore_golden_inventory.sh` → rc=128（sandbox 無法建立 `.git/index.lock`，inventory diff=none）。
FAILURES_SEEN: 首次 pytest 與 mutation 並行造成 4 個競態假紅；待 mutation 完成後序列重跑 43 passed。該次結果不採用。
SCOPE_CHANGES: none；未改 source、spec、todo、test 或 reconcile synth。
NUMERIC_OR_SCHEMA_IMPACT: review only；未改數值、schema、輸出大小。
OUTPUT_ARTIFACT: handoffs/20260911-splitunify-b2-review-r3-codex.md

## Verdict

不可進 B2c：CODEX-R3-P1-01、CODEX-R3-P1-02；`CODEX-R3-P2-03` 與 `CODEX-R3-P3-04` 明確不擋 B2c。
STATUS: DONE
