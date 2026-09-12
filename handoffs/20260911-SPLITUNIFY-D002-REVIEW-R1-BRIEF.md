# SPLITUNIFY D-002 延伸檔找碴 R1

brief-kind: review
task-id: 20260911-SPLITUNIFY-D002-REVIEW-R1
findings-round: R1

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**（本輪只開 finding）。
🔴 **P0／P1 必附修法與可行性評估**，只點出問題不算完成。

## 審查對象

`docs/SPLITUNIFY_SPEC.D-002.md`（commit `c4bf6229`）——第 9 批（`SU-RESID-2` 多 TF 複合鍵）之延伸規格。
BASE `docs/SPLITUNIFY_SPEC.md @ 1be5be3f`、PREDECESSOR `docs/SPLITUNIFY_SPEC.D-001.md`。

上游收斂（本檔之依據）：`handoffs/reconcile/20260911-splitunify-b9-consult-r1/synth.md`
（四家偵察 18 條／六群；主委自產另見 `handoffs/20260911-splitunify-b9-consult-r1-claude.md`）。

## 前提（範本 §0；請逐條挑戰）

fact-verified: 現行跨 TF 不 fail-closed、未選 TF 靜默丟棄 → 主委探針四情形＋codex Probe A
（`input_per_tf_rows 4 output_rows 2 UNSELECTED_ROWS_DROPPED 2`），兩份獨立實跑逐值一致
fact-verified: D-001 第 189 行「六處」不完整 → 四家合併盤點得 15 處，逐處碼證見 D-002 觸及面宣告
fact-verified: `docs/SPLITUNIFY_SPEC.D-002.md` 之 `doc_format_precheck` rc=0 → 主委實跑
fact-verified: 交叉引用掃描顯示無現行文件仍沿用被推翻的舊說法 → `grep -rln "多 TF 同批.*fail-closed"`
命中者僅 D-001（凍結檔，由本延伸覆寫）、委員 runlog（歷史）、主委偵察 brief（該處本就標 assumed）

assumed: 15 處就是**全部**的單鍵消費面
→ 否證觀測：指出第 16 處（含 `api/services/` 內以 dict 推導／`groupby().first()` 等非型樣形態）／
我跑了: 四家合併 grep，但 `api/services/` **未逐檔讀**
assumed: Phase 9A（揭露）可獨立回退，不需連動 9B
→ 否證觀測：指出 9A 的 summary 新欄會被哪個下游消費而無法單獨移除／我跑了: **沒跑**，這是設計判斷
assumed: 同一事件的不同 TF **應同簇**（時間簇按事件級 interval 合併）
→ 否證觀測：給出「同事件不同 TF 應分屬不同簇」成立的情境／我跑了: **沒跑**，四家立場一致但無實跑
assumed: `g5_row_fingerprint_*` 不受複合鍵影響（payload 無 `timeframe`）
→ 否證觀測：指出 g5 會位移的路徑／我跑了: 讀 `build_row_time_fingerprint` 簽名，**未**實跑多 TF fixture

## 必答（成對，缺一不算完成）

1. **觸及面完整性**：15 處之外還有第 16 處嗎？請給檔案:行號。若你認為完整，說明你掃了哪些範圍
   （特別是 `api/services/`、`frontend/`、`tests/golden/`）才得出這個結論。
2. **兩階段切分**：「揭露先行（9A）→ 複合鍵主體（9B）」是否正確？9A 真的能獨立回退嗎？
   若你認為該一次做完，給出「分階段會產生中間不一致狀態」的具體路徑。
3. **cluster 語意**：D-002 定「同一事件的不同 TF **同簇**」。請嘗試構造一個反例
   （某情境下應分屬不同簇）；構造不出來也要說明你試了什麼。
4. **事件數與列數分離**：D-002 要求 `n_events` 與 `n_event_tf_rows` 並存且不得混用。
   請盤出**還有哪些地方**會把列數當事件數（報告、API、前端、既有測試斷言）。
5. **§G 與 mutation**：①`g5` 不受影響的判斷對嗎？②`M-SU-D2-01`～`06` 是否足以覆蓋 9A／9B 的失效面？
   缺哪些？特別是**靜默面**（D-002 標記的第 5／7／8／9／10／11／12／14 項）。

## 停輪條件

①必答 1–5 皆有立場；②必答 1、3、4 須附**實跑或具體反例**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**——若判定可進實作，須說明你主動攻了哪些面而未成功；
④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明，請對號入座）

findings 用 `## <你的家族大寫>-R1-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。
🔴 **`CLOSED:` 欄只列「你自己家族」開過的 finding ID**；本輪為首輪，通常**留空**（不得寫 `none`）。
裁決塊三行分寫：

```
VERDICT: proceed
BLOCKED-BY:
CLOSED:
```

`blocked` 時 `BLOCKED-BY:` 填你自己家族的 ID。
