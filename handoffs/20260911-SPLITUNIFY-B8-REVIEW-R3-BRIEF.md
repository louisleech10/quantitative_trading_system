# SPLITUNIFY 第 8 批（b8）閉合輪 R3

brief-kind: review
task-id: 20260911-SPLITUNIFY-B8-REVIEW-R3
findings-round: R3

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。本檔只是把該範本套到本輪的聚焦範圍上；
範本與本檔衝突時**以範本的格式要求為準**。🔴 **禁改碼**。

## 前提（範本 §0；請逐條挑戰）

fact-verified: R2 三家一致之 finding（adapter 的 NaT 閘引用未匯入之 `AlignmentViolationError`）
已修補 → `ic_split_adapter.py` 自 `momentum.core.contracts` 匯入該類別；主委探針實跑：
修補前 `NameError`、修補後 `AlignmentViolationError` 且訊息含 `NaT`
fact-verified: 漏網原因為「上一批只補 `split_per_symbol` 路徑的 NaT 測試，adapter 路徑無測試」
→ 已補兩條 adapter 路徑測試（NaT 反例＋乾淨時間軸正例）
fact-verified: R1 三條 findings 已於 R2 由 codex（原提出方）與 composer 判定 `CLOSED`
→ `handoffs/reconcile/20260911-splitunify-b8-review-r2/synth.md`
fact-verified: 修補後 227 條目標測試面跑完無失敗、`freeze_splitunify_golden.py` 回報 `GOLDEN OK`
→ 主委實跑

assumed: adapter 與 `split_per_symbol` 兩條路徑的 NaT 閘**語意等價**（只是例外型別不同：
前者 `AlignmentViolationError`、後者 `ValueError`）
→ 否證觀測：指出兩者在相同輸入下行為不一致、或呼叫端會因型別不同而走到不同分支／
我跑了: 各自的反例與正例，**未**比對兩條路徑在同一 caller 下的處理差異
assumed: 這次沒有再引入第三個同型缺陷（用了未匯入的名字、或閘只覆蓋單一路徑）
→ 否證觀測：找出本批新增碼中任何未匯入符號、或任何「只在一條路徑上生效」的閘／
我跑了: 只跑了測試與探針，**未**做全檔 import 靜態掃描
assumed: 修補未改變任何既有數值輸出
→ 否證觀測：指出會位移 golden digest 或改變既有 plan 內容的路徑／
我跑了: golden 凍結比對與目標測試面，**未**跑 IC 端到端真實 run

## 本輪分工

- **grok（R2 原提出方，本輪重點）**：依章程 §B8，請**重跑你自己 R2 的反例**
  （`ICSplitAdapter._with_row_positions` 餵含未選 `NaT` 的 frame），確認是否真關閉：
  現在應為 `AlignmentViolationError` 且訊息含 `NaT`，而非 `NameError`。
  逐條給判定並附**你自己重跑**的輸出。
- **codex／composer**：你們 R2 同樣開了這條（P2）。請確認修補是否對應你們的 finding，
  並攻「有沒有第三個同型缺陷」——本批新增碼中是否還有未匯入的符號，
  或任何「閘只在一條 producer 路徑上生效」的情形。

## 停輪條件

①對 R2 的該條 finding 給出 `CLOSED` 或仍 `blocked` 的明確判定，並附你自己重跑的輸出；
②🔴 **禁以「無 finding」當停輪**——若判定可收案，須說明你這輪主動攻了哪些面而未成功；
③若發現本次修補引入**新**問題，照常開新 finding（沿用 R3 編號）。

## 格式（🔴 分家族寫明，請對號入座）

findings 用 `## <你的家族大寫>-R3-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`CLOSED:` 欄只能列「你自己家族」開過的 finding ID**——契約如此，列他家 ID 會被
`register-output` 拒收。R2 就發生過：我的格式範例是寫給原提出方的，另一家照抄了別家 ID
而被擋（責任在我，已記錄）。所以本輪逐家寫明：

- **grok**（R2 的 `GROK-R2-P1-01` 是你開的）：
  ```
  VERDICT: proceed
  BLOCKED-BY:
  CLOSED: GROK-R2-P1-01
  ```
- **codex**（你開的是 `CODEX-R2-P2-01`）：
  ```
  VERDICT: proceed
  BLOCKED-BY:
  CLOSED: CODEX-R2-P2-01
  ```
- **composer**（你開的是 `COMPOSER-R2-P2-01`）：
  ```
  VERDICT: proceed
  BLOCKED-BY:
  CLOSED: COMPOSER-R2-P2-01
  ```

若仍 `blocked`，`BLOCKED-BY:` 填你自己家族的 ID，`CLOSED:` 留空（**不得**寫 `none`）。
