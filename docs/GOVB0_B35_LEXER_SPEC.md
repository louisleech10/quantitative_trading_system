# GOVB0 B3.5 — 詞法層重寫 SPEC（草案 R1）

**狀態**：DRAFT — 待三家審查
**上游裁定**：`handoffs/reconcile/20260805-gatelex-redesign2/synth.md`（三家 APPROVED，`sha256:862f7bee…`）
**觸發**：B3 連續兩輪「修補引入新缺口」→ epic 收斂斷路器 → 設計重審 → 本批

## §0 全域規則與約束

### §0.A 數值影響

N/A — 純詞法判定層，不涉數值計算、不動 `data_cache/`、不影響回測或 ML 路徑。

### §0.B 不變式（違反即 BLOCKING）

1. **語料 A（`tests/governance/fixtures/gate_invariance_corpus.txt`）一行不得改。**
2. **禁回復長度截斷後放行**（B3 的 8192 `head -c` 是 fail-open 源頭）。
3. **禁以子字串比對做自我豁免**（B3 的 `grep -Eq 'scripts/gate(_check)?\.sh'` 是萬用繞道）。
4. **熱路徑禁 subprocess 呼叫 python**（沿用 Task 2.0 既有約束）；bash 3.2 相容。
5. **禁改檢查器讓測試變綠**、**禁恆真斷言**、**禁弱化既有斷言**。

### §0.C 本批不做（明列，避免審查無終點）

- C6 多 heredoc 第二 body 誤擋 → 順延 B4。
- latency 測試任何改動 → 三家已裁「維持現狀」，本批不碰。
- B4 以後的 Task（2.2／2.3／2.4／2.5／3.\*）。
- `audit.log` 瘦身／封存。

---

## §RISK 風險分級

RISK-HIT: b,c

- **(b) 跨模組／共用路徑**：`_gate_lex.sh` 由 `gate_check.sh`（PreToolUse，每次工具呼叫）與
  governance 測試共用；改動面波及所有派工判定。
- **(c) 多 phase／難回退**：本批分「原型→差分→落地」三階段，
  且工作區已有暫緩的 B3 修補，回退路徑非單一 commit。
- **(a) 數值／資料品質**：不命中——純詞法層，不觸數值。
- **(d) ML／回測正確性**：不命中——不觸 `momentum/`、不觸 `data_cache/`。

## §A 問題陳述

現行 `_gate_lex.sh` 採「**先轉換、再 grep**」：把整條指令改寫一份（引號 span 內空白→US），
再對改寫結果跑多條 `grep -Eq`。三家重審確認兩個**獨立**缺陷：

| 代號 | 缺陷 | 實測 |
|---|---|---|
| **E-1** | `_gate_cmd_is_self_gate` 以 ERE **字面 `\n`** 比對，抓不到真換行 ⇒ 換行複合命令被當自呼叫 ⇒ `gate_check.sh:211-212` **早退 `exit 0`**，判定函式從未執行 | `bash scripts/gate.sh\ncodex exec hi` → rc=0（應 2） |
| **E-2** | awk 以 `out = out c` 逐字元累加建構輸出 ⇒ 字串反覆重配置，**超線性** | 引號內字元數：10K→0.09s／100K→1.32s／**500K→29.92s** |

**共同背景**（非共同根因）：缺少單一權威 tokenizer，每個判定各自 grep 近似
⇒ 每加一條規則就多一個漏洞面。

**待使用者確認：本任務無。** 本批全部事實均可由 repo 內程式碼、既有 SPEC 契約與
實跑量測導出；不依賴任何只有使用者知道的資訊。三家設計重審已於
`handoffs/reconcile/20260805-gatelex-redesign2/synth.md` 全數 APPROVED。

---

## §B 設計：單趟串流掃描器 + 事件契約

### §B.1 掃描器介面

```
_gate_lex_scan <cmd>   →  stdout：逐行事件，每行一筆
```

**約束**：單趟、O(n) 時間；**不建構改寫後的完整字串**（這是 E-2 的直接死因）。
事件以 `printf` 逐筆輸出，不在 awk 內累加大字串。

### §B.2 事件型別（**本節為 F-2 的修補：委員判定原提案欄位不足**）

| 事件 | 欄位 | 語意 |
|---|---|---|
| `CMD` | `depth`／`start`／`word1`／`word1_decoded`／`context` | 一個**命令位置**及其第一個 word。`word1_decoded`＝去引號後的字面值；`context`＝`top`\|`inner_c`\|`inner_eval`\|`cmdsub`\|`backtick` |
| `ARGSPAN` | `depth`／`kind`(`-c`\|`eval`)／`start`／`end`／`quoted`(0/1) | `(bash\|sh\|zsh) -c` 與 `eval` 的**引數 span**，含 **unquoted 形式** |
| `EXECSPAN` | `depth`／`kind`(`cmdsub`\|`backtick`)／`start`／`end` | `$()`／反引號 span（雙引號內亦會執行） |
| `HEREDOC` | `status`(`ok`\|`unparsable`)／`delim`／`body_start`／`body_end` | 依 Task 2.0 契約 10 之①～⑦ |
| `PATHWORD` | `raw`／`normalized` | 命令位置 word 的路徑正規化結果（`./`／`//`／`../`） |
| `LEXERR` | `kind`(`unclosed_quote`\|`unclosed_heredoc`\|`depth_exceeded`\|`unparsable_heredoc`)／`offset` | **任一出現即 fail-closed** |
| `CMDCOUNT` | `n` | 頂層命令位置總數（供自我豁免述詞用） |

### §B.3 十一條契約 × 事件欄位對照（**逐條，缺一即設計不完整**）

| # | Task 2.0 契約 | 由哪些事件導出 | 判定 |
|---|---|---|---|
| 1 | 引號內 `;&\|` 不作分隔符 | `CMD` | 掃描器在 quote 狀態內**不產生** `CMD` |
| 1b | 剝引號須跨行有狀態 | `CMD` | 狀態機逐字元跨行追蹤；**不做行內替換、不正規化為單行** |
| 2 | 命令位置完整定義（`^ ; & \| ( ` $( && \|\| eval xargs` 之後） | `CMD.start` | 每個位置產一筆 `CMD` |
| 3 | `-c`／`eval` 引數遞迴 | `ARGSPAN` → 遞迴 | 對 span 內容重入掃描器，`depth+1`、`context=inner_c`/`inner_eval` |
| 4 | 帶引號的路徑（`"/my dir/codex" exec`） | `CMD.word1_decoded` | 以**去引號後**的字面值比對 executor 名單 |
| 5 | 路徑正規化 | `PATHWORD.normalized` | `./`／`//`／`../` 正規化後再比對 |
| 6 | 未閉合引號 → fail-closed | `LEXERR:unclosed_quote` | 出現即 BLOCK |
| 7 | **unquoted** `-c` 引數（`bash -c codex`） | `ARGSPAN.quoted=0` | 與 quoted 形式**同樣**遞迴（原提案漏此欄，`GROK-R17-P0-01`） |
| 8 | 遞迴深度上限 3 | `CMD.depth`／`LEXERR:depth_exceeded` | 逾限 fail-closed |
| 9 | 跳脫引號不終止 span | 掃描器內部狀態 | 無法確定 span 邊界 ⇒ `LEXERR` |
| 10 | heredoc span 界定（①～⑦） | `HEREDOC` | `status=unparsable` ⇒ fail-closed；`ok` ⇒ body 不產 `CMD` |
| 11 | executor 名單＝`governance_families.json` | `CMD.word1_decoded` | 熱路徑寫死＋測試釘死 == SoT |

🔴 **自我豁免述詞（E-1 的修法，`COMPOSER-R17-P2-01` 指出原提案語意不足）**：

```
豁免 ⟺ CMDCOUNT.n == 1
      ∧ 該唯一 CMD 的 depth == 0
      ∧ ( word1_decoded 為 gate 腳本路徑
          ∨ (word1_decoded ∈ {bash,sh,zsh} ∧ 其第二個 word 正規化後為 gate 腳本路徑) )
      ∧ 無任何 LEXERR
```

⚠️ 原提案只寫「總數 == 1 且 token 為 gate 腳本」，**對 `bash scripts/gate.sh …` 不成立**
（第一個 word 是 `bash`）。

---

## §P Phase 與依賴

**Phase 1 — 契約定案（不寫產品碼）**

**Task 1.1 — 事件契約定稿並逐條對照 11 契約**
- 產出：§B.2 事件表 ＋ §B.3 對照表定版。依賴：無。
- **存活至**：Phase 3（本 SPEC 為 Phase 3 實作的唯一契約來源，不被覆寫）。
- **覆蓋風險**：Phase 2 原型若證明某欄位不可實作，**本表須回頭修訂並重審**，不得於實作端悄悄偏離。
- **驗證**：§B.3 對照表 **11 列全部非空**，每列「由哪些事件導出」欄須指名 **≥1 個** §B.2 事件；
  三家報告各自逐列標記 `可/不可`，三家 `可` 的列數須 **== 11**；任一家標 `不可` 即本 Task 未完成。
- **邊界**：只定義**輸出什麼**，不定義**怎麼實作**（awk/sed 選型屬 Task 2.1）。
- **不可做**：不得新增 Task 2.0 以外的契約；不得刪減既有 11 條。

**Task 1.2 — 自我豁免述詞定稿**
- 產出：§B.3 末的述詞定義（含 `bash scripts/gate.sh …` 形式）。依賴：Task 1.1。
- **存活至**：Phase 3。
- **覆蓋風險**：Phase 3 實作可能發現述詞與既有 TN 語料衝突 ⇒ 須回頭修訂述詞，**不得改語料**。
- **驗證**：三樁合法自呼叫 rc=0 ＋ 三樁繞道變體 rc=2（含換行形式）。
- **邊界**：只管「整條是否為 gate 自呼叫」，不管 gate 自身的參數合法性。
- **不可做**：**禁用子字串比對**（B3 的萬用繞道成因）。

**Phase 2 — 原型與差分（`/tmp`，不寫入 repo）**

**Task 2.1 — 掃描器原型**
- 產出：`/tmp` 內 `_gate_lex_scan` 原型，實作 §B.1／§B.2。依賴：Phase 1 全部。
- **存活至**：Phase 3 起（原型碼經驗證後移入 repo；**原型檔本身不保留**）。
- **覆蓋風險**：Task 3.1 會以此為基礎改寫並**取代**現行 `_gate_lex.sh` 對應函式。
- **驗證**：在 `/tmp` 執行 §V.2 之 C-1～C-5，通過項數 **== 5**；
  其中 C-5 效能樁 100K **< 2.0s**、500K **< 5.0s**（`/usr/bin/time -p` 取 real）。
- **邊界**：只做掃描與事件輸出，**不做判定**（判定屬 `gate_check.sh` 消費端）。
- **不可做**：不得寫入 `scripts/`；不得改任何既有測試。

**Task 2.2 — 差分矩陣建置**
- 產出：凍結 snapshot ＋ `phase2_expected_flips` 合成的 old/expected 判定矩陣。
- 依賴：無（可與 2.1 併行）。
- **存活至**：Phase 3 及之後（**作為 golden 長期保留**，B4 亦沿用）。
- **覆蓋風險**：B4 擴充語料 A 時矩陣須同步擴充；**不得刪除既有列**。
- **驗證**：矩陣由腳本產生且可重現（同輸入→同輸出，sha256 一致）；**禁手編**。
- **邊界**：矩陣只涵蓋語料 A＋B 既有條目，不自行發明新案例。
- **不可做**：不得以工作區現況產生矩陣（該版自身帶缺陷）。

**Task 2.3 — 差分驗證**
- 依賴：2.1＋2.2。**出口＝非預期差集為零**。
- **存活至**：Phase 3（驗證腳本移入 repo 作為回歸測試）。
- **覆蓋風險**：Task 3.1 落地後此驗證改為對 repo 版執行，原 `/tmp` 版廢棄。
- **驗證**：非預期差集列數 **== 0**；**mutation**：刻意把矩陣中任一列的期望值反轉後重跑，
  差集列數須 **== 1**（證明比對非恆真）。兩次結果均須貼出。
- **邊界**：只比對判定結果（BLOCK/ALLOW），不比對事件輸出的逐欄位。
- **不可做**：發現差異時**不得調整矩陣使其消失**——須先判定是新版錯還是矩陣錯。

**Phase 3 — 落地**

**Task 3.1 — 寫入 repo 並補測試**
- 產出：`scripts/_gate_lex.sh` 重寫 ＋ §V 全部測試。
- 依賴：Phase 2 全部通過。🔴 **Phase 2 未過不得進入本 Task。**
- **存活至**：長期（本批最終交付物）。
- **覆蓋風險**：B4 會在同檔加 Task 2.2～2.4 的規則；**本批的事件契約須維持向後相容**。
- **驗證**：§V.2 C-1～C-6 全綠 ＋ 全套 `pytest tests/governance -q` rc=0。
- **邊界**：只重寫詞法層與其消費點；不動 debt/audit/stamp 任何路徑。
- **不可做**：不得回復長度截斷放行；不得放寬 latency 門檻；不得改語料 A。

**Task 3.2 — 雙家族 code review**
- 依賴：3.1。出口＝findings ≤3 且 BLOCKING=0 且無 `NEW-DEFECT-INTRODUCED`。
- **存活至**：長期（review 報告與收斂檔入 `handoffs/`）。
- **覆蓋風險**：無後續 Phase 覆寫本 Task 產出；若 B4 推翻設計須另立收斂檔，不得就地改本批結論。
- **驗證**：`bash scripts/reconcile_stamps_check.sh <本批 synth.md>` rc **== 0**（三家 APPROVED）；
  `bash scripts/completeness_check.sh --lock <本批 sources.lock>` rc **== 0**；
  收斂檔 findings 去重後 **≤3** 且 BLOCKING **== 0**。
- **邊界**：只審本批交付物，B4 內容標 `OUT-OF-SCOPE`。
- **不可做**：實作者不得自審。

**與 B4 的關係**：B4 **必須**等本批 Task 3.2 過關。三家一致「禁在 B3 內再補一刀後併 B4」。

## §V 驗證策略與邊界（**差分基準已由 codex 定死，不得自行更改**）

### §V.1 差分驗證

**基準＝凍結 snapshot ＋ `phase2_expected_flips` 合成的不可變 old/expected 判定矩陣。**

| 候選 | 為何**不能**當基準 |
|---|---|
| 工作區未 commit 的 B3 修補 | 自身帶 E-1 fail-open 與 E-2 超線性 |
| pre-Phase2 snapshot 單獨 | 缺 Phase 2 的正確新行為 |

**通過條件＝非預期差集為零。**

### §C.2 獨立測試（不靠差分涵蓋）

| # | 項目 | 通過條件 |
|---|---|---|
| C-1 | 11 契約各 TP＋TN（≥22 條進語料 B） | 全綠；每條附 mutation |
| C-2 | 原型③ 26 條 parity | 新舊逐條相同，差異須具名 |
| C-3 | 11 條 mutation | 每條 revert 修法後**須轉紅** |
| C-4 | E-1 回歸樁 | `bash scripts/gate.sh\ncodex exec hi` → rc=**2**；三樁合法自呼叫 → rc=**0** |
| C-5 | E-2 效能 | 引號內 100K → **<2s**；500K → **<5s**；4MB → **有界且不 fail-open** |
| C-6 | latency canary | `test_gate_check_latency_under_100ms` rc=0，**門檻不得放寬** |

### §C.3 分階段落地

**①～④全部通過才准寫入 repo**；原型階段一律在 `/tmp` 進行。

---

## §D 已知風險（主委承認未查證）

> <!-- claim-context: discussion -->
> 1. **awk 能否真正 O(1) 記憶體串流**——bash 3.2＋macOS awk 的限制主委未查證。
> 2. **`PATHWORD` 與 `CMD` 的產生順序**——路徑正規化發生在比對前或後，主委未定義清楚。
> 3. **`ARGSPAN` 與 `HEREDOC` 重疊時的優先序**（`bash -c "cat <<EOF"`）主委未定義。
> 4. **`phase2_expected_flips` 本身由抽取器產生**——它可信嗎？若抽取器有漏，基準就有漏。

## §R 回退

| 階段 | 回退方式 | 代價 |
|---|---|---|
| Phase 1／2（`/tmp`） | 直接棄置原型；repo 未變動 | 零 |
| Phase 3 落地後 | `git revert <落地 commit>` | 重開 E-1／E-2；**但不會重開 B3 的三條原始 fail-open**（那三條在暫緩的工作區修補內，未 commit） |

🔴 **回退的既有障礙（本批開工前須先解）**：工作區現有**未 commit 的 B3 修補**，
內含三條原始 fail-open 的修法。Phase 3 落地前必須先決定它的去向——
**併入本批一起落地**（推薦：本批本就要重寫同一檔）或**先獨立 commit**。
現況「長期不 commit」會使回退基準模糊，屬 `RISK-HIT: c` 的具體來源。

## §N N/A 登記

| 項目 | 判定 | 理由 |
|---|---|---|
| §0.A 數值影響 | **N/A** | 純詞法判定層；不觸 `momentum/`、不觸 `data_cache/`、無浮點運算 |
| ML／回測正確性（風險 d） | **N/A** | 不涉特徵、標籤、切分或回測路徑 |
| 前端／API 變更 | **N/A** | 本批不動 `api/`、`frontend/` |
| 資料遷移 | **N/A** | 無持久化格式變更；`phase2_expected_flips` 為既有格式 |
| 效能基準（`l65_benchmark`） | **N/A** | 該 CI 已於 2026-07-26 刪除；本批效能以 §V.2 C-5 自帶樁量測 |

## §G Golden 狀態

**filled** — 差分基準即為 golden：凍結 snapshot ＋ `phase2_expected_flips`，
非預期差集為零。golden 檔不得於本批修改。
