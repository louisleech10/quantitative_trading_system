
# 斷路器裁定戳記（**設計重審派工前最後一道**）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-govb0-b3-fix2review/synth.md

## 任務

複核**群集／處置段**是否忠實反映本輪，確認無誤後
**append 一行 RECONCILE-STAMP** 到 `## 戳記` 區段。

本輪特殊：**兩家裁決完全相反**（codex 2 BLOCKING／composer 0 findings 通過），
主委採 codex 並宣告 epic 收斂斷路器觸發。

## 🔴 首要攻擊標的（三項，逐項回答）

### A1 — 主委推翻了 composer 的通過判定

主委以獨立探針重現 codex 兩條 finding，據此判 composer **兩條全漏**。

**請獨立實跑驗證**（勿採信主委轉述）：

| 探針 | 主委宣稱 |
|---|---|
| `bash scripts/gate.sh\ncodex exec hi`（**換行**，非分號） | 現行 rc=0（應 2） |
| `bash scripts/gate_check.sh\ngrok -m x -p y` | 現行 rc=0（應 2） |
| `echo "<500,000 個字元>"` | 現行約 30s（二次方） |

🔴 **composer 請特別回答**：你交 `FINDINGS_COUNT: 0`。
上述三條若屬實，**你為何沒抓到**？是攻擊向量沒涵蓋，還是判定標準不同？
**這關係到後續選層，請據實回答，不要護短也不要過度自責。**

### A2 — 主委更正了 codex 的 `NEW-DEFECT-INTRODUCED` 標籤

codex 標 2 條為新引入。主委對照 pre-Phase2 snapshot 實跑後改判：

| 探針 | 舊 rc | 新 rc | 主委裁定 |
|---|---|---|---|
| 換行繞道（兩條） | **0** | 0 | **非新引入**——修不完整 |
| 引號 4MB | 0（1s） | 124（30s） | **確為新引入** |

**請驗證此對照，並判斷**：「修不完整」與「新引入」的區分是否成立？
codex 若不同意，請說明。

### A3 — 斷路器是否該觸發

主委理由：`NEW-DEFECT-INTRODUCED` 雖僅 1 條（非 codex 說的 2 條），
但 R1 引入 D-2、R2 引入 quadratic hang ⇒ **連續兩輪修補引入新缺口**，
符合預先寫定的觸發條件（`20260805-govb0-b3-fixreview/synth.md`）。

**請判斷**：
| # | 問題 |
|---|---|
| A3a | 觸發條件的解讀是否正確？「連續兩輪」是否成立？ |
| A3b | 停手重審 vs 再修一輪——哪個成本低？**若你認為不該停，請說** |
| A3c | 工作區現有未 commit 修補（三條原始 fail-open 已關，但帶換行繞道與大輸入卡死）——應**保留待重審**、**部分回退**、還是**全部回退**？ |

## 逐條歸戶核對

```
E-1 ← CODEX-R15-P0-01   （換行繞道）
E-2 ← CODEX-R15-P0-02   （引號大輸入非 O(n)）
E-3 ← CODEX-R15-P0-02 附屬（harmless-oversize 測試無鑑別力）
```

composer 本輪零 findings，故無來源 ID。**請確認此歸戶無錯位。**

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-05 sha256:58e7bc2715da9c63a8ef118ca2f04cd46165afb76cc0ab90cef96d6dc6da6cc7 task:<派工注入給你的 task-id>
```

- `sha256` **逐字照抄上方**；`task:` **逐字使用派工注入給你的 task-id**。
- **只 append 到 `## 戳記` 區段之後**，不得改動該檔任何其他位元組。
- **不同意就不要蓋**，但仍須交產出說明理由。

## 不受理範圍（標 `OUT-OF-SCOPE`）

1. 詞法層的**新設計方案**——下一輪（`GATELEX-REDESIGN`）專門處理，本輪只判斷路器。
2. C6、B4 以後的 Task。
3. `audit.log` 封存／瘦身。
4. latency 門檻——併入下一輪。
5. 措辭／命名／可讀性。

## 硬性要求

1. **只准動該 synth.md 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **禁改碼、禁改測試**。
3. **rc 一律直接取，禁經 pipe**。
4. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**；誤動請回報，不要自行還原。
5. 不要 commit、不要 push；**禁碰 `data_cache/`**。
6. ⚠️ 測大輸入請自行加 `timeout`，工作區有已知的卡死路徑。
7. 貼出 `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-b3-fix2review/synth.md` 的完整 stdout 與 rc。

## 產出

改了哪一行（貼 diff）、檢查器 stdout 與 rc、逐條歸戶確認、
**A1–A3 的獨立驗證與判斷**（composer 另答「為何沒抓到」）。
收尾清 /tmp workdir（保留 claude-501）。
