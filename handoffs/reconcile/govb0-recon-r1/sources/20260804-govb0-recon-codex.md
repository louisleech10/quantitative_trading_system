# GOVB0 第 0 批偵察 — codex

task-id: GOVB0-RECON-R1
family: codex
brief-kind: consult
scope: B-24 / B-15 / B-14；只讀 repo，探針在隔離副本

## Verdict

可以進入下一步起草 SPEC，但目前只能起草「修正後的契約」草案，不能直接 freeze/dispatch。B-15 backlog 的三個 FP 並非同一根因；選項②單獨使用會 fail-open；B-24 的「不另建檢查器」違反工具強制要求；B-14 的 `--single` 不能證明逾時產出完整。SPEC 必須先把這四個事實寫正。

## Findings

## CODEX-R1-P0-01

**斷言**：B-15 的「三個 FP 都是 regex 不理解引號」不成立；只重現第一例，後兩例餵入 `gate_check.sh:86` 等價正則均不命中。

**碼證**：隔離副本使用與 `scripts/gate_check.sh:86` 相同的 command-position alternation；`pgrep` 在引號內的 `|grok ` 被當成分隔符，位置 35（1-based），移除引號內容後不命中。`for` 與 `--lock` 均 raw/quote-aware 皆為 NO。

**來源摘要**: `scripts/gate_check.sh#871258c9ea2e`; `handoffs/20260801-GOV-AMEND-BACKLOG.md#13cc634125da`; `handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345`

Q1 receipt：

| FP | 完整指令字串 | raw 命中 | 命中 alternation／位置／上下文 | quote-aware |
|---|---|---|---|---|
| 1 | `pgrep -fl 'codex exec|cursor-agent|grok '` | YES | 第一段 `(codex|cursor-agent|grok|agy)`；`|grok ` 起點 35（1-based），上下文 `...cursor-agent|grok `；分隔符在 shell 引號內 | NO |
| 2 | `for f in codex composer grok; do sed -n 1p "$f"; done` | NO | none | NO |
| 3 | `bash scripts/completeness_check.sh --lock /tmp/sources.lock` | NO | none | NO |

結論：第一例是可重現的 quoted-separator FP；第二、三例不是這條 regex 的可重現結果。backlog 對第二、三例的記載應保留為「事故觀察、觸發源未定位」，不可寫成已證實根因。

## CODEX-R1-P0-02

**斷言**：B-15 選項②「只看是否呼叫 wrapper/callpoint」不可單獨採用，因為它漏掉直接手搓的 agent CLI；選項③必須是 quote-aware executor 判定加 wrapper callpoint 補強。

**碼證**：`cx_run.sh:443`、`:452`、`:461` 實際執行三家 CLI；`committee_run.sh:268` 實際呼叫 `cx_run.sh`。隔離原型對同一語料的結果是：方案①直接 CLI 4 條擋住、2 條 wrapper 漏網；方案② 2 條 wrapper 擋住、4 條直接 CLI 漏網；方案③ 6 條 TP 全擋，5 條 TN 全放。

**來源摘要**: `scripts/cx_run.sh#39cfdddec350`; `scripts/committee_run.sh#4c6bdeff1a15`; `scripts/gate_check.sh#871258c9ea2e`; `handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345`

Q2 corpus 與 receipt：

| 標籤 | 語料形態 | 來源 |
|---|---|---|
| TP | `codex exec ...` | `scripts/cx_run.sh:443` |
| TP | `grok -m grok-4.5 ... -p ...` | `scripts/cx_run.sh:452` |
| TP | `cursor-agent -p --force ...` | `scripts/cx_run.sh:461` |
| TP | `bash scripts/cx_run.sh codex ...` | `scripts/committee_run.sh:268` 的實際 caller 形態 |
| TP | `bash scripts/committee_run.sh ... codex` | `handoffs/20260804-GOVB0-RECON-BRIEF.md` 的手搓路徑前提；用於 mutation |
| TP | `GATE_DIR_OVERRIDE=/tmp/x codex exec ...` | `scripts/gate_check.sh:78` 的 env-prefix stripping 後仍命中 |
| TN | `pgrep -fl 'codex exec|cursor-agent|grok '` | backlog `:340`；quote-aware 後放行 |
| TN | `for f in codex composer grok; do ... done` | backlog `:341`；本正則下放行 |
| TN | `completeness_check.sh --lock ...` | backlog `:342`；本正則下放行 |
| TN | `cat sp_codex.txt` | `scripts/gate_check.sh:82` 明列的檔名子字串例 |
| TN | `bash scripts/gate.sh dispatch --reason "read-only codex closure review"` | 隔離原型；quote-aware executor 判定不命中 |

| 方案 | TP 被擋 | TP 漏網 | FP 誤擋 | TN 正確放行 |
|---|---:|---:|---:|---:|
| ① quote-aware family-position | 4 direct/env | 2 wrapper | 0 | 5 |
| ② wrapper/callpoint only | 2 wrapper | 4 direct/env | 0 | 5 |
| ③ ① + ② | 6 | 0 | 0 | 5 |

原型採用：先移除 shell 引號內的內容，再套用 `gate_check.sh:86` 的命令位置判定；另加 `scripts/cx_run.sh`／`scripts/committee_run.sh` 的 tokenized callpoint。方案③是本輪建議，仍需在 SPEC 中補齊 env prefix、shell separator、self-exclusion 與 `Task` kind 分支的 mutation case。

## CODEX-R1-P0-03

**斷言**：B-24 的「只把狀態斷言寫入各票，不另建檢查器」不能滿足使用者定死的 machine-enforced 條款；沒有 checker/hook，仍是 prose discipline。

**碼證**：backlog `:734-736` 明寫「不另建檢查器」。現有 `templates/RESULT_TEMPLATE.md:5-24` 已有可機讀枚舉欄位，但未形成所有 `docs/*{SPEC,TODO}*.md` 驗收欄的強制入口。機械盤點在明確定義的窄條件下得到 templates 2 candidate（only-run=0、state=2），docs root glob 629 candidate（only-run=304、state=325）；這是候選列盤點，不是語意 oracle 或 FPR。

**來源摘要**: `handoffs/20260801-GOV-AMEND-BACKLOG.md#13cc634125da`; `templates/RESULT_TEMPLATE.md#03e6eb5d3462`; `templates/SPEC_TEMPLATE.md#d667a8f74305`; `docs/GOVERNANCE_HARNESS_P0_TODO.md#05a0d809c6ef`

Q4 scan receipt：使用命令 `awk '/驗收|驗證|acceptance|validation/ && /rc|exit|pytest|bash|grep|PASS|passed|全綠/'`，只掃 `templates/*.md` 與 shell literal glob `docs/*SPEC*.md docs/*TODO*.md`，再以 `狀態|state|result_state|git status|非空|存在|hash|sha|==|輸出|結果|檔案` 標記 state；結果為 `templates candidate=2 only=0 state=2`、`docs-root candidate=629 only=304 state=325`，`wc -l` 對應的 docs candidate 行輸出為 629 條。

代表性行號：`templates/SPEC_TEMPLATE.md:26-34` 已有固定 `ASSERT ... THEN rc=` 文法；`templates/COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md:26-28,38-43` 有 rc 與 Fresh findings 狀態；`templates/RESULT_TEMPLATE.md:7-24` 有枚舉狀態與 receipt 綁定。反例是 `docs/GOVERNANCE_HARNESS_P0_TODO.md:182-184` 只把 `gate.sh dispatch` rc=0 當驗收，`docs/FRACDIFF_MAXLAG_TODO.md:164` 只寫 receipt passed 計數與 restore exit 0；狀態例是 `docs/P2DEBT_T3_TSCFIX_TODO.md:57` 的 `comm -13` 精確 delta。

不能估出可信的誤報率：現有 repo 沒有標註 corpus、checker 或 acceptance schema；直接用「rc=0 同行沒有 state keyword」會把合法的 help/syntax/non-conditional checks 與文件討論行一起報錯，也會漏掉跨行或自然語言狀態。B-24 應改為固定 grammar 或結構化 acceptance manifest，由 hook/CI 實際執行 post-state assertion；304 只代表待標註候選數，不是 304/629 的 FPR。

## CODEX-R1-P0-04

**斷言**：B-14 提議用 `completeness_check.sh --single` 判斷逾時產出「完整即成功」是不充分的；一份剛好最後一個 finding body 完整的截斷檔會被誤判成功。

**碼證**：`completeness_check.sh:1451-1473` 的 `--single` 只檢查 canonical ID、同檔重複 ID、finding body 與來源摘要格式，不檢查 producer 是否已退出、EOF/terminal marker、預期 finding 數或寫入是否完成。隔離副本把真實 handoff `handoffs/20260804-p16-r9-codex.md` 截成 6 行，保留一個完整 finding body；實跑輸出 `COMPLETENESS PASS(single): ... — 1 個 canonical ID，格式合規。`、`CHECK_RC=0`、`STATUS_ASSERTION_LINES=6`，最後一行仍是完整 body。

**來源摘要**: `scripts/completeness_check.sh#12e981972d78`; `scripts/cx_run.sh#39cfdddec350`; `handoffs/20260801-GOV-AMEND-BACKLOG.md#13cc634125da`

所以 timeout 後若沒有 CLI exit=0 的直接證據，`--single` PASS 仍應判 `failed`；若格式檢查真的失敗才是 `format-failed`。可接受的成功機械依據應由 SPEC 定義為 producer 最後寫入的 terminal marker/atomic close receipt（並在 marker 前完成 flush/fsync），再加 `--single`；不能只看 finding 恰好閉合。

## CODEX-R1-P1-01

**斷言**：B-14 的主要 timeout 應包在 `cx_run.sh` 的 per-family CLI 呼叫，`committee_run.sh` 的 `wait` 只能做外層安全閥；建議第一版 timeout 20 分鐘，證據是 18 分鐘內完成的實測批次加 2 分鐘明示政策 margin，不是憑感覺的 30 分鐘。

**碼證**：`cx_run.sh:443,452,461` 是三家前景 CLI；`:468-497` 只有 CLI 返回後才做 format check、emit、register。`committee_run.sh:280` 是裸 `wait`，外層 timeout 若先殺 wait，容易留下 child/orphan、缺 result_state/audit 或不完整 runlog。既有 B-14 事故記錄三家 output mtime 在 18 分鐘內、committee 仍等 2 小時 20 分。

**來源摘要**: `scripts/cx_run.sh#39cfdddec350`; `scripts/committee_run.sh#4c6bdeff1a15`; `handoffs/20260801-GOV-AMEND-BACKLOG.md#13cc634125da`

Q3 mtime receipt：對 `handoffs/20260803-*`／`handoffs/20260804-*` runlog，從 `out=handoffs/...md` 取實際 output，直接比較 `stat -f %m`；127 筆且 stats file 非空，結果：

| family | N | P50 | P90 | max |
|---|---:|---:|---:|---:|
| grok | 43 | 26s | 41s | 70s |
| composer | 40 | 27s | 51s | 8466s |
| codex | 44 | 68s | 164s | 719s |

`DELAY_GE_600` 只有 `20260803-frozen-proc-v2-stamp-codex`=719s 與 `20260803-govflow-todo-r2-composer`=8466s。這是 output-write 到 runlog-close 的 proxy，不是 CLI runtime；timeout 的硬下限仍取事故中「18 分鐘內完成」的觀測，20 分鐘的 2 分鐘 margin 需由 SPEC/主委核准。

`result_state` 合法值與寫入點：`cx_run.sh:258,264-272` 寫 `success`／`format-failed`／`failed`；`cx_run.sh:277-287` 以 `committee_family_result` audit event 寫出 `result_state` 與 output sha。timeout 且未取得完整 terminal evidence：`failed`；已觀測 CLI rc=0 但格式不合：`format-failed`；正常 rc=0 且完整格式：`success`。

## Q5 — 三票順序與耦合

backlog 的 `B-24 → B-15 → B-14` 順序（`handoffs/20260801-GOV-AMEND-BACKLOG.md:547-568`）方向正確，但前提要改成：先定義可機檢 acceptance state contract，再做 B-15 predicate/mutation，最後做 B-14 timeout/result lifecycle。B-15 與 B-14 沒有共同修改 `gate_check.sh` 的檔案衝突；B-14 內部必須同批改 `cx_run.sh` 與 `committee_run.sh`，因後者 `:268` 呼叫前者、`:280` 等前者。若 B-24 checker 另觸及 shared hook，需拆出其 schema/checker 變更再合併。

## Q6 — 是否可起草 SPEC

**可起草，但不可直接派工或 freeze。** 起草版必須：

1. 更正 B-15 三個 FP 的證據狀態，將後兩例列為未重現／觸發源待查。
2. 將 B-15 方案③作為 baseline，加入 direct CLI、wrapper、env prefix、quoted TN、`Task` kind 與 self-exclusion mutation。
3. 將 B-24 從 prose-only 改成固定 grammar/manifest + 實際 checker/hook，並先標註 304/629 候選的 false-positive corpus。
4. 將 B-14 的 terminal completeness evidence、process-group termination、20m 初始值與三值 `result_state` 寫成可證偽 acceptance。

## Assumptions / receipts

- `scripts/gate_check.sh:86` 實際 regex 與 brief 一致；env prefix stripping 後 direct CLI 仍命中。
- B-15 第一例 raw YES / quote-aware NO；第二、三例 raw/quote-aware 均 NO。
- `scripts/cx_run.sh` 有 `success`／`failed`／`format-failed` 三值與明確 emit；沒有 timeout branch。
- `committee_run.sh:280` 為裸 `wait`；`completeness_check --single` 對 6 行截斷檔仍輸出 PASS、rc=0。
- 127 筆 runlog/output mtime proxy stats file 非空；兩筆 ≥600s outlier 已列出。

## Scope / artifact

沒有修改 repo 內 scripts、tests、data_cache 或 root `HANDOFF.md`。canonical 產出：`handoffs/20260804-govb0-recon-codex.md`。本輪不產 gating stamp，因 brief 明定 `brief-kind: consult` 且尚無 SPEC。

