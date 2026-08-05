# Reconcile — 20260805-govb0-b3-fixreview

**來源** 20260805-govb0-b3-fixreview-codex.md, 20260805-govb0-b3-fixreview-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

Verdict: 需修補後合併。四條全數本批修，**不順延 B4**；R2 為確認輪，禁新增 scope。

### 兩家裁決分歧與裁定

| 群 | codex | composer | 主委裁定 |
|---|---|---|---|
| D-1 M-1 繞道 | **BLOCKING** | MAJOR，順延 B4 | **本批修**（採較嚴） |
| D-2 M-2 誤擋 | **BLOCKING** | MAJOR，視為過渡 | **本批修**（採較嚴） |

**兩家對「是否為真問題」完全一致**，分歧只在嚴重度與時程。裁定理由：

1. **D-2 是本批新引入的**，不是既有債。使用者定死「面向未來，不溯及既往」是針對**舊**錯誤；
   本批自己製造的缺口不適用該原則——把 fail-open 換成未量測的 fail-closed，是**平移**不是修復。
2. **D-1 落在本批正在加固的同一機制內**。第 0 批的存在理由就是「工具自己擋你、或該擋的沒擋」，
   而 D-1 正是「該擋的沒擋」的最嚴重形態：**一個子字串即可整條放行**。
   在加固它的同一批裡發現它卻順延，等於本批的驗收標準自相矛盾。
3. 兩條修法皆**有界**（各集中在單一函式），不觸發膨脹升級 5 訊號。

🔴 **收斂趨勢警訊（具名記錄）**：本批 R1 找到 3 條 fail-open，修補後 R2 出現 **1 條由修補新引入**
（D-2）。屬「修補引入新缺口」型態。⇒ **R2 定為確認輪**：只驗這四條是否關閉，
**禁新增 scope**；若 R2 再出現「修補引入新缺口」，即觸發 epic 收斂斷路器，停手開委員會重審 C1 設計。

### 群集

| # | 群集 | 來源 ID | 級別 | 處置 |
|---|---|---|---|---|
| **D-1** | `gate_check.sh` 自我排除為子字串比對 ⇒ 任意位置嵌入 `scripts/gate.sh` 即整條 ALLOW | `CODEX-R14-P0-01`＋`COMPOSER-R14-P1-01`（兩家獨立同結論；主委 M-1 亦獨立重現） | **BLOCKING** | **本批修**。收斂為「僅當該字串位於**命令位置**、且整條為 gate invocation 時才排除」 |
| **D-2** | C1 的 `>8192 一律 fail-closed` 誤擋無害超長指令 | `CODEX-R14-P0-02`＋`COMPOSER-R14-P1-02`（同上；主委 M-2 亦獨立重現） | **BLOCKING** | **本批修**。採 O(n) 流式掃描取代長度上限；**禁**以子字串型逃生口規避（會與 D-1 疊加成新繞道） |
| **D-3** | C4 新測試非真 mutation——僅於測試內建 poisoned list，未複製並執行 altered subject | `CODEX-R14-P2-03` | MAJOR | **本批修**。改為隔離副本移除 C4 修法後實跑，須 rc 由 pass 轉 fail 並貼前後對照 |
| **D-4** | C5 決策以 HTML 註解就地寫入 Internal Frozen TODO | `CODEX-R14-P2-04`＋`COMPOSER-R14-P2-01` | MAJOR | **本批修**。移至延伸檔（使用者定死「修訂凍結文件走延伸檔非就地改」）；TODO 還原為未改 |

### 主委自身的一項更正（具名記錄）

主委在 R2 派工前的回報中稱「C4 恆真斷言已被真突變測試取代」，**該敘述不成立**——
主委實際檢視的是 C5 的測試（該條確為真突變：複製原始碼→移除修法→斷言行為消失），
未逐條檢視 C4。`CODEX-R14-P2-03` 抓到此點。
⇒ 同型錯誤：**驗了 A 就當作 B 也成立**（本 epic 第 4 次）。

### 一項有價值的旁證（不列 finding）

codex 複跑 latency：**首次 108.8／128.2ms 未過**，第二次 72.8／72.1ms 通過，門檻未動。
⇒ 獨立佐證該測試確有冷啟抖動，與 `fd6dc77` 撤回 audit 封存時的判斷一致。

### 出場判準核算（本輪）

findings 去重後 **4** 群（≤5 ✓）｜BLOCKING **2**（需 0 ✗）⇒ **未通過**，須 R2 確認輪。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R14-P0-01
**斷言**: `gate(_check)?.sh` 任意位置子字串排除是真繞道，不能接受為「擋意外不防蓄意」邊界；應只豁免整條 gate invocation。
**碼證**: `scripts/gate_check.sh:211-216`；無 token 獨立 probe `codex exec x; echo scripts/gate.sh`、comment、長前綴 chain、`scripts/gate_check.sh` 均 `rc=0`，裸 `codex exec x` `rc=2`。
**來源摘要**: scripts/gate_check.sh#c680a558d851；[BLOCKING] 信心度=High；修法建議為解析完整命令段，僅整條命令為 gate invocation 時排除。
## CODEX-R14-P0-02
**斷言**: `_max_lex=8192` 對所有超長命令 blanket fail-closed，沒有量測或規格依據，將 B-15 的誤擋摩擦換成未量測的新誤擋；需先修正。
**碼證**: `_gate_lex.sh:355,362-366`；`echo`+8200 字元新版 `rc=2`、pre-Phase2 `rc=0`；4,000,048-byte stdin `rc=2`、3,911ms；audit 718 個 gate_deny JSON 僅 51 有 cmd_head、667 無完整 command，無法導出發生率。
**來源摘要**: scripts/_gate_lex.sh#f54c3baad924；docs/GOVB0_FRICTION_TODO.md#37d1c0067780；[BLOCKING] 信心度=High；修法建議為完整輸入的 O(n) 掃描，無一般逃生口。
## CODEX-R14-P2-03
**斷言**: C4 測試不是 brief 要求的 true mutation；它只在同一測試內建立 `poisoned` Python list，未複製/執行 altered subject，因此移除新增斷言可維持綠燈。
**碼證**: `test_gate_deny_fields.py:590-654` 只有 `_reverse1_holds()`、list 注入與 `pytest.raises`；targeted test `1 passed`，沒有 before/after altered-test rc 對照。
**來源摘要**: tests/governance/test_gate_deny_fields.py#03bbf7630df2；[MAJOR/non-blocking] 信心度=High；修法建議為隔離副本移除 C4 修法並實跑同一驗收測試，確認 rc 由 pass 轉 fail。
## CODEX-R14-P2-04
**斷言**: 實作端就地改寫 `Internal Frozen` TODO 違反文件自身修訂程序；C5 選 (a) 並非 brief 允許的選項。
**碼證**: `docs/GOVB0_FRICTION_TODO.md:3,10-11` 明定 Frozen 且須走延伸檔不得就地改；工作區 diff 在 line 338 新增 HTML comment。
**來源摘要**: docs/GOVB0_FRICTION_TODO.md#37d1c0067780；[MAJOR/non-blocking] 信心度=High；修法建議為把決策記錄移至 amendment/extension artifact，TODO 就地變更由主委另行處置。
## COMPOSER-R14-P1-01

**斷言**: `gate_check.sh:216` 以子字串 `grep -Eq 'scripts/gate(_check)?\.sh'` 自我排除，使含真派工之指令在任意位置嵌入該字串即整條 **ALLOW（rc=0）**——為可重現之蓄意繞道。

**碼證**:
- `scripts/gate_check.sh:214-217`：dispatch 命中後 `grep` 全 cmd，非命令位置語法
- RECHECK（`GATE_DIR_OVERRIDE=/tmp/govb0-b3-fixreview-composer/gate`）：
  - `codex exec x` → **rc=2**
  - `codex exec x; echo scripts/gate.sh` → **rc=0**
  - `codex exec x  # scripts/gate.sh` → **rc=0**
  - `x×8200; scripts/gate.sh; codex exec hi` → **rc=0**（與 C1 fail-closed 疊加仍被繞過）

**來源摘要**: `scripts/gate_check.sh#c680a558d851`

[MAJOR] 信心度=High。真繞道；**非 B3 引入**（主委與本 reviewer 新舊 rc 同）。設計意圖似為放行 gate 自身呼叫，但實作過寬。  
**修法**: 僅在**命令位置**匹配 gate 腳本（例如 `(^|[;&|][[:space:]]*)…scripts/gate(_check)?\.sh`），或白名單僅允許 `bash scripts/gate.sh dispatch|artifact` 等固定前綴；須補 TP/TN 語料 B + mutation。建議 **B4** 與 Task 2.2–2.4 同批收斂。  
**風險**: 收斂過嚴可能誤擋合法 `bash scripts/gate_check.sh` 勘查——須對照既有 TN 語料。

---

## COMPOSER-R14-P1-02

**斷言**: C1「>8192 字元一律 fail-closed」使**無派工字樣**之超長無害指令被誤擋，與摩擦止血史（票 B-15）方向衝突；8192 僅繼承舊 `head -c` 截斷常數，**未見量測或文件化依據**。

**碼證**:
- `scripts/_gate_lex.sh:355-366`：`#cmd > 8192` → `_GATE_LEX_OVERSIZE=1; return 0`（BLOCK）
- RECHECK：`echo` + `a×8200`（總長 >8192）→ **rc=2**；主委假設「舊 rc=0」與本 reviewer 一致
- `audit.log` 可解析之 `gate_deny.cmd_head`（n=51）：**max=512, p95=468, gt8192=0**——僅能證明記錄欄位未見超長，**不能**證明歷史完整 cmd 長度分布（欄位本身截斷）
- C1-c：`y×4000000` → **rc=2, dur_s=3.944**（有界，非 fail-open）

**來源摘要**: `scripts/_gate_lex.sh#f54c3baad924`

[MAJOR] 信心度=High。安全 fail-open 已關（C1-a rc=2 ✓），但摩擦缺口**未量測**即上線。  
**修法（擇一，建議 B4）**:
1. **首選**（對齊 R12 reconcile）：取消字元長硬頂，改 O(n) 流式/分塊掃描全 cmd（composer 首選方案未實作）。
2. **次選**：僅在 `len>8192` **且** 含 executor 字樣時 fail-closed；純資料/echo 超長放行——須證明無尾端派工漏網。
3. **維持現法**：須文件化 8192 依據 + 摩擦取樣；任何「逃生口」不得復活 M-1 型子字串繞道。

**M-2 子題**:
| 子題 | 判定 |
|---|---|
| M-2a | 8192 = 舊 `_max_lex` 截斷值；audit `cmd_head` 無 >8192 樣本，**完整 cmd 分布未驗** |
| M-2b | 更精準判準見上；4MB 路徑 3.9s 可接受（僅超長觸發，正常 PreToolUse 不經此路） |
| M-2c | 逃生口若用子字串 gate 自我排除 → 與 M-1 疊加變新繞道；不建議 |

---

## COMPOSER-R14-P2-01

**斷言**: C5 選 (a) 之決策以 HTML 註解**就地**寫入 Internal Frozen `docs/GOVB0_FRICTION_TODO.md`，違反「修訂凍結文件走延伸檔非就地改」之程序。

**碼證**:
- `docs/GOVB0_FRICTION_TODO.md:338`：`<!-- C5 選 (a)：extract_phase2_expected_flips.py … -->`
- brief 標的 3：原僅允許選修法 (b) 時改 TODO

**來源摘要**: `docs/GOVB0_FRICTION_TODO.md#37d1c0067780`

[MINOR] 信心度=High。不影響 gate 行為或抽取正確性（`--check` rc=0）；屬程序/可追溯性。  
**修法**: 撤回就地註解；改 `docs/GOVB0_FRICTION_TODO.ext.md`（或專案既定延伸檔）記錄 C5 裁決 + sha 指回。

---


## 戳記

<!-- 委員 append RECONCILE-STAMP 行於此區段之後 -->
RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:eea35be5ad843c324be939736cf0f51aae25dc15589d044347f41992b5dc39a3 task:GOVB0-B3-FIXSTAMP
RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:eea35be5ad843c324be939736cf0f51aae25dc15589d044347f41992b5dc39a3 task:GOVB0-B3-FIXSTAMP
RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:eea35be5ad843c324be939736cf0f51aae25dc15589d044347f41992b5dc39a3 task:GOVB0-B3-FIXSTAMP
