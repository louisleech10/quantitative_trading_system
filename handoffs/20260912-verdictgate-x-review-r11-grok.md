# VERDICTGATE 收票審 R11 — grok

task-id: 20260912-VERDICTGATE-X-REVIEW-R11  
family: grok  
brief: `handoffs/20260912-VERDICTGATE-X-CLOSEOUT-R1-BRIEF.md`  
findings-round: R11

---

## 必答 1–5

### 1. C-4「已進入跳過」是否有假輪縫？

**有縫（非「假審查輪」，是「假閉合輪首進」）。**

主委立場「開審查輪必經 verdictgate ⇒ 假輪開不了」對 **`brief_kind=review`** 成立：

- `VERIFY:` 暫存 audit：b1 三家齊、codex `blocked` 未 CLOSED；`bash scripts/verdictgate_check.sh DEMO 2 DEMO-b1-REVIEW` → **rc=1**（擋）。
- `gate.sh:946-960`／`committee_run.sh:433-441`：非 closure 之 `-b<N>-` 開輪／dispatch 皆呼叫同一 checker。

但跳過條件（`verdictgate_check.sh:36-54`）是「本批**任一** `committee_round_open` task_id 前綴 `{root}-b{n}-`」——**不區分 `brief_kind`**。而 closure 開輪**刻意**跳過 verdictgate（`committee_run.sh:433`、`gate.sh:957`）。構造：

1. 前批 blocked（上列 rc=1）。
2. 寫入 `DEMO-b2-CLOSURE-R1`（`brief_kind=closure`）之 `committee_round_open`（模擬 closure 開輪零新增前之放行）。
3. 再跑同一 checker → **rc=0**，stdout 含「本批已有審查輪…不重驗前批」。
4. 即使再 append `debt_abandon`（`collection-failed`）清 OPEN 債以便後續 `--impl-self`，skip **仍熱**（abandon 不刪 round_open；skip 碼亦不看 abandoned）。

`VERIFY:` 暫存 audit 上步驟 3／4 皆 rc=0。`--impl-self` 之 brief-kind 須為 `impl`（不得直接塞 closure brief），故完整鏈＝「closure 首進寫 round_open →（可 abandon）→ impl brief 領 token」；判定面與 checker 直呼等價（gate 發 token 前呼叫同一支）。

否證觀測成立：**前批 blocked 時，仍可令 bN checker／後續 `--impl-self` 路徑放行**（經 closure 首進，非經假 review）。見 `GROK-R11-P1-01`。

### 2. 與 SPEC C-4 字面之差：收票內修正 or FROZEN？

**立場：接受「只擋進入新批」為收票內範圍修正**（與使用者 2026-08-05 不溯及既往、補裁決／閉合／修補同批不應連鎖回溯一致；p2 `test_check_batch_already_entered_skips_prev_verdicts` 正向覆蓋）。**但現狀實作過寬，不得在未收窄前結案。**

SPEC C-4（`docs/VERDICTGATE_SPEC.md`）字面強調「開下一批前」讀前批裁決；未寫「本批已有任意 round_open 則跳過」。主委註解假設「有 round_open＝審碼 R1 已驗過前批」——對 review 首開為真，對 closure 首開為假。

建議：收票內把 skip 收窄為「本批已存在 `brief_kind=review`（或 legacy 視為 review）之 `committee_round_open`」才跳過；與註解意圖對齊，**不必**為意圖本身走 FROZEN。若堅持「任意 round_open」⇒ 須 FROZEN 改 SPEC 並明示接受 closure 首進縫（本家不接受）。

### 3. E-022～E-025

| ID | 歸類 | 行號／碼 | 立場 |
|---|---|---|---|
| E-022 | 豁免（執行端 CLI 寫檔，主控無 Edit/Write） | `cx_run.sh:612`＝`gate.sh register-output` 呼叫，正確；第二層 `verdictgate_check.sh:28` 為 argc 用法檢查，**可執行但語意錨偏**（讀裁決在 :36+） | 歸類正確；第二層行號宜改 :36 或 :53，本輪不升格（非 fail-open） |
| E-023 | 產出端（PreToolUse→gate_check→gate.sh） | `gate.sh:951` 在 verdictgate 解析／呼叫塊內，可執行 | 歸類正確 |
| E-024 | 豁免（commit 訊息不在 Bash 字串） | `commit-msg:41` 正確呼叫 `--msg`；文稱 `ticket_batch_check.sh:49` 為 `--push-range`，**實為 `:49 --msg`，`--push-range` 在 `:88`** | 歸類正確；見 `GROK-R11-P2-01` |
| E-025 | 產出端 PostToolUse | `synth_attribution_hook.sh:40`、`debt_clear.sh:584` 正確 | 歸類正確 |

`VERIFY:` `bash scripts/gen_fact_key_blocks.sh --check` → **rc=0**。

### 4. E-5 probe 重跑＋立場

`VERIFY:` `bash handoffs/20260911-verdictgate-e5-probe.sh` → **rc=0**；`E5 PROBE: ORDER-ALWAYS-HOLDS`；ticket_commit 5 列皆在 token 後 append；4 列 `token_fresh=false`（mtime）。

**立場：同意「第二層無增量；mtime 保留」。** 合法 amend／rebase 之 append 序恆 ≥ token ⇒ 純序判對過期 token fail-open；序＋audit ts 差與 mtime 同型、無額外防護。E-5 可維持「研究完成、不做第二層」（或下票改標 user-ruling／researched-wont-do；本輪不要求改 TODO 文字）。

### 5. 可否收票？

**不可（就 grok）。** B1–B4 實戰擋過與 E-1～E-7「現在不做」大多仍成立，但 C-4 收票修正留下 **closure 首進 → 越过前批 blocked** 之機械縫（P1），未修前 `VERDICT: blocked`。

---

## §E E-1～E-7 殘留

| ID | 為何現在不做 | 本輪立場 |
|---|---|---|
| E-1 | user-ruling 刪 CI | 仍成立（蓄意 `--no-verify`） |
| E-2 | user-ruling 停鑽 small | 仍成立 |
| E-3 | needs-research（蘊涵判準） | 研究問題／完成判準仍具名；與 1b「偽 heading CLOSED」同族，維持 |
| E-4 | 補裁決輪處置 | 本輪前 SPLITUNIFY B7 補裁決已走；殘留觸發條件可標完成於 synth，非本家阻塞 |
| E-5 | needs-research → 本輪重跑 | 研究完成；不做第二層（見必答 4） |
| E-6 | needs-research | 判準仍具名，維持 |
| E-7 | user-ruling 停輪 | 仍成立（scripts-only 擴 scope 代價未評估） |

---

## 1b. register-output 語料納 expected_outputs

**無新縫（相對本改動）。** 語料按 `expected_outputs[family]`；`verdict_parse` CLOSED 只准本家前綴；不存在檔 `OSError: continue` ⇒ ID 不在集合 ⇒ 拒收。偽 heading 寫進本輪自己的 expected 檔即可 CLOSED——此為 E-3 語意層既有面，非本改動引入；主委「只 CLOSE 本家」立場對**跨家**攻擊成立。

---

## Findings

## GROK-R11-P1-01

**斷言**: `verdictgate_check`「本批已有任一 `committee_round_open` 則跳過前批驗證」加上 closure 開輪免除 verdictgate，構成「closure 首進批次 → 前批 blocked 仍可領下批 token」的機械縫。

**碼證**: ①`scripts/verdictgate_check.sh:36-54` skip 不讀 `brief_kind`／abandoned。②`scripts/committee_run.sh:433`、`scripts/gate.sh:957` closure 不呼叫 checker。③暫存 audit：b1 blocked ⇒ checker rc=1；append `DEMO-b2-CLOSURE-R1` round_open ⇒ rc=0；再 append `debt_abandon` 同 round_id ⇒ 仍 rc=0。④`--impl-self` 發 token 前走同一 checker（`gate.sh:959`）；impl brief-kind 約束不消除「先造 closure round_open」路徑。RECHECK: 重跑本檔必答 1 之暫存 audit 三步；或加測「僅 closure round_open 於 bN 且 bN-1 blocked ⇒ `--impl-self`／checker rc≠0」。

**來源摘要**: scripts/verdictgate_check.sh#e2bd25b73715; scripts/committee_run.sh#34a7ad787de0; scripts/gate.sh#ebc27429b84f

[MAJOR] 信心度=High。會怎麼失敗：補裁決／閉合豁免被濫用成「未審碼進入新批」。修法：skip 僅當本批已有 review（或 legacy-as-review）之 `committee_round_open`；mutation 加「sole closure open 不得 skip」。未修前不得收票。

## GROK-R11-P2-01

**斷言**: E-024 理由欄寫 `ticket_batch_check.sh:49` 為 `--push-range`，該行實為 `--msg` 分支；`--push-range` 在 `:88`。

**碼證**: `docs/GOV_ENFORCEMENT_REGISTRY.md` E-024 列；`scripts/ticket_batch_check.sh:49`＝`--msg)`，`:88`＝`--push-range)`。`commit-msg:41` 主錨點仍正確。RECHECK: `sed -n '49p;88p' scripts/ticket_batch_check.sh`。

**來源摘要**: docs/GOV_ENFORCEMENT_REGISTRY.md#8124ffba100b; scripts/ticket_batch_check.sh#7e3422da39eb

[MINOR] 信心度=High。不擋收票邏輯；收票修登記行號即可。E-022 第二層 `:28` 同類錨偏，併記不另開 ID。

---

## §1 其餘類別

矛盾／漏項／不可測／quant／過度工程／OOM／Cache／API／短命工：無（本輪收票範圍）。  
測試品質：already_entered 正向有測；**缺** sole-closure 負向（併入 P1-01 修法）。  
被當成事實的未驗證假設：主委「假輪要能開，前批就已放行」把「輪」默認為 review——**assumed**，已被 closure 首進否證。

---

VERDICT: blocked
BLOCKED-BY: GROK-R11-P1-01
CLOSED:
STATUS: DONE

---

ASSUMPTIONS_VERIFIED: closure 開輪跳過 verdictgate；skip 不看 brief_kind／abandoned；impl brief 不得為 closure；E-5 probe ORDER-ALWAYS-HOLDS；gen_fact_key_blocks --check rc=0；E-022~025 行號可執行（E-024:49 語意誤錨）。
TESTS_RUN: `bash handoffs/20260911-verdictgate-e5-probe.sh` → rc=0 ORDER-ALWAYS-HOLDS；暫存 audit verdictgate CASE A rc=1／B+C+abandon后 rc=0；`bash scripts/gen_fact_key_blocks.sh --check` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260912-verdictgate-x-review-r11-grok.md --family grok`（見收尾）。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: handoffs/20260912-verdictgate-x-review-r11-grok.md
TMP_CLEANUP: 清除 `/tmp/vgseam*` `/tmp/e5probe*` `/tmp/vg_*.out` `/tmp/gfkb_check.out`；保留 `/tmp/claude-501*`
STATUS: DONE
