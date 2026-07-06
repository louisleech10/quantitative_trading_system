# 制度層總審查 Phase B TODO(版本 V1/狀態 DRAFT/基於 docs/INSTREV_PHASEB_SPEC.md/2026-07-05)

> 冷啟動說明:本 TODO 自足,執行端不需回讀 SPEC 即可逐 Task 寫改動;有疑義以 `docs/INSTREV_PHASEB_SPEC.md` 為準,矛盾 → `STATUS: BLOCKED`。

## §0 全域規則與約束(執行端讀完即可遵守)

- **本批=治理腳本工具改動**,允許改的檔案**只有**:`scripts/check_agent_contract_sync.sh`、`scripts/gate_check.sh`、`scripts/git_hooks/pre-commit`、`scripts/verification_claim_check.py`、`scripts/gate.sh`、新建 `scripts/dispatch.sh`、新建/擴充 `tests/governance/test_*.py`。**禁改**:`momentum/`、`api/`、`frontend/`、四治理文件(CLAUDE.md/AGENTS.md/.cursorrules/ORCH)本體、根 `HANDOFF.md`、本 TODO/SPEC。
- **fail-closed 不變式紅線**(一字不可弱化):gate_check.sh 的 parse-fail fail-open(0)/無 token exit 2;gate.sh 的缺必填 exit 1 拒發 token;verification_claim_check.py 的 claim 極性/backing 判定;sync check 既有 9 個 token 全驗。四支腳本改動只**追加能力**,不改既有裁決語義。
- **語義守恆鐵律(U-14)**:改 verification_claim_check.py / pre-commit 後,既有 `pytest tests/governance/test_verify_gate*.py` **須全數仍綠**;`git diff` 這些既有測試檔的斷言=0 放寬/刪除(防假綠)。
- **每 Task 獨立 commit**:B1/B2/B3/B4 各自成 commit,commit 前綴 `chore(gov):` 或 `test(gov):`。
- 語言:繁體中文,禁簡體字。交接寫 `handoffs/20260705-INSTREV-PHASEB-impl.md`(append-only,≤30 行),**不改根 HANDOFF.md**(由 Claude 維護)。收尾報告列出所有產出檔路徑(Claude 會 register-output 入帳)。
- **VERIFY 義務**:收尾任何「已驗/passed」須附實跑命令+輸出摘要(如 `pytest tests/governance/ -q` 的實際輸出),否則標「未驗證」。

## §B 批次執行策略

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | B1.1 | 無 | U-9 sync 兩層重構,單檔+新測 | 中 |
| B2 | B2.1 | 無 | U-12 DENY 留痕,單檔+新測 | 小 |
| B3 | B3.1 | 無 | U-14 auto-fix+輸出豐富化,兩檔+測 | 中 |
| B4 | B4.1 | 無 | U-15 用法模板+新 wrapper,兩檔+測 | 中 |

- 四 Task 互獨立無依賴,可任意順序;建議序列 B1 → B2 → B3 → B4,各自 commit + 各自跑該 Task 驗證命令。
- **§B Gate(整批驗收,全部須過)**:
  ```bash
  bash scripts/check_agent_contract_sync.sh                       # exit 0,stdout 含 ✅
  source venv/bin/activate && pytest tests/governance/ -q         # 全綠(既有 9 檔 + 新增測)
  bash scripts/gate.sh dispatch 2>&1 | grep -q "gate.sh dispatch --intent"   # U-15 用法模板
  git diff --stat                                                 # 僅 §0 允許檔
  ```

## Phase B1 — U-9 sync check 兩層重構

### Task B1.1 — check_agent_contract_sync.sh 兩層 token + 選層單一來源反向檢查
- SPEC ref:Task B1.1　目標:消滅「合約補新制度但 sync 仍綠」假綠 + 選層單一來源機檢化。
- 輸入/輸出:輸入=現 `scripts/check_agent_contract_sync.sh`(44 行,CONTRACT_TOKENS 6 + GLOBAL_TOKENS 3);輸出=兩層結構 + 反向檢查的腳本。
- 實作要點:
  ① **CONTRACT_REQUIRED**(AGENTS.md+.cursorrules 兩份皆須含)=既有 6 個 + 新增 `register-output`、`RECONCILE-STAMP`、`VERIFY`、兩輪斷路器字樣(接受 `≤ 2 輪` 或 `兩輪` 命中其一)。
  ② **PLANNER_REQUIRED**(CLAUDE.md+ORCH 至少一處含)=既有 `preflight`/`斷路器`/`委員會`。
  ③ **選層單一來源反向檢查**:`grep -cE "^\*\*現行分工|^- \*\*現行分工|現行分工[（(]" docs/MULTI_AGENT_ORCHESTRATION.md` 須 == 1(權威錨點行,全半形括號皆涵蓋 ADV-CODEX-7);且 `grep -nE "Codex.*實作|Composer.*實作|GPT-5.5.*實作"` 對 CLAUDE.md/AGENTS.md/.cursorrules == 0(不寫死執行端)。任一違反 → fail=1 且印明確訊息。
  ④ 保留 `exit 0/1` 與 `✅ 四源關鍵不變式一致` 字樣。
- 修改檔案:`scripts/check_agent_contract_sync.sh`;新建 `tests/governance/test_sync_check.py`。
- **驗證(可證偽)**:改後 `bash scripts/check_agent_contract_sync.sh` exit 0 且 stdout `grep -q ✅`;`pytest tests/governance/test_sync_check.py -q` 綠,涵蓋反例(i)刪 AGENTS.md 的 `RECONCILE-STAMP`→exit 1(ii)CLAUDE.md 植入 `Composer 實作`→exit 1(iii)ORCH 複製第二錨點行→exit 1(iv)未動→exit 0。測試以 tmp 副本/隔離工作區,`sed`/`cp` 造反例,不污染真檔。
- **邊界**:①token 在錯層(`VERIFY` 只在 CLAUDE 不在合約)→ CONTRACT_REQUIRED FAIL;②錨點括號 grep 用 `現行分工[（(]` 全半形皆涵蓋(ADV-CODEX-7),fixture 植入全形錨點行仍計數==1;③四檔任一不存在 → 明確報錯非靜默 pass。
- 不可做:不改 exit code 語義;不移除/改字既有 9 token;不塞無語義 token 過機檢。

## Phase B2 — U-12 gate DENY 落 audit

### Task B2.1 — gate_check.sh DENY 事件 append audit.log
- SPEC ref:Task B2.1　目標:fail-closed 擋下留痕供稽核。
- 輸入/輸出:輸入=現 `scripts/gate_check.sh`(exit 2 只寫 stderr);輸出=exit 2 前 append JSON 事件的腳本。
- 實作要點:
  ① 在**兩條 DENY 路徑**(token 不存在、token 過期 TTL)的 `exit 2` 前 append 一行到 `${GATE_DIR}/audit.log`:`{"event":"gate_deny","ts":"<UTC ISO8601>","tool":"<tool_name>","kind":"<dispatch|artifact>","reason":"no_fresh_token"|"token_expired"}`(過期路徑 reason=`token_expired`,ADV-CODEX-4)。
  ② `GATE_DIR="${GATE_DIR_OVERRIDE:-.claude/gate}"`(與 gate.sh 對齊,測試隔離);helper 內 `mkdir -p "${GATE_DIR}" 2>/dev/null || true`。
  ③ **append 護欄(ADV-CODEX-5)**:append redirection 整體 `>> "${GATE_DIR}/audit.log" 2>/dev/null || true`;寫失敗/非法路徑都吞掉,**保證仍走既有 exit 2**(明文 `|| true` 防 subshell/未來 set -e 提前 exit)。只記真 DENY,不記 fail-open(0)/放行。
- 修改檔案:`scripts/gate_check.sh`;新建 `tests/governance/test_gate_deny_audit.py`。
- **驗證(可證偽)**:①`GATE_DIR_OVERRIDE=<tmp>` + `{"tool_name":"Task"}` stdin → exit 2 且 `<tmp>/audit.log` 尾行 `grep -q '"event": "gate_deny"'` 含 `"tool": "Task"`、`"reason": "no_fresh_token"`;②**過期 token(ADV-CODEX-4)**:預建 `<tmp>/dispatch.token` 且 `touch -t` 設 mtime >TTL(900s)→ 餵 Task → exit 2 且尾行 `"reason": "token_expired"`;③fresh-token/非 gated 放行 → `grep -c gate_deny` 不增;④**不可寫 GATE_DIR(ADV-CODEX-5)**:`GATE_DIR_OVERRIDE` 指非法/唯讀路徑 → 仍 exit 2。`pytest tests/governance/test_gate_deny_audit.py -q` 綠。
- **邊界**:①`GATE_DIR` 不存在 → helper mkdir -p 後仍 exit 2;②audit.log 不可寫/非法路徑 → `|| true` 靜默略過,exit 2 不變;③無 jq fail-open(0) → 不記錄。
- 不可做:不改任何放行/擋下判定;不因 append 失敗 fail-open 或改 exit code;不記錄放行事件。

## Phase B3 — U-14 claim-check 摩擦降低(語義不弱化)

### Task B3.1 — pre-commit 尾隨空白 auto-fix + checker 缺 backing 可貼 diff
- SPEC ref:Task B3.1　目標:降誤攔學習曲線,claim 語義判定一字不弱化。
- 輸入/輸出:輸入=現 `pre-commit`(只 exec checker)+ `verification_claim_check.py`(violation 只印 file:line+message+unit_text);輸出=前處理 auto-fix + 豐富化輸出。
- 實作要點:
  ① `scripts/git_hooks/pre-commit`:跑 checker **前**,對 staged 且屬掃描範圍(`HANDOFF.md`/`handoffs/*.md`/`docs/*.md`)的檔移除尾隨空白,**必須 index-only(ADV-CODEX-1 BLOCKING)**:`git show :<path>` 取 staged blob → strip → `git hash-object -w --stdin` → `git update-index --cacheinfo 100644 <newsha> <path>`;**絕不 `sed -i` 工作樹再 `git add`**(會納入未 staged 工作樹改動,污染 commit + 破壞既有 partial-stage 防線)。**排除(ADV-CODEX-2)**:fenced code(``` 圍籬)整段不動、行尾剛好兩空白(hard break)保留、表格列(`|` 起始)不動,只 strip 一般 prose 行;非 UTF-8/blob 讀取失敗略過該檔不崩。
  ② `verification_claim_check.py`:當 violation.message 為 `operational claim 缺少 VERIFY/REF/SIGNOFF backing` 時,在**原 `file:line: message` 行之後追加**可貼上修法提示(`建議加 VERIFY:<receipt-id> 或 VERIFY-EXEMPT:<類別>:<id>`);**不改 exit code、不改 violation 判定/數量、不改原訊息行順序/格式**(ADV-CODEX-8)。
- 修改檔案:`scripts/git_hooks/pre-commit`、`scripts/verification_claim_check.py`;新建 `tests/governance/test_precommit_autofix.py`;既有 `tests/governance/test_verify_gate*.py` 不改。
- **驗證(可證偽)**:①staged md 含行尾空白 → 前處理後 `git show :<file>` 無尾隨空白且除尾隨空白外位元組不變;②**partial-stage 回歸(ADV-CODEX-1)**:staged 版含假 claim+尾隨空白、工作樹再改別的 → 前處理後 index blob 只反映 staged 版(去尾空白)、工作樹改動未納入,既有 `test_git_hook_rejects_partial_stage_fake_claim` 仍擋;③**語義保留(ADV-CODEX-2)**:fenced 內尾隨空白 + 一行兩空白 hard-break → 前處理後皆保留;④既有 `pytest tests/governance/test_verify_gate*.py` **全綠**且 `git diff` 這些檔斷言=0 改動;⑤**提示(ADV-CODEX-8)**:缺 backing operational claim → checker exit 1(不變)、原 `file:line: operational claim 缺少…` 行仍存在、violation 數量不變、stderr `grep -q "VERIFY-EXEMPT"` 命中。`pytest tests/governance/ -q` 全綠。
- **邊界**:①尾隨空白在 fenced code / 兩空白 hard-break / 表格列 → 保留不動(ADV-CODEX-2);②非 UTF-8/blob 讀失敗 → 略過不崩,checker 照原邏輯;③無 staged md → 前處理 no-op。
- 不可做:不弱化任何 claim 極性/backing 判定;不放寬既有 governance 斷言;auto-fix 只 index-only strip 一般 prose 行尾隨空白,不碰工作樹、不 reformat、不動 fenced/hard-break/表格。

## Phase B4 — U-15 provenance 學習曲線

### Task B4.1 — gate.sh 缺參印用法模板 + dispatch wrapper 自帶 --task-id/--output
- SPEC ref:Task B4.1　目標:降 provenance 上手門檻。
- 輸入/輸出:輸入=現 `gate.sh`(缺必填只印零散 miss 行);輸出=缺參印完整用法模板 + 新 `scripts/dispatch.sh`。
- 實作要點:
  ① `gate.sh`:缺必填拒發 token 時(現印 `GATE 拒發 token — 缺以下必填`)在 miss 清單後追加**完整用法模板**(檔頭註解的 dispatch/artifact/register-output 三種完整範例);kind 錯誤(現 `ERROR: kind 必須是...`)亦印模板。以 shell function `_print_usage()` 統一輸出。
  ② 新建 `scripts/dispatch.sh`:薄 wrapper——未給 `--task-id` 時自動生成 `<YYYYMMDD>-<slug>`(slug 由 --intent 正規化:非字母數字→`-`、去頭尾 `-`、截長度),未給 `--output` 時預設 `handoffs/<task-id>-RESULT.md`;填好後 `exec bash scripts/gate.sh dispatch "$@"` **原樣透傳所有既有參數,不解析/不過濾/不吞**(ADV-CODEX-6,未知參數與 `--spec/--todo/--manifest/--reconcile` 皆透傳;gate.sh 唯一裁決)。**碰撞 fail-closed(ADV-CODEX-3 BLOCKING)**:自動生成 output 前,若 `handoffs/<task-id>-RESULT.md` 已存在或該 task-id 已在 `.claude/gate/audit.log` committee_dispatch → wrapper `exit 1` 報「已存在,請顯式給唯一 --task-id」,不覆寫;給定 --task-id 時不覆蓋自動值。
- 修改檔案:`scripts/gate.sh`(錯誤訊息);新建 `scripts/dispatch.sh`;新建 `tests/governance/test_dispatch_wrapper.py`。
- **驗證(可證偽)**:①`bash scripts/gate.sh dispatch`(缺全必填)→ exit 1 且 stdout `grep -q "scripts/gate.sh dispatch --intent"`;②`bash scripts/gate.sh badkind` → exit 1 且印模板;③`pytest tests/governance/test_dispatch_wrapper.py -q`:`dispatch.sh --intent x --risk low ...`(不給 task-id/output)轉呼 gate.sh 帶自動 task-id(`grep -qE '[0-9]{8}-'`)與 `handoffs/*-RESULT.md`;給 --task-id 時不覆蓋;④**碰撞(ADV-CODEX-3)**:預建同名 `handoffs/<task-id>-RESULT.md` 再跑同 intent → wrapper `exit 1` 不覆寫;⑤**透傳/唯一裁決者(ADV-CODEX-6)**:`dispatch.sh --intent x --risk low --bogus y` → gate.sh 回 `ERROR: 未預期參數`;高風險帶 `--spec` 缺其他必填 → 仍由 gate.sh 報缺(未被繞過)。
- **邊界**:①--intent 含空白/特殊字元 → slug 正規化不產 `..`/絕對路徑等非法路徑;②同日多次同 intent → 碰撞偵測 exit 1(ADV-CODEX-3),要求顯式唯一 task-id;③未知參數 → 原樣透傳給 gate.sh 由其報錯(ADV-CODEX-6)。
- 不可做:不在 wrapper 重實作/繞過 gate.sh 必填檢查;不改 gate.sh exit code 語義;不自動生成覆蓋既有檔或既有 task-id 的 output 路徑。

## Phase B 測試與 Gate 總表
- 單元層=各 Task 新 `tests/governance/test_*.py`(可獨立 `pytest` 跑,不需 run_api.py);整合層=§B Gate 全套;無 Golden 層(純工具,零數值 baseline)。
- Phase Gate:每 Task 收尾跑該 Task 驗證命令 + `pytest tests/governance/ -q` 全綠並貼輸出於收尾報告 `TESTS_RUN`;既有測試轉紅=語義弱化=BLOCKED,不得輸出 `STATUS: DONE`。

## Frozen 前 handoff
SPEC=docs/INSTREV_PHASEB_SPEC.md TODO=docs/INSTREV_PHASEB_TODO.md FOCUS=fail-closed不變式不弱化+既有governance測試回歸+四支腳本只追加能力
