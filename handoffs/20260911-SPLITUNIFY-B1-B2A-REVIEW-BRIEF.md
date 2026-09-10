# SPLITUNIFY B1＋B2a code review（R1）

brief-kind: review
task-id: 20260911-SPLITUNIFY-B1-REVIEW-R1
findings-round: R1

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；
findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`，結尾附 **Verdict**。
**禁改碼**（發現問題寫進你自己的交件檔）；碼證以檔案:行號指名。

## 審查對象（兩批合審）

- **B1**（commit `9607430d`）：`docs/GAP3_EVENT_UX_SPEC.D-002.md`（新）、
  `docs/GAP3_EVENT_UX_SPEC.md`（只動延伸索引行）、
  `momentum/Analysis/contracts/split_unify.json`（新）、
  `tests/momentum/Analysis/test_splitunify_contract.py`（新）、
  `tests/baselines/analysis_known_failures.nodeids`（新）、
  `handoffs/run_receipts/splitunify-analysis-baseline.stdout`（新）。
- **B2a**（commit `a58754d6`）：`momentum/core/split_preview.py` 新增
  `holdout_boundary` 與 `_as_ms`；`tests/momentum/core/test_splitunify_boundary.py`（新）。

規格：`docs/SPLITUNIFY_SPEC.md`（v5）之 C-0／C-4／C-8／Task 1.1／1.2／1.3／2.1；
`docs/SPLITUNIFY_TODO.md`（v5）同編號。

## 主委已跑的驗收（請複驗，別照抄）

- `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py` → **8 passed**。
  mutation：JSON 加回 `assignment_states` ⇒ **1 failed**；移除 ⇒ 8 passed。
- `venv/bin/python -m pytest -q tests/momentum/core/test_splitunify_boundary.py` → **9 passed**。
  mutation `M-SU-11` 兩個方向：(a) `test_start_ms` 改 `index[split_point]`（略過 purge+embargo）
  ⇒ **1 failed**（`ms_same_source`）；(b) `test_rows` 自算且漏 embargo ⇒ **2 failed**；還原 9 passed。
- `venv/bin/python -m pytest -q tests/momentum/core` → 75 passed；
  `tests/api/test_evtlabel_staging.py` → 40 passed。
- `bash scripts/template_check.sh dext docs/GAP3_EVENT_UX_SPEC.D-002.md` → PASS。
- `bash scripts/check_decoupling.sh` → `R2=1 R3=17 R4=3`，**逐值等於**
  `scripts/decouple_baseline.txt`（rc=1 為既有債，非本批新增）。
- Task 1.3 基準：`tests/momentum/Analysis` 實跑 **19 failed / 1103 passed / 15 skipped / 1011.82s**，
  receipt 內 `pytest_rc=1`；19 條 nodeid 全數 `--collect-only` rc=0。

## 🔴 必答

1. **B2a 的 `holdout_boundary` 真的沒有第二份算術嗎**？請正面掃：
   有沒有哪一個回傳值是「看起來同源、實際上另算」的？`_as_ms` 對
   `pd.Timestamp`／`np.datetime64`／`int64` 三種輸入的行為一致嗎？時區呢？
2. **`test_rows` 為空時回 `None`** 是否會讓下游踩到？誰會消費 `test_start_ms`？
   （SPEC 說「空段先 fail-closed／轉 event-study-only」，但 B2a 的 builder 本身
   只回 `None` 不 raise——這個分工對嗎？）
3. **B1 的契約測試是不是「兩端對證」**？B1 不動生產碼，所以還沒有 `split_projection.py`
   可對 Python 常數，我改用「SPEC 文件字面」當第二來源。這算真對證還是自證？
   若不算，B1 應該怎麼做才對（在不動生產碼的前提下）？
4. **Task 1.3 的基準清單可信嗎**？19 條 vs `HANDOFF.md` 記的 20 條不一致——
   是我少抓了，還是既有紅本來就會飄？請用碼證判斷，並說「這個差異要不要處理」。
5. **D-002 有沒有寫錯或漏寫**？特別是「覆寫」欄宣告的兩條（B1.3 邊界來源、
   事件掃描報告三鍵）是否確實對應原檔的真實條文？
6. **`docs/GAP3_EVENT_UX_SPEC.md` 只動索引行**是否合規？
   （`FROZEN_DOC_AMENDMENT_PROCEDURE_V2` §2.3 說那是唯一允許的原檔改動。）
7. **可否進 B2b**（投影純函式）？直接回「可以」或「不可以＋ID」。

## 停輪條件

① 必答 1–7 皆有明確立場；② 必答 1／4 有具體檔案:行號或實跑輸出；
③ 三家若分歧，各自寫出**判準**（看碼證不數人頭）；
④ 禁以「三家零 finding」當停輪——零 finding 須走 sentinel 契約。

## 本 brief 之前提（逐條標）

fact-verified: 上方所有數字皆為主委實跑，命令逐字如上。

fact-verified: `_normalize_ic_time_index` 拒收毫秒 → `momentum/Analysis/ic_filter_orchestrator.py:269-271`，故 B2a 自帶 `_as_ms` 而非復用它。

assumed: `holdout_boundary` 目前**無 caller**（B3 才接線），故本批不可能改變任何既有數值
← 否證觀測：`grep -rn holdout_boundary momentum api` 命中測試以外的生產路徑。
／我跑了：**沒跑**。請正面打（必答 1）。

assumed: 既有紅 19 vs 20 之差是測試間污染造成的浮動，非本批引入
← 否證觀測：以 `git stash` 回到 B1 之前重跑得到 20 條且差集包含本批新增檔。
／我跑了：**沒跑**（該重跑要 17 分鐘）。請正面打（必答 4）。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| `_as_ms` 對 tz-aware DatetimeIndex 的行為 | 有時區的 index 會位移數小時 | cost |
| `tests/baselines/` 這個新目錄有沒有被既有 pytest 收集規則掃到 | 清單檔被當測試檔收集而報錯 | cost |

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md` 與任何 reconcile synth。
- 不得跑 `pytest tests/governance`（小時級）；跑 `tests/momentum/Analysis` 全套要 17 分鐘，
  非必要別跑（要跑請說明為什麼）。
- 跑完測試請 `bash scripts/restore_golden_inventory.sh`。
- 收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（第一句必須是「可進 B2b」或「不可進 B2b：<ID>」）。
