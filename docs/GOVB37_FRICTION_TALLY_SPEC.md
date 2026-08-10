# 站 2.6 — 摩擦統計（唯讀最小版，`票 B-37`）— SPEC

> 來源診斷：`handoffs/20260801-GOV-AMEND-BACKLOG.md` §B-37
> | 日期：2026-08-10 | 對應 TODO：`docs/GOVB37_FRICTION_TALLY_TODO.md`（本 SPEC 定案後生成）
> | 排期：`docs/GOVERNANCE_EXECUTION_ORDER.md` 序 `034`（唯讀最小版；完整版留序 `140`）
> | **版本：r3（定案）**（r1 七條 ＋ r2 兩條，全數接受；收斂檔
> `handoffs/reconcile/20260810-govb37-x-review-r{1,2}/synth.md`）
> 🔴 r1 之最大變更：**Phase 2 整段移除**（兩家實測判死）＋ **新增 `--by-node`／`--by-signature` 兩視圖**。
> 🔴 r2：解析契約 2 改為 **quote-aware**；§R 之文件落地升為 **Task 1.3**。
> 🔴 `CODEX-R2-P0-01` 之關閉**待原提出方複驗**——併入 TODO 審查輪必答第 1 條，不另開 r3 審查輪。

## §RISK 風險分級

- **大小**：**中**。
- **命中高風險原則**：**無**。本交付為**唯讀導出工具**——只讀 `.claude/gate/audit.log`，
  不改任何判定邏輯、不掛在既有閘上、不寫入任何受管檔案。
  未命中 (a) 數值/資料品質、(b) 跨模組共用路徑、(c) 多 phase/難回退、(d) ML/回測正確性。
- RISK-HIT: none
- ⇒ §G 移 §N 標 N/A。

## §A 假設與待使用者確認

🔴 **快照座標（r1 `CODEX-R1` verdict 段／`COMPOSER-R1-P2-01`：裸數字必漂，第二次同型病）**
`.claude/gate/audit.log` 為 **append-only**，任何計數當日即漂
（主委 r1 記 `3950`，codex 重跑得 `3953`，本次重跑得 `3955`——三次三個數字）。
**下列每條 receipt 一律綁定同一快照，比對須以同一快照為準**：

```
snapshot: .claude/gate/audit.log  lines=39482  sha256[0:12]=9c3f06956468  取樣 2026-08-10
```
複驗方式：先確認 `wc -l` 與 `shasum -a 256 | cut -c1-12` 相符；不符即**不可直接比對數字**，
須改以**比例**或重新取樣後整組重算。

**已驗證事實**（主委 2026-08-10 實跑，皆綁定上列快照 `sha256[0:12]=9c3f06956468`）：

- 🔴 `FACT-RECEIPT: LC_ALL=C grep -c '"event": "' .claude/gate/audit.log` → 印出 `3955`；
  `LC_ALL=C grep -c '"event":"' .claude/gate/audit.log` → 印出 `1385`（主委 實跑 2026-08-10）
  ⇒ **兩種間距並存**，且以有空格樣式掃描會漏掉 1385 筆（約占含 `event` 之行的 **26%**）。
- 🔴 `FACT-RECEIPT: LC_ALL=C grep -o '"event":"[a-z_]*"' .claude/gate/audit.log | sort | uniq -c` →
  印出 `1385 "event":"gate_deny"`（主委 實跑 2026-08-10）
  ⇒ **無空格者恰為 `gate_deny` 一類，且該類 100% 無空格**——漏掉的正好是全部攔截紀錄。
- `FACT-RECEIPT: LC_ALL=C grep '"event":"gate_deny"' … | grep -c cmd_sha256` → 印出 `718`（主委 實跑 2026-08-10）
  ⇒ `gate_deny` **欄位集合隨時間演進**（Phase 0 之後才有 `cmd_sha256`／`cmd_head`／`match_rule`），
  舊筆無該欄；統計須容忍缺欄，不得因缺欄而丟棄整筆。
- `FACT-RECEIPT: reason 分布` → `token_expired 980`／`open_debt 405`；
  `match_rule 分布` → `token_expired 454`／`open_debt 264`（主委 實跑 2026-08-10）
  ⇒ `reason` 全筆皆有、`match_rule` 僅新筆有；**兩者不可互相替代**。
- `FACT-RECEIPT: LC_ALL=C grep -m1 '"event":"gate_deny"' …` → 印出
  `{"event":"gate_deny","ts":"2026-07-06T05:08:30Z","tool":"Bash","kind":"dispatch","reason":"token_expired"}`（主委 實跑 2026-08-10）

**待確認：無**

**已確認結果**：`2026-08-10 使用者「技術問題和如果需要順序調整，一律你跟委員共識和淨摩擦決定，把需要的都做完，不要殘留也不用停下來問我」`
⇒ 本 SPEC 之技術裁決由主委與 codex／composer 共識決，不上呈。

## §C 約束

- 解耦 7 條不涉及（純治理工具，無 `momentum/`／`api/` 改動）。
- **本任務特別注意**：
  - `.claude/gate/audit.log` **只讀不寫**；工具**不得**有任何寫入該檔之路徑。
  - `.claude/gate/*.log` **不得 commit**（既有紀律）⇒ 測試不得依賴真實 log 內容，須自帶 fixture。
  - 新增 `scripts/friction_tally.sh` **不在 `scripts/govb1_scope.manifest` allow 內**
    ⇒ commit 須帶 `Governance-Scope: out-of-epic` trailer，收尾跑 `bash scripts/govb1_final_gate.sh --only g7`。
  - 🔴 **不得改 `scripts/gate_check.sh` 或任何判定邏輯**——本站是唯讀最小版；
    修正 `gate_deny` 之寫入端間距屬**行為改動**，不在本站 scope（見 §N 殘留 1）。
- **資料結構單一真相源紀律**：事件名／reason 值之枚舉**不得**在本 SPEC 或 TODO 散文列舉；
  一律由 `audit.log` 實際內容導出，或 pointer 回 `scripts/audit_events.json`（若存在）。

## §G Golden / Baseline

移 §N（RISK-HIT: none）。

## §P Phase 與依賴

### Phase 1 — 解析層（依賴：無；單一 commit）

**Task 1.1 — 間距無關之事件解析**

- 目標：以**兩種間距皆計入**的方式解析 `audit.log`，杜絕「靜默漏掉整類」。
  檔案：`scripts/friction_tally.sh`（新建）之 `_ft_field` / `_ft_event`。
  既有 caller/影響面：**無**（新工具，無人呼叫）。
- 改法：欄位擷取一律以 `"<key>"[[:space:]]*:[[:space:]]*"<value>"` 之樣式，
  **不得**寫死 `"event": "` 或 `"event":"`。
  🔴 **不得**改為「先正規化整份 log 再掃」——那需要寫入或大量暫存；本工具須能對 40MB log 串流處理。

  🔴 **解析契約（r1 `CODEX-R1-P1-02`；每條皆有可重現反例，缺一即靜默欠收）**：
  1. **輸入路徑**：`--log PATH`，預設 `.claude/gate/audit.log`。缺該檔／不可讀 ⇒ fail-closed 具名路徑。
  2. 🔴 **逐行 JSON 判準 ＝ 下列參考實作**（r2 `CODEX-R2-P0-01`／r3 `CODEX-R3-P0-01`）。
     **不再以散文描述跳脫規則**——r2、r3 連續兩輪之 BLOCKING 都是「散文沒定義到某個邊界」，
     該類可無限產生（字串內 `}`、反斜線奇偶、`\n` 字面…）⇒ 改以**實作＋差分 fixture**為契約。
     ```
     LC_ALL=C awk '
       function json_line_ok(s,   i, j, c, n, inq, depth, objs, bs) {
         n = length(s); inq = 0; depth = 0; objs = 0
         for (i = 1; i <= n; i++) {
           c = substr(s, i, 1)
           if (inq) {
             if (c == "\"") {
               # 🔴 引號是否結束字串 ＝ 其前方連續反斜線數為**偶數**
               bs = 0; j = i - 1
               while (j >= 1 && substr(s, j, 1) == "\\") { bs++; j-- }
               if (bs % 2 == 0) inq = 0
             }
             continue
           }
           if (c == "\"") { inq = 1; continue }
           if (c == "{") { depth++; if (depth == 1) objs++ }
           else if (c == "}") { depth--; if (depth < 0) return 0 }
         }
         return (inq == 0 && depth == 0 && objs == 1)
       }'
     ```
     **差分 fixture 表（主委 2026-08-10 實跑，9 類；本表即驗收 oracle）**：
     | 輸入 | 期望 | 為何 |
     |---|---|---|
     | `{"e":"a","r":"x}y"}` | ok | 字串內 `}` 不計入配平（r2 第七類） |
     | `{"e":"a","r":"a\\"b"}`（2 反斜線） | unparsed | 偶數 ⇒ 引號結束，其後 `b` 落字串外，確為非法 |
     | `{"e":"a","x":"p\\\\"}`（4 反斜線） | ok | 偶數 ⇒ 正常結束（r3 第八類） |
     | `{"e":"a","x":"p\\\\\\"q"}`（6 反斜線） | unparsed | 同上，其後 `q` 在字串外 |
     | `{"meta":{"event":"fake"},"event":"real"}` | ok | 行本身合法；root-only 擷取為契約 3 |
     | `{"a":1}{"b":2}` | unparsed | 同行雙物件 |
     | `=== dispatch ===` | unparsed | 非 JSON |
     | `{"unclosed":"x` | unparsed | 字串未閉合 |
     | `{"e":"a","x":"{"}` | ok | 字串內 `{` 不計入 |
     （實測 86.8% 的行非 JSON——含 `=== dispatch ===` 舊區塊；故不得整檔 `jq`。）
  3. **root-only 鍵擷取**：巢狀物件內之同名鍵**不得計入**。
     反例：`{"meta":{"event":"fake"},"event":"real"}` 前版得**兩個** event，正解只取 `real`。
  4. **跳脫引號**：值內 `\"` 不得被視為值的結束。
     反例：`{"reason":"foo\"bar"}` 前版得 `"reason":"foo\"`（截斷）。
  5. **同行多物件**：一行含兩個以上完整 JSON 物件 ⇒ 計入 `unparsed`，**不得**只取第一個。
  6. **對帳恆等式**：輸出須含 `total` 與 `unparsed`，且 **`total == 各分類次數和 ＋ unparsed`**
     ——此為機械可驗之防漏算 oracle。
- **驗證（可證偽）**：`pytest tests/governance/test_govb37_friction_tally.py -q` 全綠，且下列三條同時成立：
  `ASSERT bash scripts/friction_tally.sh --by-event WHEN log_spacing=with_space THEN rc=0`
  `ASSERT bash scripts/friction_tally.sh --by-event WHEN log_spacing=no_space THEN rc=0`
  `ASSERT bash scripts/friction_tally.sh --by-event WHEN log_spacing=mixed THEN rc=0`
  三者對**同一組事件**須得**相同計數**——此為承重 oracle（只吃一種間距即某欄為 0）。
- **邊界（≥2）**：①空 log ⇒ rc=0 且輸出零列（非 fail）②非 JSON 之雜訊行 ⇒ 跳過並計入 `unparsed` 計數，
  **不得靜默丟棄**（丟棄會使總數對不上）③缺欄之舊筆 ⇒ 該欄計為 `-`，整筆仍計入
  ④log 不存在／不可讀 ⇒ fail-closed 且訊息具名路徑。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得寫入 `audit.log`；不得引入任何寫入路徑；不得依賴 `jq`（log 含非 JSON 雜訊行時 `jq` 會整份失敗）。

**Task 1.2 — 導出視圖與決定性輸出**

- 目標：回答「**哪個節點、什麼原因、多少次**」（使用者 2026-08-05 原話）。
  檔案：`scripts/friction_tally.sh` 之 `--by-event` / `--by-reason` / `--by-day` 三模式。
- 改法：
  - `--by-event`：事件名 × 次數
  - `--by-reason`：僅 `gate_deny`，`reason` × `match_rule` × 次數（`match_rule` 缺欄計 `-`）
  - `--by-day`：`ts` 之日期部分 × 事件名 × 次數
  - 🔴 `--by-node`：`tool` × `kind` × 次數（r1 `CODEX-R1-P1-01` 之最小補救）
  - 🔴 `--by-signature`：`cmd_sha256` × `cmd_head` × 次數（舊筆該欄為 `-`；同上）
  - 🔴 `--field-presence`：**`event` × 欄位名 × `present`／`absent` × 次數**（r3 `CODEX-R3-P1-02`；
    key 含 `event` 為 r4 `CODEX-R4-P1-01` 之修正）。
    理由：既有文件第二條查詢問的是**欄位是否存在**（`grep -c cmd_sha256`），
    而 `--by-reason` 只輸出 `reason×match_rule` ⇒ **語義遺失**，換上去就答不出原問題。
    🔴 **key 必含 `event`**：codex 三行 fixture 實跑顯示，全域統計得 `cmd_sha256 present=2 absent=1`、
    僅 `gate_deny` 得 `1/1` ⇒ **兩種 scope 給出不同答案**，而既有查詢明確只數 `gate_deny`。
    不寫死 scope（那會使工具答不出其他事件之欄位覆蓋率），改以 `event` 入 key。
    **對帳關係（逐事件成立）**：對任一 `event e` 與欄位 `f`，
    `presence(e,f,present) + presence(e,f,absent) == by-event(e)`。
  輸出一律 TSV、`LC_ALL=C sort`、無時間戳、無環境相依。
  🔴 **`cmd_head` 截斷之處置**：composer 實測含 `\"` 之行使 `cmd_head` 截斷，影響 **145/1385 ＝ 10.5%**。
  新增 `--by-signature` 後該欄進入輸出 ⇒ **截斷即整欄標 `-`，不得輸出半截字串**
  （半截字串會在 `uniq -c` 下裂成多列，使次數失真）。
- **驗證**：`ASSERT bash scripts/friction_tally.sh --by-event WHEN run=3 THEN rc=0` 且三次輸出逐位元組相同；
  各模式對 fixture 之期望輸出寫入測試（非 golden 檔，避免另立維護面）。
- **邊界（≥2）**：①未知模式 ⇒ rc=2 且印用法 ②同時給兩個模式 ⇒ rc=2（不得靜默取第一個）
  ③`ts` 缺欄或格式異常 ⇒ 該筆日期計為 `unknown`，不得丟棄。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不得輸出任何隨執行時間改變之欄位；不得在輸出中寫入絕對路徑（跨機器不可比）。

**Task 1.3 — 文件落地：既有導出命令改為 canonical（r2 `CODEX-R2-P1-02`）**

- 目標：本工具無 caller 是**設計如此**（唯讀查詢工具，由人主動跑）；
  為避免「交了但沒人知道怎麼用」，把既有文件內之**手搓 grep** 換成本工具之 canonical 命令。
  🔴 原為 §R 之敘述，因「未具名檔案與命令 ⇒ 不可驗收」而升為 Task。
- 檔案（逐檔具名，**不得增列**）：
  1. `白話說明/接下來要做什麼.md` 之「要看現值請跑」段——現用
     `grep -c '"event":"gate_deny"'` 與 `grep … cmd_sha256`，
     **正是 spacing-sensitive 的寫法**（此例恰好命中，因 `gate_deny` 全無空格；
     同一寫法套到其他事件即漏）。
  2. `handoffs/20260801-GOV-AMEND-BACKLOG.md` 之 `## B-37` 節「導出指令」段。
- 改法：兩處之導出命令各以**具名區塊**界定，區塊內只放本工具之 canonical 命令
  （`<!-- BEGIN FRICTION-CMD -->` … `<!-- END FRICTION-CMD -->`）：
  `bash scripts/friction_tally.sh --by-event` 與 `bash scripts/friction_tally.sh --field-presence`
  （🔴 第二條用 `--field-presence` 而非 `--by-reason`——r3 `CODEX-R3-P1-02`：
  既有第二條查的是**欄位是否存在**，`--by-reason` 答不出該問題）。
  區塊外註明「數字不寫死，跑上列指令取現值」。
- **驗證（🔴 r3 `CODEX-R3-P1-03` ＋ r4 `CODEX-R4-P1-02`）**：檢查**只在具名區塊內**進行，
  且為 **exact two-command closure**，四條**同時**成立才算通過：
  1. 每檔 marker **唯一成對**（`BEGIN` 與 `END` 各恰 1）
  2. 區塊內**恰有兩行非空行**，逐字為
     `bash scripts/friction_tally.sh --by-event` 與 `bash scripts/friction_tally.sh --field-presence`
  3. 區塊內不得含 `"event"[[:space:]]*:[[:space:]]*"`（涵蓋兩種間距變體）
  4. 兩個指定 active 段**已被替換**（原手搓 `grep` 不再出現於該段）
  🔴 缺 2 即**空區塊可通過**——codex 實跑空區塊得 `begin=1 end=1 canonical=0 forbidden=0`，
  只驗「禁用樣式不存在」會讓文件遷移**漏做而無人發現**。
  區塊**外**之歷史敘述與說明範例**不納入**，不得成為假紅。
  另 `bash scripts/friction_tally.sh --by-event` 於真實 log 實跑 rc=0 且輸出非空。
- **邊界（≥2）**：①兩檔之外不得改動（避免 scope 蔓延）
  ②`白話說明/` 改動後 `bash scripts/plain_docs_sync_check.sh` 須維持 rc=0
  ③`handoffs/**` 不 commit ⇒ 該檔改動屬工作區內容，不進版控（既有紀律）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：🔴 **不得恢復 Phase 2 之強制機制**（codex r2 明示不要求）；不得新增受管檔案清單。

### ~~Phase 2 — 強制機制~~ 🔴 **整段移除**（r1 兩家一致判死，見 §N 殘留 3）

原案：`--check-docs` 偵測「摩擦統計語境下的裸數字」（三條件 AND ＋ 反引號豁免）。
**r1 兩家各自實測後一致判定不可上線**：
- composer：非 grandfathered 命中 **10 行全為 FP（≈100%）**；且**反引號豁免**使最主要違規行
  （`治理待辦總覽.md` 內之 `gate_deny` 三個數字）**完全不觸發** ⇒ **判準與目標互斥**。
- codex：未定義 TP/FP 標註規則、單位/分母、抽樣快照與判定者協議；
  且要求 grandfather 既有數字卻**未把 `docs/GOVERNANCE_EXECUTION_ORDER.md` 放進豁免**
  （該檔在 active scope，其自證段必被誤擋）。
- codex 另指出：Phase 2 既「不得掛閘」又要「強制執行」⇒ 可提交後永遠無 caller ＝**靜默欠收**。

⇒ **本 SPEC 改為單一 Phase。** 依既有紀律「沒有 100% 解就取 95/99% 那版現在收，
殘留具名記錄」與「文字問題用白名單機械卡；黑名單永遠列不完」——
**摩擦數字是無界集合，任何散文偵測都會重蹈 `票 B-23`／`票 B-39` 的路**。
已證偽之方向記於 §N 殘留 3，避免下一手重試同一條死路。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：RISK-HIT 為 none，但本工具之**唯一價值**即「不漏算」⇒ 附定向 mutation：
  - M1：把 Task 1.1 之欄位樣式改回寫死 `"event": "` ⇒ 「無空格 fixture 計數 == 有空格 fixture 計數」測試須轉紅。
  - M2：把 Task 1.1 之 `unparsed` 計數移除（改為靜默丟棄）⇒ 「總數 == 各分類和 ＋ unparsed」測試須轉紅。
  - M3：把 Task 1.2 之 `LC_ALL=C sort` 拿掉 ⇒ 決定性測試須轉紅。
  - M4：把 root-only 擷取改為全文擷取 ⇒ 巢狀 `{"meta":{"event":"fake"},"event":"real"}` 測試須轉紅。
  - M5：把跳脫引號處理拿掉 ⇒ `{"reason":"foo\"bar"}` 測試須轉紅。
  - M6：把「同行多物件計入 unparsed」改為只取第一個 ⇒ 對帳恆等式測試須轉紅。
  - M7：把 `--by-signature` 之 `cmd_head` 截斷標 `-` 改為輸出半截字串 ⇒ 次數不裂列之測試須轉紅。
  - M9：把引號結束條件由「前方連續反斜線數為**偶數**」改回「前一字元不是反斜線」
    ⇒ 差分 fixture 表之「4 反斜線」與「6 反斜線」兩列須轉紅
    （此即 `CODEX-R3-P0-01` 之承重證明；M8 抓不到——天真配平在該兩列上恰好也得同樣結果）。
  - M10：把 `--field-presence` 移除或改為輸出 `reason×match_rule` ⇒ 「present + absent == 事件次數」
    對帳測試須轉紅（`CODEX-R3-P1-02` 之承重證明）。
  - M8：把契約 2 之 quote-aware 配平改回天真計數 ⇒ fixture
    `{"event":"gate_deny","reason":"x}y"}` 之「事件 1、`unparsed=0`」測試須轉紅
    （此即 `CODEX-R2-P0-01` 之承重證明；M2 之對帳恆等式抓不到——誤列 unparsed 時恆等式仍成立）。
- 測試層級：單元（五模式）／對照（三種間距同計數）／邊界（空、雜訊、缺欄、未知模式）／決定性。
  fixture **自帶**（不得讀真實 `audit.log`——該檔不 commit 且內容每日變動，測試會不可重現）。
- **防假綠**：新測試須有**差分自證**——三種間距 fixture 之計數若在 M1 下仍相同，代表 fixture 沒有鑑別力。
- **邊界目錄**：空檔／單行／全雜訊／缺 `ts`／缺 `match_rule`／混合間距／超長行／非 UTF-8 位元組。

## §R 回退

- 🔴 **單一 Phase、單一 commit**（Phase 2 已於 r1 移除 ⇒ codex `CODEX-R1-P1-04` 所指之
  「獨立 revert 與強制執行互斥」隨之消失）。
- 本交付**不改任何既有判定邏輯、不掛任何既有閘、不寫入任何受管檔案**
  ⇒ **不存在「改壞既有行為」之回退情境**；最壞情況＝新工具本身無用，`git revert` 即可。
- 🔴 **靜默欠收之防線已升為 Task 1.3**（r2 `CODEX-R2-P1-02`：原敘述未具名檔案與命令 ⇒ 不可驗收）。

## §N N/A 登記

- **§G**：N/A — 唯讀導出工具，不碰數值／特徵／ML／回測，無 baseline 可凍。
- **具名殘留（逐條登記非省略）**：
  1. 🔴 **`gate_deny` 寫入端之間距不一致本身不修**——那是行為改動，需改 `gate_check.sh`；
     本站只讓**讀取端**容忍兩種間距。寫入端統一另立後續票（避免動判定邏輯）。
  2. **票 ↔ 事件簽章對照表**（`票 B-37` 修法①）不在本站 ⇒ 本工具**無法**回答「哪張票撞了幾次」，
     只能回答「哪個節點、什麼原因、幾次」。完整版留序 `140`。
  3. 🔴 **`票 B-37` 修法③「強制機制」未交付**——原 Phase 2 已於 r1 移除，文件內數字仍**靠紀律**。
     **已證偽之方向（記錄以免下一手重試同一條死路）**：
     「同一行同時出現 (a) 摩擦關鍵字 (b) 三位以上數字 (c) 不含導出命令特徵」之三條件 AND：
     composer 實測非豁免命中 **10 行全為 FP（≈100%）**，且**反引號豁免**使最主要違規行完全不觸發
     ⇒ **判準與目標互斥**。根因＝摩擦數字是**無界集合**，散文偵測必重蹈 `票 B-23`／`票 B-39`。
     可行方向須是**封閉可導出**者（例：數字本身成為機械產物），非關鍵字黑名單。
  4. `ts_stamp.log.slow`（B 類卡頓）**不在本站解析範圍**——其格式為 TSV 非 JSON，另立解析路徑；
     `票 B-37` 修法②原含該檔，本站刻意縮小範圍以求可交付。
  5. 撞擊次數**不得單獨作為排序依據**（`票 B-37` 已載明會偏袒高頻低痛）；
     本站只產數據，**排序設計不在本站**。
