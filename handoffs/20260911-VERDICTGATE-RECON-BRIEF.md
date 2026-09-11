# VERDICTGATE 偵察（三家平行，與主委版互審）

brief-kind: consult
task-id: 20260911-VERDICTGATE-X-CONSULT-R1
findings-round: R1

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`。
**唯讀偵察，禁改碼**。主委版在 `handoffs/20260911-VERDICTGATE-RECON-claude.md`——**先自己偵察、再讀它**，不要照抄。

## 要偵察的問題
批次之間「委員寫不可進卻照樣進下一批」為何擋不住？主委版列了 F1–F10 十條事實與 G-1–G-6 六條提案。

## 🔴 必答（逐條附碼證或實跑輸出）
1. F1–F10 逐條：**同意／推翻＋證據**。特別打 F5（Verdict 是否真的無法機械解析——請自己 grep 全部 `handoffs/*-review-*-{codex,composer,grok}.md`，不只 SPLITUNIFY）。
2. 「我沒查的」三條，請實查：①GAP-3／EVTLABEL 是否也有「不可進卻跨批」（給輪次與 ID）；②pre-commit 加 trailer 檢查對 `cx_run.sh` 執行端 commit 是否相容；③`Ticket-Batch` 與 `Governance-Scope` 同段共存是否可解析（讀 `scripts/gov_check.sh` G-7 段）。
3. G-2 觸發點：主委說「派下一批 review 時＋pre-commit」。**還有沒有第三條所有實作者必經、而這兩處抓不到的路？**（例：直接 `git push` 不 commit？`--no-verify`？委員在 worktree commit？）
4. G-3 `--impl-self`：主委自己領權限，**誰擋主委不領**？只有 pre-commit 嗎？pre-commit 用 `--no-verify` 繞過時有沒有第二層？
5. G-4 逐字引用 20 字：**可被怎樣繞過**？（例：引用了但決議內容無關。）給你認為做得到的最強判準，並明說做不到的部分。
6. 順序與規模：這六條你會怎麼切批？哪些是前置（沒有它其他做不了）？
7. 🔴 全專案已廢止「95% 就收」，殘留只准「已定義在其他 Phase」或「現階段完全不可能」。本票有哪一條你判「現階段完全不可能」？**要說明為什麼不可能，不是為什麼不方便。**

## 停輪條件
①必答 1–7 皆有立場；②必答 1、2 每條附證據；③禁以「同意主委」當停輪——至少推翻或補強一條，做不到要說明你怎麼試過。

## 前提（逐條標）
fact-verified: F1–F10 之證據路徑皆主委實跑，見主委版。
assumed: 委員產出格式可以由範本強制 ⇒ 否證觀測：範本 2026-08 起就規定 Verdict 三值，實際 0 份照用。請正面打（必答 1 之 F5）。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套（小時級）；禁跑 `tests/momentum/Analysis` 全套；禁與其他委員平行跑重測試（本 session 已 OOM 一次）。收尾清 /tmp workdir（保留 claude-501）。
