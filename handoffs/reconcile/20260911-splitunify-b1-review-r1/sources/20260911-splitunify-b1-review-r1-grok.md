# SPLITUNIFY B1＋B2a code review R1（grok）

brief-kind: review  
task-id: 20260911-SPLITUNIFY-B1-REVIEW-R1  
family: grok  
findings-round: R1  
標的：B1 commit `9607430d` ＋ B2a commit `a58754d6`  
規格：`docs/SPLITUNIFY_SPEC.md`（sha256 `1bf699fbde5b…`）／`docs/SPLITUNIFY_TODO.md`（sha256 `f18c6a09ec30…`）  
SCOPE: review-only；禁改碼／禁改 `docs/SPLITUNIFY_*.md`／禁改 reconcile synth  
**範本**：`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄

### §0 前提宣告（本輪覆核）

fact-verified: B1／B2a 檔案與 commit 一致 → `git show --stat 9607430d a58754d6`

fact-verified: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py tests/momentum/core/test_splitunify_boundary.py` → **17 passed**；mutation 加回 `assignment_states` → `test_assignment_states_must_not_exist` 紅、還原後 8 passed

fact-verified: `holdout_boundary` 生產 caller＝0（僅 `split_preview.py` 定義＋`test_splitunify_boundary.py`）→ `grep -rn holdout_boundary momentum api`（測外無命中）

fact-verified: 四回傳欄皆同源 → 以 N=20352 實跑：`train/test_row_index`＝既有兩支；`train_end_ms`／`test_start_ms`＝`_as_ms(index, rows[±])`（見必答 1）

fact-verified: `_as_ms` 對 naive DatetimeIndex／UTC／`datetime64`／int64 **ms** 一致；`Asia/Taipei` tz-aware 相對 naive 偏 −8h；int64 **秒**（FF `timestamps.parquet` 同形）→ year=1970（當 ms 解）

fact-verified: Task 1.3 receipt 內 `19 failed, 1103 passed, 15 skipped`＋`pytest_rc=1`；`awk '/^FAILED /{print $2}' … | grep '::' | sort -u` 與 `tests/baselines/analysis_known_failures.nodeids` **逐行相等**；`--collect-only` 19 collected rc=0

fact-verified: `docs/GAP3_EVENT_UX_SPEC.md` B1 只改索引行一處 → `git diff e0f3cb52 9607430d -- docs/GAP3_EVENT_UX_SPEC.md`；`template_check.sh dext` PASS；`check_decoupling.sh` 印 `R2=1 R3=17 R4=3`＝`decouple_baseline.txt`

fact-verified: BASE `GAP3_EVENT_UX_SPEC.md` **無** `B1.3` heading（grep count=0）；真文在 `docs/GAP3_EVENT_SPEC.md:168` `**Task B1.3 — …**`

assumed: HANDOFF「20 failed／1615 passed」與本 receipt「19／1103」非同一套件快照（passed 差 ~500）→ 未重跑全套 Analysis（brief 非必要勿跑 17 分）；以 receipt 自洽＋集合差為準（必答 4）

assumed: B3 接線會把 post-trim `feature_index` 以 **ms 相容**形態餵給 boundary／投影 → 否證觀測＝FF parquet 為秒、orchestrator `_normalize_ic_time_index` 為秒語意；若直餵則踩 P2-02

---

## Verdict：可進 B2b

B2a 列計畫無第二份算術、B1 契約／基準／D 延伸索引行程序合規；殘留為 D-002 覆寫錨點跨檔、`_as_ms` 單位／時區防禦不足、SPEC 回傳形與 Task 1.3「20 條」散文漂移——皆 **P2／P3，不擋投影純函式開工**。B2b 開工 checklist 必須自帶 ms 單位閘（勿盲複用 `_as_ms` 的 int 直通）。

---

## 必答 1–7

### 1. `holdout_boundary` 有沒有第二份算術？`_as_ms` 三種輸入／時區？

**沒有第二份切分算術。** 回傳四欄皆「看起來同源、實際也同源」：

| 欄 | 來源 | 碼證 |
|---|---|---|
| `train_row_index` | `np.arange(0, holdout_split_point(...))` | `split_preview.py:101-102` |
| `test_row_index` | `holdout_test_row_index(...)` | `:103-105` |
| `train_end_ms` | `_as_ms(index, train_rows[-1])`（空⇒None） | `:110` |
| `test_start_ms` | `_as_ms(index, test_rows[0])`（空⇒None） | `:111` |

實跑 N=20352／OOS=0.3／purge=12／embargo=144：`np.array_equal` 對既有兩支通過；ms 等於 `_as_ms` 對應列。無「另算 split_point／另跳過 purge」的隱藏路徑。生產 caller＝0（brief assumed 成立）。

**`_as_ms` 行為（實跑）：**

- `pd.Timestamp`／`np.datetime64`／naive／UTC DatetimeIndex／int64 **毫秒**：同一牆鐘 → 同一 epoch ms。
- **tz-aware 非 UTC**（`Asia/Taipei`）：相對同 civil label 的 naive **偏 −8h**（`Timestamp.value` 走 UTC epoch）。
- int64 **秒**（與 `data_cache/features/**/timestamps.parquet` 同形）：走 `return int(value)` 直通 → 當 ms 解 year=1970。見 **GROK-R1-P2-02**。

### 2. `test_rows` 空時回 `None`——下游會踩嗎？分工對嗎？

**目前不會踩；分工正確。** 今日消費 `test_start_ms` 的只有 `test_splitunify_boundary.py`（`test_test_rows_empty_returns_none_not_zero`）。生產尚無 caller。

SPEC C-4／D-002 §D2-2 寫死投影端：

```text
if test_plan.row_index.size == 0:
    raise ValueError("missing_test_plan: …")  # 先 fail-closed，禁與 None 比較
test_start_ms = as_ms(feature_index[test_plan.row_index[0]])
```

⇒ builder 回 `None`（禁 −1／0）＋投影／接線先驗空段 raise，符合「空段 fail-closed／轉 event-study-only」的分層：B2a 不決定政策，只不造假數字。B2b／B3 若漏先驗、直接 `label_end_ms >= test_start_ms` 會 TypeError——屬接線漏測，不是 builder 該 raise 政策例外。

### 3. B1 契約測試是不是「兩端對證」？

**是「文件字面對證」，不是「實作兩端對證」。** `test_every_reason_appears_verbatim_in_spec` 把 SPEC 當第二來源；同 PR 可同時改 JSON＋SPEC 字面而雙綠——擋不住「兩邊一起寫錯」。  
但 B1 不動生產碼、無 `split_projection.py` 常數可對，此折衷**可接受於 B1**，且另有：

- 封閉集合 exact set（四 reason／`kline_holdout`／`full_sample_not_oos`）
- `assignment_states` 禁回潮（本輪 mutation：加回 → 1 failed；移除 → 8 passed）
- purge reason 釘在 `event_import_contract.json`

**B1 在不動生產碼前提下應做的**＝現狀＋檔尾 TODO（B2b 加 JSON↔Python 常數）已寫明；建議 B2b 第一批就落地該條，並把 SPEC Task 1.2 驗證欄「與 Python 常數集合相等」改成與現況一致（或等 B2b 真有常數後再算驗收通過）。見 P3-02。

### 4. Task 1.3 基準清單可信嗎？19 vs 20？

**本 freeze 以 receipt 為準，可信；HANDOFF「20」不可當同一快照。**

| 來源 | failed | passed | 備註 |
|---|---|---|---|
| B1 receipt `splitunify-analysis-baseline.stdout` | **19** | 1103 | `pytest_rc=1`；19 條 `FAILED …::…` |
| `analysis_known_failures.nodeids` | **19** | — | 與 receipt `grep '::'` **exact match** |
| HANDOFF.md 既有紅盤點 | 20 | 1615 | passed 差 ~500 ⇒ **不是同一次／同一收集範圍** |

判準：差異要處理，但處理對象是 **HANDOFF／SPEC Task 1.3 目標句仍寫「20 條」的散文**，不是把清單灌回 20。無碼證的第 20 條不得手補。污染造成「少一條變綠」可由「只准變短」協議吸收。未做 `git stash` 前回跑（17 分）；B1 新增 8 條皆綠，本身不會把 failed 20→19。見 P3-01。

### 5. D-002 有沒有寫錯或漏寫？

**語意方向對；覆寫錨點程序不合格。**

- 「B1.3 …每 symbol 各自按時間切＋緩衝 ≥ 答案窗」逐字對得上 `docs/GAP3_EVENT_SPEC.md:168-172` 的 Task B1.3 改法——但 D-002 的 **BASE 是 `GAP3_EVENT_UX_SPEC.md`**，該檔 **0 個 B1.3 heading**。違反凍結程序「觸及面錨點＝原檔實際存在的 heading 逐字」（v1 §2／v2 §2.2；`template_check` 只驗非空、不驗存在）。見 **GROK-R1-P2-01**。
- 第二條覆寫（`summary.split`／`n_train`／`n_test`／`n_purged` 移除＋`capability.split=unavailable`）：對得上實碼 `pipeline.py:729-732` 寫死 0 與 `EventTablesPanel.tsx:352` 假 OOS 顯示；UX SPEC 有 Task 1.12 event-study-only，但**沒有**與這三鍵同名的 heading。§D2-5 內容本身正確，宣告欄應改指 UX 內真實 heading（如 Task 1.12）或明寫「覆寫實碼報告鍵、非原檔 heading」。

### 6. 原檔只動索引行是否合規？

**合規。** `git diff e0f3cb52 9607430d -- docs/GAP3_EVENT_UX_SPEC.md` 僅一行：  
`延伸: D-001 …` → `延伸: D-001 …, D-002 docs/GAP3_EVENT_UX_SPEC.D-002.md`。  
符合 `FROZEN_DOC_AMENDMENT_PROCEDURE` v1 §1／§3 與 V2 §2.3「唯一允許的原檔改動＝索引行」。

### 7. 可否進 B2b？

**可以。** 判準：B2b＝投影純函式；B2a 列計畫同源已立、答案窗兩段式契約在 SPEC C-4／D-002 §D2-2；本輪無 P0／P1 擋投影簽名可執行性。P2-02 必須進 B2b checklist（`as_ms` 單位閘），不回退重做 B2a 才能開工。

---

## GROK-R1-P2-01

**斷言**: D-002「覆寫」欄宣告的 `B1.3 事件切分` 不是其 BASE（`docs/GAP3_EVENT_UX_SPEC.md`）內任何 heading；真文住在兄弟檔 `docs/GAP3_EVENT_SPEC.md` Task B1.3——凍結 D 延伸的觸及面錨點規則被架空，後續讀者／機檢無法對讀原檔。

**碼證**: `docs/GAP3_EVENT_UX_SPEC.D-002.md:3` BASE＝`GAP3_EVENT_UX_SPEC.md @ e0f3cb52`；`:12` 覆寫寫 `**B1.3 事件切分**`；`grep -c 'B1\.3' docs/GAP3_EVENT_UX_SPEC.md` → 內容提及亦無 Task heading；`docs/GAP3_EVENT_SPEC.md:168` 才有 `**Task B1.3 — per-symbol 時間切分＋…**`，改法句含「每標的各自按時間切＋緩衝 ≥ 答案窗」。`scripts/template_check.sh` dext 段註明「是否為原檔實際 heading 屬語意，交審查者」。RECHECK: 對 BASE 跑 `grep -n 'B1\.3\|^## \|^### ' docs/GAP3_EVENT_UX_SPEC.md | head`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.D-002.md#92cd70b1f366

[MAJOR] 信心度=High；**不擋 B2b**。修法：覆寫改指 UX SPEC 內真實 heading（例如 Task 1.12 之 event-study-only／報告鍵語意），並交叉引用 `GAP3_EVENT_SPEC` B1.3；或升 R／另開以 EVENT_SPEC 為 BASE 的延伸。勿再寫不存在於 BASE 的 `B1.3`。

---

## GROK-R1-P2-02

**斷言**: B2a `_as_ms` 對 int64 假設「已是 epoch ms」直通、對非 UTC tz-aware 會平移絕對 ms，且無測試鎖這兩條；與 FF `timestamps.parquet`（秒）及 orchestrator 秒語意同形的輸入會得到 year=1970 的「邊界」，B2b／B3 若複用會讓答案窗比較靜默錯位。

**碼證**: `split_preview.py:49-58`（datetime → `Timestamp.value//10**6`；else `int(value)`）；實跑 Taipei vs naive 差 8h；實跑 `pd.Index([1704067200+…])` → `train_end_ms=1705323600`、`unit='ms'`→1970、`unit='s'`→2024。現測只覆蓋 DatetimeIndex／int64 **ms**（`test_splitunify_boundary.py:91-96,100-105`），無秒級／tz-aware 用例。FF 樣本 `data_cache/features/BCHUSDT/1h/…/timestamps.parquet` 首值 `1704067200`（秒）。RECHECK: 對 `_as_ms` 餵秒 Index 與 `tz='Asia/Taipei'` Index；對照 `feature_reader.py:205` `unit="s"`。

**來源摘要**: momentum/core/split_preview.py#58a4ef2c7033

[MAJOR] 信心度=High；**不擋 B2b 開工**，但 B2b 的 `as_ms`／`feature_index` 契約須先 fail-closed（拒秒級 int、拒非 UTC tz，或先正規化），**禁止**盲 `from momentum.core.split_preview import _as_ms`。可選回修 B2a 加數量級閘＋兩條紅測。

---

## GROK-R1-P3-01

**斷言**: Task 1.3 目標句／HANDOFF 仍寫「20 條」既有紅，與 B1 凍結的 receipt／nodeids **19** 條不一致；passed 基數 1615 vs 1103 證明「20」不是本 receipt 的漏抓。

**碼證**: SPEC Task 1.3「把 HANDOFF…之 20 條落成」；HANDOFF.md:50「20 failed／1615 passed」；receipt 末行 `19 failed, 1103 passed, 15 skipped`＋`pytest_rc=1`；`diff <(awk …|grep '::') tests/baselines/analysis_known_failures.nodeids` 空。RECHECK: 重讀 receipt 摘要與 HANDOFF 段；勿在無新跑下把清單改回 20。

**來源摘要**: handoffs/run_receipts/splitunify-analysis-baseline.stdout#（pytest_rc=1）

[MINOR] 信心度=High；**不擋 B2b**。修法：主委更新 HANDOFF 散文為 19／1103（或註明舊快照）；SPEC／TODO 目標句改「以 B1 receipt 凍結之 N 條」免寫死 20。

---

## GROK-R1-P3-02

**斷言**: SPEC／TODO Task 2.1 輸入輸出仍寫元組形 `(train_row_index, …)`，B2a 實作回 `Dict[str, Any]`；Task 1.2 驗證欄仍寫「與 Python 常數集合相等」，B1 實測是 SPEC 字面對證——文件驗收句與交付不一致，B3 呼叫端可能按 tuple unpack 寫錯。

**碼證**: SPEC:417-418／TODO:153-154 之 `→ (train_row_index, …)`；`holdout_boundary` `:107-112` `return {…}`；測試一律 `out["test_start_ms"]`；SPEC Task 1.2 驗證「JSON 之值集與 Python 常數集合逐值相等」vs `test_splitunify_contract.py:2-7,97-109` 明文改 SPEC 字面。RECHECK: `sed -n '415,420p;360,370p' docs/SPLITUNIFY_SPEC.md` 對照 `split_preview.py:61-112`。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#1bf699fbde5b

[MINOR] 信心度=High；**不擋 B2b**。修法：Task 2.1 改標 `Dict`／TypedDict；Task 1.2 驗證改「B1＝SPEC 字面；B2b＋＝Python 常數」。

---

## 被當成事實的未驗證假設（§0）

- brief assumed「`holdout_boundary` 無生產 caller」→ **本輪確認成立**（測外 0 hit）。
- brief assumed「19 vs 20 是污染浮動」→ **部分成立、證據不足當唯一解釋**：receipt 自洽 19；HANDOFF 20 的 passed 基數不同，更像舊／異範圍快照，不是「同跑漏一條」。未 stash 重跑全套。
- 「`_as_ms` 對三種輸入一致」→ **對 datetime／ms 成立；對秒級 int／非 UTC tz 不成立**（P2-02）。
- 「`tests/baselines/` 會被 pytest 當測試收集」→ **否證**：`python_files=test_*.py`，`--collect-only tests/baselines/` → 0 items。

STATUS: DONE
