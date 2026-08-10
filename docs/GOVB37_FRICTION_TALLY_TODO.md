# 站 2.6 摩擦統計（`票 B-37` 唯讀最小版）— 實作 TODO

> 底本 SPEC：`docs/GOVB37_FRICTION_TALLY_SPEC.md`（**r3 定案**）
> 收斂檔：`handoffs/reconcile/20260810-govb37-x-review-r{1,2}/synth.md`（7＋2 條，全數接受）
> 實作端：主委自任｜審查：codex ＋ composer（兩個非實作者家族）｜日期：2026-08-10

## §0 全域規則與約束

### 0.1 🔴 兩項必讀狀態宣告

1. **`CODEX-R2-P0-01` 之關閉尚待原提出方複驗**——本 TODO 之審查輪必答第 1 條即為該複驗。
   在 codex 判「已關閉」之前，Task 1.1 之 quote-aware 解析**不得視為定案**。
2. **`票 B-37` 修法③（強制機制）不在本站**——原 Phase 2 已於 r1 移除，
   已證偽之方向記於 SPEC §N 殘留 3，**不得重試關鍵字黑名單**。

### 0.2 scope 與凍結約束

- 🔴 **只讀 `.claude/gate/audit.log`，不得有任何寫入該檔之路徑。**
- 🔴 **不得改 `scripts/gate_check.sh` 或任何判定邏輯**（寫入端間距統一屬 §N 殘留 1）。
- 新增 `scripts/friction_tally.sh` **不在 `scripts/govb1_scope.manifest` allow 內**
  ⇒ commit 須帶 `Governance-Scope: out-of-epic` trailer，收尾跑 `bash scripts/govb1_final_gate.sh --only g7`。
- `.claude/gate/*.log`、`handoffs/**` **不得 commit**。
- `_B45_HARNESS` 五檔、`docs/GOVB1_*`、`docs/GOVB0_*` 全程唯讀。

### 0.3 不可違反原則

- `rc` 禁經 pipe 取；改檔一律用 Edit/Write，禁 `sed -i`／heredoc。
- 🔴 **BSD awk 的 `-v` 值不接受換行**（本 epic 已犯三次）⇒ 多行值一律經**檔案**餵入。
- 不得依賴整檔 `jq`（實測 86.8% 的行非 JSON）。

### 0.4 防假綠

- 測試 fixture **自帶**，不得讀真實 `audit.log`（該檔不 commit 且每日變動 ⇒ 測試不可重現）。
- 三種間距 fixture 之計數若在 M1 mutation 下仍相同，代表 fixture **沒有鑑別力**，須重做。
- 對帳恆等式 `total == 各分類和 ＋ unparsed` 為**必附**斷言，不得省略。

## §A 假設與事實（facts-resolved）

🔴 **快照座標**（`audit.log` 為 append-only，數字必漂；三次重跑得 3950／3953／3955）：
```
snapshot: .claude/gate/audit.log  lines=39482  sha256[0:12]=9c3f06956468  取樣 2026-08-10
```
- facts-resolved: 兩種間距並存 → 有空格 3955／無空格 1385，無空格者**恰為 `gate_deny` 一類且 100% 無空格**
- facts-resolved: `gate_deny` 欄位隨時間演進 → 1385 筆中 718 筆帶 `cmd_sha256`；`reason` 全筆有、`match_rule` 僅新筆有
- facts-resolved: 整檔非 JSON 比例高 → 39479 行中僅 5221 行為合法 JSON（composer 實測，86.8% 非 JSON）
- facts-resolved: 第七類反例 → `{"event":"gate_deny","reason":"x}y"}` 天真配平得 `open=1 close=2`（codex 實跑）
- **待確認：無**

## §B 批次執行策略

| 批 | Task | 前置 | 為何不可再拆 | 大小 |
|---|---|---|---|---|
| **D1** | `1.1`／`1.2`／`1.3` | 無 | `1.2` 之五視圖全部依賴 `1.1` 之解析層；`1.3` 之驗收要求 `1.2` 之命令已可跑 ⇒ 分拆會產生「文件指向不存在的命令」之中間狀態 | 中 |

**Gate（D1 → 完工）**：
1. `pytest tests/governance/test_govb37_friction_tally.py -q` rc=0
2. `pytest tests/governance -q` **全套**全綠（丟背景，跑完 `bash scripts/restore_golden_inventory.sh`）
3. `bash scripts/friction_tally.sh --by-event` 於真實 log 實跑 rc=0 且輸出非空
4. `bash scripts/govb1_final_gate.sh --only g7` rc=0
5. `bash scripts/plain_docs_sync_check.sh` rc=0
6. `bash scripts/gen_fact_key_blocks.sh --check` rc=0（Task 1.3 動到受管檔案）

## Phase 1 — 解析、導出與文件落地（批 D1；單一 commit）

### Task 1.1 — quote-aware 解析層

- **新建**：`scripts/friction_tally.sh`
- **修改**：無
- 實作要點：
  1. `--log PATH`（預設 `.claude/gate/audit.log`）；缺檔／不可讀 ⇒ fail-closed 具名路徑。
  2. 🔴 **逐行 JSON 判準 ＝ 照抄 SPEC Task 1.1 契約 2 之參考實作**（`json_line_ok`）。
     核心一行：**引號是否結束字串 ＝ 其前方連續反斜線數為偶數**。
     🔴 **不得**自行改寫成散文規則後重新實作——r2／r3 連續兩輪之 BLOCKING 皆源於散文沒定義到邊界。
     SPEC 之 **9 類差分 fixture 表即驗收 oracle**，逐列寫入測試。
  3. **root-only 鍵擷取**：只取巢狀深度 0 之鍵；`{"meta":{"event":"fake"},"event":"real"}` 只取 `real`。
  4. **同行多物件** ⇒ `unparsed`（不得只取第一個）。
  5. 欄位樣式 `"<key>"[[:space:]]*:[[:space:]]*"<value>"`，**不得**寫死任一種間距。
  6. 輸出含 `total` 與 `unparsed`，且 `total == 各分類和 ＋ unparsed`。
- **驗證**：`pytest tests/governance/test_govb37_friction_tally.py -q` rc=0；三種間距 fixture 對同一組事件得**相同計數**；
  fixture `{"event":"gate_deny","reason":"x}y"}` 得事件 1、`unparsed=0`。
- **邊界**：SPEC Task 1.1 四項 ＋ 契約 1–6 各一測試；另加空檔／全雜訊／超長行／CRLF。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得寫入 `audit.log`；不得整檔 `jq`；不得先正規化整份 log。

### Task 1.2 — 五視圖與決定性輸出

- **新建**：無（同檔）
- **修改**：`scripts/friction_tally.sh`
- 實作要點：**六**模式 `--by-event`／`--by-reason`／`--by-day`／`--by-node`／`--by-signature`／
  🔴 `--field-presence`（**`event` × 欄位名 × present/absent × 次數**；r3 `CODEX-R3-P1-02` ＋
  r4 `CODEX-R4-P1-01`——既有文件第二條查的是**欄位是否存在**，`--by-reason` 答不出；
  且 key **必含 `event`**，否則全域與 gate_deny-only 兩種 scope 答案不同而無法唯一對帳）；
  對帳（**逐事件**）：`presence(e,f,present) + presence(e,f,absent) == by-event(e)`；
  驗收須含 **mixed-event fixture** 與精確 TSV 期望；
  輸出 TSV、`LC_ALL=C sort`、無時間戳；`cmd_head` 截斷 ⇒ 整欄標 `-`；
  未知模式或同時給兩模式 ⇒ rc=2 並印用法。
- **驗證**：連跑 3 次輸出逐位元組相同；各模式對 fixture 之期望輸出寫入測試。
- **邊界**：SPEC Task 1.2 三項；`ts` 缺欄或格式異常 ⇒ 日期計 `unknown` 不丟棄。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得輸出隨執行時間改變之欄位；不得輸出絕對路徑。

### Task 1.3 — 文件落地（逐檔具名）

- **新建**：無
- **修改**：`白話說明/接下來要做什麼.md`（「要看現值請跑」段）、
  `handoffs/20260801-GOV-AMEND-BACKLOG.md`（`## B-37` 節導出指令段）
- 實作要點：兩處各以 `<!-- BEGIN FRICTION-CMD -->` … `<!-- END FRICTION-CMD -->` 界定，
  區塊內只放 `bash scripts/friction_tally.sh --by-event` 與 `… --field-presence`；
  區塊外註明「數字不寫死，跑上列指令取現值」。
- **驗證（🔴 r3 `CODEX-R3-P1-03` ＋ r4 `CODEX-R4-P1-02`）**：
  **exact two-command closure**，四條同時成立才通過：
  ①marker 唯一成對 ②區塊內**恰兩行非空**且逐字為兩條 canonical 命令
  ③區塊內不得含 `"event"[[:space:]]*:[[:space:]]*"` ④兩個 active 段已被替換。
  🔴 缺②即**空區塊可通過**（codex 實跑得 `canonical=0 forbidden=0` 卻判過）⇒ 文件遷移漏做無人發現。
  🔴 區塊**外**之歷史敘述與說明範例**不納入**（原案錨定全檔，codex 實測既誤擋又漏擋）；
  `bash scripts/friction_tally.sh --by-event` 真實 log rc=0 且輸出非空。
- **邊界**：兩檔之外不得改動；`plain_docs_sync_check` rc=0；`handoffs/**` 不進版控。
- **存活至**：永久。
- **覆蓋風險**：無。
- **不可做**：不得恢復 Phase 2 強制機制；不得新增受管檔案清單。
