# VERDICTGATE SPEC v2 adversarial review（R2）

brief-kind: review
task-id: 20260911-VERDICTGATE-X-REVIEW-R2
findings-round: R2

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12（STAMP-BLOCKED：reconcile 未核可不動工）只約束「動工」，對審查任務不適用。** R1 codex 據此回 `STATUS: BLOCKED` 並交空檔——請勿重蹈；審查 SPEC 就是本輪的工作。**禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R2-P<0-3>-<NN>`。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （你在 R1 提過、v2 已閉合者；只列你自己的）
```

## 審查對象
`docs/VERDICTGATE_SPEC.md` **v2**。R1 收斂 `handoffs/reconcile/20260911-verdictgate-x-review-r1/synth.md`（W1–W4）。R1 之五條（composer 3、grok 3，全採納）之修法摘要在 SPEC 檔頭版本行。

## 🔴 必答
1. **composer／grok**：你 R1 的每一條在 v2 是否閉合？逐條「已閉合／未閉合＋理由」，並在 `CLOSED:` 列出已閉合者。**codex**：R1 未交件，請完整審 v2（等同 R1 必答 1–7）。
2. **W1 之修法比三家提的更徹底**（舊產出一律不判、取消基準）：這會不會讓「本票上線前已存在的跨批」永遠沒人管？它們是否該以**另一種**方式（非閘）具名？
3. **W2**：改讀全部輪 blocked 聯集後，還有沒有跨批繞法？（例：同家在同批 R1 提 P1、R2 把同一問題改成新 ID 提 P2 並 `CLOSED:` 舊 ID；或 DEGRADE 缺席。）
4. **W3**：push 時對 small commit 取聯集——能否被「分兩次 push」繞過？`origin/main..HEAD` 在第二次 push 時會不會看不到第一次的 small？給實跑或可重現構造。
5. **Task 3.1 `--impl-self` 在 b1（無前批）只驗 SPEC/TODO 戳記**——請對照 `gate.sh` 既有 impl 派工的 b1 條件，兩者是否一致？不一致處給碼證。
6. 🔴 §N 三條殘留是否**真的**符合「已定義在其他 Phase」或「現階段完全不可能」？
7. **可否據此生成 TODO**？

## 停輪條件
①必答 1–7 皆有立場；②必答 3、4 附可重現構造；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」。

## 前提
fact-verified: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0（v2，主委 2026-09-11）。
fact-verified: R1 composer／grok 之 `VERDICT: blocked` 已依本票 Task 1.1 契約先行試用並成功解析（主委目視；Task 1.2 實作前無機械 parser）。
assumed: 「舊產出一律 unknown 不判」不會讓任何**現行進行中**的票（SPLITUNIFY 暫停中、EVTLABEL 已收）在本票上線後被誤擋或誤放 ⇒ 否證觀測：某票的前一批 review 是本票上線前登記的（unknown）、下一批在上線後開輪 ⇒ 閘對它無輸入而放行，等於該票的第一個跨批邊界沒被看。／我跑了：**沒跑**任何票的批次時間線。請正面打（必答 2）。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
