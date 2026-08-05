# 治理 backlog 第 0 批（摩擦止血）— SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/govb0-recon-r1/synth.md`（R1 偵察，21 findings，rc=0）　|　日期：2026-08-04　|　對應 TODO：`docs/GOVB0_FRICTION_TODO.md`（待生成）

**版本 R4**（R1 的 D-1～D-13 ＋ R2 的 E-1～E-13 ＋ R3 的 F-1～F-7 全數修訂）。
**收斂趨勢**：R1 19 findings（5 P0）→ R2 17（**7 P0**）→ R3 **11**（3 P0）。
R3 的 11 條**大多是主委自身的漏改與計數漂移**（收斂裁決未同步進 SPEC、契約加項未改計數、引用 ID 錯位），
非新機制缺口 ⇒ **scope accretion 已中止**，`E-SCOPE` 生效（codex 明確標示四項為 `OUT-OF-SCOPE`，未再列 BLOCKING）。
R1 收斂＝`handoffs/reconcile/20260804-govb0-spec-r1/synth.md`（三家戳記 APPROVED，body sha `25e1241f…`）。
R2 收斂＝`handoffs/reconcile/20260805-govb0-spec-r2/synth.md`（17 findings，`completeness --lock` rc=0）。
🔴 **R3 起本 SPEC 帶「明確不受理範圍」**（見 §N 末段），依使用者定死「95% 解法就收、殘留具名記錄」，
以中止 R1→R2 觀察到的 scope-accretion（P0 數未下降）。

**涵蓋票**：`B-15`（gate 判定：2 個誤擋機制 ＋ 2 個 fail-open）／`B-14`（委員不退出）／`B-30`（委員覆蓋自己產出）／`B-32`（stamp prompt 無條件注入）／`B-24`**僅紀律面**。
**唯一票登記處**：`handoffs/20260801-GOV-AMEND-BACKLOG.md`。

🔴 **R2 相對 R1 的範圍變更**：**刪除原 Phase 4**（`B-24` 機械強制面）。
依 `D-6` 裁決 SPLIT：`B-24` 紀律面（驗收欄一律寫狀態斷言，零新增元件）留本批並落實於 §V；
機械強制面（`acceptance_state_check.sh`＋grandfather SoT＋owner／UTC 到期／到期後 fail-closed）移出獨立排期，
理由與 grandfather 三要件已記於 backlog「`票 B-24` 的拆分裁決」節。

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：大。
- **命中高風險原則**：
  - **(b) 跨模組／共用路徑** — `scripts/gate_check.sh` 是**每一次** `Task|Bash|Write` 工具呼叫的 PreToolUse 攔截點；`scripts/cx_run.sh`／`committee_run.sh` 是**所有**委員派工的唯一通道。
  - **(c) 多 phase／難回退** — 4 Phase；Phase 2 改判定放行/擋下，錯誤方向為 fail-open。
- RISK-HIT: b,c
- 未命中 (a)／(d)：不碰數值、特徵、ML、回測路徑 → §G 於 §N 標 N/A。
- **adversarial review 必跑**；**code review 兩個非實作者家族**（角色 SoT `scripts/governance_roles.json`：implementer=grok ⇒ 審查為 codex＋composer）。

## §A 假設與待使用者確認（事故：拿推論代替問人）

- **FACT-RECEIPT 格式**：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`

**已驗證事實（**10 條**，每條附實跑 stdout 摘要；本數字導出命令＝`grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md`）**：
🔴 R4 曾寫 9 而實為 10（`CODEX-R4-P1-03`）——**本 SPEC 內第三次計數漂移**（Task 總數／契約項數／本條），
與 `票 B-17` 同型。R4 已定紀律「凡可由 `grep -c` 導出的數字須同行註明導出命令」，本行即為落實。

- FACT-RECEIPT: `grep -o '"reason":"[^"]*"' .claude/gate/audit.log | sort | uniq -c` → 印出 `493 token_expired` / `106 open_debt`，全檔 599 筆僅此兩值，**無指令欄位**（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `LC_ALL=C grep -ac 'closure review' .claude/gate/ts_stamp.log` → 印出 `0`；`LC_ALL=C grep -ac 'hmsg.txt'` → 印出 `2`（Claude 實跑 2026-08-04）⇒ 被擋指令零紀錄、成功重試有紀錄
- FACT-RECEIPT: `bash .claude/tmp/b15probe.sh` → `pgrep -fl 'codex exec|cursor-agent|grok '` 與 `git commit -m "…; codex closure review…"` 皆 BLOCK；7 條真派工全 BLOCK（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `bash .claude/tmp/b15probe2.sh` → `head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD` BLOCK（命中 `claude-501/x.output; git rev-p`）；拆解對照組兩條皆 ALLOW（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `bash .claude/tmp/b15probe3.sh` → 原型①（單純剝引號）對 `bash -c "codex exec x"` 與 `sh -c 'grok … -p x'` 皆 **ALLOW（fail-open）**；原型②（剝引號＋對 `(bash|sh|zsh) -c` 引數遞迴）9/9 全對（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `grep -c 'token' scripts/cx_run.sh` → 印出 `0`；`grep -c 'token' scripts/_role_gate.sh` → 印出 `0`（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `grep -c 'timeout' scripts/cx_run.sh` → 印出 `0`；`scripts/committee_run.sh:280` 為裸 `wait "${pid}"`（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `sed -n '512p' scripts/cx_run.sh` → 印出含 `RECONCILE-STAMP 的 task: 欄位須逐字使用此值` 的 prompt 賦值，**無 brief-kind 分支**，且該行同時寫著「產出寫到 ${out}」（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `bash .claude/tmp/runlog_dur.sh` → 印出 `TOTAL_RUNLOGS=462`；`codex n=166 max=45.1m`／`composer n=153 max=146.7m`／`grok n=143 max=64.6m`；於 codex 50m／grok 65m／composer 75m 下誤殺各為 `0/166`、`0/143`、`0/152`（Claude 實跑 2026-08-04，獨立於委員報告）

- FACT-RECEIPT: `bash handoffs/govb0_probes/awk_hotpath_bench.sh` → 印出 `A. 現行（僅 grep）: 0 秒 / 200 次 = 0 ms 每次`、`B. 新做法（awk + grep）: 1 秒 / 200 次 = 5 ms 每次`、`差額 … 5 ms 每次工具呼叫`（Claude 實跑 2026-08-05）⇒ 契約 1b 的 `awk` 跨行掃描在 PreToolUse 熱路徑的成本為 **+5 ms／次**（`CODEX-R3-P0-02` 要求的效能 receipt）

**待使用者確認**：**待確認：無**

**已確認結果**：`2026-08-04 使用者指示「有疑慮和問題就跟委員討論，有撞到問題需開票或合併的也就跟委員討論寫到 backlog」——技術取捨交委員裁決，不阻塞等使用者。`

**未決技術項（已由 R1 審查裁定，非使用者事項）**：

- **OPEN-1（已裁定，值為暫定）**：timeout 涵蓋區間＝**CLI process-group launch → return/kill**（兩家一致；明文否決 output-mtime proxy，因其無法覆蓋「產出已寫完但 CLI 不退出」的 `B-14` 掛死型態）。
  暫定值（取兩家保守聯集）：**codex 50m／grok 70m／composer 75m**，`committee_run.sh` 外層安全閥 **90m**。
  🔴 **暫定理由**：現有數據皆為 runlog `birth→mtime` proxy，非 CLI wall-clock。**Task 3.1 上線取得真實 duration 後須重算並在 TODO 定稿**（`CODEX-R1-P0-07` 條件，已接受）。
- **OPEN-2（已裁定，移出本批）**：locale 相依守衛 → 已開 `票 B-33 GOV-LOCALE-GUARD-DRIFT`，嚴重度 MAJOR，排第 1 批之後。**本批不併入**（兩家一致），但須寫入本批 TODO §0 已知債。
- **OPEN-3（已裁定，不除役）**：`B-15` FP-2（`for` 迴圈形態）以「Phase 0 上線後補查」結案。
  **補查條件（`CODEX-R1-P1-08` 要求，本 R2 補上）**：Phase 0 上線後累積 **≥200 筆 `gate_deny` 紀錄**或 **≥30 個日曆日**（先到者為準）後，以 `match_rule` 反查；
  若期間零命中 `for` 迴圈形態 ⇒ 從 `票 B-15` 除役並在票面記「觀測期無再現」；若命中 ⇒ 依實際 `match_rule` 另立修法。**除役須有紀錄支撐，不得因「現在重現不出來」而除役。**

## §C 約束（不重抄，引用 + 只列本任務相關）

- 解耦 7 條不適用（本批不動 `momentum/`／`api/`／`frontend/`）。
- **共用路徑與既有 caller**：
  - `scripts/gate_check.sh` — PreToolUse 第 1 個 hook（`.claude/settings.json:99-135`；`ts_stamp.sh IN` 為第 4 個）。**熱路徑，禁引入 subprocess**。
  - `scripts/cx_run.sh` — 唯一委員 CLI 呼叫點（`:443` codex／`:452` grok／`:461` composer）；`_emit_family_result`（`:250-288`）為 `result_state` 唯一寫入點；`:512` 為 prompt 賦值。
  - `scripts/committee_run.sh:268` 呼叫 `cx_run.sh`、`:280` 裸 `wait`。
  - `scripts/completeness_check.sh:179` 為 finding ID schema 拒收點；`:1459-1472` 為 `--single`。
  - `scripts/governance_families.json`（家族 SoT）／`scripts/governance_roles.json`（角色 SoT）／`scripts/audit_events.json`（事件與枚舉 SoT）。**禁在他處再寫一份。**
- **禁止**：改檢查器或加排除清單使測試變綠；恆真斷言；弱化既有斷言；空 monkeypatch 騙靜態檢查。
- **禁止**：`git checkout`／`git restore` 任何 tracked 檔。探針一律隔離副本。

> **新資料結構檢查點**：本 SPEC 新增枚舉 `gate_deny.match_rule`。
> 依範本規定，其**封閉值集合與事件契約寫入 `scripts/audit_events.json`**（既有 SoT，已有 `registry_version`／`schema_version`／`unknown_event_policy`／`required_fields_per_event`），
> **SPEC 不在散文中列舉任何值**。`result_state` 三值為既有定義，同樣只 pointer。

## §P Phase 與依賴

**依賴圖（`D-13` 要求，全部宣告，含 R1 未宣告者）**：

```
Phase 0 ──────────────► Phase 2        （驗收依賴：無 deny 紀錄則差集不可驗）
Phase 0 ──registry enum─► Phase 2       （match_rule 契約須先存在）
Phase 1 ──prompt 路徑──► Task 3.2       （prompt 仍寫 <out> 則 .part 方案失效）
Task 3.1 ──duration───► Task 3.3        （timeout 值定稿依賴真實 duration）
OPEN-1 裁決 ──────────► Task 3.3 TODO   （值填入 TODO 前須完成 Task 3.1 重算）
immutable corpus ─────► Task 2.5        （語料檔須先進版控並記 sha256）
舊版 gate snapshot ───► Task 2.5        （差集的「舊版」須為固定 sha 的副本，非 HEAD）
```

**無其他 forward dependency。** Phase 3 不影響 Phase 0 的紀錄內容，亦不影響 Phase 2 的判定。

### Phase 0 — 可觀測性前置（依賴：無）

> 目標：讓「被 gate 擋下」留下可機械分析的紀錄。**Phase 2 的驗收完全依賴本 Phase。**

**Task 0.1 — `gate_deny` 記錄被擋指令與命中規則**

- 目標：`gate_deny` 事件新增指令與命中規則兩欄，使誤擋率可事後量測。
  檔案：`scripts/gate_check.sh` 的 `_append_gate_deny_audit()`（`:21-30`）與 `:86` 判定段；枚舉與事件契約寫入 `scripts/audit_events.json`。
  既有 caller：`gate_check.sh:117`、`:128`。
- 改法：
  1. **先判定、後記錄**：命中後才以 `grep -Eo` 取命中片段。**取片段的結果不得回饋進判定**。
  2. `match_rule` 的封閉 enum 與 `gate_deny` 的 `required_fields` 寫入 `scripts/audit_events.json`；`gate_check.sh` 只引用，不自列。未知值依該檔既有 `unknown_event_policy` 處理。
  3. **命令欄截斷規則**：存全文 `sha256` ＋ 前 512 位元組。理由：委員 prompt 可達數十 KB；`sha256` 使同一指令可被歸併計數。
  4. **不變式（`D-3` 收窄 ＋ `E-7`／`E-8` 分離 baseline）**：**判定行為不變** ＝ 對**語料 A**，Phase 0 改前與改後的 `(rc, kind)` 序列**逐項相等**。
     🔴 **audit 內容本來就會增加欄位，不在本不變式範圍內**（R1 原文「行為逐位元組不變」有歧義，已修正）。
     🔴 **兩個 baseline 必須分離**（`CODEX-R2-P0-03`／`CODEX-R2-P1-10`：R2 未區分，同一份 snapshot 使兩個驗收互斥）：
     - **語料 A**（Phase 0 專用，`tests/governance/fixtures/gate_invariance_corpus.txt`）：判定**應完全相同**，比較基準＝Phase 0 改動前後。
     - **語料 B**（Phase 2 專用，`tests/governance/fixtures/gate_decision_corpus.txt`，見 Task 2.5）：判定**應該改變**，比較基準＝Phase 2 動工前的 `gate_check.sh` 固定 sha snapshot。
     - 兩份語料檔與兩份 snapshot **各自獨立、不得共用**；測試須斷言兩份語料檔的 sha256 不同且各自入版控。
  5. **event object contract（`CODEX-R2-P0-03`）**：`scripts/audit_events.json` 須新增
     `gate_deny` 的 `required_fields_per_event` 條目、`match_rule` 的封閉值集合、以及該欄位在
     `event_object_allowed_keys` 中的登記。**SPEC 不列舉值**（範本規定），但 TODO 須逐 key 列出待新增項，
     使實作者不必猜測。驗收＝以 `jq` 從該檔讀出的 key 集合與 `gate_check.sh` 實際寫出的欄位集合**相等**。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/gate_check.sh WHEN input=blocked_cmd THEN rc!=0`
  - `ASSERT bash scripts/gate_check.sh WHEN input=allowed_cmd THEN rc=0`
  - 狀態斷言（**`F-1`：R3 此處與不變式定義互斥，R4 改寫**）：對**語料 A**，Phase 0 改前與改後的
    **decision trace**（只含 `(rc, kind)` 兩欄的逐條紀錄，由測試 harness 另行輸出，**與 audit 事件是兩份不同產物**）
    **逐項相等、diff 為空**。
    🔴 **不得要求「兩份 audit JSON diff 為空」**——本 Task 的全部目的就是替 `gate_deny` **新增欄位**，
    audit 內容必然不同。R3 原句與改法④的不變式定義自相矛盾（`CODEX-R3-P0-01`／`COMPOSER-R3-P0-01`），已刪除。
  - 狀態斷言（audit 面，與上一條**分開驗**）：新 `gate_deny` 事件的欄位集合 == `scripts/audit_events.json`
    所定 `required_fields_per_event` 集合（以該檔為斷言來源，非硬編）。
  - 狀態斷言：新 `gate_deny` 事件經 `jq` 取出後，命令欄非空、`match_rule` 值屬 `scripts/audit_events.json` 所定集合（**以該檔為斷言來源，非硬編**）。
  - mutation：移除欄位寫入 → 對應測試轉紅。
- **邊界（≥2）**：①指令含換行與控制字元 → 欄位須為合法 JSON 字串，不破壞 audit 逐行 JSON 結構 ②`tool_input.command` 缺失 → 欄位寫空字串而非缺欄，且不得例外中止 ③4 MB 巨量 prompt → 截斷後 audit 單行 ≤1 KB。
- **存活至**：永久（`票 B-29` 差集工具的資料來源）。
- **覆蓋風險**：無。
- 不可做：**不得把 `grep -Eo` 放進判定前主路徑**（`D-12`／`COMPOSER-R1-P2-01`：`grep` 失敗或效能變化會改 rc）；不建新 log 檔；不改 hook 順序；不動 `ts_stamp.sh`。

### Phase 1 — `B-32` stamp prompt 條件化（依賴：無）

> 目標：停止讓系統自己誘發委員交件失敗。**Task 3.2 依賴本 Phase 的 prompt 路徑對齊。**

**Task 1.1 — `cx_run.sh` prompt 依 `brief-kind` 分支**

- 目標：只有需要戳記的輪次才在 prompt 中提及 RECONCILE-STAMP。
  檔案：`scripts/cx_run.sh:512`。既有 caller：`_run_cli_and_emit`（同檔 `:513`）。
- 改法：
  1. `brief-kind` 沿用 `brief_conformance_check.sh` 經 `_bc_kv` 回傳的既有解析結果，**禁再寫一份 parser**（出生事故：`committee_run.sh` 第二份 parser 造成孤兒債）。
  2. `brief-kind ∈ {stamp, closure}` → 保留注入句並**補充格式說明**：戳記為單獨一行 `RECONCILE-STAMP: <family> APPROVED <date> sha256:<hash> task:<id>`，**非 `## ` 標題**。格式的單一真相源＝`cx_run.sh:345` 的正則，測試須斷言 prompt 說明與該正則機械一致。
  3. 其餘 `brief-kind` → **完全不提** RECONCILE-STAMP，只注入 task-id。
  4. **unknown `brief-kind` → fail-closed，拒派**（`D-5`／`CODEX-R1-P1-09`：R1 原文「視同不需戳記＋audit 警示」與 fail-closed 互斥，已改為單一行為）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/cx_run.sh WHEN brief_kind=consult THEN rc=0`（且 prompt 不含字串 `RECONCILE-STAMP`）
  - `ASSERT bash scripts/cx_run.sh WHEN brief_kind=stamp THEN rc=0`（且 prompt 含該字串與格式說明）
  - `ASSERT bash scripts/cx_run.sh WHEN brief_kind=unknown THEN rc!=0`
  - 狀態斷言（**`E-2`：R2 此處只有 rc，缺無副作用證明**）：`brief_kind=unknown` 被拒後，
    ①**未發 token**（`.claude/gate/` 內無新 token 檔或 mtime 未更新）②**audit 零新增**（該次呼叫前後 `.claude/gate/audit.log` 行數相等）
    ③**未開債**（`bash scripts/debt_ledger.sh --has-open` 的狀態與呼叫前相同）④**未產生任何 `handoffs/` 檔案**。
  - 狀態斷言：prompt 中的格式說明字串與 `cx_run.sh:345` 正則所接受的樣本**互為可解析**（以一個合法戳記樣本同時通過兩者）。
  - mutation：還原無條件注入 → `brief_kind=consult` 斷言轉紅；移除 unknown 分支 → 第三條與四項無副作用斷言轉紅。
- **邊界（≥2）**：①`brief-kind` 解析失敗／缺欄 → fail-closed，維持現行拒派行為 ②`brief-kind` 為未知值 → fail-closed（同上，**不再有第三種行為**）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 🔴 **誠實邊界（`D-11`／`COMPOSER-R1-P2-02`）**：本 Task 只保證 **harness 端不再誘導**；**無法保證委員不自行寫出 `## RECONCILE-STAMP` 標題**。後者若再發生，屬 `票 B-31`（format-failed 無便宜修正路徑）範疇，不由本 Task 承擔。驗收**不得**以「委員這次沒寫」為斷言（不可重現）。
- 不可做：不改 `completeness_check.sh` 的 ID schema（`票 B-32` 修法③，本批不做）；不改既有戳記格式。

### Phase 2 — `B-15` gate 判定修正（依賴：Phase 0）

> **設計約束（`CLAUDE-R1-P1-03`）**：現行正則 TP 面 7/7 完好，**本 Phase 不得使任何既有 TP 轉為放行**。

**Task 2.0 — 詞法契約（lexical contract）先定義，後實作**

- 目標：`D-1`／`CODEX-R1-P0-02` 指出「前處理語義與命令遞迴語義衝突」，故四項修法**共用一份詞法契約**，不得各自為政。
  檔案：`scripts/gate_check.sh`（契約以註解形式寫在判定段上方，並由測試釘死）。
- 改法：契約須明確定義下列每一項的判定結果，**且每一項都要有對應測試**：
  1. 引號內的 `;` `&` `|` **不作分隔符**；
  1b. 🔴 **剝引號必須「跨行有狀態」**（逐字元追蹤 in-quote 狀態），**不得用 `sed 's/"[^"]*"//g'` 這種行內替換**。
     出生事故（2026-08-05 00:4x，主委實測 `handoffs/govb0_probes/b15probe6.sh`）：
     `git commit -m "…（多行訊息，某行以 codex 開頭）…"` 被誤擋；`sed` 版**仍誤擋**（`s///` 不跨行），
     `awk` 跨行狀態機版 **4/4 全對**。
     ⚠️ **不得改用「正規化為單行」**——真正的多行指令第 2 行開頭可能是真派工（`echo start` 換行 `codex exec …`），
     逐行 `^` 命中在該情境下是**正確行為**，正規化會使其漏網（主委首擬此法，已由實測推翻）。
  2. **「命令位置」的完整定義**（R3 依 `E-3` 擴充；R2 只列 `^ ; & |`，實測不足）＝
     行首／`;`／`&`／`|`／`(`／`` ` ``／`$(`／`&&`／`||`／`eval` 之後／`xargs` 之後；
  3. `(bash|sh|zsh) -c <引號引數>` **與 `eval <引號引數>`** 的引數內容須**遞迴套用同一判定**（不得因剝引號而消失）；
  4. 帶引號的路徑（`"/my dir/codex" exec`）；
  5. 路徑正規化（`./scripts/cx_run.sh`、`scripts//cx_run.sh`、`scripts/../scripts/cx_run.sh`）；
  6. 未閉合引號 → **fail-closed**（視為未剝除）；
  7. **unquoted `-c` 引數**（`bash -c codex`）→ **BLOCK**（語意上即「執行 codex」，與帶引號等價）；
  8. **遞迴深度上限**（`bash -c "bash -c 'codex exec x'"`）→ **上限 3 層；逾限 fail-closed（BLOCK）**（正常派工不會嵌套，逾限即可疑）；
  9. **跳脫引號**（`"a\"b"`、`'a"b'`）→ 跳脫字元**不終止引號 span**；掃描器若無法確定 span 邊界 ⇒ **fail-closed（視為未剝除）**；
  10. **heredoc**（`cat <<EOF; codex exec x`）→ **heredoc 本體視為引號 span**（不作分隔符、不掃描），**heredoc 之外照常判定**；
      R2 原型②在此**誤擋**（`COMPOSER-R2-P1-02`）。
      🔴 **可機械執行的 span 界定規則（R5 補上；R4 只寫「視為引號 span」不可實作 — `COMPOSER-R4-P1-03`）**：
      ①**起點**＝匹配 `<<[-]?[[:space:]]*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1` 之後的**下一個換行**；
      ②**delimiter**＝上式捕捉到的識別字（**去除引號**；`<<'X'`／`<<"X"`／`<<X` 的 delimiter 皆為 `X`）；
      ③**終點**＝**行首**恰為該 delimiter 的那一行（`<<-` 形式允許行首 tab 縮排，其餘形式不允許任何前導空白）；
      ④**多個 heredoc 併存**（`cat <<A <<B`）：**依出現順序依序消耗**，第 n 個 heredoc 的 body 起於第 n−1 個 body 結束之後；
      ⑤**delimiter 未出現到字串結尾** ⇒ **fail-closed**（視為未剝除，同契約第 6 項）。
      🔴 ⑥**delimiter 文法＝允許清單，不是識別字、也不是「排除清單」**
      （R6 修；`CODEX-R5-P0-01` 提出、`CODEX-R6-P0-01` 二次收緊，兩家一致）：
      起點改為 `<<[-]?[[:space:]]*` 後接下列**三者之一**——
      (a) `'([^']*)'`　(b) `"([^"]*)"`　(c) `([A-Za-z0-9_.:+=,%@^~{}\[\]!*?-]+)`（**允許清單**）；
      🔴 **`~{}[]!*?` 八字元為 R7 補入**（`CODEX-R7-P1-01`／`COMPOSER-R7-P2-01`，兩家獨立提出）：
      codex 實跑 `BASH_UNQUOTED[~|{|}|[|]|!|*|?] rc=0` 證實 bash **皆接受**為合法 delimiter。
      未補前這些會落入⑦ ⇒ **誤擋合法 heredoc**，與本批「止血摩擦」目標自相矛盾。
      ⚠️ 這些字元在 delimiter 位置**只做 quote removal、不做展開**（無 glob／brace／tilde expansion），
      故納入允許清單**不會**造成掃描器與 shell 的判定分歧。
      且 (c) **必須完整 token**：其後須緊接 `[[:space:]]`、換行或字串結尾（**禁前綴匹配**）。
      delimiter ＝捕捉群去引號後的字面值。
      ⇒ `EOF-1`／`EOF.1`／`E0F`／`_EOF` 等**皆為合法 shell delimiter，必須正確開 span**。
      🔴 **為何用允許清單而非排除清單**：`票 B-23` 已定「列舉禁止符號永遠列不完 ⇒ 反轉為允許清單」。
      R6 初版寫成排除清單 `([^[:space:]|&;()<>]+)`，**當場被證偽**（見下事故二）。
      🔴 ⑦**`<<` 無法依⑥解析 ⇒ 整個掃描 fail-closed（BLOCK）**，
      **不得略過該 `<<` 繼續掃描**。⑥的允許清單與⑦是**互補且不重疊**的：
      凡不落在 (a)(b)(c) 三形式者一律走⑦，**不得有「⑥接受但⑦說要拒絕」的重疊區**。

      **事故二（`CODEX-R6-P0-01`，實跑證偽 — R6 初版的⑥自身有缺陷）**：
      初版⑥用排除清單 `([^[:space:]|&;()<>]+)`，造成兩個問題：
      **(i) 與⑦矛盾**——`grep -Eq '^([^[:space:]|&;()<>]+)$'` 對 `E'O'F`／`E"O"F`／`$'EOF'` **皆回 yes**，
      即⑥**接受**了⑦明文要求拒絕的混合引號／ANSI-C quote。
      **(ii) 前綴匹配漏掃**——`E\ F` 被解析成 delimiter `E\`（在空白處停），
      與 shell 實際的 `E F` 不符 ⇒ span 界定錯誤；codex 實跑 `bash -c` 輸出 `ESCAPED_ATTACK_EXECUTED`，
      而依初版契約的掃描器回 `ALLOW`。同理 `EOF$(` 被解析成 `EOF$`。
      ⇒ 改為**允許清單＋完整 token 邊界**後，上述五個向量（`E'O'F`／`E"O"F`／`$'EOF'`／`E\ F`／`EOF$(`）
      **全部落入⑦ fail-closed**。

      **⑥⑦ 的出生事故（實跑反例，勿弱化）**：R5 版起點 regex 為
      `<<[-]?[[:space:]]*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1`，**只吃識別字**。
      攻擊鏈：delimiter 用合法的 `EOF-1` ⇒ 不匹配 ⇒ **不開 span** ⇒ 掃描器改在 body 內的
      `<<INNER`（識別字）**開錯位置的 span** ⇒ 一路吞到行首為 `INNER` 的行，
      **把 `EOF-1` 終止行與其後的真實外部派工整段吃掉** ⇒ **fail-open**。
      codex 實跑：`bash -c` 輸出含 `ATTACK_EXECUTED`（`HEREDOC_SHELL_RC=0`），
      而依 R5 契約寫的最小掃描器回 `CONTRACT_SHAPE_SCAN=ALLOW`。
      ⚠️ **只補⑦不補⑥並不足夠**：那會把 `EOF-1` 這類**合法且常見**的用法變成誤擋，
      與本批「止血摩擦」的目標相反。**⑥⑦ 必須同時實作。**

      **驗收語料**（納入語料 B，各 1 條 TP＋1 條 TN）：
      `<<EOF`／`<<'X'`／`<<-EOF`（縮排）／`cat <<A <<B`（雙 heredoc）／未閉合 heredoc／
      🔴 `<<EOF-1`（非識別字 delimiter）／`<<'EOF-1'`（引號包非識別字）／
      **body 內含假 marker 且 delimiter 後接真派工**（即上述攻擊鏈，TP 必須 BLOCK）／
      🔴 **⑦ fail-closed 五向量（事故二，各須 TP）**：`<<E'O'F`／`<<E"O"F`／`<<$'EOF'`／
      `<<E\ F`（含跳脫空白，**禁前綴匹配成 `E\`**）／`<<EOF$(`（**禁前綴匹配成 `EOF$`**）。
      **mutation（可證偽性證明）**：把⑥的允許清單改回排除清單 `([^[:space:]|&;()<>]+)`
      或移除「完整 token 邊界」要求 ⇒ 上述五向量**必須有至少一條轉為 ALLOW**（斷言 FAIL）。
  🔴 **上列 7–10 的判定結果在 R4 定死**（R3 只列項目未定結果，`CODEX-R3-P0-02`）。
  🔴 **契約共 11 項**（`1`／`1b`／`2`–`10`）——本行數字須與本 Task「改法」下的條目數相等；
  R3 曾寫「10 項」而實為 11（`COMPOSER-R3-P2-01`），與 §V 的 Task 數漂移同型（`票 B-17`），
  **本 SPEC 內已第二次**。**code review 須機械核對。**
- **參考實作＝原型③**（`handoffs/govb0_probes/b15probe5.sh`，主委實跑 **26/26 全對**）。
  它已涵蓋第 2、3 項；第 4、5、7、8、9、10 項**尚未在原型中實作**，實作者須補齊並補測試。
  🔴 **禁止照抄原型即宣稱完成**（`COMPOSER-R2-P1-01`：原型與契約有落差）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：契約 **11 項**（`1`／`1b`／`2`–`10`）各至少 1 條 TP 與 1 條 TN，**共 ≥22 條**，全部進入 Task 2.5 的 immutable corpus（語料 B）。
  - 狀態斷言：對 `handoffs/govb0_probes/b15probe5.sh` 的 26 條既有語料，新實作的判定結果與原型③**逐條相同**（差異須具名說明）。
  - mutation：契約每一項各自 revert → 對應語料轉為錯誤方向（**11 項各一個 mutation**）。
- **邊界（≥2）**：見上述契約第 6、8、9、10 項，各自即為邊界情境並已要求測試。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得在四個 Task 中各寫一份剝引號邏輯。

**Task 2.1 — 引號感知 ＋ `-c` 遞迴（洞 A ＋ `D-1` 的 fail-open）**

- 目標：引號**內**的分隔符不生效；但 `(bash|sh|zsh) -c` 的引數仍受檢。
  檔案：`scripts/gate_check.sh:86` 判定段（新增前處理）。
- 改法：依 Task 2.0 契約實作。**純 shell／`sed`／`awk`，禁 subprocess 呼叫 python**（熱路徑）。
  🔴 **R4 放寬至含 `awk`**（`CODEX-R3-P0-02` 要求「明文解除限制並附效能 receipt」）：
  契約 1b 要求**跨行狀態機**，`sed` 的 `s///` 做不到；`awk` 與 `sed`／`grep` 同級（POSIX，單次 fork）。
  **FACT-RECEIPT**（見 §A 第 10 條）：實測每次工具呼叫 **+5 ms**（正常工具呼叫約 80 ms、
  權限分類器 2300–3000 ms）⇒ 約 6% 開銷，**可接受**。**維持禁 python。**
  參考原型＝`handoffs/govb0_probes/b15probe5.sh`（原型③，26/26）＋ `b15probe6.sh`（1b 跨行剝引號，4/4）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`pgrep -fl 'codex exec|cursor-agent|grok '`、`git commit -m "…; codex closure review…"` 由 BLOCK 轉 ALLOW。
  - 狀態斷言（**`E-3`：現行 gate 即已 fail-open，本 Task 一併修**）：
    `eval "codex exec x"`、`out=$(codex exec x)`、`` out=`codex exec x` ``、`(codex exec x)`、`eval 'grok -m grok-4.5 -p x'`
    **五條全部由 ALLOW 轉 BLOCK**。
  - 狀態斷言：`bash -c "codex exec x"`、`sh -c 'grok -m grok-4.5 -p x'`、`bash -c "claude -p x"`、
    `true && codex exec x`、`false || grok -m x -p y`、`echo x | xargs codex exec` **六條皆 BLOCK**。
  - 狀態斷言：`echo start; grok -m grok-4.5 -p "x"`（引號**外**的分號）維持 BLOCK。
  - 狀態斷言（**`F-6`：契約 1b 的具名語料，R3 缺，R4 補**；來源 `handoffs/govb0_probes/b15probe6.sh`）：
    ①`git commit -m "<多行訊息，第 2 行以 codex 開頭>"` → **ALLOW**
    ②`git commit -m "<多行訊息，第 2 行以 grok 開頭>"` → **ALLOW**
    ③`echo start` 換行 `codex exec -s workspace-write "p"`（**真多行指令**）→ **BLOCK**
    ④`set -e` 換行 `grok -m grok-4.5 -p "x"`（**真多行指令**）→ **BLOCK**
    🔴 四條全部納入語料 B。**只實作原型③（不含 1b）者，①②會誤擋 ⇒ 本 Task 不通過**（`COMPOSER-R3-P1-02`）。
  - mutation：移除 `-c`／`eval` 遞迴 → 對應語料轉為 ALLOW；縮回 R2 的命令位置定義（僅 `^ ; & |`）→ 上述五條 `E-3` 語料轉回 ALLOW；
    把跨行剝引號換成 `sed` 行內替換 → 上述①②轉為 BLOCK（**這是 1b 的守護測試**）。
- **邊界（≥2）**：①未閉合引號 → fail-closed ②巢狀／跳脫引號 → 依 Task 2.0 契約 ③`bash -c` 引數不加引號（`bash -c codex`）→ 依契約定義並測試。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得白名單化「唯讀動詞」（R1 偵察已否決：清單列不完，且與 `票 B-23` 方向矛盾）。

**Task 2.2 — `claude` 段收窄（洞 B，含一條 fail-open）**

- 目標：`claude` 不再子字串比對；`-p`／`--print` 須為獨立引數。
  檔案：`scripts/gate_check.sh:86` 第二段 alternation。
- 改法：`claude` 比照家族名限定命令位置並允許路徑前綴；`-p`／`--print` 須有詞界；移除 `[^|]*` 跨字元貪吃。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD`、`cat .claude/tmp/x.txt; git rev-parse HEAD`、`ls /private/tmp/claude-501/; git status --porcelain`、`find .claude/tmp -name "*.md" -print` **四條全由 BLOCK 轉 ALLOW**。
  - 狀態斷言：`claude -p "x"`、`claude --print "x"` 維持 BLOCK。
  - 狀態斷言（**修 fail-open**）：`cat x | claude -p "y"` 由 **ALLOW 轉 BLOCK**。
  - 狀態斷言（🔴 **防 R2 設計造成的回歸**）：`v=$(claude -p "hi")` 與 `/usr/local/bin/claude --print "x"` **兩條須 BLOCK**。
    R2 把 `claude` 收窄到命令位置後，命令替換形態**由 BLOCK 退化為 ALLOW**（現行 gate 靠子字串偶然擋住）——
    此為 `E-3` 實測發現，須由 Task 2.0 契約第 2 項（命令位置含 `$(`）承接。
  - mutation：還原子字串比對 → 前四條轉回 BLOCK、fail-open 條轉回 ALLOW；
    自命令位置定義中移除 `$(` → 回歸守護條轉為 ALLOW。
- **邊界（≥2）**：①`claude` 在檔名中段（`my-claude-notes.md`）→ ALLOW ②絕對路徑（`/usr/local/bin/claude -p x`）→ BLOCK ③`-p` 為他人旗標（`grep -p`）且無 `claude` → ALLOW。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得整段刪除 `claude` 判定（會失去子代理攔截）。

**Task 2.3 — 家族名 basename 化（fail-open ①）**

- 目標：帶路徑前綴的家族 CLI 須被擋。
  檔案：`scripts/gate_check.sh:86` 第一段 alternation。
- 改法：命令位置比對允許可選路徑前綴，含帶引號路徑（依 Task 2.0 契約第 3 項）。家族清單維持既有 SoT 語意（`:79-80` 註解已載明熱路徑寫死＋測試釘死 == SoT）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`/opt/homebrew/bin/codex exec hi`、`/Users/…/.grok/bin/grok -m x -p y`、`venv/bin/codex exec hi`、`./scripts/../codex exec hi`、`"/my dir/codex" exec hi` **五條全由 ALLOW 轉 BLOCK**。
  - 狀態斷言：`cat sp_codex.txt` 維持 ALLOW。
  - mutation：還原無前綴版 → 五條轉回 ALLOW。
- **邊界（≥2）**：①檔名為 `mycodex`（非 basename 相等）→ ALLOW ②`grok` 為目錄名（`/tmp/grok/notes.md`）→ ALLOW ③路徑含空白且未加引號 → 依契約定義。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得把家族清單複製一份到別處。

**Task 2.4 — 官方外層腳本呼叫點（fail-open ②）**

- 目標：直接執行 `cx_run.sh`／`committee_run.sh` 亦須有 gate token。
  檔案：`scripts/gate_check.sh:86-90`。
- 改法：命令位置出現 `cx_run.sh` 或 `committee_run.sh`（含 Task 2.0 契約第 4 項的路徑正規化變形）→ `kind=dispatch`；`scripts/gate.sh` 維持排除（否則無法 bootstrap）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`ROUND_ID=x bash scripts/cx_run.sh composer b.md o.md`、`bash ./scripts/cx_run.sh …`、`bash scripts//cx_run.sh …` 三條由 ALLOW 轉 BLOCK（無 token 時）。
  - 狀態斷言：`bash scripts/committee_run.sh --session s b.md o codex -- --task-id T` 由 ALLOW 轉 BLOCK（無 token 時）。
  - 狀態斷言：`bash scripts/gate.sh dispatch --intent x …` 維持 ALLOW。
  - **回歸護欄（端到端）**：`committee_run.sh` 取得 token 後呼叫 `cx_run.sh` 的既有流程須仍能完成一次真實派工。
  - 狀態斷言（**不得製造新誤擋**）：`sed -n '1,40p' scripts/cx_run.sh`、`grep -n timeout scripts/cx_run.sh`、`wc -l scripts/committee_run.sh` **三條唯讀查看維持 ALLOW**。
  - mutation：移除呼叫點判定 → 前四條轉回 ALLOW。
- **邊界（≥2）**：①相對路徑變形 → BLOCK ②唯讀查看該腳本 → ALLOW ③腳本名出現在字串引數中（`echo "run cx_run.sh later"`）→ ALLOW。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得把 `gate.sh` 納入（會鎖死取 token 的唯一路徑）。

**Task 2.5 — 行為差集報表（`票 B-29` 手動版）＋ immutable corpus**

- 目標：對**固定**語料，列出「本來擋現在放行」「本來放行現在擋」「未變」三堆。
  檔案：新增 `scripts/gate_decision_delta.sh`（一次性可重跑，非 hook）＋語料檔 `tests/governance/fixtures/gate_decision_corpus.txt`（**進版控**）。
- 改法（依 `D-4` 修訂）：
  1. **immutable corpus**：語料檔進版控，其 `sha256` 寫入報表標頭；差集結果綁該 sha。語料變更須另行 commit 並重跑，**不得在同一次驗收中修改語料**。
  2. **舊版判定來源**＝Phase 2 動工前的 `gate_check.sh` 副本，**以固定 sha 存於 `tests/governance/fixtures/`**，非 `HEAD`（`D-13`：舊版 snapshot 為 forward dependency）。
  3. 每條語料標明出處，禁憑空造。
- **驗證（可證偽，`D-4` 改寫後）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：「本來放行現在擋」欄 ⊇ Task 2.2／2.3／2.4 列舉的 fail-open 修復項（**必要子集**）。
  - 狀態斷言：「本來擋現在放行」欄 ⊇ Task 2.1／2.2 列舉的誤擋修復項（**必要子集**）。
  - 狀態斷言：兩欄中**不屬於 SPEC 列舉的項目**（附加項）**逐項人工標註**為「預期」或「非預期」，標註結果寫入報表；**存在任一「非預期」⇒ rc≠0**。
  - 🔴 R1 原文要求「每一項都須在 SPEC 中被預期」，`COMPOSER-R1-P1-01` 指出 Phase 0 真實語料上線後必然產生 SPEC 未列舉項 ⇒ 永遠 FAIL 或被悄悄放寬。**已改為「列舉項為必要子集 ＋ 附加項須人工標註」。**
  - 狀態斷言：語料檔 sha256 與報表標頭一致（**防止「改語料換綠燈」**）。
- **邊界（≥2）**：①語料為空 → rc≠0 並明確報錯，**不得靜默輸出「無差異」**（出生事故：2026-08-04 zsh 斷詞使 2559 條路徑變成一個檔名，報表印「前 0 後 0、無差異」）②語料含 Phase 0 記錄的真實被擋指令 → 須能吃 ③舊版 snapshot 檔缺失 → fail-closed。
- **存活至**：永久（`票 B-29` 實作時取代）。
- **覆蓋風險**：`票 B-29`（第 1 批）可能以更通用機制取代 ⇒ **屆時應取代而非並存**，理由已註記。
- 不可做：不掛 hook、不進 CI。

### Phase 3 — `B-14` ＋ `B-30` 委員產出生命週期（依賴：Phase 1）

> 兩票共用同一機制（attempt-scoped atomic publish），故同 Phase。

**Task 3.1 — per-family 耗時紀錄**

- 目標：先有資料，才有 timeout 值的依據。**Task 3.3 的定稿依賴本 Task。**
  檔案：`scripts/cx_run.sh` 的 `_run_cli_and_emit` 與 `_emit_family_result`（`:250-288`）。
- 改法：記錄 CLI 呼叫的起、訖與時長，寫入既有 `committee_family_result` 事件（**沿用既有事件，不新增事件型別**；欄位加入 `scripts/audit_events.json`）。時間源須為單調時鐘或 UTC epoch。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：一次真實派工後，`committee_family_result` 含起訖與時長三欄，且時長 == 訖 − 起（自洽檢查）。
  - 狀態斷言：欄位名與 `scripts/audit_events.json` 所定 schema 一致（以該檔為斷言來源）。
  - mutation：移除欄位 → 測試轉紅。
- **邊界（≥2）**：①CLI 未執行即失敗（binary 不存在）→ 時長欄為 0 或缺，不得為負 ②跨日／時區 → 用單調時間或 UTC epoch，禁本地時間字串相減。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不新增 audit 事件型別。

**Task 3.2 — attempt-scoped atomic publish（同時解 `B-30` 與 `B-14` 的 terminal marker）**

- 目標：委員寫入中的產出對外不可見；**publish 動作本身**即 terminal marker。
  檔案：`scripts/cx_run.sh`（產出路徑處理 ＋ `:512` prompt）；`scripts/new_brief.sh`／`brief_conformance_check.sh` 的骨架文字。
- 改法（依 `D-2` 全面改寫；R1 版本被兩家判 BLOCKING）：
  1. **attempt identity**：每次派工產生唯一 attempt id，產出寫入 **attempt 專屬 temp namespace**（例：`<out>.<attempt-id>.part`），**非共用的 `<out>.part`**。
  2. **prompt 對齊（`D-2` 核心）**：`cx_run.sh:512` 的「產出寫到 `${out}`」**必須同步改為 attempt 路徑**。
     🔴 **prompt-only 或 wrapper-only 皆不成立**：只改 prompt → 委員可忽略；只改 wrapper → 委員仍寫 `<out>`。**兩者必須同時改，且測試須同時覆蓋。**
  3. **啟動前檢查**：確認 final path 的 marker 不存在；若存在 stale `<out>` → **拒絕啟動或明確標記為 stale**，不得沿用（`CODEX-R1-P0-03`：舊 `<out>` 會被誤當本輪 terminal marker）。
  4. **publish 條件**：CLI 返回 rc=0 → 先 flush/fsync → 跑格式檢查 → 通過才原子 publish（rename）。**不通過則保留 attempt 檔並記 `format-failed`**（產出不消失，供人工檢視）。
  5. **terminal marker ≠ 檔案存在**：marker 為「本 attempt 的 publish 已完成」，須可由 audit 與檔案系統雙向確認（attempt id 綁定）。
     🔴 **明確不受理（`E-SCOPE`／`CODEX-R2-P0-01`）**：本 marker **不保證內容完整**——
     一份中途截斷但恰好最後一條 finding 格式完整的產出，仍會通過格式檢查並被 publish。
     可靠的截斷偵測需委員端產生 expected manifest（**跨越本批元件邊界**），已開 `票 B-35 GOV-OUTPUT-TRUNCATION-ORACLE`。
     本 Task 解掉的是 stale `<out>` 誤判、委員覆蓋自產（`B-30`）、未完成即上架**三種**失效模式；截斷是第四種，本批不解。
  6. **`B-30` 回歸**：委員若誤寫 attempt 檔，最終以 publish 為準；另加**大小回歸偵測**（曾非空後歸零 → 記警示）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：CLI 執行期間 `<out>` **不存在**、attempt 檔存在；正常結束後 `<out>` 存在且 attempt 檔已清除。
  - 狀態斷言：格式不合格時 attempt 檔**仍存在**且 `<out>` 不存在，`result_state=format-failed`。
  - 狀態斷言（**stale 防護**）：預先放置一個舊 `<out>`，CLI 逾時未 publish ⇒ **不得**判 `success`；audit 須顯示該 `<out>` 非本 attempt。
  - 狀態斷言（**`B-30` 回歸**）：以「寫入 → 清空 → 重寫」序列模擬 codex 事故，最終 `<out>` 等於最後一次寫入，且警示已記入 audit。
  - 狀態斷言（**prompt 對齊**）：`cx_run.sh` 產生的 prompt 內產出路徑 == wrapper 實際期待的 attempt 路徑（**同一來源，測試比對兩者字串相等**）。
  - **lock 生命週期（`F-3`：R3 只寫「拒絕」未定義生命週期，R4 定死 — `CODEX-R3-P0-03`／`COMPOSER-R3-P1-03`）**：
    - **ownership**：lock 綁 attempt id，內容含 pid 與起始時間戳（UTC epoch）。
    - 🔴 **acquire 必須是原子 exclusive claim（R6 補 — `CODEX-R5-P0-02`，兩家一致）**：
      取得 lock **不得**用「先檢查、再建立」兩步；須以**單一原子操作**取得 ownership，二選一：
      (a) `mkdir <out>.lockdir`（POSIX 保證同名目錄僅一個建立者成功），或
      (b) `O_CREAT|O_EXCL` 開檔（`set -o noclobber` 下的 `> file` 等價）。
      **取得成功者**才寫入 attempt id／pid／時間戳並啟動 CLI。
      **取得失敗者**重讀 lock 判定 stale：非 stale ⇒ 拒絕啟動（**不寫 `result_state`**，只記拒絕事件）；
      stale ⇒ **須先取得回收權再接管**（見下「stale takeover 協定」），**不得直接覆寫、亦不得裸刪重建**。

      🔴 **stale takeover 協定（R7 補 — `CODEX-R6-P0-02`，R6 初版的裸「刪除+重建」已被實跑證偽）**：
      ①以 `mkdir <out>.reclaim.lockdir` 的**原子操作**取得**回收權**；EEXIST ⇒ **直接拒絕啟動**，
      **不得再碰主 lock**（他人正在接管中）。
      ②取得回收權後**重讀主 lock**，確認其 attempt id **仍等於**先前判定 stale 時觀察到的那一個；
      **不相等 ⇒ 已被他人接管，不得刪除，直接拒絕**。
      ③相等才可刪除主 lock，並以⑥同款原子操作建立新 lock；建立失敗 EEXIST ⇒ **拒絕，不得再刪**。
      ④無論成敗，最後**釋放回收權**（`rmdir <out>.reclaim.lockdir`），且釋放前須確認回收權仍為自己所有。

      **事故三（`CODEX-R6-P0-02`，實跑證偽 — R6 初版的接管路徑有缺陷）**：
      初版寫「stale ⇒ 先原子刪除再原子建立」，**但刪除未綁定 observed owner**。
      競態：A、B 皆判定同一 lock 為 stale ⇒ B 先刪除、建立、啟動 CLI ⇒
      **A 接著把 B 剛建立的 live lock 刪掉**、建立自己的、也啟動 CLI ⇒ **兩個 CLI 並存**。
      codex deterministic ordering probe：`STALE_TAKEOVER_LOG=B:START,A:START`、`STALE_TAKEOVER_STARTS=2`。
      ⇒ **「取得是原子的」不等於「接管是原子的」**：接管是「讀 owner → 刪 → 建」三步，
      必須另有一把鎖把這三步序列化，否則原子 `mkdir` 只保證單步互斥。
      🔴 **`lock-create` 或 process-discovery 任一發生錯誤 ⇒ fail-closed（拒絕啟動）**，不得當作「無鎖」放行。

      **出生事故（實跑反例，勿弱化）**：R5 版只寫 ownership 綁 attempt id 與 release 比對 owner，
      **全文無 `O_EXCL`／`flock`／`mkdir`／`TOCTOU`**（`rg -n 'O_EXCL|flock|TOCTOU|exclusive' docs/GOVB0_FRICTION_SPEC.md` rc=1）。
      owner-safe release 只能防「**舊** owner 釋放**新** lock」，
      **擋不住兩個 dispatcher 在 precheck 都看到「無存活 lock」之後各自啟動 CLI**。
      codex barrier 模擬：A／B 兩者 precheck 皆通過，stdout 出現
      `A:START`、`B:START`、`TOCTOU_SIM_BOTH_PRECHECKS_PASSED=yes`。
      ⚠️ **「存活中」判準的聯集（見下）是「讀取面」的修補，不能取代「取得面」的原子性**——
      兩個 dispatcher 可以同時讀到正確的「無存活 attempt」，問題出在讀完到寫入之間的窗口。
    - **release**：`_emit_family_result` 寫入後**必定釋放**（無論 `success`／`failed`／`format-failed`），
      **不依賴 publish 是否成功**——否則失敗路徑會永久鎖死該 `<out>`。
      🔴 **owner-safe release（R5 補 — `CODEX-R4-P0-02`）**：釋放前**必須比對 lock 內的 attempt id 與自己相同**；
      不同即**不得釋放**（代表該 lock 已被 stale takeover 交給新 attempt）。
      ⇒ 防「舊 attempt 收尾時解掉新 attempt 的鎖」造成兩個 CLI 並存。
    - 🔴 **wrapper 本身被殺（`CODEX-R4-P0-02`）**：若 `cx_run.sh` 在 CLI 返回後、`_emit_family_result` 前被 SIGKILL，
      lock 與 attempt 檔皆殘留且**無 `result_state`**。此路徑**依賴 stale 判定回收**（pid 已死 ⇒ 可接管），
      **不得**因為「lock 存在」而永久拒絕重派。驗收須含此情境。
    - 🔴 **外層 timeout 觸發時（`CODEX-R4-P0-02`）**：`committee_run.sh` 的安全閥殺掉 `cx_run.sh` 後，
      **由 stale 判定負責回收 lock**（外層不直接刪 lock，避免 owner 不符的誤釋放）。
    - 🔴 **跨裝置 rename 失敗時**：publish 失敗 ⇒ 仍走 `_emit_family_result`（記 `failed`）⇒ **lock 照常 owner-safe 釋放**。
    - **stale lock**：lock 的 pid 已不存在，**或**起始時間戳距今 > (該家族 timeout ＋ 外層安全閥) ⇒ **視為 stale，可強制接管**並記 audit。
    - 🔴 **lock 檔被外部刪除但 attempt 進程仍存活**（`COMPOSER-R4-P2-02`）：**「存活中」的判準不得只看 lock 檔存在**，
      須為「lock 檔存在 **且** 其 pid 存活」**或**「該 `<out>` 的 attempt 進程存活」二者取聯集。
      實作上：啟動前除檢查 lock 檔外，**另查該 `<out>` 是否有存活的 attempt 進程**（以 attempt id 標記於進程參數或另存 registry）；
      任一為真即拒絕啟動。⇒ **刪 lock 檔不足以繞過序列化。**
    - **逾時後重派**：`failed` 的 attempt 其 lock 已釋放 ⇒ **同 `<out>` 重派正常放行**（不得誤拒）。
    - **被拒 attempt 的狀態**：**不寫 `result_state`**（該 attempt 從未啟動 CLI），只記一筆 audit 拒絕事件。
      🔴 理由：`result_state` 三值是 CLI 執行結果的語意；未啟動者寫入會**污染 Task 3.1 的 duration 統計**，
      進而影響 Task 3.3 的 timeout 定稿。
  - 狀態斷言（**並發 — R3 改設計**）：同一 `<out>` 已有**存活中**的 attempt 時，第二次派工**直接拒絕啟動**（rc≠0）並記 audit；
    第一個 attempt 不受影響、正常 publish。
  - 狀態斷言（**防誤拒／防鎖死**，`CODEX-R4-P0-02` 要求逐路徑覆蓋）：
    ①`failed` 收尾後同 `<out>` 重派 → **放行**且成功完成
    ②pid 已死的 stale lock 存在時重派 → **放行**且 audit 有接管紀錄
    ③被拒的 attempt 在 audit 中**無 `committee_family_result`**（只有拒絕事件），
      且 Task 3.1 的 duration 統計筆數**不因被拒而增加**
    ④**owner-safe release**：構造「舊 attempt 的 lock 已被 stale takeover 給新 attempt」後，
      令舊 attempt 走 `_emit_family_result` → **lock 不得被釋放**，新 attempt 仍持有
    ⑤**wrapper 在 CLI 返回後被 SIGKILL**：lock 與 attempt 檔殘留、無 `result_state` ⇒
      經 stale 判定後重派 **放行**（不得永久拒絕）
    ⑥**外層 timeout 殺掉 `cx_run.sh`**：lock 由 stale 判定回收，**外層不直接刪 lock**
    ⑦**lock 檔被外部刪除但 attempt 進程存活** → 第二次派工仍 **拒絕**（見上「存活中」判準取聯集）
    ⑧**跨裝置 rename 失敗** → `result_state=failed` 且 lock 已 owner-safe 釋放。
    🔴 ⑨**原子取得（barrier race，R6 補 — `CODEX-R5-P0-02`）**：兩個 dispatcher 對同一 `<out>`
      在 precheck 之後以 **barrier 同步**（不得用 `sleep` 競速，須 deterministic），
      **恰有一個** CLI 啟動、另一個 rc≠0；loser **不寫 `result_state`**，只記拒絕事件。
      **反向 mutation**：把原子 `mkdir`／`O_EXCL` 換回「先檢查再建立」兩步 ⇒ 本斷言**必須 FAIL**
      （出現兩個 `START`）。此 mutation 是本條可證偽性的證明，不得省略。
    🔴 ⑩**lock-create 錯誤 fail-closed**：令 `mkdir`／`O_EXCL` 因權限或 I/O 失敗（非 EEXIST）⇒
      **拒絕啟動**，不得視為「無鎖」而放行。
      🔴 ⑪**process-discovery 錯誤 fail-closed（R7 補 — `CODEX-R6-P1-03`）**：
      注入 process-discovery 的 `EIO`／權限錯誤 ⇒ **rc≠0、CLI 不啟動、不寫 `result_state`、只記拒絕 audit**。
      🔴 SPEC 內文（`acquire` 條款）已要求「`lock-create` **或** process-discovery 任一錯誤 ⇒ fail-closed」，
      但 R6 初版只有 `lock-create` 有可執行斷言 ⇒ **後半不可證偽**。⑪即補此缺。
      **兩者各須反向 mutation**：把該錯誤路徑改為「當作無鎖／無存活進程」放行 ⇒ 對應斷言**必須 FAIL**。
    🔴 ⑫**stale takeover 序列化（R7 補 — `CODEX-R6-P0-02`）**：A、B 皆判定同一 lock 為 stale，
      以 deterministic barrier 同步後各自嘗試接管 ⇒ **恰有一個** CLI 啟動；
      **且不得出現「A 刪除 B 已建立的 live lock」**——斷言 `STALE_TAKEOVER_STARTS == 1`，
      且 audit 中該 `<out>` 的 lock attempt id 序列**恰 1 次**變更（`grep -c` 導出）。
      **反向 mutation**：移除 `<out>.reclaim.lockdir` 回收權或移除「重讀比對 observed owner」⇒
      本斷言**必須 FAIL**（出現 2 個 `START`）。
    🔴 演進紀錄：R1 寫「後者覆蓋前者」（`CODEX-R1-P0-03` 指出會丟失成功產出）→ R2 改「兩者皆須保留可追溯」
    （`CODEX-R2-P0-02` 指出與單一 final `<out>` 的資料模型不相容，無可執行取勝規則）→ **R3 改為序列化拒絕**。
    理由：委員派工本就不應對同一產出路徑並發；**拒絕比仲裁簡單，且不丟資料**。
  - 狀態斷言（**publish 與 timeout 的順序契約，`E-9`／`CODEX-R2-P1-08`**）：
    `format check` 與 `publish` **均在 CLI wait 返回之後**由 wrapper 執行；**timeout 只涵蓋 CLI process-group 區間，不涵蓋 publish 階段**。
    ⇒ CLI 已返回但 publish 進行中時**不得**被 timeout 判 `failed`；`result_state` 每個 attempt **恰寫一筆**（測試須斷言 audit 中該 attempt id 的 `committee_family_result` 計數 == 1）。
  - mutation：移除 publish 改為直接寫 `<out>` → 前三條轉紅；移除 prompt 對齊 → prompt 對齊斷言轉紅。
- **邊界（≥2）**：①CLI 被 SIGKILL → attempt 檔殘留、`<out>` 不存在 ⇒ 判 `failed`，**不得因 attempt 檔格式合格而 publish** ②跨裝置 rename 失敗 → fail-closed 並明確報錯 ③attempt 檔在 publish 瞬間被外部刪除 → fail-closed。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**不得只改 prompt 要求委員自己做 atomic write**（不可靠，違反「工具必須自帶強制機制」）；**不得只改 wrapper 而不動 prompt**（`D-2`）。

**Task 3.3 — per-family timeout 與逾時後的 `result_state`**

- 目標：委員掛住時自動收斂，且不誤判成功。**值的定稿依賴 Task 3.1。**
  檔案：`scripts/cx_run.sh`（主 timeout）＋ `scripts/committee_run.sh:280`（外層安全閥）。
- 改法：
  1. **主 timeout 在 `cx_run.sh`**：涵蓋區間＝**CLI process-group launch → return/kill**（兩家一致），逾時終止該進程群組（避免孤兒）。
  2. **外層安全閥在 `committee_run.sh`**：上限略大於主 timeout；只在主 timeout 失效時作用。
  3. **逾時後判定**：本 attempt 已 publish → 依格式檢查落 `success`／`format-failed`；未 publish → **`failed`**。**不新增第四個 `result_state` 值**（SoT 見 `scripts/audit_events.json`）。
  4. **值與定稿門檻（`E-10`，R3 補上；R2 只說「須重算」未給可執行門檻）**：
     暫定 codex 50m／grok 70m／composer 75m、外層 90m（§A `OPEN-1`）。定稿規則＝
     ①**定稿門檻**：Task 3.1 上線後，**每家族累積 ≥50 筆** `committee_family_result` 且 `result_state=success`、含 duration 三欄，
       **且該 50 筆跨 ≥3 個不同 session／UTC 日期**（避免單日單批取樣偏差）；
       🔴 **R3 誤寫 ≥20**，與 R2 收斂 `E-10` 的裁決不符（該裁決已採 codex 較嚴者），**R4 依收斂裁決更正**
       （`CODEX-R3-P1-04`／`COMPOSER-R3-P1-01`）。另一家主張的 ≥20 僅作**中途 sanity check**，非定稿門檻。
     ②取各家族 `max(duration)` 與 `P99(duration)`（**單調時鐘欄位，非 runlog proxy**）；
     ③`timeout_family = ceil(max(max, P99 × 1.25))`；外層 `= max(family_timeouts) + 15m`；
     ④**未達定稿門檻時（含 R3 未定義的 10–19 區間，`CODEX-R3-P1-04`）**：
       timeout **機制照常上線並以暫定值運作**，值須**逐行標 `PROVISIONAL`**，
       **Task 3.3 不得宣稱完工**，`票 B-14` 保持「未定稿」直到門檻達成。
       ⇒ **只有「達標／未達標」兩種狀態，無中間灰區。**
       🔴 與 codex 原主張「未達門檻不得用暫定值」的差異與理由：**無 timeout 正是 `B-14` 事故成因**（空等 2h20m），
       「有暫定 timeout」嚴格優於「無 timeout」。此取捨經 R2 收斂 `E-10` 明示並獲三家戳記 APPROVED。
     ⑤歷史 runlog proxy（n=462）僅作 sanity check，**不可替代** Task 3.1 欄位。
     須可由環境變數覆寫以利測試。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/cx_run.sh WHEN cli=hang timeout_sec=1 THEN rc!=0`
  - 狀態斷言：上述情境 audit 的 `result_state` 為 `failed`，且 `<out>` 不存在、attempt 檔存在。
  - 狀態斷言：CLI 在 timeout 內正常結束且格式合格 → `result_state=success`、`<out>` 存在。
  - 狀態斷言（**孤兒檢查**）：逾時後查不到該 CLI 的殘留子進程（以 process group 為單位斷言）。
  - 狀態斷言（**值來源**）：TODO 中的 timeout 值與 Task 3.1 產出的 duration manifest 一致（**禁硬編未經重算的暫定值**）。
  - 狀態斷言（**`E-10` 取捨的可證偽化，R5 補 — `COMPOSER-R4-P2-01`**）：
    未達定稿門檻（任一家族 <50 筆或未跨 ≥3 session／UTC 日）時，
    ①TODO §0 與 duration manifest **含 `PROVISIONAL` 字樣**；②Task 3.3 在 TODO 中**標記為未完工**；
    ③`票 B-14` 票面狀態**含「未定稿」**。三者**任一缺失即 FAIL**。
    ⇒ 使「機制上線但不宣稱完工」這個取捨**可機械驗證**，而非只寫在改法散文裡。
  - mutation：移除 timeout → 掛住情境測試逾時失敗（測試自身須有上限）。
- **邊界（≥2）**：①CLI 在 timeout 邊界正常結束（競態）→ 不得寫兩筆 `result_state` ②timeout 值為 0 或負 → 拒絕啟動並報錯 ③三家並行時其中一家逾時 → 其餘兩家不受影響。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得只加 timeout 就殺（`票 B-14` 明載：會把已完成的審查誤判為失敗）；不得繞過 Task 3.2 的 terminal marker 自行判定完整性。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 為 `b,c`；**全部 11 個 Task**（`0.1`／`1.1`／`2.0`／`2.1`／`2.2`／`2.3`／`2.4`／`2.5`／`3.1`／`3.2`／`3.3`）皆宣稱「驗證判定正確性」 ⇒ **mutation 必附**，逐 Task 已列出，全部落為 `pytest tests/governance/` 斷言。設計依 `docs/TEST_DESIGN_CHARTER.md`。
  🔴 **本行數字須與 `grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md` 相等**；R2 曾寫 10 而實為 11（`CODEX-R2-P0-05` 抓出），與 `票 B-17`「手寫的機器依賴表必漂」同型。**code review 須機械核對本行。**
- **測試層級**：單元（正則判定／prompt 生成）＋整合（`cx_run.sh` 端到端一次真實派工）＋邊界。全部可 `pytest tests/governance/...` 獨立跑，不需 `run_api.py`。
- **`票 B-24` 紀律面（本批交付物之一，零新增元件）**：
  **規範性驗收（normative acceptance）一律為執行後狀態斷言**——檔案存在/不存在、序列逐項相等、集合包含關係、欄位值屬 SoT 集合、sha256 一致。
  **`rc` 只能作為輔助護欄（process guard），不得單獨構成驗收。**
  🔴 **R2 曾寫「每一條驗證皆非腳本 rc」，該敘述不實**（`CODEX-R2-P1-09`／`COMPOSER-R2-P2-01` 具名 `Task 0.1`／`1.1`／`2.5`／`3.3` 仍有 `ASSERT … rc`）。
  現行規則：`ASSERT … THEN rc=…` 為**範本規定的固定文法**（見 `templates/SPEC_TEMPLATE.md:26-34`），保留；
  但**每一條 `ASSERT … rc` 都必須有同 Task 內的對應狀態斷言**，否則不成立。
  本批 TODO 須逐條沿用；**code review 須逐條檢查「有 rc 斷言但無對應狀態斷言」者**。
- **防假綠**：
  - 禁改檢查器或加排除清單換綠；禁恆真斷言；禁弱化既有斷言。
  - **每個新測試須 mutation 自證**：revert 修法 → 該測試轉紅，並貼實跑 rc。
  - **既有 701 passed 為下限**；本批完工後總數只增不減；任何既有測試轉紅須具名說明。
  - 跑完測試須 `bash scripts/restore_golden_inventory.sh`，**驗收以 `git status --short tests/golden/` 輸出為空為準，不得以該腳本 rc 為證**。
- **行為差集**：Phase 2 完工須附 Task 2.5 報表；**列舉項為必要子集，附加項須逐項人工標註**，存在「非預期」即 FAIL。
- **邊界目錄**：空輸入（空語料／空指令）／並發寫（同 `<out>` 兩次派工）／API 重啟（CLI 被 SIGKILL）／大尺度輸入（4 MB prompt）。不適用：全 NaN 列、Inf、std=0、大尺度浮點 reduction。

## §R 回退

- **每 Phase 獨立 commit，可單獨 revert。** Phase 1 → Phase 3 有依賴（prompt 路徑）；Phase 0 → Phase 2 有依賴。Phase 0 與 Phase 1 彼此獨立。
- **Phase 2 為最高風險**（改判定放行/擋下）：
  - 逃生口＝環境變數一鍵回到舊判定（**僅供緊急回退，非預設關閉**——依使用者定死「驗過就別預設關閉」，Task 2.5 差集報表 rc=0 後新判定即為預設）。
  - 差集報表出現「非預期」項 → **不 merge**。
- Phase 0 為純觀測（判定行為不變），可最先 merge。
- 任一 Phase 使既有測試轉紅且無具名理由 → 不 merge。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）

- **§G Golden / Baseline：N/A** — 本批不碰數值正確性、特徵計算、ML 或回測路徑。RISK-HIT 為 `b,c`，不含 (a)／(d)。
  **替代保證**＝Phase 0 的判定行為不變證明（`(rc, kind)` 序列逐項相等）＋ Task 2.5 綁 sha256 的 immutable corpus 差集報表——兩者共同扮演本批的 baseline。
- **§A 待使用者確認：無** — 使用者 2026-08-04 明示技術取捨交委員裁決。三項 `OPEN` 已由 R1 審查裁定，裁定內容與條件已寫入 §A。
- 🔴 **本批明確不受理範圍（R3 新增；依使用者定死「沒 100% 解就做 95% 那版現在收，殘留具名記錄不當阻塞」）**
  收斂趨勢警訊：R1 19 條（5 P0）→ R2 17 條（7 P0），**P0 未下降**，命中 `docs/SCAR_LEDGER.md` 記載的
  P16 scope-accretion 失敗模式（每輪修訂新增機制，審查者在新機制上再找缺口，八輪卡在 20-25 findings）。
  故本批**逐項宣告不受理**，並各自具名殘留：

  | 不受理項 | 來源 finding | 殘留處置 |
  |---|---|---|
  | **產出截斷偵測 oracle**（expected manifest／record count／byte digest） | `CODEX-R2-P0-01`／`CODEX-R1-P0-04`／`GROK-R1-P1-01` | **`票 B-35 GOV-OUTPUT-TRUNCATION-ORACLE`**；`票 B-14` 須標「截斷偵測未解」 |
  | **`B-34` 語意閉合**（stamp roster vs 角色閘） | `CODEX-R2-P0-06`／`COMPOSER-R2-P1-03` | **`票 B-34`**；本批僅用權宜第三方戳記並明文標註 |
  | **`B-24` 機械強制面** | `COMPOSER-R2-P2-02` | R1 `D-6` 已裁 SPLIT；**TODO §0 須強制標「`B-24` 部分完成」**，code review 不得宣稱 `B-24` 全綠 |
  | **`B-15` FP-2 定位** | R1 `OPEN-3` | 已定補查條件（Phase 0 後 ≥200 筆 `gate_deny` 或 ≥30 日） |

  🔴 **另一項具名殘留（`F-7` 要求寫入 SPEC，R4 漏記，R5 補 — `COMPOSER-R4-P1-02`）**：
  `票 B-36`（收斂工具群集表盲點）已裁定併入 `票 B-13`、修法在**產出端**（`reconcile_build.sh` 生成骨架時預列全部 ID）。
  **但產出端修法只能擋「漏」，擋不了「錯位」**——ID 是預列的，錯的是「哪一列配哪個主張」。
  實證：本 SPEC 制定過程中，主委在群集表／SPEC 內文共犯 **6 次** ID 歸錯或對調，
  `completeness_check --lock`、主委逐 ID 自檢、`B-36` 的產出端修法**三者對「錯位」皆無感**，
  僅委員語意複核抓得到（其中 3 次為三家各自獨立指出）。
  ⇒ **「ID 錯位」目前無任何機械防線**，屬本批**具名接受的殘留**，須隨 `B-36` 併入 `B-13` 時一併記載。
  | **locale 相依守衛** | R1 `D-8`／`COMPOSER-R1-P1-03`／`CODEX-R1-P0-07` | **`票 B-33`**；TODO §0 須列為已知 MAJOR 債 |

  ✅ **使用者已核可（2026-08-05）**：「你們委員決定不受理，那我接受，就先記著就好」
  ⇒ 本不受理範圍**不再是主委單方裁決**，已獲委員（R2／R3 戳記輪三家表態）＋使用者雙重確認。
  四項殘留各自具名留票（`B-35`／`B-34`／`B-24` 機械面／`B-15` FP-2），**日後由 backlog 排期，不在本批重開**。

  🔴 **後續審查輪處置規則**：委員若再提上述任一議題，請標 `OUT-OF-SCOPE` 並附「不做會怎樣」的具體失效場景，
  **不作為 BLOCKING**。**例外**：若能證明不做會使**本批交付物本身失效**（而非只是不夠完美），仍可 BLOCKING，但須寫明失效路徑。

  ---

  🔴 **R7 具名殘留（兩家獨立提出同兩條，皆判 named-residual、非 deliverable-invalidating）**

  R7 為 P0-1／P0-2 的**最後一輪**（依「95% 解法就收・殘留先記錄」定死終止條件）。
  兩家 `FINDINGS_COUNT: 2`、deliverable-invalidating **0**、一致判**可進 TODO 生成**。

  | 殘留 | 來源 finding | 方向 | 處置 |
  |---|---|---|---|
  | **⑥允許清單仍非完整 shell-word grammar** | `CODEX-R7-P1-01`／`COMPOSER-R7-P2-01` | **fail-closed（誤擋）** | R7 已補入 codex 實跑驗證的 8 字元 `~{}[]!*?`；**未列字元一律走⑦ BLOCK** |
  | **reclaim lock 孤兒** | `CODEX-R7-P1-02`／`COMPOSER-R7-P2-02` | **fail-closed（可用性）** | 見下 |

  **殘留一（允許清單不完整）— 已部分修，殘留具名接受**：
  R7 補入 `~{}[]!*?` 八字元後，兩家點名的向量已解。
  **但允許清單本質上是「已知安全字元」的枚舉，不等於完整 shell-word grammar** ⇒ 仍可能有未列的合法字元。
  🔴 **殘留的方向是安全的**：未列字元 ⇒ ⑦ fail-closed ⇒ **過擋而非漏放**，不會使 gate 失效。
  **補查條件**（與 `B-15` FP-2 同機制）：Phase 0 上線後以 `gate_deny` 反查 heredoc 誤擋；
  命中則擴允許清單或開 `票 B-15` 子項。**本批不再擴。**

  **殘留二（reclaim lock 孤兒）— 具名接受，修法寫入 TODO 運維項**：
  stale takeover 協定的持有者若在步驟③（刪主 lock＋建新 lock）之後、④（釋放回收權）之前 crash，
  `<out>.reclaim.lockdir` 會殘留 ⇒ 後續 takeover 在步驟①即 EEXIST 拒絕 ⇒ **該 `<out>` 路徑鎖死至人工清理**。
  codex 實跑：`CRASH_CHILD_RC=137`、`MAIN_LOCK_AFTER_CRASH=present`、
  `RECLAIM_LOCK_AFTER_CRASH=present`、`NEXT_DISPATCH=REJECT_EEXIST`。
  🔴 **最壞後果＝單一 `<out>` 路徑暫時不可用，不會雙 CLI 並存、不會漏放真派工** ⇒ 非 deliverable-invalidating。
  **TODO 須落為運維項**（擇一，實作者定）：(a) 清 orphan reclaim 的運維腳本；
  (b) reclaim lock 加 TTL／lease（owner token＋pid＋時間戳）＋受保護的 stale-reclaim CAS；
  (c) 改用 crash 時自動釋放的 `flock`。
  **TODO §0 須明文標「reclaim 孤兒回收未實作 ⇒ 需人工清理」**，不得宣稱 lock 機制全綠。
- **原 Phase 4（`B-24` 機械強制面）：移出本批** — 依 `D-6` SPLIT 裁決，理由與 grandfather 三要件（具名 owner／UTC 到期日／到期後 fail-closed 行為）已記於 `handoffs/20260801-GOV-AMEND-BACKLOG.md` 的「`票 B-24` 的拆分裁決」節，不隨拆分遺失。
