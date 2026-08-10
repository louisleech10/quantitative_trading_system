# 站 2.5 — 狀態事實入 fact-key（`票 B-25` scope 擴充）— SPEC

> 來源診斷：`handoffs/20260801-GOV-AMEND-BACKLOG.md` §B-25「2026-08-10 scope 缺口」
> | 日期：2026-08-10 | 對應 TODO：`docs/GOVB25_STATUS_FACTKEY_TODO.md`（本 SPEC 定案後生成）
> | **版本：r5（定案版）**（r1 12 條 ＋ r2 7 條 ＋ r3 4 條 ＋ r4 1 條，全數接受；
> 收斂檔見 `handoffs/reconcile/20260810-govb25-x-review-r{1,2,3,4}/synth.md`）
> 🔴 `CODEX-R4-P1-01` 之關閉**待原提出方複驗**——依「閉合再驗證」紀律併入 TODO 審查輪必答第 1 條，不另開 SPEC r5 輪。
> 凍結文件 `docs/GOVB1_INPUT_QUALITY_SPEC.md`／`_TODO.md` **不就地修改**；
> 對其宣告之偏離登記於 `docs/GOV_B25_SCOPE_AMENDMENT.md`（體例同 `GOV_B8_SCOPE_AMENDMENT.md`）。

## §RISK 風險分級

- **大小**：**大**。
- **命中高風險原則**：**(b) 跨模組/共用路徑** — `scripts/gen_fact_key_blocks.sh` 同時掛在
  `scripts/gov_check.sh:310`（pre-push）與 `scripts/govb1_final_gate.sh:754`（g3）兩條共用閘；
  `--check` 誤紅會擋死每一次 push。**(c) 難回退** — 宿主檔敘述段改為生成區塊後，
  回退須同時還原資料檔、三份以上宿主檔、正反 fixture。
- RISK-HIT: b,c
- 未命中 (a)/(d) ⇒ §G 移 §N 標 N/A。

## §A 假設與待使用者確認

**已驗證事實**（皆為主委實跑；r1／r2 兩家已各自複跑前五條）：

- `FACT-RECEIPT: LC_ALL=C jq -r 'keys[]' scripts/fact_keys.json` → 印出 `_schema` `governance-execution-order`（主委 實跑 2026-08-10）
- `FACT-RECEIPT: grep -n "fact_keys == \[KEY\]" tests/governance/test_govb1_factkey_gen.py` → 印出 `68:    assert fact_keys == [KEY], (`（主委 實跑 2026-08-10）
- `FACT-RECEIPT: find tests/governance/fixtures/govb1/factkey_clean tests/governance/fixtures/govb1/factkey_drifted -type f | LC_ALL=C sort` → 印出 4 筆，每根各含 `README.md` 與 `docs/GOVERNANCE_EXECUTION_ORDER.md`（主委 實跑 2026-08-10）
- `FACT-RECEIPT: wc -l < tests/governance/fixtures/govb1/factkey_{clean,drifted}/docs/GOVERNANCE_EXECUTION_ORDER.md` → 兩者皆印出 `26`（主委 實跑 2026-08-10）
- `FACT-RECEIPT: grep -n "GOVB1_\|_G7_OOE_HARD_PROTECTED" scripts/govb1_final_gate.sh` → 印出 `380:_G7_OOE_HARD_PROTECTED='docs/GOVB1_`（主委 實跑 2026-08-10）⇒ 本 SPEC 不得置於 `docs/GOVB1_` 前綴下
- 🔴 `FACT-RECEIPT: 逐檔套用偵測詞彙（識別碼 ∩ 狀態值）計數` → 印出
  `HANDOFF.md 0`／`白話說明/接下來要做什麼.md 2`／`白話說明/第0批-在做什麼.md 3`／`白話說明/流程摩擦記錄.md 9`／
  `白話說明/第1批-在做什麼.md 17`／`白話說明/治理待辦總覽.md 18`／`白話說明/治理進度日誌.md 20`／
  `白話說明/第0批-施工清單.md 24`／`白話說明/第1批-施工清單.md 28`／`白話說明/README.md 29`／
  `docs/GOVERNANCE_EXECUTION_ORDER.md 17`（主委 實跑 2026-08-10）
  ⇒ 此 receipt 推翻 r1 `CODEX-R1-P1-02` 之前提「只需豁免 append-only README」：`白話說明/` 前綴下實為 **150 行**分佈於 9 檔。
- 🔴 `FACT-RECEIPT: 三條識別碼 extractor（見 Task 1.3 §E1–E3）實跑` → 分別印出
  `B0 B1 B2 B3 B4 B5 B6 B7`（第 0 批）／`b1 b2 b3 b4 b5 b6 b7 b8 b9 b10`（第 1 批）／
  `B-15 B-31 B-50 B-53 B3R`（票收案 union）（主委 實跑 2026-08-10）
- 🔴 `FACT-RECEIPT: git ls-files 不含未追蹤檔` → codex 於 `白話說明/` 建未追蹤探針檔，
  `git status --short` 得 `??`，`git ls-files -- <同路徑>` **空輸出且 rc=0**（codex 實跑 2026-08-10，探針已刪除）
  ⇒ r2 前之「新增檔案自動落入掃描」宣稱**不成立**，已於 Task 2.1 改正。

**待確認：無**

**已確認結果**：
- `2026-08-10 使用者「同意照你們的建議排序」＋「按照執行順序將任務都完成」` ⇒ 站 2.5 為當前施工標的。
- `2026-08-10 使用者「你跟委員共識決，你們決定就可以執行，這些技術面的我無法回答」` ⇒ 技術裁決由主委與兩家委員共識決，不上呈。
- `2026-08-10 使用者「Grok 沒額度，委員只剩 Codex 和 Cursor；實作者是 Opus，兩家 Codex+Cursor review」` ⇒ 實作端＝主委；審查家族＝codex、composer。

🔴 **`票 B-51` 事前裁決 receipt（Task 1.4 動碼之前置，r2 取得）**：
codex 裁 **(C) 核可但附條件**、composer 裁 **(A) 核可**（附條件）⇒ **兩家皆核可，裁決成立**。
出處：`handoffs/reconcile/20260810-govb25-x-review-r2/synth.md`「B-51 事前裁決 receipt」節。
合併後之**六項條件**逐條列於 Task 1.4 驗收欄；**未滿六條前不得動碼**。

## §C 約束

- 解耦 7 條與資料真實性原則本任務不觸及（純治理工具與文件路徑，無 `momentum/`／`api/` 改動）。
- **本任務特別注意（共用路徑與既有 caller）**：
  - `scripts/gov_check.sh:310` — `env -u GOVB1_FACTKEY_ROOT bash scripts/gen_fact_key_blocks.sh --check`（pre-push）
  - `scripts/govb1_final_gate.sh:754` — g3 語法/契約列
  - `tests/governance/test_govb1_factkey_gen.py`／`test_govb1_factkey_hook.py` — 既有 30+ 斷言
  - `scripts/govb1_scope.manifest` — `fact_keys.json`／生成器／兩支測試／`fixtures/govb1/` 皆在 `allow`；
    `HANDOFF.md`／`白話說明/`／backlog 在 `meta`；**`docs/` 下的檔皆不在 manifest ⇒ 須走 OOE trailer**。
  - `scripts/plain_docs_sync_check.sh` — `白話說明/接下來要做什麼.md`、`白話說明/治理待辦總覽.md` 均在 WATCHED 分派內。
- **資料結構單一真相源紀律**：本 SPEC 新增之枚舉（狀態值集合）、狀態 key 名集合、偵測範圍與豁免清單
  **一律定義於 `scripts/fact_keys.json` 之 `_schema`**，本 SPEC 只 pointer，不在散文列舉其值。

## §G Golden / Baseline

移 §N（未命中 (a)/(d)）。

## §P Phase 與依賴

> 🔴 **Phase 編制於 r3 重編**（r2 `CODEX-R2-P1-03`）：原編制要求 Phase 1 之 `status_keys` 非空且所列 key
> 須為已註冊 key，而狀態 key 原排在 Phase 2 ⇒ **Phase 1 單 commit 無法通過自己的 `--check`**，自相矛盾。
> 對照：舊 Task 2.1 → 新 **1.3**；舊 Task 2.4 → 新 **1.4**；舊 Task 2.2 → 新 **2.1**；舊 Task 2.3 → 新 **2.2**。

### Phase 1 — 機制、schema、資料與斷言（依賴：無；**單一 commit**）

**Task 1.1 — `target` 支援多宿主檔，且各宿主內容須逐位元組相同**

- 目標：一個 fact-key 可宣告 ≥1 個宿主檔，使同一事實在技術文件與使用者文件**皆為機械產物**。
  檔案：`scripts/gen_fact_key_blocks.sh` 之 `_fk_target`（改為 `_fk_targets`，逐行輸出）、
  `_fk_check`／`_fk_write`／`_fk_reject_unregistered_blocks` 三處迴圈。
  既有 caller/影響面：`gov_check.sh:310`、`govb1_final_gate.sh:754`、上列兩支測試。
- 改法：`.[$k].target` 型別為 `string` ⇒ 視為單元素序列；型別為 `array of string` ⇒ 逐筆；
  其餘型別 fail-closed。既有路徑檢查（絕對路徑／`..`）逐筆套用，**不得只驗第一筆**。
  🔴 **projection oracle**（r1 `CODEX-R1-P1-01`，r2 兩家確認已落實）：同一 key 之**所有** target
  其 `BEGIN/END` 區塊內容須**逐位元組相同**——生成內容只有一份，投影不得分歧。
  🔴 **必要性論證（碼證）**：若不支援多宿主，使用者端文件只能放指標；而 Task 2.1 偵測器之範圍
  以「登記路徑集合」計算，該檔仍在範圍內卻無區塊可對照 ⇒ §A 實測之 2 行手寫狀態永遠無法轉為機械產物。
- **驗證（可證偽）**：`pytest tests/governance/test_govb1_factkey_gen.py -q` 全綠，且下列三條同時成立：
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<多宿主 clean fixture> THEN rc=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<僅第二宿主漂移之 fixture> THEN rc!=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<兩宿主各自自洽但彼此不同之 fixture> THEN rc!=0`
  第二條之 stderr 須含**該第二宿主檔之相對路徑**；第三條即 projection oracle 之承重測試。
- **邊界（≥2）**：①`target` 為空陣列 ⇒ fail-closed ②含重複路徑 ⇒ fail-closed
  ③元素非字串／絕對路徑／含 `..` ⇒ fail-closed ④第一筆存在、第二筆缺檔 ⇒ rc≠0 且訊息具名缺的那筆。
- **存活至**：永久（機制本體）。
- **覆蓋風險**：無。Phase 2 只新增偵測器，不改本 Task 產出之函式契約。
- 不可做：不得引入 glob／目錄遞迴宿主；宿主集合須為註冊表逐筆字面宣告。

**Task 1.2 — `_schema` 增訂四項封閉集合宣告**

- 目標：把 Task 2.1 偵測器所需之**封閉集合**全部定義在資料檔，杜絕散文列舉與實作者猜測。
  檔案：`scripts/fact_keys.json` 之 `_schema`。
- 改法：新增四項，皆為資料、皆 fail-closed：
  1. `status_enum` — 狀態字面值之字串陣列。
  2. `status_keys` — **哪些 key 屬狀態 key** 之封閉名稱陣列（r1 `CODEX-R1-P1-04`／`COMPOSER-R1-P1-05`）。
     識別碼集合僅由此清單所列 key 之 rows 第 2 欄導出；🔴 明確排除 `governance-execution-order`
     ——其第 2 欄為站名，併入會放大誤擋。
  3. `status_scope` — 偵測範圍之 **path/prefix 集合**（r1 `CODEX-R1-P1-02` 之機制）。
     🔴 **編碼恰兩種、無第三種**（r3 `CODEX-R3-P1-02`；探針：`白話說明/第`→0 筆、
     `白話說明/第*`→4 筆、`白話說明/`→9 筆，證明「prefix」原樣當 pathspec 無決定性語意）：
     · **exact path** ＝ 不以 `/` 結尾之字串，比對方式為**全等**；
     · **directory prefix** ＝ **必以 `/` 結尾**之字串，比對方式為字首相符。
     **禁 wildcard**（`*`／`?`／`[`）——含之即 fail-closed，不得交由 pathspec 語意自行解釋。
  4. `status_scope_grandfathered` — **在本 SPEC r2 當下凍結**之既存檔豁免清單，逐筆帶實測命中數。
  並更新 `fields.target` 之型別說明為 `string | array of string`（r1 `COMPOSER-R1-P2-01`）。
- **驗證**：`pytest tests/governance/test_govb1_factkey_gen.py -q` 全綠，且下列三條同時成立：
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN registry_status_enum=absent THEN rc!=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN registry_status_keys=absent THEN rc!=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN registry_status_keys_contains_unregistered THEN rc!=0`
  🔴 **唯一語義（r5 `CODEX-R5-P1-02`；本欄為三處同步之一）**——新增之 fail-closed
  **不得**與既有「空註冊表 rc=0」契約衝突（`test_empty_registry_is_rc_zero_not_failure` 對 `{}` 期待 rc=0）：
  · 註冊表**無任何 fact-key** ⇒ `--check` rc=0（既有契約不變）
  · 註冊表**有 ≥1 fact-key** ⇒ `_schema` 四欄必須存在且合法，否則 fail-closed
  ⇒ 驗證須**先判有無 fact-key**。**不得刪該測試或放寬 fail-closed**。
- **邊界（≥2）**：①任一新增欄為空陣列 ⇒ fail-closed（**僅當有 ≥1 fact-key**）②含非字串元素 ⇒ fail-closed
  ③`status_keys` 列出註冊表中不存在之 key ⇒ fail-closed
  ④`_schema` 仍須被生成器當保留鍵跳過（既有 `test_reserved_schema_key_is_skipped…` 不得轉紅）
  ⑤空註冊表 `{}` ⇒ rc=0（`test_empty_registry_is_rc_zero_not_failure` 不得轉紅）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得在本 SPEC／TODO／任何 markdown 重列上述四項之值。

**Task 1.3 — 新增狀態 fact-key 與宿主標記（識別碼由三條 extractor 機械導出）**

- 目標：批次狀態與票收案狀態成為單一來源之機械產物。
  檔案：`scripts/fact_keys.json`（新增 key）、宿主檔（置入空 `BEGIN/END` 標記）、
  `tests/governance/fixtures/govb1/factkey_{clean,drifted}/`（補齊新宿主檔）。
- 改法：
  - `governance-batch-status`：rows 欄位 `ord`／`批次`／`狀態`。
    target ＝ `docs/GOVERNANCE_EXECUTION_ORDER.md` ＋ `白話說明/接下來要做什麼.md`。
  - `governance-ticket-closure`：rows 欄位 `ord`／`票`／`狀態`／`對外不得宣稱`。
    target ＝ `docs/GOVERNANCE_EXECUTION_ORDER.md` ＋ `白話說明/治理待辦總覽.md`。
  - `HANDOFF.md` **不設宿主**，維持指標制（實測命中 0 行）。
- 🔴 **§E 識別碼之機械導出（r2 `CODEX-R2-P1-02`／`COMPOSER-R2-P1-01`／`P1-02`；命令寫在 SPEC 本體，不 defer 到 TODO）**

  **共同規則**：三條 extractor 一律以 `git show <snapshot>:<path>` 讀取來源，
  `snapshot` ＝ `git rev-parse HEAD`；並記錄逐檔 blob SHA（`git rev-parse HEAD:<path>`）。
  🔴 任一來源檔之工作樹內容與 HEAD blob 不一致 ⇒ **fail-closed**（杜絕自未審內容抽取；r2 codex 指出
  `git rev-parse HEAD` 本身不綁工作樹內容）。
  🔴 **票號文法（封閉，含 token 邊界；r3 `CODEX-R3-P1-01`）**
  **token 字元類**定為 `[0-9A-Za-z_-]`。票號 ＝ 下列二者之一，且**兩側皆不得緊鄰 token 字元**：
  ① `票 B-[0-9]+`（取 `B-` 起之部分；左側由 `票 ` 前綴自然界定，故只驗右側邊界）
  ② 具名例外字面值 `B3R`（左右兩側皆驗邊界）
  **具名排除**（非票）：`R-[0-9]+`（規則編號）、`GOVB0 B[0-9]+`／裸 `B[0-9]+`（批次代號）、
  `[A-Z]+-R[0-9]+-P[0-9]-[0-9]+`（finding ID）——排除由文法本身達成，非另設黑名單。
  🔴 **不得**以 `grep -oE '票 B-[0-9]+|B3R'` 實作：該寫法無邊界，codex 實跑
  `票 B-99foo` → `B-99`、`XB3R`／`B3RISH` → `B3R`，且會被「逐筆比對」測試固化成假 oracle。
  **參考實作**（`LC_ALL=C awk`；`\b` 不可用——BSD/GNU 語法分歧，故以 `RSTART`/`RLENGTH` 自行驗邊界）：
  ```
  LC_ALL=C awk '
    # 一律以「原始行 s ＋ 絕對位置 st」判邊界，不依賴切片後的位置
    function boundary_ok(s, st, len,   pre, post) {
      pre  = (st == 1) ? "" : substr(s, st - 1, 1)
      post = substr(s, st + len, 1)
      if (pre  ~ /[0-9A-Za-z_-]/) return 0
      if (post ~ /[0-9A-Za-z_-]/) return 0
      return 1 }
    function scan(s, re,   off, rest, st, tok) {
      off = 0; rest = s
      while (match(rest, re)) {
        st  = off + RSTART
        tok = substr(s, st, RLENGTH)
        if (boundary_ok(s, st, RLENGTH)) print substr(tok, index(tok, "B"))
        off  = st + RLENGTH - 1
        rest = substr(s, off + 1) } }
    { scan($0, "票 B-[0-9]+"); scan($0, "B3R") }'
  ```
  🔴 **兩個必須照抄的細節（各由一次實跑失敗換來，皆為靜默錯誤）**：
  ① **絕對位移，不得切片後重判**（r4 `CODEX-R4-P1-01`）：前版每輪 `s = substr(s, RSTART + RLENGTH)`
  丟失原始左側前文，第二個相鄰候選之 `RSTART` 變 1、`boundary_ok` 誤判前界為空
  ⇒ `B3RB3R`／`XB3RB3R` 錯抽成 `B3R`。
  ② **樣式一律以「字串」傳入 `match()`**：awk **無 regex 型別**，`scan($0, /票 B-[0-9]+/)`
  會先求值成 `$0 ~ /re/` 的 `0`／`1` 再傳入，整支輸出變成 `0 1` 而**不報錯**（主委實跑踩到）。
  **TP/TN 測試矩陣（實跑輸出，主委 2026-08-10；本表即驗收 oracle，不得只測正例）**：
  | 輸入 | 輸出 | 類 |
  |---|---|---|
  | `票 B-15` | `B-15` | TP |
  | `票 B-15、票 B-31` | `B-15` `B-31` | TP（相鄰票號） |
  | `票 B-53）落地前` | `B-53` | TP（右側全形標點） |
  | `（B3R）` | `B3R` | TP（兩側全形標點） |
  | `票 B-99foo` | 空 | TN（suffix） |
  | `XB3R` | 空 | TN（prefix） |
  | `B3RISH` | 空 | TN（suffix） |
  | `B3R-lexer` | 空 | TN（連字號屬 token 字元） |
  | `GOVB0 B4` | 空 | TN（批次代號） |
  | `R-15` | 空 | TN（規則編號） |
  | `CODEX-R8-P1-03` | 空 | TN（finding ID） |
  | `B3RB3R` | 空 | TN（**相鄰重疊**；r4 `CODEX-R4-P1-01`） |
  | `XB3RB3R` | 空 | TN（**prefix ＋ 相鄰重疊**；同上） |

  **E1 第 0 批識別碼**（來源 `docs/GOVB0_FRICTION_TODO.md` 之 `## §B 批次執行策略` 節至下一 `^## `）：
  ```
  awk '/^## §B 批次執行策略/{f=1;next} f&&/^## /{exit} f' <src> \
    | LC_ALL=C grep -oE '^\| \*\*B[0-9]+\*\*' | LC_ALL=C grep -oE 'B[0-9]+' | LC_ALL=C sort -u
  ```
  實跑輸出（2026-08-10）：`B0 B1 B2 B3 B4 B5 B6 B7`；另加具名例外 `B3R`。
  🔴 **`B3R` 之存在性判定須 snapshot 綁定**（r3 `CODEX-R3-P1-03`）：
  用 `git cat-file -e <snapshot>:docs/GOVB0_B3R_LEXER_SPEC.md`，**不得**用工作樹 `test -f`
  ——後者違反本節自訂之綁定規則，同一 snapshot 下可被工作樹檔案切換輸出。
  該 path 亦納入逐檔 blob receipt；worktree／HEAD mismatch 一律先 fail-closed。

  **E2 第 1 批識別碼**（來源 `scripts/govb1_task_tickets.tsv`，即 `票 B-25` 已認可之機械權威 W′）：
  ```
  awk -F'\t' 'NR>1 && $1 ~ /^[0-9]+$/ {print "b"$1}' <src> | LC_ALL=C sort -u -V
  ```
  實跑輸出（2026-08-10）：`b1 b2 b3 b4 b5 b6 b7 b8 b9 b10`。

  **E3 票收案 union**（兩操作數；r2 composer 指出原第二操作數「backlog 表內票號」**不存在票號欄**，本版改正）：
  - 操作數 1 ＝ `HANDOFF.md` 之 `## 🔴 未修的活缺口` 節（至下一 `^## `）內之票號
  - 操作數 2 ＝ `handoffs/20260801-GOV-AMEND-BACKLOG.md` 之 `### 🔴 2026-08-10 scope 缺口` 子節
    （至下一 `^### `）內之票號——**依同一文法抽取，不指涉任何表格結構**
  ```
  { awk '/^## 🔴 未修的活缺口/{f=1;next} f&&/^## /{exit} f' <src1>
    awk '/^### 🔴 2026-08-10 scope 缺口/{f=1;next} f&&/^### /{exit} f' <src2>
  } | <上列票號 token 抽取器> | LC_ALL=C sort -u
  ```
  實跑輸出（token 邊界版，主委 2026-08-10）：操作數 1 得 `B-15 B-31 B-50 B-53 B3R`；操作數 2 得 `B3R`；
  union ＝ `B-15 B-31 B-50 B-53 B3R`。同節之 `B3`（裸批次代號）**未入集合**，證明排除規則有效。
  🔴 此 union 與 r3 無邊界版**相同**——邊界修正未改變本次結果，但消除了「不同實作者得不同集合」之可能。
  🔴 **不在 union 之票不得入 key**；已入 key 者須逐筆附 `source_path` 與 `line`。
- **驗證**：`pytest tests/governance/test_govb1_factkey_gen.py tests/governance/test_govb1_factkey_hook.py -q` 全綠，且：
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=unset THEN rc=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<factkey_clean> THEN rc=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<factkey_drifted> THEN rc!=0`
  另須有一支測試**逐筆比對 E1–E3 之輸出與 key rows 第 2 欄**（第三方可重跑）。
- **邊界（≥2）**：①新 key 之宿主檔缺標記 ⇒ rc≠0 ②`factkey_drifted` 須保留「兩份 fixture 對應檔列數相同、
  恰一列不同」之對照力（既有 `test_fixtures_differ_only_in_block_content` 不得放寬）
  ③任一 extractor 輸出為空 ⇒ fail-closed，不得產出空 key 後宣稱完成
  ④來源檔工作樹與 HEAD blob 不一致 ⇒ fail-closed。
- **存活至**：永久。
- **覆蓋風險**：無。Task 2.2 只刪敘述段之字面狀態，不動生成區塊。
- 不可做：不得放寬 `test_fixtures_differ_only_in_block_content`；不得把不在 union 之票塞進 key。

**Task 1.4 — 凍結宣告偏離之延伸檔與測試斷言修訂**

- 🔴 **前置裁決閘已滿足**（r1 `CODEX-R1-P0-05` 要求、r2 兩家核可）——見 §A 之 B-51 receipt。
  **動碼前須逐條滿足下列六項條件**（r2 兩家條件合併）：
  ①延伸檔體例對齊 `docs/GOV_B8_SCOPE_AMENDMENT.md`
  ②測試斷言與延伸檔 key 清單**集合相等**（禁 `issubset`／`>=`）
  ③不得就地改凍結 `docs/GOVB1_INPUT_QUALITY_{SPEC,TODO}.md`
  ④凍結 hash 閘須綠
  ⑤延伸檔 commit 須 `Governance-Scope: out-of-epic` trailer ＋收尾 `bash scripts/govb1_final_gate.sh --only g7`
  ⑥延伸檔缺失／key 重複／含未知 key ⇒ 測試 fail-closed
- 目標：`test_registry_is_valid_json_object_with_the_single_initial_key` 之「恰一個 key」斷言
  來自凍結 TODO「實作要點 1」；擴充必然使其轉紅。
  檔案：`docs/GOV_B25_SCOPE_AMENDMENT.md`（新建）、`tests/governance/test_govb1_factkey_gen.py`（修訂該斷言）。
- 改法：斷言由「恰等於 `[KEY]`」改為「**恰等於延伸檔宣告之 key 清單**」——仍為封閉集合相等比對。
  🔴 **normative expected set（r3 `CODEX-R3-P1-04`；本條為本 Task 最重要之防自證機制）**：
  單靠「registry ＝ 延伸檔」是**自我循環**——三者可彼此一致卻**漏交**一個狀態 key 而無人轉紅。
  故另加兩條與 Task 1.3 交叉之相等斷言：
  ①延伸檔宣告之**新增** key 清單 **恰等於** Task 1.3 明定之兩個 key；
  ②registry 完整 key 集合 **恰等於** 凍結期單一 key ∪ 該新增集合。
  兩條皆為集合相等，**禁 `issubset`／`>=`／`in`**。
- **驗證**：`ASSERT pytest tests/governance/test_govb1_factkey_gen.py -q THEN rc=0`；
  差分自證四條，缺一不可：註冊表多一個未宣告之 key ⇒ 轉紅；延伸檔刪除 ⇒ 轉紅（條件⑥）；
  延伸檔 key 清單**漏列任一** Task 1.3 新 key ⇒ 轉紅；延伸檔 key 清單有重複項 ⇒ 轉紅。
- **邊界（≥2）**：①延伸檔缺失 ⇒ fail-closed ②凍結檔 sha 不變（凍結 hash 閘）
  ③延伸檔落於 `docs/`、不在 manifest allow ⇒ commit 須帶 OOE trailer，收尾跑 `--only g7`
  ④延伸檔內 key 清單有重複項 ⇒ fail-closed。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：**不得就地修改凍結 TODO**；不得將斷言放寬成「至少包含」。

### Phase 2 — 偵測器與副本拆除（依賴：Phase 1 全部 Task；**單一 commit，且須含本 Phase 兩 Task**）

**Task 2.1 — 手寫狀態偵測器（registry 宣告之 path/prefix 範圍、封閉集合）**

- 目標：閉合條件後半「手寫狀態即 `--check` 非零」。
  檔案：`scripts/gen_fact_key_blocks.sh` 新增 `_fk_reject_handwritten_status`，掛在 `_fk_check` 尾端。
- 改法：掃描檔案集合 ＝ `status_scope` 宣告之 path/prefix 展開 **減去** `status_scope_grandfathered`；
  對每個檔取**所有生成區塊以外**之行；若某行同時命中「識別碼集合（由 `status_keys` 所列 key 之
  rows 第 2 欄導出）」與「`status_enum` 之任一值」⇒ rc≠0，訊息含檔名、行號、命中的識別碼與狀態值。
  🔴 **列舉器（r2 `CODEX-R2-P1-01`／`COMPOSER-R2-P1-03`；r2 前之寫法有實證旁路）**：
  ```
  git ls-files --cached --others --exclude-standard -z -- <repo 根> \
    | 逐筆依 status_scope 之 exact/prefix 規則過濾（見 Task 1.2 之編碼定義）
  ```
  **不得只用 `git ls-files`**——codex 實跑證明未追蹤檔不在其輸出，可在首次 `git add` 前手寫狀態而 `--check` 仍為 0。
  🔴 **不得把 `status_scope` 字串原樣當 git pathspec**（r3 `CODEX-R3-P1-02`）——三種寫法得三種集合；
  一律先列舉全樹再依 Task 1.2 之兩種編碼**在腳本內過濾**，使集合語意不依賴 pathspec 實作。
  🔴 **非 regular file 之處置（全部 fail-closed，不遞迴、不略過）**：symlink、
  submodule（gitlink）、以及任何 `git ls-files --stage` 模式非 `100644`／`100755` 之項目
  ⇒ rc≠0 並具名該路徑。理由：若一人遞迴、另一人拒絕，`--check` 的集合即不一致。
  🔴 **豁免清單以集合相等鎖死**：`status_scope_grandfathered` 之內容須與測試內之期望集合逐筆相等
  ⇒ 新增檔案（含未追蹤者）自動落入掃描範圍，無法靜默加進豁免。
- **驗證（可證偽）**：`pytest tests/governance/test_govb1_factkey_gen.py -q` 全綠，且下列四條同時成立：
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<範圍內已追蹤檔於區塊外手寫一行狀態> THEN rc!=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<範圍內未追蹤檔於區塊外手寫一行狀態> THEN rc!=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<同一行改置於生成區塊內> THEN rc=0`
  `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=<豁免清單多一筆未經修訂> THEN rc!=0`
  第二條即 r2 旁路之承重測試；第三條證明鑑別力來源是「在不在區塊外」。
  🔴 **硬驗收（r1 `COMPOSER-R1-P1-02`）**：另須產出誤擋率 receipt `handoffs/20260810-govb25-fp-receipt.md`，
  含分母、全量命中清單、逐筆 TP/FP 標註、Wilson 95% CI ≤5%，且經**至少一非實作者家族複核**；
  **無 receipt 或未複核 ⇒ 本 Task 判 BLOCKED，不得宣稱完成**。
- **邊界（≥2）**：①識別碼與狀態值分處兩行 ⇒ 不觸發（具名為偵測邊界）
  ②宿主檔完全無生成區塊 ⇒ 由既有 `_fk_markers_ok` 先行 fail-closed，本偵測器不得重複報
  ③範圍內但非宿主之檔 ⇒ 全檔皆屬「區塊外」
  ④宿主檔含 ≥2 個生成區塊時，區塊間之行仍屬「區塊外」
  ⑤`status_enum` 值出現在 `BEGIN/END` 標記行本身 ⇒ 不觸發
  ⑥`git ls-files` 不可用（非 git 樹）⇒ fail-closed，不得靜默退回「只掃 target」
  ⑦被 `.gitignore` 忽略之檔 ⇒ 不掃（`--exclude-standard` 之定義；具名為偵測邊界）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得在偵測器內硬編任何識別碼、狀態值、路徑或豁免項——一律由註冊表導出。

**Task 2.2 — 範圍內檔案拆除字面狀態**

- 目標：使 Task 2.1 之偵測器在真實 repo 為綠，且敘述段不再是第二份副本。
  檔案（實測命中數見 §A）：`docs/GOVERNANCE_EXECUTION_ORDER.md` 17 行、
  `白話說明/接下來要做什麼.md` 2 行、`白話說明/治理待辦總覽.md` 18 行。
- 改法：命中行改寫為指向生成區塊之指標，或改寫為**不含狀態值**之歷史敘述；
  **不得**以改用同義詞規避偵測（同義詞若確為狀態值，應加入 `status_enum` 而非繞開）。
- **驗證**：`ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=unset THEN rc=0`；
  並附**改寫前後逐行對照表**（17+2+18 ＝ 37 行），逐行標「改為指標／改為歷史敘述（不含狀態值）」。
- **邊界（≥2）**：①`docs/GOVERNANCE_EXECUTION_ORDER.md` 不在 manifest ⇒ commit 須帶
  `Governance-Scope: out-of-epic` trailer，收尾必跑 `bash scripts/govb1_final_gate.sh --only g7`
  ②`白話說明/` 兩檔改動後 `bash scripts/plain_docs_sync_check.sh` 須維持 rc=0
  ③`白話說明/治理待辦總覽.md` 之票狀態改為生成區塊後，其餘敘述不得再重述同一狀態。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得動 `status_scope_grandfathered` 所列之 7 個歷史日誌檔。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 不含 a/d，但本任務之測試**宣稱驗機制正確性** ⇒ 附定向 mutation，
  引 `docs/TEST_DESIGN_CHARTER.md`。**必附之承重證明**：
  - M1：移除 Task 1.1 多宿主迴圈中「第二筆之後」的處理 ⇒ 第二宿主漂移測試須轉紅。
  - M2：移除 Task 1.1 之 projection oracle ⇒ 「兩宿主各自自洽但彼此不同」測試須轉紅。
  - M3：把 Task 2.1 列舉器改回 `git ls-files`（去掉 `--others --exclude-standard`）⇒ 未追蹤檔測試須轉紅。
  - M4：把 Task 2.1 之「區塊外」判定改成「全檔」 ⇒ 「同一行置於區塊內應 rc=0」之測試須轉紅。
  - M5：把 Task 2.1 之豁免清單比對由集合相等改為 `issubset` ⇒ 「豁免清單多一筆」測試須轉紅。
  - M6：把 Task 1.4 之集合相等改為 `issubset` ⇒ 「未宣告的 key」測試須轉紅。
  - M7：把 Task 1.3 之 E3 排除規則拿掉（改抽裸 `B[0-9]+`）⇒ 逐筆比對測試須轉紅（`B3` 會混入）。
  - M8：把 Task 1.3 票號抽取器改回無邊界之 `grep -oE '票 B-[0-9]+|B3R'`
    ⇒ TP/TN 矩陣中四條 TN（`票 B-99foo`／`XB3R`／`B3RISH`／`B3R-lexer`）須轉紅。
  - M8b：把絕對位移掃描改回「每輪切片後重判邊界」⇒ `B3RB3R`／`XB3RB3R` 兩列須轉紅
    （此即 `CODEX-R4-P1-01` 之承重證明；M8 抓不到這一類）。
  - M9：把 Task 1.3 之 `B3R` 存在性改回工作樹 `test -f` ⇒ 「同一 snapshot 下工作樹刪檔仍應 fail-closed」測試須轉紅。
  - M10：把 Task 2.1 之 `status_scope` 過濾改為原樣 pathspec ⇒ directory prefix 之集合 oracle 測試須轉紅。
  - M11：把 Task 2.1 之 symlink／gitlink fail-closed 改為略過 ⇒ 對應邊界測試須轉紅。
  - M12：把 Task 1.4 之「延伸檔新增 key ＝ Task 1.3 兩 key」交叉斷言拿掉
    ⇒ 「延伸檔漏列一個新 key」測試須轉紅（此即 `CODEX-R3-P1-04` 之承重證明）。
- **誤擋率 receipt**：見 Task 2.1 硬驗收欄（本節不重述判準，避免第二份副本）。
- 測試層級：單元（生成器四模式）／整合（真實 repo `--check`）／對照（正反 fixture）／
  導出對照（E1–E3 vs key rows）／邊界（上列各 Task）。皆可獨立 `pytest tests/governance/…` 跑。
- **防假綠**：`test_fixtures_differ_only_in_block_content`、`test_real_repo_check_passes`、
  `test_t21_m1a/m1b/m1c` 既有斷言**不得放寬或刪除**；新斷言須對應新行為。
  收斂前 diff 既有測試檔，逐處說明「為何這是新行為而非放寬」。
- **邊界目錄**：空輸入（空陣列 target／空 `status_enum`／空 extractor 輸出）／重複輸入（重複 target）／
  缺檔／缺標記／標記重複／非 ASCII 路徑（`白話說明/` 宿主）／非 git 樹／未追蹤檔／被 ignore 之檔。

## §R 回退

🔴 **commit 依賴矩陣**（r1 `CODEX-R1-P1-06`／`COMPOSER-R1-P1-03`；r2 `CODEX-R2-P1-03`／`COMPOSER-R2-P2-01`）：

| 約束 | 拆開的後果 |
|---|---|
| Task 1.1 ＋ 1.2 同 commit | `_schema` 新欄之驗證與其消費路徑分離 ⇒ 契約與消費者版本錯開 |
| Task 1.2 ＋ 1.3 同 commit | `status_keys` 要求非空且須為已註冊 key，而狀態 key 由 1.3 建立 ⇒ 拆開則 Phase 1 無法通過自己的 `--check` |
| Task 1.3 ＋ 1.4 同 commit | 新增 key 而「恰一個 key」斷言未改 ⇒ `test_registry_is_valid_json_object…` 轉紅 |
| Task 1.3 資料 **不得早於** Task 1.1 程式 | 現行 `_fk_target`（`gen_fact_key_blocks.sh:73-81`）對陣列型 `target` fail-closed ⇒ `--check` 非 0 |
| Task 2.1 ＋ 2.2 同 commit | 偵測器先落地 ⇒ 真實 repo 37 行命中，`--check` 立刻轉紅 |
| 🔴 Phase 2 **不得只交 Phase 1**（靜默欠收） | 只落地 Phase 1 時 pytest 與 `--check` **可綠**，但偵測器與 37 行拆除均未交付＝違 B-25 閉合意圖 ⇒ **判 BLOCKED，非完成** |

⇒ **落地形態＝ Phase 1 單 commit、Phase 2 單 commit**（各自可獨立 `git revert`）。
每個 commit 落地前須同時通過：真實 repo `--check` rc=0、`pytest tests/governance -q` 全綠、
凍結 hash 閘、`bash scripts/govb1_final_gate.sh --only g7`。
任一階段 `--check` 在真實 repo 轉紅且非預期 ⇒ 立即 revert 該 commit，**不得以 `--no-verify` 繞過**。

## §N N/A 登記

- **§G**：N/A — 本任務不碰數值／特徵／ML／回測路徑，無 baseline 可凍（RISK-HIT 為 `b,c`）。
- **具名殘留（不在本 SPEC scope，逐條登記非省略）**：
  1. 不在 E3 union 之票不入 `governance-ticket-closure` ⇒ 其狀態仍只存在於 backlog 散文。
  2. `status_scope_grandfathered` 所列 7 個歷史日誌檔（實測共 130 行）**維持手寫**；
     依「面向未來不溯及既往」不回頭整治，但清單以集合相等鎖死，新增檔案不得靜默加入。
  3. `docs/` 前綴除已登記 target 外不納入掃描（多為凍結檔，改不得）。
  4. 識別碼與狀態值分處兩行之手寫副本偵測不到。
  5. 被 `.gitignore` 忽略之檔不掃（`--exclude-standard` 之定義）。
  6. `git push --no-verify` 可繞過整條 pre-push 鏈（既有殘留，非本票新增）。
  7. `票 B-25` 原條文之「判準資料化」（2026-08-07 併入項，需兩欄表格型 schema）**不在站 2.5**，
     其前置 `x-consult-r12 J-1` 仍成立；本 SPEC 只做「狀態事實」一半。
