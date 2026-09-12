# SPLITUNIFY 第 8 批（b8）審碼 R1

brief-kind: review
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R1
findings-round: R1

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；
findings 用 `## <FAMILY>-R1-P<0-3>-<NN>` **二級**標題，結尾附 **Verdict**。
`CLOSED:` 無內容**留空**、不得寫 `none`；完成訊號**逐字** `STATUS: DONE`（裁決 blocked 也一樣）。
🔴 **禁改碼**（唯讀審查）。🔴 **P0／P1 必附修法與可行性評估**，只點出問題不算完成。

## 審查對象

b8 之七筆 commit（`git log 0190c918..HEAD`）：

| commit | 內容 |
|---|---|
| `f75454c9` | 三個產生端寫入並 attest `row_index_local` 與逐列時刻指紋 |
| `927161a9` | 凍結腳本改用共用指紋序列化器 |
| `40ccc40c` | 投影支援 per-symbol 批（R-1），修逐標的門檻判定 |
| `29582d96` | 指紋時鐘改取 plan 自己 `time_bounds` 的那一支（修上一批的自傷缺陷） |
| `dc0757b8` | 補 Task 8.1／8.3 驗收斷言；修違反 C1 第 3 點的 fail-closed 訊息前綴 |
| `b272286f` | 新增 producer attest 與 `SplitPlan` 座標欄契約測試 |
| `8f2c228a` | 補兩個由 mutation 自證撈出的測試缺口 |

範圍檔：
`momentum/core/contracts.py`、`momentum/core/split_preview.py`、
`momentum/Analysis/event_samples/split_projection.py`、
`momentum/Analysis/ic_split_adapter.py`、`momentum/Analysis/ic_filter_orchestrator.py`、
`scripts/freeze_splitunify_golden.py`、
`tests/momentum/Analysis/test_splitunify_derive.py`、
`tests/momentum/core/test_splitunify_producer_attest.py`、
`tests/momentum/event_samples/test_splitunify_wiring.py`

規格（已定案、三家戳記核可）：`docs/SPLITUNIFY_SPEC.D-001.md`，Task 8.1／8.2／8.3 與
`M-SU-D1-01`～`23`。

## 前提（fact-verified，附可複驗出處）

fact-verified: 三個驗收命令 `-k per_symbol`／`-k fingerprint`／`-k insufficient` 在本批之前
對 `test_splitunify_derive.py` **各收到 0 條**（`56 deselected / 0 selected`）→ 主委實跑 `pytest --collect-only`
fact-verified: `attest_row_index_local` 在本批之前於 `tests/` 之引用數為 0 → `grep -rln`
fact-verified: mutation 22 條執行、22 條被抓到；首輪 4 條未被抓到之逐條處置與第 23 條不可觸發理由
→ `handoffs/run_receipts/20260912-splitunify-b8-mutation-selfcheck.md`
fact-verified: 本批回歸為零——`tests/momentum`＋`tests/api` 浮現之 10 筆紅，在把六個生產檔整組
`git checkout 0190c918` 後**同樣全紅**（還原前後各以 `grep -c row_index_local` 驗證 checkout 生效）
→ 主委實跑對照
fact-verified: `CrossSymbolLeakageError` 繼承 `ValueError` → `momentum/core/contracts.py:431`

assumed: 指紋時鐘取「該 producer 自己 `time_bounds` 已在用的那一支」對三個 producer 皆正確
→ 否證觀測：必答 2 指出任一 producer 的 `time_bounds` 與指紋用到不同時鐘的具體路徑／
我跑了: 目標測試面與 golden 凍結比對，**未**跑 IC 端到端真實 run
assumed: `_SYMBOL_SET_MISMATCH` 不進封閉值集不會削弱守衛
→ 否證觀測：必答 3 指出有消費端依賴該字面做分支／我跑了: `grep` 該字面之消費端，**未**查前端

## 必答（成對，缺一不算完成）

1. **座標語意**：三個 producer 寫入的 `row_index_local` 是否**都**是「該標的依時刻排序後」的序號？
   逐一給出碼證行號；若有任一處其實是 frame 序，給出會錯分的具體反例。
2. **指紋時鐘**：`split_per_symbol`／`ic_split_adapter`／`ic_filter_orchestrator` 三處，
   指紋用的時鐘與該 plan `time_bounds` 用的時鐘**是否同一支**？各給碼證；
   若有不同，給出兩端指紋永遠對不上的具體輸入。
3. **守衛合取**：指紋閘與遞增閘是否真為合取？請各給一個**只有該閘能擋**的輸入；
   若你認為某一閘可被另一閘完全涵蓋，請給出反證輸入。
4. **入口重驗的覆蓋**：`row_index_local` 在建構後被竄改的路徑，是否**全部**會在投影入口被擋？
   請嘗試構造一條繞過（含 `pickle`／`deepcopy` 往返），並說明擋不擋得住。
5. **測試鑑別力**：任挑 3 條本批新增測試，各構造一個「該測試仍綠但程式其實壞了」的改法；
   若構造不出來，說明你嘗試了什麼。

## 停輪條件

①必答 1–5 皆有立場；②必答 2–4 須附**實跑或具體反例**，不得只讀規格推論；
③🔴 **禁以「無 finding」當停輪**——若你判定可收案，必須說明你**主動攻擊過哪些面**而未成功；
④若仍 blocked，須說明「不改會在 b8 收案或 b9 實作時具體怎麼失敗」。

## 已具名殘留（請裁定，不要當成缺陷重報）

- `M-SU-D1-23`（golden oracle 改用 `row_index` 重算應紅）在現行**單標的** golden fixture 下
  不可觸發：該 fixture 的 `row_index_local` 由 `b["test_row_index"]` 直接指派、與 `row_index`
  逐值相同。歸類 `needs-research`：是否值得把 golden fixture 改成兩標的交錯並重凍（會移動既有 digest）。
  **請三家各自表態**。
