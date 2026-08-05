# Reconcile — 20260805-govb0-b3-fix2review

**來源** 20260805-govb0-b3-fix2review-codex.md, 20260805-govb0-b3-fix2review-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 不可合併。**epic 收斂斷路器觸發** —— 停止由主委發修補派工，
C1（oversize 掃描）設計交委員會重審。B3 不進 B4。

### 🔴 兩家最大分歧

| | codex | composer |
|---|---|---|
| findings | **2**（BLOCKING 2） | **0** |
| `NEW-DEFECT-INTRODUCED` | **2** | 無 |
| Verdict | 不通過，觸發斷路器 | 可進 B4 |

**主委獨立實跑裁定：codex 的兩條 findings 皆為真，composer 兩條皆漏。**

### 主委對 codex 標籤的一項更正（實跑對照 pre-Phase2 snapshot）

| 探針 | 舊 rc | 新 rc | codex 標籤 | 主委裁定 |
|---|---|---|---|---|
| `bash scripts/gate.sh\ncodex exec hi`（換行） | **0** | **0** | NEW-DEFECT | ❌ **非新引入**——修法只關分號形式，換行形式未關＝**修不完整** |
| `bash scripts/gate_check.sh\ngrok -m x -p y` | **0** | **0** | NEW-DEFECT | ❌ 同上 |
| 引號內 4MB | rc=0，**1s** | rc=124，**30s 逾時** | NEW-DEFECT | ✅ **確為新引入** |

⇒ `NEW-DEFECT-INTRODUCED` 實際為 **1** 條，非 2。但**斷路器仍觸發**：
R1 引入 D-2（誤擋摩擦）、R2 引入 quadratic hang ⇒ **「修補引入新缺口」連續兩輪**，
符合本 epic 於 `20260805-govb0-b3-fixreview/synth.md` 預先寫定的觸發條件。

### 主委實測的耗時曲線（判定即時風險用）

`echo "<n 個字元>"` 經現行工作區 `gate_check.sh`：

| n | 耗時 |
|---|---|
| 1,000 | 0.06s |
| 10,000 | 0.09s |
| 50,000 | 0.42s |
| 100,000 | 1.32s |
| 500,000 | **29.92s** |

⇒ **二次方成長**。主委實際指令長度 <10K（0.09s）⇒ **非即時風險**，
但 `gate_check.sh` 為 live PreToolUse hook，**具名列為已知危害**。

### 群集

| # | 群集 | 來源 ID | 級別 | 處置 |
|---|---|---|---|---|
| **E-1** | self-gate 豁免僅擋分號形式，**換行形式仍放行** | `CODEX-R15-P0-01` | **BLOCKING**（既有缺陷，修不完整） | **交委員會重審**：豁免判定須跨行狀態機，確認整體為單一簡單命令 |
| **E-2** | 移除 8192 硬頂後，引號／特殊字元大輸入走非 O(n) 路徑，4MB 逾時 | `CODEX-R15-P0-02` | **BLOCKING**（**新引入**） | **交委員會重審 C1 設計**。不得再由主委單發修補派工 |
| **E-3** | `test_21_d2_harmless_oversize_allows` 對 C1 hard-cap mutant 不轉紅（無鑑別力） | `CODEX-R15-P0-02` 附屬 | MAJOR | 併入 E-2 重審 |

### 🔴 審查品質記錄（composer）

composer 本輪交 `FINDINGS_COUNT: 0`、判 `可進 B4`，**兩條可重現的 BLOCKING 全漏**。
主委以獨立探針於數分鐘內重現兩條。
⇒ 本 epic 第二次出現 composer 判定顯著寬於 codex（前次為 `M-1`／`M-2` 判 non-blocking）。
**具名記錄，供後續選層參考**；不影響本輪結論（結論採 codex）。

### 出場判準核算（本輪）

findings 去重後 **3** 群（≤3 ✓）｜BLOCKING **2**（需 0 ✗）｜`NEW-DEFECT-INTRODUCED` **1**（需 0 ✗）
⇒ **不通過**，且觸發斷路器。

### 銷帳處置

`completeness_check` 無法通過——composer 零 findings 之報告抽不到 heading ID，
判 vacuous（`票 B-38`，本日第 5 次）。本輪以 `--abandon` 具名棄輪，
**實質產出為本收斂檔**。⇒ `票 B-38` 已由「儀式成本」升級為**會擋住斷路器紀錄**的缺陷。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R15-P0-01
**斷言**: D-1 的 self-gate 豁免仍以首行 grep 命中，跨行後的真派工可被放行。
**碼證**: `scripts/_gate_lex.sh:351-360`；`bash scripts/gate_check.sh` 對 `bash scripts/gate.sh\ncodex exec hi` 與 `bash scripts/gate_check.sh\ngrok -m x -p y` 均實測 `rc=0`；分號同型向量 `rc=2`。RECHECK 可用 `jq -nc --arg c $'bash scripts/gate.sh\ncodex exec hi' '{tool_name:"Bash",tool_input:{command:$c}}'` 產 payload 後以 here-string 直接呼叫 gate。
**來源摘要**: `scripts/_gate_lex.sh#debe1484a7e5` / `scripts/gate_check.sh#b454a55ea513`
[BLOCKING|P0] 信心度=High；`NEW-DEFECT-INTRODUCED`。`grep` 逐行處理使 `\n` 未被 `[... ]` 檢查，後續正則又非全字串錨定；修法方向是以跨行狀態機確認整體單一簡單命令後才豁免。
## CODEX-R15-P0-02
**斷言**: D-2 移除 8192 硬頂後，含引號/特殊字元的 4MB 路徑仍非 O(n)，且對應 harmless-oversize 測試缺真 mutation 牙齒。
**碼證**: `scripts/_gate_lex.sh:76-81,143-180,382-390` 以 awk 全量字串反覆拼接；4,000,057-byte 合法 JSON `echo "<4MB>"` 經 `timeout 30 ... bash scripts/gate_check.sh < file` 實測 `rc=124`、`real 30.01s`；plain 4MB tail 向量則 `4,000,063B rc=2 real 5.65s`。C1 hard-cap mutant 對 `echo`+8200B 實測 `rc=0`，所以 `test_21_d2_harmless_oversize_allows` 仍會綠。
**來源摘要**: `scripts/_gate_lex.sh#debe1484a7e5` / `tests/governance/test_gate_decision.py#5d5fe4fb59e2`
[BLOCKING|P0] 信心度=High；`NEW-DEFECT-INTRODUCED`。原本前綴截斷遮住此 quadratic path，現行修法把任意長特殊輸入送入非 O(n) 前處理；需重審 C1 設計並補 quoted/特殊字元大輸入與 harmless case 的逐測試 mutation。

## 戳記

<!-- 委員 append RECONCILE-STAMP 行於此區段之後 -->
RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:58e7bc2715da9c63a8ef118ca2f04cd46165afb76cc0ab90cef96d6dc6da6cc7 task:GOVB0-BREAKER-STAMP
RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:58e7bc2715da9c63a8ef118ca2f04cd46165afb76cc0ab90cef96d6dc6da6cc7 task:GOVB0-BREAKER-STAMP
RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:58e7bc2715da9c63a8ef118ca2f04cd46165afb76cc0ab90cef96d6dc6da6cc7 task:GOVB0-BREAKER-STAMP
