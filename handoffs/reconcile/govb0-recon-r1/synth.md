# Reconcile — govb0-recon-r1

**來源** 20260804-govb0-recon-codex.md, 20260804-govb0-recon-grok.md, 20260804-govb0-recon-claude.md　|　**roster** claude,codex,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 可合併 — 21 條全數 ACCEPT 或 NOTED，零 REJECT；一條（C-7 timeout 值）為家族間實質分歧，
不阻擋合併，改列為 SPEC adversarial 輪的必答題。本輪為偵察（discovery），產出直接作為第 0 批 SPEC 的事實前提。

**收斂基數**：21 條（codex 5／grok 9／claude 7）。下表逐條對應，**無未分群 ID**。

| 群 | 主張 | 對應 finding | 處置 |
|---|---|---|---|
| C-1 | `票 B-15` 記載的根因句錯誤；三例 FP 分屬不同機制 | `CODEX-R1-P0-01`／`GROK-R1-P0-01`／`CLAUDE-R1-P1-02`／**`CLAUDE-R1-P0-07`** | **ACCEPT（含內部覆寫）** |
| C-2 | 修法選項②單獨採用＝fail-open，手搓 CLI 全漏 | `CODEX-R1-P0-02`／`GROK-R1-P0-02`／`CLAUDE-R1-P0-04` | **ACCEPT** — 採方案③ |
| C-3 | 既有 fail-open：帶路徑前綴的家族 CLI 不擋 | `GROK-R1-P0-03` | **ACCEPT** — 納入 `B-15` scope |
| C-4 | 既有 fail-open：官方外層腳本直呼不需 token | `GROK-R1-P1-03` | **ACCEPT** — 納入 `B-15` scope |
| C-5 | `票 B-24`「不另建檢查器」不滿足使用者定死條款 | `CODEX-R1-P0-03`／`GROK-R1-P1-02` | **ACCEPT** — 改寫 `B-24` 修法欄 |
| C-6 | `completeness_check --single` 不足以判「逾時且完整＝success」 | `CODEX-R1-P0-04`／`GROK-R1-P1-01` | **ACCEPT** — 需 terminal marker |
| C-7 | `B-14` timeout 值：20m（codex）vs 60m（grok） | `CODEX-R1-P1-01` vs `GROK-R1-P2-01` | **PARTIAL — 分歧未解，見下** |
| C-8 | 前置阻塞：被擋指令全系統零紀錄 ⇒ 誤擋率不可量測、改完不可驗收 | `CLAUDE-R1-P0-01` | **ACCEPT** — `B-15` 拆兩段 |
| C-9 | 現行正則 TP 面完好（7/7），問題純在 TN 面 | `CLAUDE-R1-P1-03` | **ACCEPT** — 列為設計約束 |
| C-10 | `cx_run.sh` 零耗時紀錄 ⇒ timeout 值無一手數據 | `CLAUDE-R1-P1-05` | **ACCEPT** — 併入 `B-14` |
| C-11 | 三票主改檔不相交，順序 `B-24`→`B-15`→`B-14` 維持 | `GROK-R1-P2-02` | **ACCEPT** |
| C-12 | `ts_stamp.log` 非 UTF-8 ⇒ 預設 locale 下 grep 靜默返空 | `CLAUDE-R1-P2-06` | **ACCEPT ＋ 升級，見下** |
| C-13 | brief 三條 fact-verified 經複核一致，無推翻 | `GROK-R1-P3-00` | **NOTED** |

**C-1 的內部覆寫（重要）**：`CODEX-R1-P0-01`／`GROK-R1-P0-01`／`CLAUDE-R1-P1-02` 三家一致判定
FP-2（`for` 迴圈）與 FP-3（`completeness --lock`）**不可重現**。
2026-08-04 22:5x 主委在**真實唯讀操作中被擋**（`head -3 "/private/tmp/claude-501/…"; git rev-parse --short origin/main`），
據此定位 **FP-3 屬第二段 `claude[^|]*(-p|--print)`**（`CLAUDE-R1-P0-07`，附隔離重現表）。
⇒ **三家的「不可重現」是重建語料缺 `claude` 或缺 `-p` 所致，非該 FP 不存在。**
現況：**FP-1＝洞 A（引號）已證、FP-3＝洞 B（`claude` 子字串）已證、FP-2 仍未定位**（待 C-8 的紀錄機制上線）。
🔴 洞 B 同時是 **fail-open**：`[^|]` 不跨管線 ⇒ `cat x | claude -p "…"` 不被擋，須進 TP 語料。

**C-7 分歧（不阻擋合併，但 SPEC 前必須解）**：兩家的數字差一個數量級，因為**量的是不同區間**——
codex：output 寫入 → runlog 關閉（n=127；grok p50 26s／composer p50 27s／codex p50 68s），是**尾段延遲**的 proxy；
grok：runlog birth → 最後寫入（n=440；ALL p50 5.3m／p90 20.7m／p99 48.5m），是**總時長**的 proxy。
per-family timeout 要包的是 **CLI 總時長** ⇒ 量測基準應取 grok 側，但其樣本含掛死案例（composer max 146.7m）會抬高尾端。
**列為 SPEC adversarial 輪必答**：①定義 timeout 要量的精確區間 ②排除掛死樣本後重算 p95/p99 ③給出可證偽的建議值。
**主委不自裁。**

**C-12 升級（本輪後續實測，非原 finding）**：主委為繞開 `ts_stamp.log` 的 locale 問題而 `export LC_ALL=C`，
該設定洩漏進 pre-push 環境，使 6 個治理測試轉紅（拿掉後 96 passed）。逐條檢視發現**方向不一致**：

| 案例 | 期望 | `LC_ALL=C` 實際 | 方向 |
|---|---|---|---|
| `## Verdict：`（全形冒號後空白）送 `gate.sh` | 拒發 token | **發出 token** | 🔴 **fail-open** |
| `**Verdict: （待填…）**` 送 `doc_format_precheck.sh` | rc=2 擋下 | **rc=0 放行** | 🔴 **fail-open** |
| 合格 SPEC 送 `template_check.sh spec` | rc=0 | 誤判缺 §A 錨點 | fail-closed 誤報 |

⇒ **`gate.sh` 與 `doc_format_precheck.sh` 的守衛是 locale 相依的**；委員或 CI 在非 UTF-8 環境執行會**靜默失去該防線**。
**處置：開新票，交下一輪委員裁決嚴重度與修法**（不在本批 scope 內自行擴張）。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## GROK-R1-P0-01

**斷言**: backlog 所稱 FP2（`for f in codex…`）與 FP3（`completeness_check --lock`）在現版 `gate_check.sh:87` **無法重現為 dispatch 誤擋**；不得寫進 SPEC 當已證根因。

**碼證**: 隔離 `gate_check`：`FP2 rc=0`、`FP3 rc=0`；regex 無 match。對照 FP1 `rc≠0` 且 span `(34,40)=|grok `。`VERIFY: printf '%s' "for f in codex composer grok; do cat x; done" | grep -Eq '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]' ; echo $?` → 預期 1。

**來源摘要**: scripts/gate_check.sh#871258c9ea2e

BLOCKING（對錯誤 SPEC 前提）信心度=High。修法：acceptance 只承諾已重現形態（FP1、引號分號、絕對路徑洞、外層 cx_run 洞）。

---

## GROK-R1-P0-02

**斷言**: B-15 修法選項②（只認 `cx_run`／`committee_run`／`gate dispatch`）對語料 TP **漏網 10/13**，含全部手搓 `codex exec`／`cursor-agent`／`grok`／`claude -p`，屬 fail-open，**不可採用為唯一判準**。

**碼證**: 隔離原型計分表（Q2）；`codex exec` CURRENT=BLOCK、OPT2=ALLOW。出處手搓風險：`scripts/cx_run.sh:5` 註解「勿再手搓」。

**來源摘要**: scripts/cx_run.sh#39cfdddec350

BLOCKING 信心度=High。修法：①+basename+呼叫點疊加；mutation 必含手搓 CLI 仍擋。

---

## GROK-R1-P0-03

**斷言**: 現版 gate 對 **絕對路徑家族 CLI**（`cx_run` 真實呼叫形態 `$CODEX`／`$GROK`）**不擋**，是已存在 fail-open，SPEC 必須修。

**碼證**: live 隔離 gate：`/opt/homebrew/bin/codex exec hi` → rc=0；`/Users/louis/.grok/bin/grok -m x -p y` → rc=0；對照 `cursor-agent -p hi` 有擋。源碼：`cx_run.sh:443,452` 使用絕對路徑變數。

**來源摘要**: scripts/cx_run.sh#39cfdddec350

BLOCKING 信心度=High。修法：命令位改 `(?:\S*/)?(codex|cursor-agent|grok|agy)[[:space:]]`。

---

## GROK-R1-P1-01

**斷言**: `completeness_check.sh --single` rc=0 **不能**單獨作為 B-14「逾時且產出完整⇒success」的充分條件。

**碼證**: 構造兩 finding 齊全但無 `STATUS: DONE` 之檔 → `DIRECT_RC=0`；缺碼證檔 → `DIRECT_RC=1`。single 路徑 :1459–1472 無結尾標記檢查。

**來源摘要**: scripts/completeness_check.sh#12e981972d78

MAJOR 信心度=High。修法：success 判準疊 STATUS/Verdict/mtime 穩定。

---

## GROK-R1-P1-02

**斷言**: B-24「不另建檢查器、只改驗收散文」與使用者定死「工具自帶強制、不准靠記性」衝突；本批若照 backlog 原文結案會假閉合。

**碼證**: backlog `## B-24`「併入…不另建檢查器」；HANDOFF「工具必須自帶強制機制」。templates 無 B-24 狀態斷言必填錨；`COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md` 反多 `rc=0`。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#13cc634125da

MAJOR 信心度=High。修法：窄域機檢或範本強制 token 或 receipt runner。

---

## GROK-R1-P1-03

**斷言**: 官方外層 `bash scripts/cx_run.sh`／`committee_run.sh` 在 CURRENT 下 **不分類為 dispatch**（PreToolUse 只見外層）；與「派工必經 gate token」政策不一致，疊加呼叫點可補。

**碼證**: live：`bash scripts/cx_run.sh codex brief out` → rc=0（無 token 仍放行）。Task 工具另計（:73–75 無條件 dispatch）。

**來源摘要**: scripts/gate_check.sh#871258c9ea2e

MAJOR 信心度=High（政策洞；子進程本就不可見）。修法：納入 ③。

---

## GROK-R1-P2-01

**斷言**: B-14 per-family timeout 建議硬頂約 **60 分鐘**（數據：ALL p99=48.5m；codex max=43.1m；掛死樣本 146.7m），**不應**用 30m 全球值。

**碼證**: 440 個 `handoffs/**/*.runlog` birth→mtime 分布（Q3 表）；最長 `20260803-govflow-todo-r2-composer.runlog` 146.7m。

**來源摘要**: scripts/committee_run.sh#4c6bdeff1a15

MINOR/建議 信心度=Medium（birthtime 代理，非 audit 內建 duration 欄）。修法：env 可覆寫；composer 可另參 p95。

---

## GROK-R1-P2-02

**斷言**: 三票主改檔不相交，可同一批次分 Phase；B-15 必須附前後對照語料（因 B-29 未做）。

**碼證**: B-15→`gate_check.sh`；B-14→`cx_run.sh`+`committee_run.sh`；B-24→templates/驗收句。HANDOFF 明示 B-15 即 B-29 差集案例。

**來源摘要**: HANDOFF.md#c49bf7e9d2b0

MINOR 信心度=High。

---

## GROK-R1-P3-00

**斷言**: 本偵察對 brief fact-verified 三條（正則命令位、audit 無指令、cx/committee 無 timeout）複核一致，無推翻。

**碼證**: 讀 `gate_check.sh:82-87`；`gate_deny` fields 僅五欄；`grep -c timeout scripts/cx_run.sh`→0；`committee_run.sh:280` 裸 wait。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

NON-BLOCKING 信心度=High。

---

## CLAUDE-R1-P0-01

**斷言**: 被 `gate_check.sh` 擋下的指令**在整個系統中沒有任何紀錄** —— `audit.log` 的 `gate_deny` 事件不含指令欄位，`ts_stamp.log` 因 hook 排序在 gate 之後而不會執行。因此 `B-15` 的誤擋率**無法事後量測**，改完也**無法驗證改對了**。

**碼證**:
- `scripts/gate_check.sh:28` 的 `_append_gate_deny_audit` 只寫 `{"event","ts","tool","kind","reason"}` 五欄，**無 command**。
- `.claude/settings.json:99-135`：`PreToolUse` 依序為 ①`gate_check.sh`（matcher `Task|Bash|Write`）②`block_busywait.sh` ③`verify_pretooluse.sh` ④`ts_stamp.sh IN`（matcher `Bash|Edit|Write`）。gate 為**第 1 個**。
- 決定性實測（今日已知被擋的指令）：`LC_ALL=C grep -ac 'closure review' .claude/gate/ts_stamp.log` → **0**；
  改用訊息檔的成功重試 `LC_ALL=C grep -ac 'hmsg.txt' .claude/gate/ts_stamp.log` → **2**。
  ⇒ 被擋者零紀錄、成功者有紀錄，機制確認。
- `LC_ALL=C grep -o '"reason":"[^"]*"' .claude/gate/audit.log | sort | uniq -c` → 全檔 599 筆僅兩值：`token_expired` 493、`open_debt` 106。**無任何 reason 指出「正則命中了什麼」**。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：這是 `B-15` 的**前置阻塞**，不是附帶改善。沒有 deny 紀錄則：①誤擋率是憑印象的 ②`票 B-29`（行為差集宣告）對 gate 這條線**做不出差集**，因為「舊版擋了誰」根本沒被記下來。
建議修法順序改為：**先讓 `gate_deny` 記下（a）完整指令（b）命中的 alternation，再談改判準**。落點＝`gate_check.sh:21-30`（`_append_gate_deny_audit` 加欄）＋ `:86` 命中時保留 `grep -Eo` 結果。
🔴 隱私/體積考量須在 SPEC 處理：指令可能含長 prompt；建議存 sha256＋前 N 字元，或另檔 `gate_deny_cmds.log` 並納入既有 rotate 機制。

---

## CLAUDE-R1-P1-02

**斷言**: backlog `## B-15` 節記載的三個 FP，**只有一例可重現**；另外兩例（`for` 迴圈讀產出、`completeness_check.sh --lock`）用票上記載的形態**跑不出 BLOCK**，且因 `CLAUDE-R1-P0-01` 無紀錄可查證。⇒ 票的事故描述是憑記憶寫的，**不可直接作為 SPEC 輸入**。

**碼證**: `.claude/tmp/b15probe.sh`（正則字面複製自 `gate_check.sh:86`，含 `:81-84` 的 env 前綴剝除與 `:88` 的 `gate.sh` 排除），實跑輸出：

| 案例 | 判定 | 命中片段 |
|---|---|---|
| `pgrep -fl 'codex exec\|cursor-agent\|grok '` | **BLOCK**（重現 ✓） | `\|grok ` |
| `for f in codex composer grok; do cat handoffs/…-$f.md; done` | ALLOW（**重現不出**） | — |
| `for f in codex composer grok ; do echo $f ; done` | ALLOW（**重現不出**） | — |
| `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260804-govb0-recon` | ALLOW（**重現不出**） | — |
| `bash …completeness_check.sh --lock handoffs/reconcile/…/sources/grok.md` | ALLOW（**重現不出**） | — |
| `git commit -m "fix: no review file; codex closure review done"` | **BLOCK**（今日實際踩到 ✓） | `; codex ` |

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：可重現的兩例**同一機制**——正則的 `[;&|]` 吃到**引號內**的 `|` 或 `;`。
不可重現的兩例有三種可能：①票記載的指令形態不精確 ②當時被擋的是同一分鐘內的**另一條**指令（我把兩者記混）③觸發源是 `claude[^|]*(-p|--print)` 那段而非家族名段。
🔴 **SPEC 不得宣稱「三例同因」**。可交付的結論只有：**引號不感知是已證實的一個真洞**；其餘待 `CLAUDE-R1-P0-01` 的紀錄機制上線後才有辦法查。

---

## CLAUDE-R1-P1-03

**斷言**: 現行正則的 **TP 面（真派工必須被擋）完好無缺**，7/7 全過；`B-15` 的問題**純在 TN 面**。任何修法若動到 TP 面就是淨損失。

**碼證**: 同 `.claude/tmp/b15probe.sh`，TP 段實跑全數 BLOCK：
`codex exec -s workspace-write`／`cursor-agent -p --force --model composer-2.5`／`grok -m grok-4.5 … -p`／
`GATE_DIR_OVERRIDE=/tmp codex exec …`（env 前綴繞過）／`cat brief.md | codex exec …`（管線後）／
`echo start; grok -m grok-4.5 -p …`（分號後）／`claude -p "…"`。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：⇒ 修法應為**收窄 TN 誤擋**，而非重寫判準。這條直接影響對方案②的評價（見下）。

---

## CLAUDE-R1-P0-04

**斷言**: `B-15` 修法選項②（改判準為「是否呼叫 `cx_run.sh`／`committee_run.sh`／`gate.sh dispatch`」）**單獨採用會造成 fail-open**：手搓 `codex exec`／`cursor-agent -p`／`grok -m` 三條真派工全部漏網，而現行正則擋得住它們。

**碼證**: `CLAUDE-R1-P1-03` 的 TP-1／TP-2／TP-3 三條命令列均**不含** `cx_run.sh`／`committee_run.sh`／`gate.sh`，在選項②判準下必然放行。手搓派工是 `AGENTS.md`／`.cursorrules` 明文禁止但**技術上完全可行**的路徑，且歷史上確實發生過（`gate_check.sh:78-80` 註解記載 2026-07-23「寫死漏 grok，主力實作 CLI 不被 PreToolUse 攔」的事故，正是同一類漏網）。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：**建議採方案③（疊加）**——保留現行家族名主判準（TP 面不動），只加**引號感知**的前處理（把引號內的 `;&|` 視為一般字元），呼叫點判準最多當**補強**、不得當替代。
⚠️ 我在 brief 裡把選項②標為 `assumed:「更乾淨」`，本條即自我推翻。

---

## CLAUDE-R1-P1-05

**斷言**: `scripts/cx_run.sh` **完全不記錄每家委員的起訖時間或耗時**，因此 `B-14` 的 timeout 值**在現有資料下無法用一手數據決定**，只能靠 runlog mtime 反推（誤差含寫檔延遲與 harness 排程）。

**碼證**: `LC_ALL=C grep -n "date\|SECONDS\|start_ts\|elapsed\|duration" scripts/cx_run.sh` → **零命中**。
`handoffs/*.runlog` 現有 460 份，內容為 CLI 原始 stdout，**無時間欄位**（樣本：`handoffs/20260804-govb0-recon-codex.runlog` 首行 `Reading additional input from stdin...`）。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：`B-14` 修法應**一併補 per-family 起訖時間戳**（寫入 runlog 檔頭或 audit 的 `committee_family_result` 事件），否則：①這次的 timeout 值是猜的 ②未來調整仍然沒有資料 ③無法偵測「某家族逐漸變慢」這種前兆。
這與 `CLAUDE-R1-P0-01` 是同一個病的兩個部位：**治理鏈在關鍵決策點不留可量測的紀錄**。

---

## CLAUDE-R1-P2-06

**斷言**: `.claude/gate/ts_stamp.log` 是 `Non-ISO extended-ASCII text, with LF, NEL line terminators`，**在預設 locale 下 BSD `grep` 對它靜默返回空**（連 `-c` 的計數都不輸出），使「查無此指令」與「量測壞掉」外觀完全相同。

**碼證**:
- `file .claude/gate/ts_stamp.log` → `Non-ISO extended-ASCII text, with LF, NEL line terminators`
- 預設 locale：`grep -c 'IN ' .claude/gate/ts_stamp.log` → **無任何輸出**，rc=1
- `LC_ALL=C grep -ac 'IN ' …` → **8702**；`git commit` 63、`pgrep` 26、`completeness_check.sh --lock` 175、`for f in` 218

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：主委本輪**已經據此做出一次錯誤結論**（誤判「被擋指令連 ts_stamp 都沒記」，理由是 grep 查不到；實際原因是 grep 壞掉，正確結論要靠另一條 hook 排序證據才成立）。
與 HANDOFF 已記的 zsh 斷詞事故同型：**壞掉的量測與「一切正常」外觀相同**。
建議：①任何對 `ts_stamp.log` 的分析一律 `LC_ALL=C grep -a` ②列入 `CLAUDE.md` Gotchas ③追根因＝`ts_stamp.sh` 寫入時未正規化控制字元（NEL 來自 CLI 輸出）。

---

## CLAUDE-R1-P0-07

**斷言**: backlog `## B-15` 第三例 FP（`completeness_check --lock`）的真正機制**已於 2026-08-04 22:5x 現場重現並定位**：不是家族名段，而是第二段 `claude[^|]*(-p|--print)`。觸發條件為「指令含字串 `claude`（`.claude/` 治理目錄或 `/private/tmp/claude-501/` scratchpad 皆命中）＋ 之後任一處出現 `-p` 子字串（`rev-parse`／`--porcelain`／`-print`，**不必是旗標**）＋ 兩者間無 `|`」。

**碼證**: 主委執行唯讀指令
`head -3 "/private/tmp/claude-501/…/tasks/bfzappo85.output"; git rev-parse --short origin/main`
遭 `[GATE BLOCKED] 偵測到 kind=dispatch` 擋下（**現場事故，非構造**）。
隔離重現 `.claude/tmp/b15probe2.sh`（正則字面複製自 `gate_check.sh:86`）：

| 案例 | 判定 |
|---|---|
| 只有 scratchpad 路徑（無 `-p`） | ALLOW |
| 只有 `git rev-parse`（無 `claude`） | ALLOW |
| **兩者併用** | **BLOCK ← 誤擋** |
| `ls /private/tmp/claude-501/; git status --porcelain` | **BLOCK** |
| `cat .claude/tmp/x.txt; git rev-parse HEAD` | **BLOCK** |
| `find .claude/tmp -name "*.md" -print` | **BLOCK** |
| `bash scripts/completeness_check.sh --lock /private/tmp/claude-501/sess; git rev-parse HEAD` | **BLOCK**（＝backlog FP-3 原形） |
| 同一條但中間加管線 | ALLOW（`[^|]` 不跨管線） |
| `claude -p "…"`／`claude --print "…"`（真 TP） | BLOCK（正確） |

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

正文：本條**推翻 `CLAUDE-R1-P1-02` 的「重現不出來」結論**，也推翻三家一致的
「FP-2／FP-3 不可重現」——**不可重現的原因是重建的指令缺了 `claude` 或缺了 `-p`**，
而非該 FP 不存在。
🔴 **嚴重性高於引號那條**：`.claude/` 是治理目錄、`/private/tmp/claude-501/` 是憲法規定的 scratchpad，
`-p` 又是極常見子字串 ⇒ **凡碰治理檔的唯讀指令都在擲骰子**；且「加管線就過」使它看起來時靈時不靈，
主委長期誤以為是隨機環境問題。
🔴 **也是一條 fail-open 線索**：`[^|]` 不跨管線 ⇒ `cat brief.md | claude -p "…"` **不會被擋**。
須併入 `B-15` 的 TP 語料驗證。
**修法**：`claude` 須比照家族名段限定在**命令位置**（`(^|[;&|][[:space:]]*)(\S*/)?claude[[:space:]]`），
且 `-p`／`--print` 須是**獨立引數**（前後為詞界），不得比對子字串。

---

