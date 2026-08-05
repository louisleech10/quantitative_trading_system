
# 第 0 批實作 — B0/B1 補修 ＋ B2

brief-kind: impl

**唯一權威來源**：`docs/GOVB0_FRICTION_TODO.md`（Internal Frozen）
**前置狀態**：B0＋B1 已完成並經雙家族 code review 通過（BLOCKING=0），commit `596fcb4`；
測試基線 `VERIFY:govb0-b0b1-test-count`（**真跑** `pytest tests/governance` → `715 passed in 221.20s`）。

## §0 前提宣告

**已查證**：

- fact-verified: B0 snapshot 時序正確 —— composer 實跑
  `git show 596fcb4^:scripts/gate_check.sh` 的 sha256 **==** snapshot **==** sidecar（`871258c9…1606a`）。
- fact-verified: B0＋B1 雙家族 review 通過 —— composer `FINDINGS_COUNT: 0`；codex 2 條皆非阻塞、`BLOCKING=0`。
- fact-verified: 既有測試檔零改動 —— 主委實跑 `git diff HEAD~1 --name-only -- tests/governance/` 排除新檔後為空。

**假設**（你若發現不成立，**停下來回報，不要硬做**）：

- assumed: `scripts/cx_run.sh` 的 prompt 組裝在 `_prepare_and_run()`（約 `:501-513`），
  `brief-kind` 已由 `_bk`（約 `:46`）提供。🔴 **實作者已於 R9 標明「`cx_run.sh` 行號可能漂」，
  動工前務必自行 `grep -n` 複驗，不得照抄行號。**
- assumed: `brief_conformance_check.sh --emit` 輸出的第 1 行即 `brief-kind`。動工前自行複驗。

---

## 第一部分（**先做**）：補修 B0/B1 的兩條 review finding

兩條皆非阻塞，但**都弱化了 B1 的核心保證**，故在 B2 之前先修。

### 修 1 — `CODEX-R10-P1-01`：語料 A 覆蓋不足

**問題**：`TEST-0.1-INVARIANCE` 用的語料 A **未覆蓋** 現行 `gate_check.sh` 的
gated `Write` artifact 分支，也未覆蓋 token／open-debt 分支。
⇒ 「判定行為不變」**只驗到部分分支**，未覆蓋者等於無保護。

**修法**：擴充 `tests/governance/fixtures/gate_invariance_corpus.txt`，
使其**涵蓋現行判定的所有分支**。
🔴 **不得憑空造**：每條標明出處（哪個分支、對應 `gate_check.sh` 哪一段）。
🔴 **語料 A 擴充後仍須通過 `TEST-0.1-INVARIANCE`**——若擴充後 diff 非空，
**代表 B1 真的改變了某分支的判定，屬 BLOCKING，須停下回報**，不得調整語料使其變綠。

**驗收**：語料 A 條數增加；`TEST-0.1-INVARIANCE` 仍 rc=0；
新增一條狀態斷言證明語料 A 覆蓋了 `match_rule` 封閉集合中**每一個**值至少一次
（以 `jq` 從 `scripts/audit_events.json` 讀該集合為斷言來源，非硬編）。

### 修 2 — `CODEX-R10-P2-02`：欄位斷言過弱

**問題**：新測試只驗 `cmd_head` 非空、hash 為 64 字元，
**未驗** `cmd_sha256 == sha256(完整 command)`，也未驗 `cmd_head == 前 512 bytes`。

**修法**：改為**值相等**斷言——測試自行對已知輸入算 sha256 與切前 512 bytes，與 audit 實際欄位比對。
**須含 mutation**：把 `cmd_sha256` 改成算「截斷後的字串」而非完整指令 ⇒ 該斷言**必須轉紅**。

**驗收**：兩條值相等斷言 rc=0；mutation 實跑 rc 貼出。

---

## 第二部分：B2 — Task 1.1（`cx_run.sh` prompt 依 `brief-kind` 分支）

**完整規格見 TODO 的「Phase 1 / Task 1.1」段，逐條照做。** 重點：

1. **沿用既有 `${_bk}`，禁再寫一份 parser**（出生事故：`committee_run.sh` 曾有第二份 parser 造成孤兒債）。
2. `brief-kind ∈ {stamp, closure}` → 保留 RECONCILE-STAMP 注入句並**補格式說明**；
   格式的單一真相源＝`cx_run.sh:345` 的正則，測試須斷言 prompt 說明與該正則**機械一致**
   （同一個合法戳記樣本同時通過兩者）。
3. 其餘 `brief-kind` → **完全不提** RECONCILE-STAMP。
4. **unknown `brief-kind` → fail-closed 拒派**（不得有第三種行為）。

**🔴 `TEST-1.1-UNKNOWN-NOSIDEEFFECT` 是本 Task 最重要的斷言**：
被拒後須同時滿足四項——①`.claude/gate/` 無新 token 檔且 mtime 未更新
②`audit.log` 行數前後相等 ③`debt_ledger --has-open` 的 rc 與呼叫前相同
④`handoffs/` 未產生任何新檔。**四項缺一即不算通過。**

**誠實邊界（TODO 已載明，不得宣稱超出）**：本 Task 只保證 **harness 端不再誘導**；
**無法保證委員不自行寫出 `## RECONCILE-STAMP` 標題**。
**驗收不得以「委員這次沒寫」為斷言**（不可重現）。

---

## 🔴 硬性禁令（違反即整批退回）

1. **禁碰 `data_cache/`**（有不可復原的真實 kline）。
2. **禁 `git checkout`／`git restore`／`git clean`**；不要 commit、不要 push。
3. **禁修改既有測試斷言**；**禁恆真斷言**；**禁改檢查器或加排除清單換綠燈**。
4. **測試基線只增不減**（B0+B1 後為 715；`VERIFY:govb0-b0b1-test-count`，**真跑**確認）。
   任何既有測試轉紅**須具名說明並停下回報**。
5. **不做 B3 以後的任何 Task**（`2.*`／`3.*` 一律不碰）。
6. **bash 3.2 相容**：禁 `declare -A`、禁 `flock`；**`rc` 一律直接取，禁經 pipe**。
7. **hot path 不新增 log**。
8. 讀 audit／log 一律 `LC_ALL=C grep -a`，**禁 `export LC_ALL`**。

## 收尾必做

1. `pytest tests/governance -q`（**丟背景，導檔再取尾**）——貼總數與 rc。
2. `bash scripts/restore_golden_inventory.sh` 之後貼 `git status --short tests/golden/`（須為空）
   ——**不得以該腳本 rc 為證**。
3. 每個 mutation **貼實跑 rc**。
4. 清 /tmp workdir（**保留 `/private/tmp/claude-501`**）。

## 產出

`git diff --stat`、語料 A 擴充後的條數與覆蓋證明、兩條值相等斷言的實跑、
`TEST-1.1-*` 各條實跑結果（尤其四項無副作用）、mutation 實跑 rc、
`pytest tests/governance -q` 總數、`git status --short tests/golden/` 輸出。

🔴 **任何一步做不到或發現 TODO 有誤，停下來回報，不要自行改 TODO**（Internal Frozen，
修訂須走 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE.md` 的延伸檔程序）。
