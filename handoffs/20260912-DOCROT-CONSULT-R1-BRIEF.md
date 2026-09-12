# DOCROT — 文檔問題偵察諮詢 R1（委員自行界定問題）

brief-kind: consult
task-id: 20260912-DOCROT-X-CONSULT-R1
findings-round: R1

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式（斷言／碼證／來源摘要／嚴重度＋修法）、結尾 Verdict 區塊。
🔴 **本輪禁改碼、禁改任何文檔**——唯讀偵察。

## 🔴 本輪的特殊要求：**你自己去研究問題是什麼**

主委（Claude）**刻意不在本 brief 提供任何診斷、根因、數據分類或修法提案**。

理由（使用者 2026-09-12 當面指示）：

> 「我覺得你不能只用口頭去問委員，你要委員自己去研究到底問題是什麼，不然你可能又亂問」

主委本 session 對同一問題提出過四個診斷／修法，**四個全部在被追問後自行推翻**。因此主委的框架
不可信，若寫進 brief 只會造成錨定。主委確實另有一份自產版本（`handoffs/20260912-docrot-x-consult-r1-claude.md`），
**本輪刻意不提供給你**，收斂時才與四家平行比對——這是為了檢驗主委的診斷是否偏誤。

⇒ **請先完成你自己的調查與結論，再提交。不得詢問或引用主委版本。**

## 使用者的原話（唯一未經主委轉述的問題陳述）

> 「你寫文檔裡面層層疊疊，前後混亂，新一輪可能還看到前幾輪修完的文字，結果又浪費時間在修已經
> 修過的東西之類，這你說的，我不知道你是不是騙我，反正就是你文檔內容的問題造成每個文檔都要花
> 好幾輪在修錯誤的東西而不是真正的程式碼或架構缺陷，這浪費大部分的輪數。
> **注意，我不是只說 SPEC，我說的是所有你寫出來的文檔**」

> 「我體感你有 7 成的時間都浪費在這上面，不是實際做事」

## 可查的原始材料（**未經主委分類或摘要**）

- **規格本體**：`docs/SPLITUNIFY_SPEC.D-002.md`（現行）；其完整修訂史在 git
- **十二輪收斂檔**：`handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md` 至 `…-r12/synth.md`
- **三十六份委員交件**：`handoffs/20260911-splitunify-b9-review-r{1..12}-{codex,composer,grok}.md`
- **其他主委文檔**：`HANDOFF.md`、`docs/SPLITUNIFY_TODO.md`、`docs/SPLITUNIFY_SPEC.D-001.md`、
  `docs/ROADMAP.md`、`白話說明/*.md`（19 份）、`docs/VERDICTGATE_SPEC.md`／`_TODO.md`
- **git 歷史**：`git log`、`git show <sha>:<path>`（可取任一版本比對成長）
- **治理閘**：`scripts/spec_xref_check.sh`、`obligation_block_check.sh`、`doc_format_precheck.sh`、
  `reconcile_cluster_attribution_check.sh`、`completeness_check.sh`、`verify_pretooluse.sh`、
  `.claude/settings.json`（hook 掛載點）

## 必答（成對，缺一不算完成）

1. **你自己量到什麼**？請自行決定要量什麼、怎麼量，並附**可重跑的指令**與輸出。
   **不得**只給意見或觀感。若你認為某個量測無意義，說明為何。
2. **問題是什麼**？用**你自己的話**界定，不得複述使用者原話或主委措辭。
   若你認為使用者的描述不準確，直說並給證據。
3. **根因是什麼**？主委的編輯方式、文檔格式、範本設計、閘的取向、審查流程、
   或其他——請指名並附碼證。**不得列一堆可能性而不排序**。
4. **修法**：須**可機械驗證**（有判定指令、有成效指標），不得是「要小心」「要注意」這類紀律。
   若你的修法只能靠紀律，明說並標為紀律型。
5. **範圍**：此病是否同樣存在於 `HANDOFF.md`、`docs/SPLITUNIFY_TODO.md`、
   `handoffs/reconcile/*/synth.md`、`白話說明/*.md`、`docs/VERDICTGATE_SPEC.md`？
   **逐類給判定與碼證**；不適用者說明為何。
6. **是否不值得解**？若正解是「接受此成本」或「換掉整個文檔體系」，請直說並給判準。
   **不得為了交差而發明做不到的機制**。

## 前提宣告（範本 §0）

fact-verified: 使用者原話如上，逐字引自 2026-09-12 對話 → 主委轉貼，未改字
fact-verified: `docs/SPLITUNIFY_SPEC.D-002.md` 已歷十二輪 review、十三次修訂 → `git log -- docs/SPLITUNIFY_SPEC.D-002.md`
fact-verified: 十二輪 synth 之 `RECONCILE-STAMP APPROVED` 數為 0 → `grep -c 'RECONCILE-STAMP.*APPROVED' handoffs/reconcile/20260911-splitunify-b9-review-r*/synth.md`

assumed: 四家在**不看主委版本**的前提下，能獨立界定出可操作的問題陳述
→ 否證觀測：若你認為缺主委的上下文就無法判斷，直說並指出缺哪一項事實／我跑了：**沒跑**——這是本輪設計的賭注
assumed: 此問題**有解**，而非文檔協作的固有成本
→ 否證觀測：舉出同類規模專案之對照，或論證為何此成本不可消除／我跑了：**沒跑**
assumed: 使用者「7 成時間浪費」之體感，其分母是**輪數／回合數**而非 commit 數
→ 否證觀測：以其他分母量測後給出不同結論／我跑了：**沒跑**——主委只量過 commit 分布，未量輪數

## 停輪條件

①必答 1–6 皆有立場；②必答 1、3、4 須附**可重跑指令或碼證**，不得只讀文件推論；
③🔴 **禁以「無 finding」當停輪**；④若你認為此問題不值得解，須給出判準而非直覺。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-DOCROT-R1-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

裁決塊三行分寫，`BLOCKED-BY`／`CLOSED` 之 ID 以**半形逗號**分隔（不得用空白）。
