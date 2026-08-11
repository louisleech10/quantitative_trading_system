# 角色 SoT 延伸：編排端自任實作（`implementer=claude`）

**日期**：2026-08-11　**出處**：使用者指示 ＋ `handoffs/reconcile/20260811-govb49-x-consult-r1/synth.md`（codex＋composer＋grok 三家 consult）

本檔是 `scripts/governance_roles.json` 之 `_claude_eligible_why` 的落地出處，
並記錄本次變更**做了什麼、沒做什麼、代價是什麼**。

---

## §A 使用者指示（逐字）

> 「現在開始委員是Codex+Grok+Composer，實作是你Opus，所以討論/review/adverserial
>   都是三家委員Codex+Grok+Composer，我不知道現在是不是一行就可以設定委員角色，
>   你記得要將委員定義該改的地方都改到，不要漏了」

## §B 為何**必須**動 `implementer` 欄（三家 Q1 一致）

`scripts/_role_gate.sh:146-167` 以 `fam == implementer` 同時實作兩條規則：
`impl` 只能派給 implementer；`review` 不得派給 implementer。

⇒ 若 `implementer ∈ {codex, composer, grok}`，該家**必被 review 規則排除**，
最多只湊得出兩家審查者。要同時滿足「三家全員可審」＋「實作者不自審」，
唯一解是 `implementer ∉ 三家 CLI 家族`。

不動 `implementer` 的替代（三家各自列出，皆需改閘門碼、工作量 ≥ 本案）：
另設 `orchestrator_self_impl` 旗標並改角色規則；或改以 `reviewers[]` 為唯一白名單、
自審規則改比「本輪實作產出者」而非比 implementer 字串。
**在只改名冊、不改閘門碼的約束下：無解。**

## §C 本次實際變更

| 檔 | 變更 | 性質 |
|---|---|---|
| `scripts/governance_roles.json` | `eligible` 加 `claude`；`implementer=claude`；`reviewers`＝三家 | 角色 SoT |
| `scripts/governance_families.json` | `active_stampers` 顯式寫三家 | 見 §E，**非**政策切換 |
| `scripts/_role_gate.sh` | `known_only` 分支對 `fam == implementer` 仍套角色規則 | 補既有 fail-open |
| `scripts/set_roles.sh` | `reviewers` 公式交集可派工集合；`eligible` 缺鍵改 fail-closed | 修本輪引入之 P0 ＋ 既有 fallback |
| `docs/MULTI_AGENT_ORCHESTRATION.md` | §1 現行分工行；戳記那行改讀 SoT | 散文 SoT |

### C-1　`_role_gate.sh` 那六行修的是什麼

`known_only` 模式**跳過**不在 `review_families` 的家族。`implementer` 一旦是編排端，
「實作者不自審」對它**靜默失效**——`scripts/verify_role_gate.sh` 反例 2 實測由 FAIL 轉 PASS 即為證。

**對舊設定行為不變之證據**：grok 以隔離 workdir 把 roles 暫改回 `implementer=grok`，
`git show HEAD:scripts/_role_gate.sh` 為對照，kind×fam 矩陣 **15/15 同 rc**。
（主委原本只有靜態推理，該假設由 grok 的實驗升為 fact-verified。）

### C-2　`set_roles.sh` 的 P0 —— 修 B-49 病① 時**新開的洞**

`eligible` 一旦含無 CLI 映射的 `claude`，舊公式 `reviewers = eligible − implementer`
會在**下次切回 CLI 家族時**把 `claude` 寫進 `reviewers`
⇒ `check-families` strict 整批 rc=2 ⇒ 全名單派工當場死。

由 grok 實跑抓到（`implementer=codex` ⇒ `reviewers=[claude,composer,grok]` ⇒ rc=2），**非主委自查**。
修法＝`reviewers = eligible ∩ review_families − {implementer}`，並在池 < 2 時 fail-closed。
隔離驗證 `.claude/tmp/setroles_probe.sh` **5/5**（含缺鍵 fail-closed 與兩家鐵律兩條反例）。

## §D 🔴 沒有做的部分（具名殘留，不得宣稱閉合）

**D-1　`票 B-49` 仍 `OPEN`。** 本次只做了它的閉合條件 ④（更新 roles SoT），
而票文要求 ①②③ 先於 ④。⇒ **順序是倒的**，這是已知且刻意的。

**D-2　🔴 本節原記「兩條轉紅」，已由全套實跑更正為「四條轉紅」。**

原清單是**只掃五個 `_B45_HARNESS` 檔**的結果。全套 `pytest tests/governance` 實跑
（**4 failed / 1468 passed / 1 skipped**，661.71s）顯示還有第四條，且**不在**凍結集合內：

| 測試 | 狀態 | 在凍結集合？ |
|---|---|---|
| `test_rolegate_predispatch.py::test_t3_u2_consult_same_set_proceeds` | FAILED | ✅ |
| `test_stamp_taskid_inject.py::test_mutation_v12_force_stamp_target_all_kinds_turns_red` | FAILED | ✅ |
| `test_result_state_format_failed.py::test_t2_c2_impl_kind_unchanged` | FAILED | ✅ |
| **`test_cxrun_selfcheck_prompt.py::test_selfcheck_absent_for_impl`** | FAILED | ❌ **不在** ⇒ 已直接修好 |
| `test_stamp_taskid_inject.py::test_v12_non_stamp_kinds_no_stamp_target_ok` | SKIPPED | ✅ ＝ 病② 本人 |

同一根：凍結的 `_B45_HARNESS` 把「implementer 必為可派工 CLI 家族」寫死。

🔴 **兩點更正，不得沿用舊敘述**：

1. **紅是四條不是兩條。** 漏掉的原因是主委把問題框成「逐檔實跑五個 `_B45_HARNESS` 檔」，
   三家給了那個問題的正確答案，**但沒人跑全套**。
   ⇒ 紀律：凡宣稱「影響面就是這幾個檔」，一律以**全套實跑**為準，禁以子集掃描代替。
2. **「最小解凍集＝三檔」這個結論本身仍然成立**——第四條不在凍結集合內，不需解凍。
   錯的是**紅的清單**，不是**解凍集**。兩者勿混為一談。

**D-2b　那條 SKIPPED 比記錄的更嚴重。** `pytest.skip` 寫在
`for kind in ("review","consult","closure","impl")` **迴圈之內**且該迴圈是單一測試函式
⇒ implementer 一旦非三家 CLI 家族，**review／consult／closure 三種 kind 的覆蓋一併靜默消失**，
整檔仍報綠。票文條件 ② 之 `skipped=0` 要擋的就是它，但票文未指出它會連帶吃掉另外三種 kind。
修法與實跑收據見 `docs/GOV_B49_PINSHAPE_RECEIPT.md`。

**D-3　⇒ 整個 repo 的 push 被擋。** `scripts/git_hooks/pre-push` 委派 `gov_check.sh`，
後者 `:227-228` 跑**全套** `pytest tests/governance`。不是只擋名冊四檔。

**D-4　閉合條件③ 的正確語義**（三家獨立收斂到同一組，本檔採納為日後施工依據）：
- `eligible` ＝ 可寫入 `implementer` 的角色值（含 `claude`）
- 可派工集合 ＝ `review_families` ∩ family→CLI 映射成功集
- `reviewers` ＝ 可派工集合 − {implementer}
- 測試內的家族三元組**須由可派工集合機械導出**，禁硬編、禁 `== eligible`

**D-5　既有殘留（與本輪正交，不得記為本輪造成）**：
`scripts/review_quorum_check.sh:35` 硬編三家（`_DRIFT` 已釘）；
`_role_gate.sh` 的 `known_only` 對「非 implementer 且不在 `review_families`」之未知家族仍靜默放行。

## §E 🔴 `active_stampers` 不是「加回 grok」——三家中有兩家判錯

codex 與 composer 皆判「加 grok 使既有雙戳記收斂檔**回溯性**失格」，各附 `rc=1 缺 grok`。
grok 判「對 HEAD 不成立」。主委獨立複驗，**grok 正確**：

```
git show HEAD:scripts/governance_families.json | grep -c active_stampers   → 0
git show HEAD:scripts/governance_families.json | grep review_families      → ["codex","composer","grok"]
```

HEAD **沒有** `active_stampers` 這個 key ⇒ `families_active_stampers` rc=3 ⇒ 回退
`review_families`＝**本來就是三家**。⇒ 舊檔缺 grok 戳記在 HEAD 的預設路徑下**早已不合格**。

codex／composer 是拿**未 commit 的工作區**（2026-08-09 那次同樣未 commit 的 `[codex, composer]`）
當基準線，把「還原既有預設」誤讀成「政策切換」。

**操作面結論仍成立**：引用舊 reconcile 的 impl 派工會被戳記閘擋下，
須補 grok 戳記或改指向新 reconcile。但那是**既有債，不是本輪新增**。

## §F 「一行就能設定委員嗎」——使用者原問的答案

**一半是。**
- 暫停／恢復**委員**：改 `scripts/governance_families.json` 的 `active_stampers` **一行**。
- 換**實作端**：在 `scripts/governance_roles.json`，且**必須**走 `bash scripts/set_roles.sh <值>`
  （它會自動同步 `reviewers`、跑 quorum 前檢、跑角色閘 oracle）。手改 JSON 會繞過這三道。
- 兩者是**不同檔、不同語義**：前者＝「這期誰要蓋章」，後者＝「誰在實作」。
