# SPLITUNIFY 第 8 批（b8）閉合輪 R2

brief-kind: review
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R2
findings-round: R2

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。本檔只是把該範本套到本輪的聚焦範圍上，
範本與本檔衝突時**以範本的格式要求為準**。

## 前提（範本 §0；請逐條挑戰，錯前提會被當成 finding 帶回來）

fact-verified: 你 R1 的兩條 P1 反例，主委已**獨立複驗成立**——float64 `[0.,1.,2.]` 經
`split_per_symbol` 為 `NO_RAISE` 並產出 `int64[0,1,2]`；含未選 `NaT` 的 frame 亦 `NO_RAISE`
→ 探針實跑：修補前 2/3 成立、修補後 0/3 成立（三條皆 raise）
fact-verified: dtype 閘已接上**三個** cast 點 → `contracts.py::split_per_symbol` 一處、
`ic_split_adapter.py` 兩處（`_build_plan_pair` 與其上游迴圈）
fact-verified: 本批修補後 b8 目標測試面 203 條與 producer 契約 22 條跑完無失敗、
`freeze_splitunify_golden.py` 回報 `GOLDEN OK` → 主委實跑

assumed: 「在 coerce **之後**驗整條時間軸」這個檢查位置足以涵蓋所有 `NaT` 來源
→ 否證觀測：指出 coerce 之後仍會生成 `NaT`、或 `NaT` 在檢查點之後才進入的路徑／
我跑了: 只驗了「coerce 後立即檢查」這一種佈局，**未**窮舉 coerce 內部行為
assumed: dtype 閘涵蓋 float／bool／object 三型即足夠
→ 否證觀測：給出第四種仍能繞過的型別（例如 pandas nullable `Int64`、`np.matrix`、
帶 `__index__` 的自訂物件）／我跑了: 只測這三型
assumed: 修補未改變任何既有數值輸出
→ 否證觀測：指出會位移 golden digest 或改變既有 plan 內容的路徑／
我跑了: golden 凍結比對與目標測試面，**未**跑 IC 端到端真實 run

## 這一輪要你做什麼

R1 的裁決：**codex** 開兩條 P1＋一條 P2 並裁決 `blocked`；**composer** 與 **grok** 皆 `proceed`、
零 P0／P1。三條 findings 都**已採納並修補**。本輪分工如下：

- **codex（原提出方，本輪重點）**：依章程 §B8，Block／Bug 退回修改後須由**原提出方**
  重跑同一反例確認真關閉＋可證偽，**不憑實作者說「已修」**。請逐條給 `CLOSED` 或仍 `blocked`，
  並附**你自己重跑**的輸出。不必重新全面審查。
- **composer／grok**：你們 R1 已 `proceed`。本輪只需確認**修補本身沒有引入新問題**
  （新增的 dtype 閘與 NaT 閘會不會誤擋合法輸入、會不會改變既有數值輸出），
  以及三條修補是否真的對應 codex 的原始 finding。不必重跑 R1 已做過的攻擊面。

## 逐條修補與你要複驗的東西

### CODEX-R1-P1-01（dtype 閘被前置 cast 繞過）

你的反例：float64 `[0.0,1.0]` 經 producer 路徑 `NO_RAISE` 並產出 `int64 [0,1]`。

修法：新增 `momentum/core/contracts.py::_assert_integer_ordinals`，對 splitter／boundary
回傳的**原始**序號驗 numpy 整數 dtype，擋在 `np.asarray(..., dtype=int)` **之前**；
三個 cast 點全數接上（`contracts.py::split_per_symbol`、`ic_split_adapter.py` 兩處）。

回歸測試：`tests/momentum/core/test_splitunify_producer_attest.py`
- `test_producer_rejects_float_ordinals_before_cast`
- `test_producer_rejects_bool_ordinals_by_dtype_gate_not_by_luck`（限定訊息含 `dtype`——
  修正前 bool 也會 raise，但擋它的是「時間戳非嚴格遞增」，是碰巧不是設計）

**請複驗**：①你原本的 float64 反例現在是否 raise，且訊息指名 dtype；
②有沒有**其他**型別（object、`pd.array` 之 nullable Int64、np.matrix 等）仍能繞過；
③三個 cast 點是否真的都接上了，有沒有第四個我漏掉的。

### CODEX-R1-P1-02（未選列 NaT 不擋）

你的反例：含未選 `NaT` 的 frame，兩 producer 均 `NO_RAISE`。

修法：`split_per_symbol` 在建立 `_ts_dt_index` 後、`ic_split_adapter._with_row_positions`
在 coerce 後，各對**整條**時間軸驗 NaT，`hasnans`／`isna().sum()` 非零即 fail-closed。

回歸測試：`test_producer_rejects_nat_anywhere_on_the_time_axis`。

**請複驗**：①你原本的反例現在是否 raise；②是否存在「NaT 出現在 coerce 之後」的路徑
（例如 coerce 本身把某些值變成 NaT 而我的檢查位置在它之前／之後）；
③orchestrator 路徑你 R1 說已由 `:285-286` 擋，是否確實。

### CODEX-R1-P2-03（投影 docstring 用全框座標）

修法：`split_projection.py` `_derive_single_symbol` 第一段判定之 docstring 改為
`test_plan.row_index_local[0]`，並註明會誘導後人把全框列號當標的內序號。

**請複驗**：該檔是否還有其他地方以全框座標描述投影語意。

## 主委的實跑（供你對照，不是要你採信）

- 修補前探針：float64 `NO_RAISE`、bool 被「非嚴格遞增」碰巧攔下、未選 NaT `NO_RAISE`。
- 修補後同一支探針：三條皆 raise。
- `tests/momentum/core/test_splitunify_producer_attest.py` 22 條、b8 目標測試面 203 條跑完無失敗；
  `scripts/freeze_splitunify_golden.py` 回報 `GOLDEN OK`。

## 停輪條件

①三條逐條給 `CLOSED` 或仍 `blocked` 的判定，並附**你自己重跑**的輸出；
②🔴 **禁以「無 finding」當停輪**——若判定可收案，須說明你這輪主動攻了哪些面而未成功；
③若發現修補引入**新**問題，照常開新 finding（沿用 R2 編號）。

## 格式

findings 用 `## CODEX-R2-P<0-3>-<NN>` 二級標題；`CLOSED:` 無內容留空、不得寫 `none`；
🔴 **裁決塊三行分寫**（R1 你寫成單行 `VERDICT: blocked; BLOCKED-BY: …; CLOSED:`，
不合 `verdict_parse` 契約，主委已代為分行正規化、語意逐字未動；本輪請直接分行）：

```
VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R1-P1-01, CODEX-R1-P1-02, CODEX-R1-P2-03
```

完成訊號**逐字** `STATUS: DONE`。**禁改碼**。
