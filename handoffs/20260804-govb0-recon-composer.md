# GOVB0-RECON R1 — composer 偵察報告（B-24／B-15／B-14）

family: **composer** | task-id: `GOVB0-RECON-R1` | brief: `handoffs/20260804-GOVB0-RECON-BRIEF.md`  
scope: 事實查證與修法方案實測；**禁改碼**（隔離探針於 `/private/tmp/govb0-recon-composer/`）

---

## Verdict：可派工（主委可起草 SPEC；須吸收下列 P0 前提）

- **B-15**：三 FP 中僅 **FP1**（quote 內 `|` 當分隔符）與 **引號內 `; codex`** 可重現；**FP2/FP3 現版正則無法重現**。修法預設 **④ basename+引號感知+呼叫點**；**禁單用 option②**。
- **B-14**：`completeness_check --single` **不充分**；逾時建議 **30–60m/家族**（見 runlog 分布）。
- **B-24**：「不建檢查器、只改驗收散文」與使用者定死「工具自帶強制」**衝突**。
- 無必須先另開 hotfix 才能寫 SPEC 的技術 blocker。

---

## Q1（B-15）三個 FP 逐例重現

**方法**：生產正則＝`gate_check.sh:86`；`eval_bash.sh` 用 bash `grep -Eq`（與 gate 一致）；`gate_live.sh` 以 stdin JSON 餵隔離 `GATE_DIR_OVERRIDE` 取 live rc（無 token → dispatch 類 rc=2）。

**VERIFY**：
```bash
bash /private/tmp/govb0-recon-composer/eval_bash.sh
bash /private/tmp/govb0-recon-composer/gate_live.sh
# FP1 MATCH=YES / fp1_rc=2；FP2/FP3 MATCH=NO / rc=0；QUOTE MATCH=YES / quote_rc=2
```

| FP | 完整指令字串 | 是否命中 | 命中的 alternation | 命中處字元位置與上下文 | live gate rc |
|---|---|---|---|---|---|
| FP1 `pgrep` | `pgrep -fl 'codex exec\|cursor-agent\|grok '` | **YES** | `\|` 後的 `grok` | pos≈34；context `…cursor-agent\|grok '`（`\|` 在 shell 引號內） | **2** |
| FP2 `for` 讀產出 | `for f in codex composer grok; do sed -n '1,3p' handoffs/x-${f}.md; done` | **NO** | — | 家族名在 `in` 列表／檔名，非命令位 | **0** |
| FP3 `completeness --lock` | `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260803-frozen-proc-amend/sources.lock` | **NO** | — | 無家族 CLI 命令位 | **0** |
| （對照）引號內 `; codex` | `git commit -m "fix: reason; codex closure review done"` | **YES** | `; codex ` | pos≈26；context `…reason; codex closure…` | **2** |
| （對照）檔名子字串 | `cat handoffs/sp_codex.txt` | **NO** | — | 與 `gate_check.sh:82` 註解一致 | **0** |

**結論**：
1. backlog `## B-15`「判定僅比對指令字串是否含家族名」**錯誤**——實碼為**命令位置**比對（brief fact-verified 複核通過）。
2. FP1 機制是 **quote 內的 `|` 被當命令分隔符**（非單純子字串匹配）；引號感知可修 FP1 與 `; codex` 類。
3. **FP2/FP3 重現不出來**——backlog 記載可能有誤，或觸發源為 Task 工具／不等價指令／舊版 gate；SPEC acceptance 不得假裝已覆蓋。

---

## Q2（B-15）語料與方案實測

### 語料（真實出處；`corpus.tsv` 於 workdir）

| 類 | 出處 | 形態 |
|---|---|---|
| TP | `scripts/cx_run.sh:443,452,461` | `codex exec`／`grok -m`／`cursor-agent -p` |
| TP | `scripts/cx_run.sh:291-292` | `/opt/homebrew/bin/codex exec`、`/Users/louis/.grok/bin/grok -m`（**絕對路徑**） |
| TP | `scripts/committee_run.sh:268` | `ROUND_ID=… bash scripts/cx_run.sh codex …` |
| TP | `cx_run.sh:5` 明文禁止 | 手搓 `codex exec`、`GATE_DIR_OVERRIDE=… codex exec` |
| TN | backlog FP1–3、`gate_check.sh:82` | pgrep／for 迴圈／completeness --lock／`cat sp_codex.txt` |
| TN | `scripts/cleanup_stale_dispatch.sh:53` | 唯讀 grep 家族名 |

### 方案（隔離原型 `eval_bash.sh`；n=17：TP=8 TN=9）

| 方案 | 規則 |
|---|---|
| 0-current | 現況 `:86` 正則 + env 前綴剝除（同 `:78-81`） |
| ① 引號感知 | 剝引號 span 後套 0 |
| ② 呼叫點 | 僅 `scripts/cx_run.sh`／`committee_run.sh`／`gate.sh dispatch` |
| ③ 疊加 | ① OR ② |
| ④ 建議 | ① + 多段路徑 basename `(/…/)*(codex|…)` + ② |

| 方案 | TP 被擋 | TP 漏網 | FP 誤擋 | TN 正確放行 |
|---|---:|---:|---:|---:|
| 0-current | 3 | **5** | **1** | 8 |
| ① 引號感知 | 3 | **5** | 0 | 9 |
| ② 呼叫點 | 1 | **7** | 0 | 9 |
| ③ 疊加 | 4 | **4** | 0 | 9 |
| ④ basename+③ | 8 | **0** | 0 | 9 |

**TP 漏網明細（fail-open 權重最高）**：
- 0/①：絕對路徑 `…/codex`、`…/grok`；外層 `bash scripts/cx_run.sh`（**官方 harness 亦漏**）
- ②：全部裸名／手搓 CLI——**不可用**
- ③：僅剩絕對路徑與 env 手搓

**VERIFY（絕對路徑繞過 + 裸名有擋）**：
```bash
bash /private/tmp/govb0-recon-composer/gate_live.sh
# abs_codex_rc=0（漏網）；bare_composer_rc=2；bare_codex_rc=2
```

**對 brief assumed 的 verdict**：
1. 「三 FP 全因引號不感知」→ **FALSE**（FP1 主因是 quote 內 `|`；FP2/FP3 未命中）
2. 「option② 更乾淨」→ **FALSE 且更危險**（TP 漏網 7/8）
3. **建議 SPEC 默認**＝④；`gate.sh dispatch` bootstrap 維持 token 政策

---

## Q3（B-14）逾時落點與「完整即成功」

### 現況（fact）

- `grep -c timeout scripts/cx_run.sh` → 0（exit 1）；`:443/:452/:461` 前景直呼 CLI
- `committee_run.sh:280` 裸 `wait "${pid}"`，無上限
- B-14 事故：`20260803-govflow-todo-r2-composer.md` mtime **17:31**；對應 runlog **19:52**（空等 ~8466s 於產出完成後）

### 落點建議

| 層 | 作法 | 代價 |
|---|---|---|
| **A. `cx_run.sh` CLI**（:443/:452/:461） | per-family `timeout` 包 CLI | 訊號進 CLI；`cli_rc=124`；可能留 sandbox 孤兒 → process group |
| **B. `committee_run.sh:280`** | `wait` + 硬上限 + 產出輪詢 | 外層安全閥；須 `kill` 掛死 pid |

**建議**：**A 為主 + B 為保險**（B 上限略大於 A）。

### `completeness_check --single` 充分性

**不充分**（實跑）：

```bash
bash /private/tmp/govb0-recon-composer/completeness_probe.sh
# trunc_test / trunc_bad(8行) / trunc_mid(無 Verdict) 皆 rc=0 PASS
```

`:1459-1472` 只檢 ID schema／body 四欄／digest，**不檢**寫作是否結束、`STATUS: DONE`、Verdict 語意。

**補救判準（建議 SPEC）**：single rc=0 **且** 產出 mtime 穩定 ≥N 秒 **且** 契約結尾（`STATUS: DONE` 或 brief 規定 Verdict）**且**（可選）runlog 有 CLI 正常結束痕跡。

### 逾時值（runlog 樣本）

**VERIFY**（`probe_timing.sh` + `probe_q3q4.sh`；output mtime → runlog close 延遲）：

| 家族 | n | p50 | p90 | max | ≥600s |
|---|---:|---:|---:|---:|---:|
| grok | 76 | 24s | 40s | 70s | 0 |
| composer | 70 | 17s | 35s | **8466s** | 1（B-14 事故） |
| codex | 35 | 36s | 200s | 68273s* | 2 |

\*68273s 為 `20260802-t2-verdict-review-codex` 異常 outlier（非典型審查輪）。

**建議**（數據導向）：
- 健康審查輪 p90：grok/composer **<1m**、codex **~3m**
- 硬頂 **30–60m/家族**（> codex 健康 p90 200s；遠低於 B-14 掛死 8466s）
- composer 逾時觸發應優先「**產出已完整 + 進程仍活**」

### `result_state` 三值（`cx_run.sh:258-288`）

| 值 | 條件 |
|---|---|
| `success` | `cli_rc==0` ∧ 產出非空 ∧ `fmt_rc==0` |
| `format-failed` | `cli_rc==0` ∧ 產出非空 ∧ `fmt_rc!=0` |
| `failed` | 其餘 |

**逾時寫入**：產出通過「充分完整」→ `success`/`format-failed`；不完整或空 → **`failed`**。

---

## Q4（B-24）驗收欄盤點與強制機制

### templates/（全檔掃描）

| 檔 | rc/腳本取向 | 狀態斷言取向 |
|---|---|---|
| `SPEC_TEMPLATE.md:26-33` | `ASSERT … THEN rc=` 固定文法 | `:51` FACT-RECEIPT 要求 stdout 摘要 |
| `COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md:12,27-28,39` | `completeness_check` **rc=0** 多處 | 無 `git status`/差集類 |
| `SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:25,30` | 不可測驗收檢查 | `VERIFY:` 命令+stdout |
| `TODO_GENERATION_PROMPT.md:54` | 可證偽驗證 | 無 B-24 範型 |

**缺口**：templates **無**「`restore_*.sh` 後 `git status --short tests/golden/` 為空」類 **B-24 必填錨點**。

### docs/*SPEC*/*TODO*（啟發式掃描）

**VERIFY**（`probe_q3q4.sh` Q4 段；驗收語境 + rc=0/exit 0）

| 桶 | 條數 |
|---|---:|
| 驗收語境含 rc=0/exit 0 | 300 |
| 僅 rc/腳本（無狀態關鍵字） | 267 |
| rc + 狀態斷言同在 | 33 |
| 僅狀態斷言 | 0 |

### 可機檢形態？

- **窄域 tripwire**：驗收行含 `restore_`／`agent_postflight` **且**同條或後 3 行無 `git status|差集|為空` → FAIL
- **誤報率預估**：全域掃 **中高（30–50%+）**；窄域 **低**

### 「不建檢查器」能否成立？

**否**。使用者定死：「工具必須自帶強制機制」。backlog `## B-24`「不另建檢查器」＝ prose，**必退化**。

**最低可接受**：窄域機檢 或 `template_check` 新增 `STATE-ASSERT:` token 或 `GOV-VERIFY-RECEIPT-RUNNER`。

---

## Q5 合成一批：順序與耦合

| 題 | 結論 |
|---|---|
| B-24→B-15→B-14？ | **合理**。主改檔：`templates/docs`／`gate_check.sh`／`cx_run.sh+committee_run.sh`——**不相交** |
| 必須拆開？ | 無強制；B-15 行為差集須**手動前後對照**（B-29 未落地） |
| 必須調換？ | 無技術依賴 |
| 衝突點 | 可能同碰 `tests/governance/`——TODO 劃模組 |

---

## Q6 可否進 SPEC？

**可以起草 SPEC**，須寫死：
1. 重寫 B-15 根因（命令位 + quote 內 `|`／`;`；非「含家族名」）
2. FP2/FP3 標 **未重現**
3. 修法默認 **④**；② 單獨 = 不可用
4. B-14：30–60m timeout + 完整判準 **> single rc=0**
5. B-24：須機械強制；禁「只改散文」當 Done

---

## 被當成事實的未驗證假設（§0）

| 假設 | verdict |
|---|---|
| 三 FP 全因引號不感知 | **證偽**（FP1=`|` 分隔符；FP2/FP3 無命中） |
| option② 更乾淨 | **證偽**（TP 漏網 7/8） |
| B-24 不建檢查器即可 | **與使用者定死衝突** |
| brief fact-verified 項 | **複核通過** |

---

## COMPOSER-R1-P0-01

**斷言**: backlog 所稱 FP2（`for f in codex…`）與 FP3（`completeness_check --lock`）在現版 `gate_check.sh:86` **無法重現**；SPEC 不得將兩者寫成已證根因。

**碼證**: `eval_bash.sh` FP2/FP3 MATCH=NO；`gate_live.sh` `fp2_rc=0`、`fp3_rc=0`。對照 FP1 `fp1_rc=2`。

**來源摘要**: scripts/gate_check.sh#871258c9ea2e

BLOCKING（對錯誤 SPEC 前提）信心度=High。

---

## COMPOSER-R1-P0-02

**斷言**: B-15 修法選項②（只認 `cx_run`／`committee_run`）對語料 TP **漏網 7/8**，**fail-open 不可用**。

**碼證**: `eval_bash.sh` 方案② `tp_miss=7`；手搓 `codex exec` 在方案②放行。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

BLOCKING 信心度=High。

---

## COMPOSER-R1-P0-03

**斷言**: 現版 gate 對 **絕對路徑** `$CODEX`／`$GROK`（`cx_run.sh:291-292,443,452` 真實形態）**不擋**，是既有 fail-open。

**碼證**: `gate_live.sh` `abs_codex_rc=0`；方案④ `tp_block=8 tp_miss=0` 可補。

**來源摘要**: scripts/cx_run.sh#39cfdddec350

BLOCKING 信心度=High。

---

## COMPOSER-R1-P1-01

**斷言**: `completeness_check --single` rc=0 **不能**作為 B-14「寫完即成功」的充分條件；缺 Verdict 的格式完整 finding 仍 PASS。

**碼證**: `completeness_probe.sh`：`trunc_bad.md`／`trunc_mid.md` 皆 `rc=0`。

**來源摘要**: scripts/completeness_check.sh#12e981972d78

MAJOR 信心度=High。

---

## COMPOSER-R1-P1-02

**斷言**: B-24「不建檢查器、只改驗收散文」無法滿足使用者定死「工具自帶強制」；docs 啟發式掃描 **267/300** 驗收 rc 行無狀態斷言。

**碼證**: `probe_q3q4.sh` Q4 段；`SPEC_TEMPLATE.md` 有 ASSERT 文法但無 `git status` 範型。

**來源摘要**: handoffs/20260801-GOV-AMEND-BACKLOG.md#13cc634125da

MAJOR 信心度=High。

---

## COMPOSER-R1-P2-01

**斷言**: 批次順序 B-24→B-15→B-14 **可維持**；三票主改檔不相交。

**碼證**: brief 表檔案落點比對；無同 hunk 依賴。

**來源摘要**: handoffs/20260804-GOVB0-RECON-BRIEF.md#dc45109da345

MINOR 信心度=High。

---

## RECONCILE-STAMP

```
task: GOVB0-RECON-R1
family: composer
verdict: APPROVED
body_sha256: (見主委收集時計算)
notes: FP2/FP3 未重現；修法④；B-24 需機械強制；B-14 single 不充分
```

---

STATUS: DONE
