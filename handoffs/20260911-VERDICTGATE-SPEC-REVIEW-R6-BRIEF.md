# VERDICTGATE SPEC v6 閉合確認（R6）

brief-kind: review
task-id: 20260911-VERDICTGATE-X-REVIEW-R6
findings-round: R6

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12 只約束「動工」，對審查任務不適用。禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R6-P<0-3>-<NN>`。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （你在 R5 提過、v6 已閉合者；只列你自己的）
```

## 審查對象
`docs/VERDICTGATE_SPEC.md` **v6**。R5 收斂 `handoffs/reconcile/20260911-verdictgate-x-review-r5/synth.md`（W1–W4 全採納；composer 之 amend 殘留判 by-design 入 §V）。

## 🔴 必答
1. **codex**：R5 三條在 v6 是否閉合（重跑 docs-only 序列、descoped caller、196 筆 fallback 抽樣）？**grok**：`GROK-R5-P1-01` 之 L159 對照組是否已與 Z4 對齊？**composer**：對 W3「上線前無 `brief_kind` 預設視為 review」獨立找碴——實跑 audit：782 筆 `round_open` 中，task_id 含 `-CONSULT-|-STAMP-|-CLOSURE-|-IMPL-|-RECON-` 之外、但**實際是 consult／stamp 性質**的有幾筆？列前 5 個 task_id。
2. **W2 消費條件加 `prod_files` 含生產路徑**：能否用「一個 1 行的生產檔 commit」消費 token 後再 small×3？主委立場：能，但那 1 行 commit 本身要先過 `--impl-self` 完整判定（SPEC/TODO 戳記、quorum、verdictgate）——即該票是真票；屬授權路徑非繞過。同意或反駁。
3. **§V by-design 之 amend 路徑**：`--no-verify` commit → 領 token → `--amend` ⇒ 放行。是否有「amend 前後內容不同」的濫用（例如 amend 時偷換 staged 內容）？post-commit 讀的是 amend 後之 tree ⇒ `prod_files` 以新 tree 計。給立場。
4. 🔴 **整體**：v1→v6 五輪共 33 條全採納。請各自做一次**全文**掃描（非只看本輪改動）：Task 之間、C 約束之間、ASSERT 之間是否還有互斥或死文（v3／v4／v5 都曾被抓到「改一處漏一處」）。列出你找到的每一處，或宣告「全文無互斥」並附掃描方法。
5. **可否據此生成 TODO**？

## 停輪條件
①必答 1–5 皆有立場；②必答 1（composer）、4 附實跑或掃描方法；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在實作批具體失敗」；⑤`CLOSED:` 只列你重驗過的。

## 前提
fact-verified: `bash scripts/template_check.sh spec docs/VERDICTGATE_SPEC.md` rc=0（v6，主委 2026-09-11）。
fact-verified: R5 三家產出已 `register-output`；round `0d15159f` 已 `debt_clear`。
fact-verified: codex R5 實跑：782 筆 `round_open`、196 筆無五種 marker；203 個 handoffs 檔非 family 尾碼（皆 brief／handoff，非 expected output）。
assumed: W3 反轉預設後，活票（SPLITUNIFY）之上線前 round 中沒有「命名不含 CONSULT／STAMP 卻是諮詢性質」者 ⇒ 否證觀測：若有，開下一批會被要求對一個諮詢輪補裁決（誤擋，可用 `--abandon` 或補裁決解，非繞過）。／我跑了：**沒跑** SPLITUNIFY 之 round 清單。請 composer 必答 1 正面打。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
