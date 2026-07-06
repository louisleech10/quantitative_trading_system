# 制度層總審查 Phase B(治理腳本補強)— SPEC

> 來源 PLAN/診斷：`handoffs/20260705-INSTREV-RECONCILE.md`(雙戳記 APPROVED,U-9/U-12/U-14/U-15 收斂)+ `HANDOFF.md` 下一步 §Phase B　|　日期：2026-07-05　|　對應 TODO：`docs/INSTREV_PHASEB_TODO.md`

## §RISK 風險分級(gate 讀此決定要求強度)

- **大小**：中(接 CLAUDE.md 任務分派決策表)。腳本層治理工具四支獨立補強,單一概念模組(governance tooling),動既有 caller(hooks/gate 流程),可本地 `pytest tests/governance/` 驗,git 可 revert;不看檔案數。
- **命中高風險原則**：(b) 跨模組共用路徑——`gate_check.sh`/`gate.sh`/`verification_claim_check.sh`/`check_agent_contract_sync.sh` 是所有派工與 commit 的 fail-closed 治理閘,改壞會靜默放行壞派工或鎖死 session。**不命中** (a)數值/資料品質(零 kline/feature/回測)、(c)本批四 Task 各自獨立 commit 易 revert、(d)ML/回測正確性(零 momentum/api 程式)。
- **RISK-HIT 宣告**(機檢依據,缺行 FAIL)：
- RISK-HIT: b
- 命中 (b) 非 (a)/(d) → §G Golden 於 §N 標 N/A;adversarial review 仍必跑(中任務完整管線不得跳步,D-1;至少一家不同模型)。

## §A 假設與待使用者確認(事故:拿推論代替問人)

> 本批純腳本工具改動;下列事實皆 code 可讀,已 Claude 實跑 receipt。設計決策非推論,來自 reconcile 委員會 3/3(或 2/3 無反對)收斂,非 Claude 臆想。

- **FACT-RECEIPT 格式**(資料結構/型別/單位斷言必填)：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>(<who> 實跑 <date>)`
- **已驗證事實**(附 receipt;皆 Claude 實跑 2026-07-05)：
  - FACT-RECEIPT: `grep -c "現行分工" docs/MULTI_AGENT_ORCHESTRATION.md` → 印出 `8`(裸字串 8 命中);`grep -cE "^\*\*現行分工|^- \*\*現行分工|現行分工\(" docs/MULTI_AGENT_ORCHESTRATION.md` → 印出 `1`(權威錨點行僅 L37)。**U-9 反向檢查須用錨點式 grep,裸字串會誤判**(Claude 實跑 2026-07-05)。
  - FACT-RECEIPT: `grep -rc "現行分工" CLAUDE.md AGENTS.md .cursorrules` → 印出 CLAUDE.md:1(pointer 句)/AGENTS.md:0/.cursorrules:0;三檔皆無寫死執行端分工(Claude 實跑 2026-07-05)。
  - FACT-RECEIPT: `cat scripts/check_agent_contract_sync.sh` → CONTRACT_TOKENS 6 個(`STATUS: BLOCKED`/`handoffs/`/`data_cache`/`SMALL_INLINE`/`ASSUMPTIONS_VERIFIED`/`反提示注入`)、GLOBAL_TOKENS 3 個(`preflight`/`斷路器`/`委員會`);**尚無** A-12 新 token 與兩層結構(Claude 實跑 2026-07-05)。
  - FACT-RECEIPT: `cat scripts/gate_check.sh` → DENY 路徑(exit 2)只寫 stderr,**不寫 audit.log**;GATE_DIR 硬編 `.claude/gate`,無 `GATE_DIR_OVERRIDE`(Claude 實跑 2026-07-05)。
  - FACT-RECEIPT: `cat scripts/git_hooks/pre-commit` → 只 `exec verification_claim_check.py --staged`,**無尾隨空白 auto-fix**;`ls scripts/ | grep dispatch` → 印出空(**無 dispatch wrapper**)(Claude 實跑 2026-07-05)。
  - FACT-RECEIPT: `ls tests/governance/` → 印出 9 檔 `test_verify_gate*.py`(既有治理測試基線,本批須不破且加新測)(Claude 實跑 2026-07-05)。
- **待使用者確認**(未確認前不得實作)：待確認：無(D-1~D-6 已全數裁決;U-9/12/14/15 設計已 reconcile 收斂,見 §C 引用)。
- **已確認結果**：2026-07-05 使用者裁決(出處:memory `project_instrev_rulings` + `handoffs/20260705-INSTREV-RECONCILE.md`)：U-9 sync 假綠→兩層重構(3/3)、U-12 audit DENY 不落地→機械化 append(2/3 無反對)、U-14 claim-check 誤攔→尾隨空白 auto-fix+可貼 diff 且語義不弱化、U-15 provenance 學習曲線→缺參印用法模板+dispatch wrapper 自帶 --task-id/--output(3/3)。附帶原則=品質優先但抓 token 冗餘平衡、機械化勝 prose。

## §C 約束(不重抄,引用 + 只列本任務相關)

- 本任務**純治理腳本工具**,不碰 `momentum/`/`api/`/`frontend/`;解耦 7 條與資料紅線不受影響。
- 共用路徑注意:本批四支腳本為 fail-closed 治理閘,**核心不變式不可弱化**——
  - `gate_check.sh`:parse 失敗 fail-open(0) 避免鎖死 session、gated 動作無 fresh token → exit 2 擋下;U-12 只**追加** DENY 留痕,不得改放行/擋下判定。
  - `gate.sh`:必填缺項拒發 token(exit 1)、高風險 adversarial/reconcile 戳記真實檢查;U-15 只**改錯誤訊息文本+加 wrapper**,不得放寬必填。
  - `verification_claim_check.py`:router 非 judge、claim 極性/backing 判定;U-14 只**加 auto-fix 前處理+豐富輸出文本**,claim 語義判定一字不弱化(既有 `tests/governance/` 斷言不得放寬)。
  - `check_agent_contract_sync.sh`:presence checklist;U-9 兩層重構後既有 9 個 token 仍須全驗,新增 token 不得漏。
- 既有 caller:`scripts/git_hooks/{pre-commit,commit-msg}`(呼叫 checker)、PreToolUse hook(呼叫 gate_check.sh)、`gate.sh`(dispatch/artifact 前置)、CI/開發者手跑 sync check。改動須向後相容此四類 caller 的既有介面。

## §P Phase 與依賴(事故:宣稱無依賴卻有 forward dependency)

> 自檢:四 Task 輸入皆為既有檔案,互相獨立無 forward dependency;可各自獨立 commit。

### Phase B1 — U-9 sync check 兩層重構(依賴:無)
**Task B1.1 — check_agent_contract_sync.sh 兩層 token + 選層單一來源反向檢查**
- 目標:消滅「合約補了新制度但 sync 仍綠」假綠(Phase A 殘量);把選層單一來源變機檢。　檔案:`scripts/check_agent_contract_sync.sh`。既有 caller:git hooks 無、CI/手跑;無腳本 grep 其 stdout 格式。
- 改法:①把 token 明分兩層——`CONTRACT_REQUIRED`(AGENTS.md+.cursorrules **兩份皆須含**):既有 6 個 CONTRACT_TOKENS + A-12 新增 `register-output`、`RECONCILE-STAMP`、`VERIFY`、兩輪斷路器字樣(`≤ 2 輪` 或 `兩輪`);`PLANNER_REQUIRED`(CLAUDE.md+ORCH **至少一處須含**):既有 GLOBAL_TOKENS `preflight`/`斷路器`/`委員會`。②新增**選層單一來源反向檢查**:權威錨點行以 `grep -cE "^\*\*現行分工|^- \*\*現行分工|現行分工[（(]"` 掃 ORCH == 1(全半形括號皆涵蓋,ADV-CODEX-7;多於 1 或落它檔=FAIL);且 CLAUDE.md/AGENTS.md/.cursorrules 不得寫死執行端(`grep -nE "Codex.*實作|Composer.*實作|GPT-5.5.*實作"` 該三檔 == 0)。③保留 exit 0/1 語義與「✅ 四源關鍵不變式一致」字樣(下游/測試依賴)。
- **驗證(可證偽)**：改後 `bash scripts/check_agent_contract_sync.sh` exit 0 且 stdout 含 `✅`;新增 `pytest tests/governance/test_sync_check.py`(新檔)涵蓋:(i)刪掉 AGENTS.md 的 `RECONCILE-STAMP` → 腳本 exit 1 且訊息含該 token;(ii)在 CLAUDE.md 植入 `Composer 實作` → 反向檢查 exit 1;(iii)在 ORCH 複製第二條錨點行 → 反向檢查 exit 1;(iv)未動時 exit 0。以 tmp 副本或 `GIT` 工作區隔離,不污染真檔。
- **邊界(≥2 具體場景)**：①token 存在但在錯層(如 `VERIFY` 只在 CLAUDE.md 不在合約)→ CONTRACT_REQUIRED 應 FAIL(兩份合約皆須含);②錨點行括號變體 → grep pattern 用 `現行分工[（(]`(**全半形括號皆涵蓋**,ADV-CODEX-7;現檔 L37 為半形 `(`,未來改全形不假紅),並加 fixture 測試植入全形錨點行仍計數==1;③四檔任一不存在 → 明確報錯非靜默 pass。
- 不可做:不改 exit code 語義;不把既有 9 個 token 移除或改字;不為過機檢在合約塞無語義 token。

### Phase B2 — U-12 gate DENY 落 audit(依賴:無)
**Task B2.1 — gate_check.sh DENY 事件 append audit.log**
- 目標:fail-closed 擋下時留痕供稽核(現只寫 stderr,擋了誰、為何無記錄)。　檔案:`scripts/gate_check.sh`。既有 caller:PreToolUse hook(stdin JSON)。
- 改法:在**兩條 DENY 路徑**(token 不存在、token 過期 TTL)的 exit 2 前 append JSON 事件到 `${GATE_DIR}/audit.log`,欄位 `{event:"gate_deny", ts:<UTC ISO8601>, tool:<tool_name>, kind:<dispatch|artifact>, reason:"no_fresh_token"|"token_expired"}`(過期路徑 reason 標 `token_expired`,ADV-CODEX-4);支援 `GATE_DIR_OVERRIDE`(與 gate.sh 一致,測試隔離用),預設 `.claude/gate`;**append 護欄(ADV-CODEX-5)**:helper `mkdir -p "${GATE_DIR}" 2>/dev/null || true` + append redirection 整體 `>> … 2>/dev/null || true`,任何寫入失敗都吞掉,保證仍走既有 exit 2(明文包 `|| true` 防 subshell/未來 set -e 提前 exit)。不記錄 fail-open(0)/放行路徑(只記真 DENY)。
- **驗證(可證偽)**：新增 `pytest tests/governance/test_gate_deny_audit.py`(新檔):①`GATE_DIR_OVERRIDE=<tmp>` 餵無 token 的 `{"tool_name":"Task"}` stdin → exit 2 且 `<tmp>/audit.log` 尾行 `grep -q '"event": "gate_deny"'` 且含 `"tool": "Task"`、`"reason": "no_fresh_token"`;②**過期 token(ADV-CODEX-4)**:預建 `<tmp>/dispatch.token` 用 `touch -t` 設 mtime 超過 TTL(>900s)→ 餵 Task → exit 2 且尾行 `"reason": "token_expired"`;③放行案例(fresh token 或非 gated)→ `grep -c gate_deny` 不變;④**不可寫 GATE_DIR(ADV-CODEX-5)**:`GATE_DIR_OVERRIDE` 指非法/唯讀路徑 → 仍 exit 2(不崩、不變 exit code)。
- **邊界(≥2 具體場景)**：①`GATE_DIR` 目錄不存在 → helper `mkdir -p` 後仍 exit 2;②audit.log 不可寫(權限/非法路徑)→ `|| true` 靜默略過 append,exit 2 不變;③無 jq 的 fail-open(0) 路徑 → 不記錄(非 DENY)。
- 不可做:不改任何放行/擋下判定邏輯;不因 append 失敗而 fail-open 或改變 exit code;不記錄放行事件。

### Phase B3 — U-14 claim-check 摩擦降低(依賴:無)
**Task B3.1 — pre-commit 尾隨空白 auto-fix + checker 缺 backing 可貼 diff**
- 目標:降低誤攔學習曲線,但 claim 語義判定不弱化。　檔案:`scripts/git_hooks/pre-commit`(auto-fix 前處理)、`scripts/verification_claim_check.py`(violation 輸出豐富化)。既有 caller:git commit。
- 改法:①`pre-commit` 在跑 checker **前**,對 staged 的 `.md`(HANDOFF/handoffs/docs 掃描範圍檔)做尾隨空白移除,**必須 index-only(ADV-CODEX-1 BLOCKING)**——取 staged blob(`git cat-file blob :<path>` 或 `git show :<path>`)→ strip 尾隨空白 → `git hash-object -w --stdin` 寫回 object → `git update-index --cacheinfo 100644 <newsha> <path>`;**絕不 `sed -i` 工作樹再 `git add`**(那會把未 staged 的工作樹改動一併納入 commit,污染並破壞既有 partial-stage 防線 `test_git_hook_rejects_partial_stage_fake_claim`)。**排除規則(ADV-CODEX-2 MAJOR)**:fenced code block(``` 圍籬內)整段不動;行尾**剛好兩個空白**(Markdown hard line break)保留;表格列(`|` 起始)不動;僅 strip 一般 prose 行的無語義尾隨空白。②`verification_claim_check.py`:當 violation 訊息為 `operational claim 缺少 VERIFY/REF/SIGNOFF backing` 時,在**原 `file:line: message` 行之後追加**一段可貼上修法提示(建議加 `VERIFY:<receipt-id>` 或 `VERIFY-EXEMPT:<類別>:<id>` 範例);提示走 stderr,**不改 exit code、不改 violation 判定/數量、不改原訊息行順序與格式**(ADV-CODEX-8)。
- **驗證(可證偽)**：①`tests/governance/test_precommit_autofix.py`(新檔):建 staged md 含行尾空白 → 跑 pre-commit 前處理後 `git show :<file>` 無尾隨空白且除尾隨空白外位元組不變;②**partial-stage 回歸(ADV-CODEX-1)**:staged 版含假 claim + 尾隨空白、工作樹再改成別的內容 → 前處理後 commit 的 index blob **只反映 staged 版(去尾空白)**,工作樹改動未被納入,且既有 `test_git_hook_rejects_partial_stage_fake_claim` 仍擋假 claim;③**語義保留(ADV-CODEX-2)**:staged md 含 fenced code 內尾隨空白 + 一行剛好兩空白 hard-break → 前處理後**兩者皆保留**;④既有 `pytest tests/governance/test_verify_gate*.py` **全數仍綠**且 `git diff` 這些檔斷言=0 改動;⑤**提示測試(ADV-CODEX-8)**:缺 backing operational claim → checker exit 1(不變)、原 `file:line: operational claim 缺少…` 行仍存在、violation 數量不變、stderr `grep -q "VERIFY-EXEMPT"` 命中追加提示。
- **邊界(≥2 具體場景)**：①尾隨空白在 fenced code / 兩空白 hard-break / 表格列 → **保留不動**(ADV-CODEX-2);②檔案非 UTF-8/blob 讀取失敗 → auto-fix 略過該檔不崩,checker 照原邏輯;③無 staged md → pre-commit 前處理 no-op。
- 不可做:不弱化任何 claim 極性/backing 判定;不放寬既有 governance 測試斷言;auto-fix 只 index-only strip 一般 prose 行尾隨空白,不碰工作樹、不 reformat 內容、不動 fenced/hard-break/表格。

### Phase B4 — U-15 provenance 學習曲線(依賴:無)
**Task B4.1 — gate.sh 缺參印用法模板 + dispatch wrapper 自帶 --task-id/--output**
- 目標:降低 provenance 上手門檻(缺參只印零散 miss 行、手打 task-id/output 易漏)。　檔案:`scripts/gate.sh`(錯誤訊息)、新建 `scripts/dispatch.sh`(薄 wrapper)。既有 caller:Claude 手跑 gate.sh。
- 改法:①`gate.sh` 缺必填拒發 token 時(現印 `GATE 拒發 token — 缺以下必填`),在 miss 清單後**追加完整用法模板**(即檔頭註解的 dispatch/artifact/register-output 三種完整範例),讓使用者一次看到正確調用;kind 錯誤時亦印模板。②新建 `scripts/dispatch.sh`:薄 wrapper,未給 `--task-id` 時自動生成 `<YYYYMMDD>-<slug>`(slug 由 --intent 正規化)、未給 `--output` 時預設 `handoffs/<task-id>-RESULT.md`,填好後 `exec bash scripts/gate.sh dispatch "$@"` **原樣透傳所有既有參數**(ADV-CODEX-6;wrapper 只補 task-id/output 兩預設,不解析/不過濾/不吞其他參數——未知參數與 `--spec/--todo/--manifest/--reconcile` 皆透傳,gate.sh 唯一裁決)。**碰撞 fail-closed(ADV-CODEX-3 BLOCKING)**:自動生成 output 前,若 `handoffs/<task-id>-RESULT.md` 已存在或該 task-id 已在 `.claude/gate/audit.log` 的 committee_dispatch → wrapper `exit 1` 報「已存在,請顯式給唯一 --task-id」,不覆寫。
- **驗證(可證偽)**：①`bash scripts/gate.sh dispatch`(缺全部必填)→ exit 1 且 stdout `grep -q "scripts/gate.sh dispatch --intent"`(用法模板出現);②`bash scripts/gate.sh badkind` → exit 1 且印模板;③`tests/governance/test_dispatch_wrapper.py`(新檔):`dispatch.sh --intent "x" --risk low ...`(不給 task-id/output)→ 轉呼 gate.sh 帶自動 task-id(`grep -qE '[0-9]{8}-'`)與 `handoffs/*-RESULT.md`;給定 --task-id 時不覆蓋;④**碰撞(ADV-CODEX-3)**:預建同名 `handoffs/<task-id>-RESULT.md` 再跑同 intent → wrapper `exit 1` 不覆寫;⑤**透傳/唯一裁決者(ADV-CODEX-6)**:`dispatch.sh --intent x --risk low --bogus y` → gate.sh 收到 `--bogus` 回 `ERROR: 未預期參數`;高風險帶 `--spec` 缺其他必填時仍由 gate.sh 報缺(未被 wrapper 繞過)。
- **邊界(≥2 具體場景)**：①--intent 含空白/特殊字元 → slug 正規化(非字母數字轉 `-`、去頭尾 `-`、截長度,不產生 `..`/絕對路徑等非法路徑);②同日多次同 intent → 碰撞偵測 exit 1(ADV-CODEX-3),要求顯式唯一 task-id;③wrapper 收到未知參數 → 原樣透傳給 gate.sh 由其報錯(不自行攔,ADV-CODEX-6)。
- 不可做:不在 wrapper 內重實作/繞過 gate.sh 必填檢查(單一裁決者=gate.sh);不改 gate.sh 的 exit code 語義;不自動生成會覆蓋既有檔或既有 task-id 的 output 路徑。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT: b(不含 a/d)且無「聲稱驗數值正確性」的測試 → mutation N/A(§N 登記)。本批驗收全走可證偽 `pytest tests/governance/` + `grep`/`exit-code`。惟 U-14「語義不弱化」以**既有 governance 測試全綠 + diff 斷言未放寬**承擔(等同回歸護網)。
- 測試層級:①單元=各 Task 新 `tests/governance/test_*.py`(可獨立 `pytest` 跑,不需 run_api.py);②整合=四支腳本改後互不干擾,`bash scripts/check_agent_contract_sync.sh` exit 0、既有 `pytest tests/governance/` 全綠;③無 Golden 對照(純工具,無數值 baseline)。
- **防假綠**:U-14 尤須 `git diff` 既有 `tests/governance/test_verify_gate*.py` 斷言,不得放寬/刪除換綠;新斷言對應新行為(auto-fix 位元組守恆、提示文本出現、DENY 留痕出現)。改壞須 FAIL——每個新測附一個「移除本次改動則該測 FAIL」的反例設計。
- **邊界目錄**(本任務適用者)：非數值故空DF/全NaN/Inf/std=0 不適用;適用=①gate DENY 時 audit 目錄不存在/不可寫、②pre-commit 無 staged md/唯讀檔、③wrapper intent 特殊字元、④sync check 四檔任一缺、⑤token 在錯層。各對應上列 Task 邊界欄。

## §R 回退

- 四 Task **各自獨立 commit**,可單獨 `git revert`;純腳本無 feature flag 需求(工具改動,壞了 revert 即回原行為)。
- 新建 `scripts/dispatch.sh` 為純新增(revert=刪檔,gate.sh 不依賴它);`gate_check.sh` audit append 為純追加(revert 回不寫 stderr-only)。
- 任一 Task 的 governance 測試 FAIL → 該 Task 不 merge;既有 `pytest tests/governance/` 若因本批轉紅 → 視為語義弱化,BLOCKED 回退。

## §N N/A 登記(被省略的必填段,逐一標理由,不可直接刪)

- §G Golden/Baseline：**N/A** — RISK-HIT: b,不含 (a)/(d);零數值/特徵/ML/回測路徑改動,無 baseline 可凍結。行為正確性由 §V 的 `pytest tests/governance/` + 可證偽 grep/exit-code + 既有測試回歸(U-14 語義守恆)承擔。
- §V mutation：**N/A** — 無聲稱驗數值正確性的測試;腳本「改壞會 FAIL」由各 Task 新測的反例設計 + 既有 governance 測試回歸承擔(見 §V 防假綠)。
- feature/kline 三方簽核：**N/A** — 不涉 feature/kline 生成/計算/merge/split。
