
# B3 review 收斂戳記（**修補派工前最後一道**）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260805-govb0-b3-review/synth.md

## 任務

複核該檔**群集／處置段**是否忠實反映本輪 findings，確認無誤後
**append 一行 RECONCILE-STAMP** 到 `## 戳記` 區段。

來源：codex 5 條 ＋ composer 2 條 ＝ 7 條，去重後群集為 `C1`～`C6`。

## 🔴 首要攻擊標的：主委降級了 codex 的一條 BLOCKING

`CODEX-R1-P1-01`（雙引號內 `$()`／反引號命令替換被放行）原判 **[BLOCKING]**。
主委在群集表把它改判為「**既有缺陷，非 B3 回歸**」，理由是實跑對照顯示 pre-Phase2 snapshot
**同樣放行**（舊 rc=0、新 rc=0），不符 brief 判準「舊版擋、新版放行且確為真派工者一律 BLOCKING」。

🔴 **這是主委單方面下修委員判定，必須被獨立驗證。** 請攻：

| # | 要驗什麼 | 若主委錯的後果 |
|---|---|---|
| A1 | **獨立實跑**該 payload 對 `tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot` 取 rc。真的是 0 嗎？ | 主委在弱化 finding ⇒ **拒絕蓋章** |
| A2 | 主委的探針是否**忠實**於 codex 原文？codex 同時列了 `$()` 與反引號兩種形式，**主委只測了 `$()`**——反引號形式在舊版是否也放行？ | 抽樣不完整導致結論失真 |
| A3 | 即使「非 B3 回歸」成立，判準本身是否該被質疑？B3 的 Task 2.1 就叫「引號感知」，引號內的 `$()` **會執行**、不是字面字串 ⇒ 是否應視為 B3 **交付不完整**而非既有缺陷？ | 歸屬影響後續 review 嚴格度 |

**注意處置未變**：C3 仍列「本批一併修」，優先度沒降。爭點**只在歸屬**，
但歸屬會進統計、影響「B3 引入幾個洞」的判斷，故不可含混。

## 逐條歸戶核對（**不是形式蓋章**）

```
C1 ← CODEX-R1-P1-03 ＋ COMPOSER-R12-P0-01    （8KiB 截斷，兩家獨立同結論）
C2 ← CODEX-R1-P1-02                          （引號 env 賦值前綴）
C3 ← CODEX-R1-P1-01                          （引號內命令替換；見上方爭點）
C4 ← CODEX-R2-P2-04                          （reverse-1 mutation 恆真）
C5 ← COMPOSER-R12-P1-01                      （抽取器未涵蓋絕對態敘述）
C6 ← CODEX-R2-P2-05                          （多 heredoc 第二 body 誤擋）
```

🔴 **請逐條核對 ID 對應**。本 epic 主委已犯 **7 次** ID 歸錯或對調，
兩道機檢（`completeness_check --lock`、主委自檢）對「錯位」**皆無感**，
只有你們的語意複核抓得到。

## 其他要判的

| # | 問題 |
|---|---|
| B1 | `C6`（多 heredoc 誤擋，MINOR）順延 B4 是否合理？主委理由＝方向為 fail-closed 不影響安全，且 B4 本就要動同一檔。**這是「95% 解就收」還是漏修**？ |
| B2 | `C1` 採 composer 首選（取消截斷改流式掃描）而非 codex 的「超長 fail-closed」——**流式掃描有無效能風險**？委員 prompt 可達數十 KB |
| B3 | 出場判準核算：去重後 6 群（brief 上限 5）、BLOCKING 2。**這個計數對嗎**？ |

## 不受理範圍（標 `OUT-OF-SCOPE`）

1. 重開 SPEC／TODO 設計裁決。
2. B4 以後的 Task 內容。
3. `audit.log` 大小／封存／latency（封存已於 `fd6dc77` 撤回）。
4. 措辭／命名／可讀性。

## 戳記格式（**逐字**，單獨一行，**不是 `## ` 標題**）

```
RECONCILE-STAMP: <你的家族名> APPROVED 2026-08-05 sha256:f9c4e0ee67936ffaddd6617eb4428d4bc5702cea884751eb5bde6d3170f33bf5 task:<派工注入給你的 task-id>
```

- `sha256` **逐字照抄上方**；`task:` **逐字使用派工注入給你的 task-id**。
- **只 append 到 `## 戳記` 區段之後**，**不得改動該檔任何其他位元組**（附錄為 byte-faithful 委員原文）。
- **不同意就不要蓋**，但仍須交產出說明理由，不要留空檔。

## 硬性要求

1. **只准動該 synth.md 的 `## 戳記` 區段**，其餘逐位元組不變。
2. **禁改碼、禁改測試**。本輪只複核收斂，不修 C1–C6。
3. **rc 一律直接取，禁經 pipe**。
4. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**——
   本輪前一位委員違反此條（自陳誤跑腳本後用 `git checkout --` 還原），已具名記錄。
   **誤動檔案請回報，不要自行還原。**
5. 不要 commit、不要 push；**禁碰 `data_cache/`**。
6. **驗收＝狀態，不是 rc**：貼出下列完整 stdout 與 rc——
   `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-b3-review/synth.md`／
   `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-b3-review/sources.lock`（須 0）。

## 產出

改了哪一行（貼 diff）、兩支檢查器完整 stdout 與 rc、逐條歸戶確認、
**A1–A3 對主委降級動作的獨立驗證**（含實跑 rc）、B1–B3 的判斷。
收尾清 /tmp workdir（保留 claude-501）。
