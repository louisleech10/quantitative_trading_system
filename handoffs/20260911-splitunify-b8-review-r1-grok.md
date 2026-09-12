# SPLITUNIFY b8 審碼 R1（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R1  
family: grok  
findings-round: R1  
標的：`0190c918..HEAD` 七筆 b8 程式／測試 commit（HEAD=`da4bdc4370b9`）  
SCOPE: review-only；禁改碼  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄  
探針：`/tmp/grok-b8-review-r1/probe_all.py`、`probe_float_and_adapter.py`（stdout 同目錄 `*.out`）

### §0 前提宣告（本輪覆核）

fact-verified: HEAD=`da4bdc4370b9`（`git rev-parse`）。

fact-verified: `-k 'per_symbol or fingerprint or insufficient'` → **22 passed / 56 deselected**；`test_splitunify_producer_attest.py` → **19 passed**。

fact-verified: 交錯 `split_per_symbol` 之 `sorted_positions[row_index_local] == row_index` 四組 plan 全 True；orchestrator holdout 之 `row_index_local` 逐值等於 `row_index`。

fact-verified: 三 producer 在 int64 epoch-秒／DatetimeIndex 存活路徑上，指紋端點 ms 與 `time_bounds` 端點 ms **相等**；orchestrator 對 float epoch-秒在 `holdout_boundary` 即 raise，**產不出**自我矛盾 plan。

fact-verified: 指紋閘與遞增閘合取——中列時刻偏移僅指紋擋；同集合重排指紋相同、由遞增閘擋（訊息含「非嚴格遞增」）。

fact-verified: `pickle`／`deepcopy` 往返後陣列可寫；成員竄改與重排皆在投影入口被擋。協調改寫 `row_index_local`＋指紋＋`time_bounds` 可通過（一致性守衛，非真偽守衛；與 SPEC (4.13)／SU-RESID-5 誠實邊界一致）。

fact-verified: `_SYMBOL_SET_MISMATCH` 字面僅出現於 `split_projection.py`（無 frontend／api 分支依賴）。

assumed: IC 端到端真實 run 未另開；本輪以 producer 單元建構＋derive 入口＋定向 pytest 為界。  
← 否證觀測：若真實 IC run 傳入非 int64／非 DatetimeIndex 之 index 語意且繞過既有 normalize 閘，需另票重開。

---

## 必答 1 — 座標語意

**立場：三個 producer 寫入的 `row_index_local` 皆為「該標的依時刻排序後」的序號。**

| producer | 碼證 | 實跑 |
|---|---|---|
| `split_per_symbol` | `contracts.py:741` `sort_values` → `positions`；`:748-775` 直接寫 `train_local_arr` 為 `row_index_local`；`:804-808` attest 用同一 `positions` | 交錯 8×2：ETH train `loc=[0..3] ri=[0,2,4,6]`，`roundtrip_ok=True` |
| `ic_split_adapter` | `ic_split_adapter.py:64-65` `group_sorted`／`positions`；`:233-255` 同語意；CPCV／WF 皆先 sort | 源碼兩處 `split_cpcv`／`split_wf` 皆 `sort_values` 後取 local |
| `ic_filter_orchestrator` holdout | `:636-638` 單標的 ⇒ local＝row_index；`:675` attest 用 `arange(n)`；前置 `_normalize_ic_time_index` 要求單調遞增（`:287-288`） | `local==row_index` True；在「index 已時間單調」前提下 arange＝時間序 |

未構造出「其實是 frame 序」的反例：交錯 fixture 下 local≠全框 `row_index`，且時間序往返成立。

---

## 必答 2 — 指紋時鐘

**立場：存活輸入上三處端點 ms 與 `time_bounds` 一致；orchestrator 函式名不同但值等價。**

| producer | 指紋時鐘 | `time_bounds` 時鐘 | 實跑 |
|---|---|---|---|
| `split_per_symbol` | `_coerce_timestamp_array` → DatetimeIndex → `epoch_ms_from_index`（`:732,758-762`） | `_time_bounds_for_indices` → 同 `_coerce`（`:700-707,768`） | 端點 ms 相等 |
| `ic_split_adapter` | 已 coerce 之 `ts` → `epoch_ms_from_index`（`:239-243`） | `pd.Timestamp(ts[rows][…])`（`:306-311`） | 同一 datetime64 陣列之兩種讀法 |
| orchestrator | `_normalize_ic_time_index` → `epoch_ms_from_index`（`:603,642-646`） | `_time_bounds_for_rows` → `_coerce_timestamp_array`（`:559-564,651`） | int64 秒／DatetimeIndex：端點相等；**float 秒**：normalize→1970、coerce→2023（值分叉），但 `_build_holdout_split_plan` 在 `holdout_boundary` raise「looks like epoch seconds」，**不產出 plan** |

結論：brief 之 assumed「皆取 time_bounds 那一支」在 orchestrator 上**函式名不成立**（指紋取切邊界那支 normalize），但在可產出 plan 的輸入上**數值等價**；未能給出「兩端指紋永遠對不上」的存活輸入。

---

## 必答 3 — 守衛合取

**立場：指紋閘與遞增閘為真合取；各有僅自身能擋的輸入。**

1. **僅指紋擋**：`_basic_case` 索引中列 `+1`（首尾不變、序號不變）→ `assert_positional_rows` 仍過；derive raise「指紋不符」（`probe_all` C1）。  
2. **僅遞增擋（指紋無感）**：同集合交換 `row_index_local[0]↔[1]` → `build_row_time_fingerprint` 兩次 hash **相同**（先 `argsort`）；derive raise「非嚴格遞增」（C2）。  
反證「一閘可涵蓋另一閘」不成立。

---

## 必答 4 — 入口重驗覆蓋

**立場：只改 `row_index_local`（含 pickle／deepcopy 還原後原地寫）會被入口擋；協調偽造全部 attested 欄不在 (4.13) 威脅模型內。**

| 攻擊 | 結果 |
|---|---|
| 建構後 `object.__setattr__` 改成員 | 指紋不符（D1） |
| `pickle` 往返後原地改成員（writeable=True） | 指紋不符（D2） |
| `deepcopy` 後原地改成員 | 指紋不符（D3） |
| `pickle` 後同集合重排 | 遞增閘擋（D4） |
| 同時改 local＋重算指紋＋對齊 `time_bounds` | **放行**（D5）——入口只驗「plan 與傳入 feature_index 一致」，不驗「仍是原 producer 意圖」 |

D5 與 SPEC (4.13)「權威＝入口重驗、不是不可變性」及 SU-RESID-5 誠實邊界一致；不另開 finding。未找到「只竄改 local 卻靜默錯分」的繞過。

---

## 必答 5 — 測試鑑別力（3 條）

| 測試 | 「仍綠但程式已壞」的改法 |
|---|---|
| `test_fingerprint_passes_when_index_is_identical` | 刪除投影入口指紋相等檢查：本測只 assert assignments 非空 → **仍綠**。鑑別力在姊妹測 `mid_row_shift`／`tampered_rows`。 |
| `test_fingerprint_independent_oracle_matches_producer_value` | producer 與本測 oracle **共用** `build_row_time_fingerprint`；把序列化改成無意義但仍兩端一致（如恒寫同一形狀）→ 本測仍綠。`M-SU-D1-08` 收據已證須靠 `freeze_splitunify_golden.py` 抓形狀漂移。 |
| `test_interleaved_producer_writes_monotonic_local_ordinals` | attest 拿掉時間序往返、只留遞增／dtype → 本測只看 `np.diff(loc)>0` → **仍綠**。姊妹測 `local_differs_from_full_frame`／`attest_rejects_when_roundtrip_differs` 補洞。 |

單測有空洞，但 b8 測試面＋ mutation 22/22 CAUGHT 使上述改法會被其他條抓到；不升級為產品缺陷 finding。

---

## M-SU-D1-23 裁定

**表態：維持 `needs-research`；本輪不建議為單條 mutation 把 golden 改成兩標的交錯並重凍。**

理由（實跑）：`freeze_splitunify_golden.py` 以 `b["test_row_index"]` 同時指派 `row_index` 與 `row_index_local`；單標的下兩欄逐值相同 ⇒ oracle 改用 `row_index` 重算與用 local 重算 hash 相同（`probe_all` F／`_basic_case`）。交錯語意已由 `test_splitunify_producer_attest.py` 的 interleaved 測與 derive `-k per_symbol` 交錯 fixture 覆蓋；重凍會移動既有 digest，成本大於多抓一條「oracle 座標選錯」mutation 的邊際收益。若日後 b9／digest 本就要動，再順手改 fixture 使 23 可觸發。

---

## 主動攻擊面（停輪條件③）

已攻擊且**未成功**開洞者：①三 producer 座標是否實為 frame 序；②orchestrator 雙函式時鐘能否產出端點分叉之存活 plan；③指紋／遞增是否可互相涵蓋；④pickle／deepcopy 只改 local 繞過入口；⑤`_SYMBOL_SET_MISMATCH` 是否有消費端依賴舊字面。皆未構成 b8 收案阻擋項。

---

## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding——必答 1–5 皆有碼證與實跑／反例；主動攻擊之座標／時鐘／合取／pickle／鑑別力面均未找出需阻擋 b8 收案的缺陷；M-SU-D1-23 維持 needs-research 不重報。

**碼證**: `PYTHONPATH=. python /tmp/grok-b8-review-r1/probe_all.py` → EXIT 0（C1 指紋擋、C2 遞增擋、D1–D4 入口擋、D5 協調偽造放行但合 SPEC）；`probe_float_and_adapter.py` → float holdout raise、DatetimeIndex 端點相等、`_SYMBOL_SET_MISMATCH` 無跨層消費；`pytest … -k 'per_symbol or fingerprint or insufficient' -q` → 22 passed；`pytest tests/momentum/core/test_splitunify_producer_attest.py -q` → 19 passed；HEAD=`da4bdc4370b9`。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B8-REVIEW-R1-BRIEF.md#5d03282d463f;docs/SPLITUNIFY_SPEC.D-001.md#73eec02bc26f;handoffs/run_receipts/20260912-splitunify-b8-mutation-selfcheck.md#fe67c1637668;momentum/core/contracts.py#9c81df6c2808;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;momentum/Analysis/ic_split_adapter.py#a3da0c9b8555;momentum/Analysis/event_samples/split_projection.py#a77abd9bf671;momentum/core/split_preview.py#95a85ec0de54

[MINOR] 信心度=High。sentinel only；非實質缺陷。

---

## 被當成事實的未驗證假設（§0）

1. 「指紋時鐘＝各 producer 的 time_bounds 那一支」——orchestrator **函式名不成立**、**存活數值成立**（本輪 fact-verified）。  
2. 「`_SYMBOL_SET_MISMATCH` 不進封閉值集不削弱守衛」——本輪 grep 無消費端分支依賴該字面 → **HOLDS**（未查前端枚舉 UI 文案，僅碼依賴）。  
3. 「IC 真實 e2e run 與單元路徑等價」——仍為 assumed（本輪未跑 e2e）。

ASSUMPTIONS_VERIFIED: 必答 1–5 實跑／反例如上；mutation 收據 22 CAUGHT／23 不可觸發與 freeze 碼證一致；定向 pytest 22+19 passed。  
TESTS_RUN: `pytest tests/momentum/Analysis/test_splitunify_derive.py -k 'per_symbol or fingerprint or insufficient' -q` → 22 passed；`pytest tests/momentum/core/test_splitunify_producer_attest.py -q` → 19 passed；探針兩支 EXIT 0。  
FAILURES_SEEN: none（產品路徑）；預期負向（C1／C2／D1–D4）皆按設計擋下。  
SCOPE_CHANGES: none（review-only）。  
NUMERIC_OR_SCHEMA_IMPACT: none。  
HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b8-review-r1-grok.md`

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
