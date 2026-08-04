# 治理 backlog 第 0 批（摩擦止血）— SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/govb0-recon-r1/synth.md`（21 findings，completeness rc=0）　|　日期：2026-08-04　|　對應 TODO：`docs/GOVB0_FRICTION_TODO.md`（待生成）

**涵蓋票**：`B-24`（驗收看狀態非 rc）／`B-15`（gate 判定誤擋＋兩個 fail-open）／`B-14`（委員不退出）／`B-30`（委員覆蓋自己產出）／`B-32`（stamp prompt 無條件注入）。
**唯一票登記處**：`handoffs/20260801-GOV-AMEND-BACKLOG.md`。

## §RISK 風險分級（gate 讀此決定要求強度）

- **大小**：大。
- **命中高風險原則**：
  - **(b) 跨模組／共用路徑** — `scripts/gate_check.sh` 是**每一次** `Task|Bash|Write` 工具呼叫的 PreToolUse 攔截點；`scripts/cx_run.sh`／`committee_run.sh` 是**所有**委員派工的唯一通道。任一處改壞即全域失效。
  - **(c) 多 phase／難回退** — 5 Phase；Phase 2 改判定放行/擋下，錯誤方向為 fail-open 且**無紀錄**（Phase 0 上線前不可觀測）。
- RISK-HIT: b,c
- 未命中 (a)／(d)：本批不碰數值、特徵、ML、回測路徑 → §G 於 §N 標 N/A。
- **adversarial review 必跑**（三家：codex／composer／grok），**code review 兩個非實作者家族**。

## §A 假設與待使用者確認（事故：拿推論代替問人）

- **FACT-RECEIPT 格式**：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`

**已驗證事實（7 條，每條附實跑 stdout 摘要）**：

- FACT-RECEIPT: `grep -o '"reason":"[^"]*"' .claude/gate/audit.log | sort | uniq -c` → 印出 `493 "reason":"token_expired"` / `106 "reason":"open_debt"`，全檔 599 筆僅此兩值，**無指令欄位**（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `LC_ALL=C grep -ac 'closure review' .claude/gate/ts_stamp.log` → 印出 `0`；同檔 `LC_ALL=C grep -ac 'hmsg.txt'` → 印出 `2`（Claude 實跑 2026-08-04）。⇒ 已知被 gate 擋下的指令零紀錄、成功重試有紀錄。
- FACT-RECEIPT: `bash .claude/tmp/b15probe.sh` → 印出 `BLOCK` 於 `pgrep -fl 'codex exec|cursor-agent|grok '`（命中 `|grok `）與 `git commit -m "fix: no review file; codex closure review done"`（命中 `; codex `）；7 條真派工全 `BLOCK`（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `bash .claude/tmp/b15probe2.sh` → 印出 `BLOCK` 於 `head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD`（命中 `claude-501/x.output; git rev-p`）；拆解對照組「只有 scratchpad 路徑」與「只有 git rev-parse」皆 `ALLOW`（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `grep -c 'token' scripts/cx_run.sh` → 印出 `0`；`grep -c 'token' scripts/_role_gate.sh` → 印出 `0`（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `grep -c 'timeout' scripts/cx_run.sh` → 印出 `0`；`scripts/committee_run.sh:280` 為裸 `wait "${pid}"`（Claude 實跑 2026-08-04）
- FACT-RECEIPT: `sed -n '512p' scripts/cx_run.sh` → 印出含 `RECONCILE-STAMP 的 task: 欄位須逐字使用此值` 的 prompt 賦值，**無 brief-kind 分支**（Claude 實跑 2026-08-04）

**待使用者確認**：**待確認：無**

**已確認結果**：`2026-08-04 使用者指示「有疑慮和問題就跟委員討論，有撞到問題需開票或合併的也就跟委員討論寫到 backlog」——本批技術取捨交委員裁決，不阻塞等使用者。`

**交委員裁決的未決技術項（非使用者事項；adversarial 輪必答）**：

- **OPEN-1（timeout 量測基準與值）**：codex 建議 20 分鐘（基準＝output 寫入→runlog 關閉，n=127），grok 建議 60 分鐘（基準＝runlog birth→最後寫入，n=440，ALL p99=48.5m）。**兩者量的區間不同，差一個數量級。**須裁定：①per-family timeout 要涵蓋的精確區間 ②排除已知掛死樣本（composer 146.7m）後重算 p95/p99 ③給出可證偽的建議值與誤殺率估計。**主委不自裁。**
- **OPEN-2（locale 相依守衛）**：`LC_ALL=C` 下 `gate.sh` 的 Verdict 守衛與 `doc_format_precheck.sh` 皆 fail-open（實測 2 例），`template_check.sh spec` 則 fail-closed 誤報（1 例）。須裁定是否開票、嚴重度、以及是否納入本批。**預設不納入本批 scope**（避免膨脹），除非委員判定為 BLOCKING。
- **OPEN-3（FP-2 未定位）**：`for f in codex composer grok; do … done` 形態的誤擋**至今無法重現**。Task 0.1 上線後才有紀錄可查。須裁定：本批是否以「Task 0.1 後補查」結案，或視為記載錯誤除役。

## §C 約束（不重抄，引用 + 只列本任務相關）

- 解耦 7 條不適用（本批不動 `momentum/`／`api/`／`frontend/`）。
- **本任務特別注意（共用路徑與既有 caller）**：
  - `scripts/gate_check.sh` — PreToolUse hook，**每次工具呼叫都執行**。`.claude/settings.json:99-135` 內為 `PreToolUse` 第 1 個 hook（`ts_stamp.sh IN` 為第 4 個）。熱路徑，禁引入 subprocess。
  - `scripts/cx_run.sh` — 唯一委員 CLI 呼叫點（`:443` codex／`:452` grok／`:461` composer）；`_emit_family_result`（`:250-288`）為 `result_state` 唯一寫入點。
  - `scripts/committee_run.sh:268` 呼叫 `cx_run.sh`、`:280` 裸 `wait`。
  - `scripts/completeness_check.sh:179` 為 finding ID schema 拒收點；`:1459-1472` 為 `--single` 實作。
  - `scripts/governance_families.json` 為家族 SoT；`scripts/governance_roles.json` 為角色 SoT。**禁在他處再寫一份清單。**
- **禁止**：改檢查器或加排除清單使測試變綠；恆真斷言；弱化既有斷言；空 monkeypatch 騙靜態檢查。
- **禁止**：`git checkout`／`git restore` 任何 tracked 檔。探針一律隔離副本。

> **新資料結構檢查點**：本 SPEC 新增的枚舉為 `gate_deny` 的 `match_rule` 欄位值集合與 `result_state` 的既有三值。
> `result_state` 三值已定義於 `scripts/audit_events.json`（既有 SoT），**本 SPEC 只 pointer 不重列**。
> `match_rule` 為**新**枚舉 ⇒ **Task 0.1 須將其定義寫入 `scripts/audit_events.json`，SPEC 不在散文中列舉值**。

## §P Phase 與依賴

### Phase 0 — 可觀測性前置（依賴：無）

> 目標：讓「被 gate 擋下」這件事留下可機械分析的紀錄。**Phase 2 的驗收完全依賴本 Phase**。

**Task 0.1 — `gate_deny` 記錄被擋指令與命中規則**

- 目標：`gate_deny` 事件新增指令與命中規則兩欄，使誤擋率可事後量測。
  檔案：`scripts/gate_check.sh` 的 `_append_gate_deny_audit()`（`:21-30`）與 `:86` 判定段；枚舉定義寫入 `scripts/audit_events.json`。
  既有 caller：`gate_check.sh:117`、`:128` 兩處呼叫點。
- 改法：
  1. `:86` 判定命中時，以 `grep -Eo` 取出命中片段，並記錄命中的是哪一條規則（家族名段／`claude` 段／未來新增段）。規則識別碼的**合法值集合定義於 `scripts/audit_events.json`**，`gate_check.sh` 只引用。
  2. `_append_gate_deny_audit()` 增加兩個欄位：命令（見下截斷規則）與命中規則識別碼。
  3. **命令欄截斷規則**：存 `sha256` 全文摘要 ＋ 前 512 位元組。理由：委員 prompt 可達數十 KB，全存會使 audit 膨脹；sha256 使同一指令可被歸併計數。
  4. **不改變任何放行/擋下的判定**——本 Task 為純觀測，行為必須逐位元組不變。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/gate_check.sh WHEN input=blocked_cmd THEN rc!=0`
  - `ASSERT bash scripts/gate_check.sh WHEN input=allowed_cmd THEN rc=0`
  - 狀態斷言：對同一批固定輸入，改前與改後的 `(rc, kind)` 序列**逐項相等**（行為不變證明）。
  - 狀態斷言：`gate_deny` 新事件經 `jq` 取出後，命令欄非空、命中規則欄值屬 `audit_events.json` 所定集合。
  - 新增測試須 mutation 自證：移除欄位寫入 → 對應測試轉紅。
- **邊界（≥2）**：①指令含換行與控制字元 → 欄位須為合法 JSON 字串，不得破壞 audit 逐行 JSON 結構 ②指令長度 0（`tool_input.command` 缺失）→ 欄位寫空字串而非缺欄，且不得例外中止 ③指令為 4 MB 巨量 prompt → 截斷後 audit 單行不超過 1 KB。
- **存活至**：永久保留（本批完工後仍為 `票 B-29` 差集工具的資料來源）。
- **覆蓋風險**：無。後續 Phase 只讀不改此欄位。
- 不可做：不建新的 log 檔（沿用 `.claude/gate/audit.log`）；不改 hook 順序；不動 `ts_stamp.sh`。

### Phase 1 — `B-32` stamp prompt 條件化（依賴：無）

> 目標：停止讓系統自己誘發委員交件失敗。**本 Phase 獨立，可先行單獨 commit。**

**Task 1.1 — `cx_run.sh` 的 prompt 依 `brief-kind` 分支**

- 目標：只有需要戳記的輪次才在 prompt 中提及 RECONCILE-STAMP。
  檔案：`scripts/cx_run.sh:512`（`prompt=` 賦值）。既有 caller：`_run_cli_and_emit`（同檔 `:513`）。
- 改法：
  1. `brief-kind` 已由 `brief_conformance_check.sh` 解析並經 `_bc_kv` 回傳，**沿用既有解析結果，禁再寫一份 parser**（`committee_run.sh` 曾因第二份 parser 造成孤兒債，見 `票 GOV-DOC-CHECK-AT-WRITE` 的 `R1-P1-01`）。
  2. `brief-kind ∈ {stamp, closure}` → 保留現行注入句，**並補充格式說明**：戳記為單獨一行 `RECONCILE-STAMP: <family> APPROVED <date> sha256:<hash> task:<id>`，**非 `## ` 標題**。格式來源＝`cx_run.sh:345` 的正則，**以該正則為單一真相源**，prompt 中的說明須與之機械對帳（測試斷言兩者一致）。
  3. 其餘 `brief-kind` → **完全不提** RECONCILE-STAMP，只注入 task-id。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/cx_run.sh WHEN brief_kind=consult THEN rc=0`（且 prompt 不含字串 `RECONCILE-STAMP`）
  - `ASSERT bash scripts/cx_run.sh WHEN brief_kind=stamp THEN rc=0`（且 prompt 含該字串與格式說明）
  - 狀態斷言：以 `handoffs/20260804-govb0-recon-composer.md`（**真實 format-failed 產物**）為回歸語料，證明其失敗原因（`## RECONCILE-STAMP` 標題）在新 prompt 下不再被誘發——以「prompt 文字不含該 token」為斷言，**不得以「委員這次沒寫」為斷言**（不可重現）。
  - mutation：還原無條件注入 → `brief_kind=consult` 的斷言轉紅。
- **邊界（≥2）**：①`brief-kind` 解析失敗／缺欄 → **fail-closed**（維持現行行為，拒派），不得因本改動變成放行 ②`brief-kind` 為未知值 → 視同「不需戳記」但須寫 audit 警示，不得靜默。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不改 `completeness_check.sh` 的 ID schema（另見 `票 B-32` 修法③，**本批不做**）；不改既有戳記格式。

### Phase 2 — `B-15` gate 判定修正（依賴：Phase 0）

> 目標：修掉兩個誤擋機制與兩個 fail-open。**驗收依賴 Phase 0 的 deny 紀錄。**
> **設計約束（`CLAUDE-R1-P1-03`）**：現行正則 TP 面 7/7 完好，**本 Phase 不得使任何既有 TP 轉為放行**。

**Task 2.1 — 引號感知（洞 A）**

- 目標：引號**內**的 `;` `&` `|` 不得被視為命令分隔符。
  檔案：`scripts/gate_check.sh:86` 判定段（新增前處理）。既有 caller：同檔 `:88` 排除段、`:90` `kind` 設定。
- 改法：判定前先產生「剝除單／雙引號 span 內容」的比對字串；原始字串仍用於 Phase 0 的紀錄。**前處理須為純 shell/`sed`，禁 subprocess 呼叫 python**（熱路徑，見 §C）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`pgrep -fl 'codex exec|cursor-agent|grok '` 由 BLOCK 轉 ALLOW；`git commit -m "…; codex closure review…"` 由 BLOCK 轉 ALLOW。
  - 狀態斷言：`echo start; grok -m grok-4.5 -p "x"`（引號**外**的分號）**維持 BLOCK**。
  - mutation：移除前處理 → 前兩條轉回 BLOCK。
- **邊界（≥2）**：①未閉合引號（`echo "abc`）→ 須有明確定義行為且**偏向 fail-closed**（視為未剝除） ②巢狀／跳脫引號（`"a\"b"`、`'a"b'`）→ 不得因剝除錯誤而放行真派工 ③引號內含真派工（`bash -c "codex exec x"`）→ **仍須 BLOCK**（此為 fail-open 風險點，須列入 TP 語料）。
- **存活至**：永久。
- **覆蓋風險**：無；Task 2.2/2.3/2.4 只增加判定條件，不移除本前處理。
- 不可做：不得白名單化「唯讀動詞」（原修法選項①，已由偵察否決——動詞清單永遠列不完，且與 `票 B-23`「禁止清單反轉為允許清單」的方向矛盾）。

**Task 2.2 — `claude` 段收窄（洞 B，含一條 fail-open）**

- 目標：`claude` 不再以子字串比對，`-p`／`--print` 須為獨立引數。
  檔案：`scripts/gate_check.sh:86` 第二段 alternation。既有 caller：同上。
- 改法：`claude` 比照家族名限定命令位置並允許路徑前綴；`-p`／`--print` 須有詞界；移除 `[^|]*` 的跨字元貪吃。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`head -3 /private/tmp/claude-501/x.output; git rev-parse --short HEAD` 由 BLOCK 轉 ALLOW。
  - 狀態斷言：`cat .claude/tmp/x.txt; git rev-parse HEAD`、`ls /private/tmp/claude-501/; git status --porcelain`、`find .claude/tmp -name "*.md" -print` 三者皆由 BLOCK 轉 ALLOW。
  - 狀態斷言：`claude -p "x"`、`claude --print "x"` **維持 BLOCK**。
  - 狀態斷言（**修 fail-open**）：`cat x | claude -p "y"` 由 **ALLOW 轉 BLOCK**。
  - mutation：還原子字串比對 → 前四條轉回 BLOCK、fail-open 條轉回 ALLOW。
- **邊界（≥2）**：①`claude` 出現在檔名中段（`my-claude-notes.md`）→ ALLOW ②絕對路徑呼叫（`/usr/local/bin/claude -p x`）→ BLOCK ③`-p` 為他人旗標（`grep -p`）且無 `claude` → ALLOW。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得為了省事把整段 `claude` 判定刪除（會失去子代理攔截）。

**Task 2.3 — 家族名 basename 化（fail-open ①）**

- 目標：帶路徑前綴的家族 CLI 須被擋。
  檔案：`scripts/gate_check.sh:86` 第一段 alternation。
- 改法：命令位置比對允許可選路徑前綴。**家族清單維持讀 `governance_families.json` 的 SoT 語意**（`:79-80` 註解已載明寫死原因為熱路徑，測試釘死該清單 == SoT；本 Task 不改此設計，只改前綴）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`/opt/homebrew/bin/codex exec hi`、`/Users/…/.grok/bin/grok -m x -p y`、`venv/bin/codex exec hi`、`./scripts/../codex exec hi` **四條全部由 ALLOW 轉 BLOCK**。
  - 狀態斷言：`cat sp_codex.txt`（`gate_check.sh:82` 註解明列的檔名子字串例）**維持 ALLOW**。
  - mutation：還原無前綴版 → 四條轉回 ALLOW。
- **邊界（≥2）**：①路徑含空白（`"/my dir/codex" exec`）→ 定義行為並在測試中固定 ②檔名為 `mycodex`（非 basename 相等）→ ALLOW ③`grok` 出現為目錄名（`/tmp/grok/notes.md`，後接空白）→ 須 ALLOW。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得把家族清單複製一份到別處。

**Task 2.4 — 官方外層腳本呼叫點（fail-open ②）**

- 目標：直接執行 `cx_run.sh`／`committee_run.sh` 亦須有 gate token。
  檔案：`scripts/gate_check.sh:86-90`。既有 caller：`committee_run.sh:268` 內部呼叫 `cx_run.sh`（**進程內部，PreToolUse 看不見，不受影響**）。
- 改法：命令位置出現 `scripts/cx_run.sh` 或 `scripts/committee_run.sh` → `kind=dispatch`；`scripts/gate.sh` 維持排除（否則無法 bootstrap 取 token）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：`ROUND_ID=x bash scripts/cx_run.sh composer b.md o.md` 由 ALLOW 轉 BLOCK（無 token 時）。
  - 狀態斷言：`bash scripts/committee_run.sh --session s b.md o codex -- --task-id T` 由 ALLOW 轉 BLOCK（無 token 時）。
  - 狀態斷言：`bash scripts/gate.sh dispatch --intent x …` **維持 ALLOW**。
  - **回歸護欄**：`committee_run.sh` 自身在有 token 後呼叫 `cx_run.sh` 的既有流程須仍可完成一次真實派工（端到端）。
  - mutation：移除呼叫點判定 → 前兩條轉回 ALLOW。
- **邊界（≥2）**：①相對路徑變形（`bash ./scripts/cx_run.sh`、`bash scripts//cx_run.sh`）→ BLOCK ②唯讀查看該腳本（`sed -n '1,40p' scripts/cx_run.sh`、`grep -n timeout scripts/cx_run.sh`）→ **必須 ALLOW**（否則製造新的誤擋，本批目的正是消滅誤擋）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得把 `gate.sh` 也納入（會鎖死取 token 的唯一路徑）。

**Task 2.5 — 行為差集報表（`票 B-29` 的手動版）**

- 目標：對同一批真實語料，列出「本來擋現在放行」「本來放行現在擋」「未變」三堆。
  檔案：新增 `scripts/gate_decision_delta.sh`（一次性可重跑，非 hook）。既有 caller：無（人工執行 + TODO 驗收引用）。
- 改法：讀入指令語料檔（一行一條），分別以舊版與新版判定，輸出三堆與計數。**語料須標明出處**，禁憑空造。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：對 Task 2.1–2.4 的全部測試語料執行，「本來放行現在擋」欄**恰等於** Task 2.3／2.4 列舉的 6 條 fail-open 修復項，**無其他項**。
  - 狀態斷言：「本來擋現在放行」欄**恰等於** Task 2.1／2.2 列舉的 6 條誤擋修復項，**無其他項**。
  - 若任一欄出現未預期項 ⇒ **FAIL**，須回頭說明。
- **邊界（≥2）**：①語料含 Phase 0 記錄的真實被擋指令（若已累積）→ 須能吃 ②空語料 → rc≠0 並明確報錯，不得靜默輸出「無差異」（**出生事故：2026-08-04 zsh 斷詞使 2559 條路徑變成一個檔名，報表印「前 0 後 0、無差異」**）。
- **存活至**：永久（`票 B-29` 實作時併入或取代）。
- **覆蓋風險**：`票 B-29`（第 1 批）可能以更通用的機制取代本腳本 ⇒ **屆時應取代而非並存**，理由已在此註記。
- 不可做：不掛 hook、不進 CI（一次性分析工具）。

### Phase 3 — `B-14` ＋ `B-30` 委員產出生命週期（依賴：無，但建議在 Phase 1 之後）

> 目標：委員掛住可自動收斂；委員無法覆蓋自己已完成的產出。**兩票共用同一機制（atomic close），故同 Phase。**

**Task 3.1 — per-family 耗時紀錄**

- 目標：先有資料，才有 timeout 值的依據（`CLAUDE-R1-P1-05`）。
  檔案：`scripts/cx_run.sh` 的 `_run_cli_and_emit` 與 `_emit_family_result`（`:250-288`）。
- 改法：記錄 CLI 呼叫的起、訖時間戳與時長，寫入既有 `committee_family_result` audit 事件（**沿用既有事件，不新增事件型別**）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：一次真實派工後，`committee_family_result` 事件含起訖與時長三欄，且時長與起訖之差一致（自洽檢查）。
  - mutation：移除欄位 → 測試轉紅。
- **邊界（≥2）**：①CLI 未執行即失敗（binary 不存在）→ 時長欄為 0 或缺，不得寫入負值 ②跨日／時區 → 使用單調時間或 UTC epoch，不得用本地時間字串相減。
- **存活至**：永久（Task 3.3 的 timeout 值調整依據）。
- **覆蓋風險**：無。
- 不可做：不新增 audit 事件型別（`scripts/audit_events.json` 只加欄位）。

**Task 3.2 — atomic close：`.part` → rename（同時解 `B-30` 與 `B-14` 的 terminal marker）**

- 目標：委員寫入中的產出對外不可見；上架動作即 terminal marker。
  檔案：`scripts/cx_run.sh` 的產出路徑處理；`brief_conformance_check.sh`／`new_brief.sh` 的 brief 骨架文字（告知委員產出路徑專用）。
- 改法：
  1. 委員寫入 `<out>.part`；CLI 正常返回後由 `cx_run.sh` 原子 rename 為 `<out>`。
  2. rename **前**執行格式檢查；不合格則保留 `.part` 並記 `format-failed`（產出不消失，供人工檢視）。
  3. 「`<out>` 存在」即成為 **terminal marker**——解 `CODEX-R1-P0-04`／`GROK-R1-P1-01` 的「`--single` rc=0 不足以證明寫完」。
  4. 解 `B-30`：委員若誤寫 `<out>`，因最終以 rename 覆寫，不會造成內容遺失；另加**大小回歸偵測**（曾非空後歸零 → 記警示）。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：CLI 執行期間 `<out>` **不存在**、`<out>.part` 存在；正常結束後 `<out>` 存在且 `<out>.part` 不存在。
  - 狀態斷言：格式不合格時 `<out>.part` **仍存在**且 `<out>` 不存在，`result_state=format-failed`。
  - 狀態斷言（**`B-30` 回歸**）：以「寫入 → 清空 → 重寫」序列模擬 codex 事故，最終 `<out>` 內容等於最後一次寫入，且警示已記入 audit。
  - 狀態斷言（**推翻「`--single` 即充分」**）：一份截斷但格式完整的 `.part` 檔**不得**被 rename 上架。
  - mutation：移除 rename、直接寫 `<out>` → 前三條轉紅。
- **邊界（≥2）**：①CLI 被 SIGKILL → `.part` 殘留、`<out>` 不存在 ⇒ 判 `failed`，不得因 `.part` 格式合格而上架 ②同一 `<out>` 併發兩次派工 → rename 為原子，後者覆蓋前者且 audit 兩筆皆在 ③檔案系統跨裝置（`.part` 與 `<out>` 不同 mount）→ rename 失敗須 fail-closed 並明確報錯。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不改委員 prompt 要求它自己做 atomic write（**不可靠，且違反「工具必須自帶強制機制」**）。

**Task 3.3 — per-family timeout 與逾時後的 `result_state`**

- 目標：委員掛住時自動收斂，且不誤判成功。
  檔案：`scripts/cx_run.sh`（主 timeout，包 CLI 呼叫）＋ `scripts/committee_run.sh:280`（外層安全閥）。
- 改法：
  1. **主 timeout 在 `cx_run.sh`**（`CODEX-R1-P1-01`／`GROK-R1-P2-01` 兩家一致）：包住 `:443`／`:452`／`:461` 的 CLI 呼叫，逾時後終止該進程群組（避免孤兒）。
  2. **外層安全閥在 `committee_run.sh`**：上限略大於主 timeout；只在主 timeout 失效時作用。
  3. **逾時後判定**：`<out>` 已由 Task 3.2 上架 → 依既有格式檢查落 `success`／`format-failed`；`<out>` 未上架（只有 `.part`）→ **`failed`**。**不新增第四個 `result_state` 值**（三值 SoT 見 `scripts/audit_events.json`）。
  4. **timeout 值**：見 §A `OPEN-1`，**由 adversarial 輪裁定後填入 TODO**；須可由環境變數覆寫以利測試。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - `ASSERT bash scripts/cx_run.sh WHEN cli=hang timeout_sec=1 THEN rc!=0`
  - 狀態斷言：上述情境下 audit 的 `result_state` 為 `failed`，且 `<out>` 不存在、`<out>.part` 存在。
  - 狀態斷言：CLI 在 timeout 內正常結束且格式合格 → `result_state=success`、`<out>` 存在。
  - 狀態斷言：逾時後 `pgrep` 查不到該 CLI 的殘留子進程（**孤兒檢查**）。
  - mutation：移除 timeout → 掛住情境測試逾時失敗（測試自身須有上限）。
- **邊界（≥2）**：①CLI 在 timeout 邊界正常結束（競態）→ 不得同時寫兩筆 `result_state` ②timeout 值為 0 或負 → 拒絕啟動並報錯，不得視為無限等待 ③三家並行時其中一家逾時 → 其餘兩家不受影響、各自獨立收斂。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得只加 timeout 就殺（`票 B-14` 明載——會把已完成的審查誤判為失敗）；不得繞過 Task 3.2 的 terminal marker 自行判定完整性。

### Phase 4 — `B-24` 驗收狀態斷言的機械強制（依賴：Phase 0–3 完成，本 Phase 對其驗收欄回頭抽驗）

> 目標：把「驗收要斷言狀態」從散文規定變成機器可檢。
> **偵察三家一致（`CODEX-R1-P0-03`／`GROK-R1-P1-02`）：backlog 原文「不另建檢查器」不滿足使用者定死條款。**

**Task 4.1 — 驗收斷言固定文法 + checker**

- 目標：驗收欄中「跑腳本看 rc」型敘述須伴隨狀態斷言，且可機械檢出。
  檔案：新增 `scripts/acceptance_state_check.sh`；掛入 `scripts/template_check.sh` 的 spec／todo kind。
  既有 caller：`gate.sh` 的 `--spec`／`--todo` 路由、`doc_format_precheck.sh`（PostToolUse，**產出端檢查**）。
- 改法：
  1. 沿用 `templates/SPEC_TEMPLATE.md:26-34` 已定義的固定文法 `ASSERT <cmd> WHEN <k>=<v> THEN rc=<n>`，**不發明第二套**。
  2. checker 規則：文件中出現 `rc=` 或 `rc!=` 的驗收行，若**同一 Task 區塊內**無任何狀態斷言關鍵字，則 FAIL。狀態斷言關鍵字集合須寫入資料檔（**非散文列舉**，避免 `票 B-16` 的病）。
  3. **檢查點放產出端**：`doc_format_precheck.sh`（寫檔當下）為主，`gate.sh` 派工前為輔。
  4. **誤報率**：`CODEX-R1-P0-03` 明確指出現無標註語料 ⇒ **不得宣稱誤報率數字**。TODO 須要求：先對本 SPEC 與本批 TODO 自身跑一次，人工標註結果作為初始語料。
- **驗證（可證偽）**：下列每條皆須落為 `pytest tests/governance/` 斷言，含狀態斷言與 mutation 自證（rc 直接取）
  - 狀態斷言：對**本 SPEC 自身**執行 checker → rc=0（本 SPEC 每個 Task 的驗證欄皆含狀態斷言）。
  - 狀態斷言：構造反例（只寫「跑 `restore_golden_inventory.sh` rc=0」而無 `git status --short tests/golden/` 斷言）→ checker rc≠0。
  - 狀態斷言：對 `docs/GOVERNANCE_HARNESS_P0_TODO.md:182-184`（`CODEX-R1-P0-03` 指出的既有反例）→ checker rc≠0。
  - mutation：移除規則 → 上述反例轉為 rc=0。
- **邊界（≥2）**：①`rc=` 出現在 help 輸出或程式碼區塊中 → 不得誤報（須排除 fenced code block） ②既有文件大量不合規 → checker 須支援 grandfather 清單，但**清單必須具名列舉且有到期日**，不得無限期豁免 ③跨行敘述（狀態斷言寫在下一行）→ 以 Task 區塊為單位判定，非逐行。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得對既有全部 `docs/` 一次性強制（`CODEX-R1-P0-03` 盤點 docs root 629 個候選，一次性強制會癱瘓）；本 Task 只對**新寫與本批修改**的文件生效。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 為 `b,c`（不含 a/d），但全部 11 個 Task 皆宣稱「驗證判定正確性」 ⇒ **mutation 必附**，逐 Task 已於上方列出，全部落為 `pytest tests/governance/` 斷言。設計依 `docs/TEST_DESIGN_CHARTER.md`。
- **測試層級**：單元（正則判定／prompt 生成）＋整合（`cx_run.sh` 端到端一次真實派工）＋邊界。全部須可 `pytest tests/governance/...` 獨立跑，不需 `run_api.py`。
- **防假綠**：
  - 禁改檢查器或加排除清單換綠；禁恆真斷言；禁弱化既有斷言。
  - **每個新測試須 mutation 自證**：revert 修法 → 該測試轉紅，並貼實跑 rc。
  - **既有 701 passed 為下限**，本批完工後總數只增不減；任何既有測試轉紅須具名說明。
  - 跑完測試須 `bash scripts/restore_golden_inventory.sh`，**且驗收以 `git status --short tests/golden/` 輸出為空為準，不得以該腳本 rc 為證**（`票 B-24` 本身的示範）。
- **行為差集（`票 B-29` 手動版）**：Phase 2 完工須附 Task 2.5 的三堆報表，**「本來放行現在擋」與「本來擋現在放行」兩欄的每一項都須在 SPEC 中被預期**，出現未預期項即 FAIL。
- **邊界目錄**（本批適用者）：空輸入（空語料／空指令）／並發寫（同 `<out>` 兩次派工）／API 重啟（CLI 被 SIGKILL）／大尺度輸入（4 MB prompt）。不適用：全 NaN 列、Inf、std=0、大尺度浮點 reduction（本批不碰數值路徑）。

## §R 回退

- **每 Phase 獨立 commit，可單獨 revert。** Phase 1（`B-32`）與 Phase 3（`B-14`／`B-30`）彼此無依賴，Phase 2 依賴 Phase 0。
- **Phase 2 為最高風險**（改判定放行/擋下）：
  - 逃生口＝環境變數一鍵回到舊判定（**僅供緊急回退，非預設關閉**——依使用者定死「驗過就別預設關閉」，Task 2.5 差集報表 rc=0 後新判定即為預設）。
  - Task 2.5 的差集報表若出現未預期項 → **不 merge**。
- Phase 0 為純觀測，行為逐位元組不變 ⇒ 回退風險最低，可最先 merge。
- 任一 Phase 使既有測試轉紅且無具名理由 → 不 merge。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）

- **§G Golden / Baseline：N/A** — 本批不碰數值正確性、特徵計算、ML 或回測路徑（改動集中於 `scripts/gate_check.sh`／`cx_run.sh`／`committee_run.sh`／新增治理 checker）。RISK-HIT 為 `b,c`，不含 (a)／(d)，依 §RISK 規則不需 Golden。
  **替代保證**＝Phase 0 的行為不變證明（同一批輸入的 `(rc, kind)` 序列逐項相等）與 Task 2.5 的行為差集報表——兩者共同扮演本批的 baseline 角色。
- **§A 待使用者確認：無** — 使用者 2026-08-04 明示技術取捨交委員裁決。三項未決技術項（`OPEN-1`／`OPEN-2`／`OPEN-3`）列於 §A，由 adversarial 輪裁定，非使用者事項。
