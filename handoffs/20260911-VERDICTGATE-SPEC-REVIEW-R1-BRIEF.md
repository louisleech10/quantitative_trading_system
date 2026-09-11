# VERDICTGATE SPEC v1 adversarial review（R1）

brief-kind: review
task-id: 20260911-VERDICTGATE-SPEC-REVIEW-R1
findings-round: R1

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`。
🔴 **本輪起，產出末段必須含機械裁決塊**（本票 Task 1.1 之契約，先行試用）：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
```
**禁改碼**（SPEC 階段禁寫實作；委員以「腳本尚不存在」作 BLOCKING 碼證＝不是 SPEC 缺陷）。

## 審查對象
`docs/VERDICTGATE_SPEC.md` v1。偵察收斂在 `handoffs/reconcile/20260911-verdictgate-x-consult-r1/synth.md`（V1–V6）——SPEC 應完整落實你在偵察輪的每一條；**請先核對自己那幾條有沒有被正確落實**。

## 🔴 必答
1. **你在偵察輪的每條 finding**：SPEC 哪個 Task 落實？落實得對不對？逐條回「已落實／落實錯誤＋ID」。
2. **Task 2.2 判定「一家 blocked 且該家無後續 closed」**：請構造能繞過它的合法-看似序列（例：同批 R2 blocked、R3 該家不再出席／DEGRADE；閉合輪由另一家寫 CLOSED；同 ID 在兩輪不同 root）。每個給「擋得住／擋不住＋為什麼」。
3. **Task 3.2 `Ticket-Batch: small` 判準**（≤3 檔且不碰 factories/protocols/config）：**可被怎樣拆 commit 繞過**？給你認為做得到的最強判準與做不到的部分。
4. **Task 2.1 legacy 字面表**：`不可進|不可收票|不可直接進` ⇒ blocked。請對全庫 628 份實跑，列出這張表**誤判**（可進被判 blocked、或 blocked 被判 proceed）的例子與數量。
5. **順序**：Phase 4 依賴 Phase 1 而非 Phase 2——對嗎？Phase 3 依賴 Phase 2——必要嗎（能否與 2 平行）？
6. 🔴 §N 三條殘留是否**真的**符合「已定義在其他 Phase」或「現階段完全不可能」？任一條你判「其實做得到」就標 P1 並說怎麼做。
7. **可否據此生成 TODO**？`VERDICT: proceed` 或 `VERDICT: blocked`＋`BLOCKED-BY:`。

## 停輪條件
①必答 1–7 皆有立場；②必答 2、3、4 附實跑或可重現構造；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」。

## 前提（逐條標）
fact-verified: SPEC §A 之每條 FACT-RECEIPT 皆附實跑者與日期。
fact-verified: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0（主委 2026-09-11）。
assumed: 「一家 blocked 即擋」不需人頭門檻 ⇒ 否證觀測：某家長期對所有票寫 blocked 而無實質內容，全線停擺。／我跑了：**沒跑**該家歷史 blocked 比例。請正面打（必答 2）。

## 🔴 我沒查的
| claim | observable_if_false | reason_code |
|---|---|---|
| `git interpret-trailers` 對 `--amend` 沿用訊息之行為 | amend 時 trailer 消失 ⇒ Task 3.2 誤擋 | cost |
| audit.log 之 `committee_output` 對同 task 多次 register 的順序語意 | Task 2.2 取「最新」時取到舊的 | cost |

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
