# Reconcile — 20260911-splitunify-b2-review-r3

**來源** 20260911-splitunify-b2-review-r3-codex.md, 20260911-splitunify-b2-review-r3-composer.md, 20260911-splitunify-b2-review-r3-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併——三條全採納**且已修完**；修完即進 B2c，**不再開 R4**（收斂斷路器）。

三家：codex（2 P1＋1 P2）、grok（1 P1＋1 P2）、composer（1 P2，判可進）。
兩條 P1 皆有**兩家獨立命中**，第三條有**三家獨立命中**。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **J1 `DatetimeIndex` 分支繞過遞增檢查** | **P1** | CODEX-R3-P1-01、GROK-R3-P1-01 | **採納，已修**。🔴 R2 我補了 `assert_epoch_ms_array` 的嚴格遞增，但 `_index_as_ms` 的 `DatetimeIndex` 分支**直接 `return`**、`holdout_boundary` 亦然 ⇒ **只修了一半**。反序的 DatetimeIndex 會靜默錯分，與 R2 那個數值反序洞是同一機制。⇒ 兩處 Datetime 分支都改為先轉毫秒再過同一支 validator。 |
| **J2 `row_index` 未驗順序** | **P1** | CODEX-R3-P1-02 | **採納，已修**。範圍與唯一性都驗了，**順序沒驗**——反序的 `test_plan.row_index` 會讓 `test_rows[0]` 取到**最晚**的 test row ⇒ `test_start_ms` 錯 ⇒ 跨進實際 test 首根的 train 事件留在 train。⇒ `assert_positional_rows` 加 `require_sorted`（預設 True）。 |
| **J3 `symbol=None` 讓三道守衛整條被跳過** | P1（三家共識為 P2，主委上調） | CODEX-R3-P2-03、COMPOSER-R3-P2-01、GROK-R3-P2-02（**三方獨立命中**） | **採納，已修**。原本寫 `{str(s) for s in ... if s is not None}` ⇒ 全為 `None` 時集合為空 ⇒ 後面的 `if symbols and ...` 整條跳過＝**fail-open**，還會輸出 `symbol=None` 的 assignment、`n_symbols=0`。⇒ **不先濾**：任一 symbol 為 `None`／空字串即 raise。🔴 主委把它由 P2 上調為 P1——理由：它與 J1／J2 同屬「守衛被靜默跳過」，且輸出**看起來正常**，比會 raise 的錯更危險。 |

### 共同形態（第三次出現）

三條又是同一形態的變體：**守衛存在，但有一條路徑繞過它**——
J1 是型別分支繞過、J2 是檢查不完整、J3 是前置過濾把觸發條件消掉。
⇒ 教訓：加守衛時要問「**有沒有哪條 input 路徑走不到這裡**」，而不只是「這個檢查對不對」。
已寫進 `HANDOFF.md` 踩坑節。

### 收斂斷路器：B2b 到此為止

| 輪 | 群集 | P1 | 性質 |
|---|---|---|---|
| R1 | 8 | 3 | 身份對帳（manifest／symbol）、oracle 循環相依 |
| R2 | 7 | 5 | 輸入不變式（遞增／唯一／finite／整數／正數／區間） |
| R3 | 3 | 3 | **繞過路徑**（型別分支／檢查不完整／前置過濾） |

三輪 P0 皆為 0，群集數 8 → 7 → **3**，且 R3 三條全部當輪修完並各配 mutation
（`M-SU-27`／`28`／`29`，UNCOVERED=0）。依 `feedback_epic_convergence_breaker` 與
`feedback_95_percent_then_record`：**不再開 R4**，進 B2c；B2c 自己還有一輪 review 可再驗。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R3-P2-01

**斷言**: `event_keys.symbol=None` 时第三道 symbol 守卫被跳过（`None` 被 filter 掉），derive 可产出 `assignments.symbol=None` 且 `summary.n_symbols=0`，fail-open 而非 fail-closed。

**碼證**: `split_projection.py:214` `if s is not None` 过滤后 `symbols` 为空集，`:235` `if symbols and ...` 不触发；实跑 A `symbol=None: PASS_THROUGH ... n_symbols=0`。RECHECK: `venv/bin/python /tmp/composer_r3_neginject.py` 看 A 行。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#cfd519d61cf8

[MAJOR] 信心度=High；B2c golden 恒有合法 symbol 故不阻 golden 五组；B3 per-symbol 接线上游若漏填 symbol 会静默产出空 `per_symbol_n` 而非 raise。**不挡 B2c**；建议 B3 checklist 补 `symbol.isna()` gate 或把 `None` 视同无效 symbol 参与 exact-set 比对。

---

## GROK-R3-P1-01

**斷言**: I1 未閉合：`DatetimeIndex` 的 `feature_index`（以及 `holdout_boundary` 的 Datetime 入口）跳過嚴格遞增／去重檢查，反序時會靜默錯分 train／test，與 R2 數值反序洞同一機制。

**碼證**: `split_projection.py:87-90` Datetime 分支只擋 NaT 後直接返回 ms；`:91-93` 的 `strictly_increasing=True` 僅數值分支。`split_preview.py:222-226` `holdout_boundary` 以 `not isinstance(..., DatetimeIndex)` 跳過同一閘。VERIFY（worktree `a8474406`）：反序 DT＋原 positional plans → `PASS_THROUGH`、`mismatch=True`、`e_train_ok` 之 `split_label=test`（sorted DT 對照為 `train`）；重複 DT → `DUP_DT_PASS`，同值數值 index → `ValueError…重複`。既有 `test_unsorted_feature_index_is_fail_closed` 只用 `pd.Index(int64)[::-1]`，未覆蓋 DT。RECHECK: 反序／重複 `DatetimeIndex` 餵 `derive_event_split_from_plans` 與 `holdout_boundary` 皆應 raise；修法建議 Datetime 轉 ms 後仍走 `assert_epoch_ms_array(..., strictly_increasing=True)`（或等價 `is_monotonic_increasing` 且無重複）。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#524f585c8d96;momentum/core/split_preview.py#75869791fe9f

[BLOCKING] 信心度=High。不改會怎麼在 B2c／B3 失敗：B3／生產特徵索引常為 `DatetimeIndex`；若順序被打亂或含重複戳，投影不 raise 卻把 train 事件標成 test（或答案窗邊界錯位）→ golden（G-1／G-3）若只以數值 fixture 綠燈會**假綠**，接線後 OOS 標籤／purge 集合同步錯。與 I1 原採納理由相同，故 **擋 B2c**。

---

## GROK-R3-P2-02

**斷言**: `event_keys.symbol` 全為 `None` 時，symbol 三道守衛因 `if s is not None`／`if symbols and …` 被跳過，投影 `NO_RAISE` 並輸出 `symbol=None` 的 train assignment。

**碼證**: `split_projection.py:214` `symbols={str(s) … if s is not None}`；`:236` `if symbols and symbols != plan_symbols`。VERIFY：`A_symbol_None` → `PASS_THROUGH assign=[{…'symbol':None,'split_label':'train'}]`；對照 `""`／`nan`／`pd.NA`／`' '` 皆 BLOCKED。RECHECK: 空／None symbol 應 fail-closed（與 `split_events` 對 manifest 缺 symbol 的閘對齊）。

**來源摘要**: momentum/Analysis/event_samples/split_projection.py#524f585c8d96

[MAJOR] 信心度=High。**不擋 B2c**（B2c golden／B3 `build_event_keys` 上游通常帶非空 symbol；`split_events` 另有 symbol 閘）。屬公開純函式殘留不變式，建議 B3 接線前補或記入 `SU-RESID-*`。

---

