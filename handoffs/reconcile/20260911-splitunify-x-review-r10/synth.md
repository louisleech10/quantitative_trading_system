# Reconcile — 20260911-splitunify-x-review-r10

**來源** 20260911-splitunify-x-review-r10-codex.md, 20260911-splitunify-x-review-r10-grok.md　|　**roster** codex,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-001.md

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **W1 唯讀旗標可被翻回，沒有任何 numpy 層做法能完整封住**——「D-001:72的defensiveco」 | P1 | CODEX-R10-P1-01 | 採納（斷言全採，主委實跑複驗並把結論推得更明確：`setflags` 唯讀可被同一物件翻回可寫，改以 `frombuffer` 之不可變底雖擋得住翻回，但 `pickle` 與 `deepcopy` 還原後仍為可寫 ⇒ **不可變性無法作為權威保證**。🔴 修法落點改變：權威守衛改為**入口重驗**——`row_time_fingerprint` 為字串欄、凍結擋得住改綁，投影入口本就以傳入索引重算並比對，故竄改 `row_index_local` 已被現行比對點擋下；不可變性降為縱深防禦並明寫其誠實邊界。竄改 `row_index` 只影響全框消費端、不影響投影，登記為殘留） |
| **W2 亂序輸入之直呼叫路徑會被新增閘擋下**——「`timedelta`producer路」 | P1 | CODEX-R10-P1-02 | 採納（斷言屬實：正常汲取路徑有排序，但直呼叫與舊呼叫端無保證。🔴 修法不是保留該閘再加例外，而是**換掉判準**：attest 改用與面板順序無關之時間序往返，於是亂序輸入不再被誤擋，同時仍驗得出真正的寫入錯誤。刪除 R9 所寫之前提條款與 `M-SU-D1-15`，改立往返不成立應紅之變異） |
| **W3 主委自產：判準選錯不變式**——「D-001:72的defensiveco」 | P2 | CODEX-R10-P1-02 | 採納（主委於本輪派工後自產並另檔立案（檔名見本輪程序記錄）：R9 之 attest 判準驗的是 frame 序，而待驗語意是時間序，今日碰巧相等不代表判準正確。🔴 誠實記錄：該條初判寫「會弄紅現行活路徑」，主委三次探針後**自行推翻並降級**，第三次探針證實生產面板標的內必為時間遞增；保留它是因修法建議更優，非因原斷言成立。與 W2 合併為同一修法） |
| **W4 sentinel**——「本輪逐項核對後無finding；`COD」 | P3 | GROK-R10-P3-00 | 採納（紀錄；該家接受主委對凍結斷言之更正，並明說其 R9 之 proceed 當時應為 blocked，屬可驗證之自我修正。其獨立實查「生產面板標的內時間遞增」與主委複驗一致。🔴 惟其必答二稱 `asarray` 與切片「已封住」，經 W1 之實跑推翻——唯讀旗標可翻回，該句不採） |

**Verdict**: 需修補後合併——W1 與 W2 為 P1 擋項，W3 併入 W2 之修法，W4 為紀錄。D-001 依上表修訂後須由原提出方於 R11 重驗閉合。本輪兩家所附戳記因規格續有實質改動而失效，須重簽。

## 本輪程序記錄

- 本輪兩家裁決再次相反（一家 blocked 開兩條 P1、一家 proceed 為 sentinel），主委一律以實跑判定，不數人頭。
- 主委實跑（不可變性三組對照）：`np.asarray` 對唯讀陣列回傳**同一物件**，`setflags(write=True)` **成功**，寫入後原陣列讀回 `[99, 2]`；`pickle` 與 `deepcopy` 還原後 `writeable` 皆為真。改以 `np.frombuffer(bytes)` 為底者，翻回可寫被擋（訊息為 cannot set WRITEABLE flag to True），但 `pickle`／`deepcopy` 還原後仍為可寫。⇒ 三種做法皆不足以作為權威保證。
- 由此導出之判準轉向：既然建構期保證不可信，權威守衛必須在**消費入口**。現行 C2 第 6 點之比對點已具此性質，且 `row_time_fingerprint` 為字串欄（Python 字串不可變、凍結擋改綁）⇒ 竄改 `row_index_local` 後入口重算必不相符。此為既有機制，非新增。
- 主委抽驗 W2 之碼證：`momentum/FeatureEngineering/feature_factory.py:796` 確有 `data.sort_index()`；`api/services/ic_analysis_service.py:1787-1792` 為逐標的 `concat` 後 `set_index`，不另行排序，故其順序承自汲取層。直呼叫與舊呼叫端無保證一節屬實。
- 主委自產之 W3 立案檔為 handoffs/20260912-SPLITUNIFY-CHAIR-R10-SELFFINDING.md，留存完整的自我推翻過程（P1 降 P2），作為「初判被自己的探針否證」之稽核紀錄。
- 兩家戳記（codex 與 grok 之 sha 皆為 `84942a34…`）於本輪交件檔內，因 D-001 續改而失效。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R10-P1-01
**斷言**: D-001:72 的 defensive copy＋`setflags(write=False)` 仍不足以維持 attest 後兩欄不可變。
**碼證**: `venv/bin/python -c 'import numpy as np,pickle; x=np.array([1,2]); x.setflags(write=False); y=np.asarray(x); y.setflags(write=True); y[0]=99; z=pickle.loads(pickle.dumps(x)); print("same",y is x,"after_reenable",x.tolist(),"pickle_writeable",z.flags.writeable)'` → `same True after_reenable [99, 2] pickle_writeable True`; deepcopy probe → `deepcopy_writeable True`; D-001:72,125-126。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#84942a34e86c
必答1：`CODEX-R9-P1-01` 規格層已閉合；body hash 實跑為 `84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c`，且 D-001:72、125-126 已納入兩條原回歸。
必答2：未完全封住；`np.asarray` 同物件、slice、`deepcopy`、`pickle.loads` 均可取得可寫路徑。`replace`／consumer `.copy()` 不會回寫原 plan，但不能抵銷上述 bypass；需補不可重新開寫的 backing 或完整 copy/pickle/deepcopy lifecycle guard。
## CODEX-R10-P1-02
**斷言**: `timedelta` producer 路徑未保證每個 symbol 的輸入 frame 按時間排序；新增 fail-closed 會改變現有亂序輸入的行為。
**碼證**: `ic_filter_orchestrator.py:1966-69` 只驗 MultiIndex，`:861-64` 保留輸入順序，`:923-930` 走 `split_per_symbol(..., purge_semantic="timedelta")`，而 `contracts.py:656-661` 另行按時間排序；亂序 probe → `True False {'BTCUSDT': False, 'ETHUSDT': False} 2`（現行 path 通過）。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#84942a34e86c
必答3：正常 factory ingestion 在 `feature_factory.py:795-796` 排序、service `ic_analysis_service.py:1787-1792` 保留各 symbol 排序；但 direct/legacy caller 未受保證，具體會被新擋的是 `analyze_cross_sectional`→`_build_cross_sectional_global_split`→`:930`。
必答4：接受主委更正；本家 R9 是 blocked 方，非「proceed」方；因此本家裁決不因該事實更正而改變。
必答5：`VERDICT: blocked`；若不補，attest 後可由可寫/反序列化 plan 造成兩欄漂移，且未排序既有 caller 會在 b8 被新閘擋下。
ASSUMPTIONS_VERIFIED: D-001／TODO／R9 synth 已讀；D-001 hash、格式、template、attribution、synth-xref 均實跑通；numpy re-enable/deepcopy/pickle 與 timedelta 亂序 producer probe 已實跑。
TESTS_RUN: `bash scripts/agent_preflight.sh` rc=0；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` rc=0；doc_format/template/attribution/synth-xref rc=0；兩組 `venv/bin/python -c` probe 如上。
FAILURES_SEEN: `spec_xref_check.sh --synth` 首次少傳 target rc=2，補正為 `... synth.md docs/SPLITUNIFY_SPEC.D-001.md` rc=0；未跑 governance 全套。
SCOPE_CHANGES: 僅新增本交件檔；未改 tracked code/data，未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；review only，未改產品數值、schema、golden 或輸出大小。
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r10-codex.md
TMP_CLEANUP: `/private/tmp` 無 `*workdir*` 目錄可清；保留 `/private/tmp/claude-501`。
RECONCILE-STAMP: codex APPROVED 2026-09-12 sha256:84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c task:20260911-SPLITUNIFY-X-REVIEW-R10
VERDICT: blocked
BLOCKED-BY: CODEX-R10-P1-01,CODEX-R10-P1-02
CLOSED: CODEX-R9-P1-01
STATUS: DONE
## GROK-R10-P3-00

**斷言**: 本輪逐項核對後無 finding；`CODEX-R9-P1-01` 已由 D-001 之 defensive copy＋唯讀＋ASSERT／mutation 閉合，timedelta 綠徑實查不受新 fail-closed 誤傷，可進 b8 實作。

**碼證**: 對讀 D-001:72-73／:105／:125-127／:153-155；R9 synth W1／W2；現行 `contracts.py:377-403` 仍無 copy／setflags（待 b8）；`contracts.py:562-568`／:657／:510-519；`ic_filter_orchestrator.py:923-934`／:1968-1969／:751；等價 `__post_init__` 探針（原地／別名／asarray／切片／replace 封住；pickle／deepcopy 還原 writeable）；`from_product`→`_cross_sectional_to_split_frame`→timedelta splitter 實跑 `ALL_EQ True`；打亂 index 對照 `eq=False`。`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#84942a34e86c；handoffs/reconcile/20260911-splitunify-x-review-r9/synth.md#249fe2729b18；handoffs/20260911-splitunify-x-review-r9-grok.md#8f07b4076af9；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_filter_orchestrator.py#4b1b8bc9f22a；momentum/Analysis/event_samples/split_projection.py#98ee62905643；handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R10-BRIEF.md#4938b6cb6e1e

本輪為閉合確認：必答 1–5 皆有立場與碼證；零實質新 finding，故以 sentinel 收斂，未捏造擋項。R9 本家對 frozen 的錯誤事實斷言已在必答 4 接受更正。

---

RECONCILE-STAMP: grok APPROVED 2026-09-12 sha256:84942a34e86cb6234d9fe7d11602a600541dba683d8ed74398afd0c161a1409c task:20260911-SPLITUNIFY-X-REVIEW-R10

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE

ASSUMPTIONS_VERIFIED: brief／HANDOFF／R9 synth／修訂後 D-001／現行 SplitPlan 可變性／split_per_symbol 排序／helper frame 序／:930 timedelta 路徑／from_product 綠徑與打亂對照／deepcopy+pickle 探針已核對。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-001.md` → `84942a34e86c…`；venv python 現行 SplitPlan 原地＋別名 → `[99, 6]` writeable；等價 post_init 探針；from_product timedelta `ALL_EQ True`；completeness 見下。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-x-review-r10-grok.md
TMP_CLEANUP: `find /tmp -maxdepth 1 -mindepth 1 -iname '*workdir*'` → 無候選；已保留 `/tmp/claude-501`。
