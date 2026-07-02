# 驗收防偽閘 全系統紅隊 — Composer 獨立版

**範圍**: B1–B5 整合系統（commit `abeb9ff`，hooks 已裝）+ Claude 版 `handoffs/20260702-VERIFYGATE-REDTEAM-CLAUDE.md` 全項挑戰。  
**隔離**: temp git repo、`GATE_DIR_OVERRIDE` / `VERIFY_GATE_*`（僅必要時）、`/private/tmp` 與 `/tmp`；**未 commit 攻擊產物**；真實 `.claude/gate/verify_audit.log` 維持 **553 bytes** 不變。  
**事故**: 早期探針曾用 symlink 指到真實 `scripts/verification_claim_check.py` 後覆寫 stub → **已 `git checkout abeb9ff --` 還原**；測試改為 `cp` 副本。

---

## A. 繞過面

### A1 — receipt 洗白（快測掛慢測聲稱）

| 判決 | **HOLDS** |
|------|-----------|
| 場景 | temp repo：`run_with_receipt.py --claim-id wash -- true`（`runtime_class=static_only`）→ HANDOFF 寫 `mutation 慢測 … test_mutation_align 已驗全綠 VERIFY:wash` |
| 證據 | `HANDOFF.md:3: runtime_class 不足: static_only vs mutation` → staged checker **exit=1** |
| 備註 | 無 node-id 時 scope 交集放行，但 **mutation 語意仍被 runtime_class 擋**；非僅 exit0 即過 |

### A2 — SUPERSEDED 洗白

| 判決 | **HOLDS**（SUPERSEDED id 不驗真為設計邊界） |
|------|---------------------------------------------|
| 場景 1 | 紅燈後同段 `已驗全綠 VERIFY:<unrelated> SUPERSEDED:fakeid999` |
| 證據 1 | 紅燈行 `operational claim 缺少 VERIFY/REF/SIGNOFF backing` → **exit=1**；假 SUPERSEDED **不驗 id 真偽** |
| 場景 2 | `SUPERSEDED:old-green … VERIFY:<good>` 格式（B5 測試同款） |
| 證據 2 | 紅燈行仍缺 backing → **exit=1**；supersede 行本身不擋，但**紅燈紀錄仍要處理** |
| 邊界 | SUPERSEDED 標記本身無 receipt 驗真 — 文件已列 tamper-evident 邊界 |

### A3 — fenced / quote / 假歸屬走私

| 判決 | **BROKEN**（PreToolUse 路徑）+ **BOUNDARY**（checker 對引用） |
|------|----------------------------------------------------------------|
| PreToolUse | `file_path=/tmp/.../HANDOFF.md` 而 `git rev-parse` → `/private/tmp/...`：`rel_path` 前綴剝除失敗 → **grep 不匹配 → exit=0 完全跳過掃描** |
| 證據 | `pretooluse exit=0`；同機 `rel_path=/tmp/...` `grep rc=1`；改 `/private/tmp` 一致路徑 → **exit=2** `operational claim 無 backing` |
| checker | `> Codex 檔案寫道：mutation align 已驗全綠` 在 HANDOFF **exit=1**（非 citation 豁免）；fenced 內容單獨未再拆測 |
| 邊界 | 假歸屬**不驗來源檔案** — 與 Claude 預判一致；git hook/CI 可補一部分 |

### A4 — 改非攔截檔（`docs/*.md`）再 include

| 判決 | **BROKEN** |
|------|------------|
| 場景 | `docs/reviews/smuggle.md` `## 已完成` + `FF align mutation 已驗全綠`；HANDOFF 只寫「見 docs/…」 |
| 證據 | pre-commit **exit=0** 成功 commit；`--files docs/reviews/smuggle.md` **exit=0**；pointer-only HANDOFF+docs 同 commit **exit=0** |
| 根因 | `_detect_source_context` → `docs_spec` → `classify_mode` → **discussion 直接放行**（`## 已完成` 不算 operational_result） |
| 對照 | 同文案若寫進 HANDOFF `## 正在做` → checker **exit=1** |

### A5 — audit + receipt 同步竄改

| 判決 | **BOUNDARY**（文件已列，非惡意防護） |
|------|--------------------------------------|
| 證據 | 單改 receipt `exit_code` 未改 audit → `receipt_sha256 不符: …` **exit=1** |
| 邊界 | 同步改 receipt+log+audit 仍可由惡意寫入者完成 — 符合 tamper-evident 誠實邊界 |

### A6 — `GATE_DIR_OVERRIDE` / env 濫用

| 判決 | **HOLDS**（fail-closed） |
|------|--------------------------|
| 證據 | `GATE_DIR_OVERRIDE=/tmp/... bash scripts/gate.sh dispatch` → token 只在 tmp；`gate_check.sh` **硬編碼 `.claude/gate`**，設 env 仍 `[GATE BLOCKED]` **exit=2** |
| 備註 | 逃生口未變成派工繞道；攻擊者無法用 override 讓 hook 讀 tmp token |

### A7 — pending ledger 偽 close

| 判決 | **HOLDS** |
|------|-----------|
| 證據 | 手寫 `fake-close.json` + close event（無 audit）→ `list-open` 仍輸出 open `p1`；HANDOFF 綠宣稱 → `task P0-FF-3 有未結 pending p1` **exit=1** |
| 根因 | `_close_event_valid` 要求 receipt audit 事件 |

### A8 — `git commit --no-verify`

| 判決 | **BOUNDARY**（本地已知洞，CI 後盾） |
|------|-------------------------------------|
| 證據 | temp repo `--no-verify` commit **exit=0**；同 range `--range HEAD~1...HEAD` → `operational claim 缺少 backing` **exit=1** |
| 邊界 | CI workflow 已存在但 **GitHub 尚未實跑**（Claude 原判）；本地 hook 可繞，遠端 range 可抓 |

---

## B. 過嚴 / 卡死面

### B1 — `REF:` 不吃路徑

| 判決 | **BOUNDARY**（摩擦真，設計取捨） |
|------|----------------------------------|
| 證據 | `REF:20260702-VERIFYGATE-REDTEAM-CLAUDE.md` → `receipt 不存在: 20260702-VERIFYGATE-REDTEAM-CLAUDE.md` **exit=1**；`REF:handoffs/...` 被截成 `receipt 不存在: handoffs` |
| 建議 | 速查文件或放寬 REF 為檔名引用（非 receipt id）|

### B2 — receipt 須 tracked/staged

| 判決 | **HOLDS**（合理）；訊息可更好 |
|------|-------------------------------|
| 證據 | receipt 在磁碟但未 `git add` → `receipt/log 未 tracked 或 staged: tr` **exit=1**；`git add` 後 **exit=0** |
| 摩擦 | 錯誤未明示「先 git add handoffs/run_receipts/…」 |

### B3 — 同 receipt 重複引用 / 小步驟成本

| 判決 | **HOLDS**（未過嚴） |
|------|---------------------|
| 證據 | 同 receipt id 兩條 `已驗全綠 VERIFY:<same>` → staged **exit=0** |
| 備註 | 改 HANDOFF 措辭可重引用既有 receipt；scope 未誤擋合法重引用 |

### B4 — `docs/*.md` 歷史敘述誤擋

| 判決 | **HOLDS**（docs 幾乎不擋 — 與 A4 同一硬幣兩面） |
|------|--------------------------------------------------|
| 證據 | `docs/ROADMAP.md` `## 已完成` +「2025…已完成上線」→ pre-commit **exit=0** |
| 解讀 | 無 receipt 歷史敘述**不誤擋**；但 operational 假聲稱寫進 docs 也**不擋**（見 A4）|

### B5 — CI 舊 range 誤報

| 判決 | **BOUNDARY** |
|------|--------------|
| `abeb9ff~1...abeb9ff` | **exit=1**（HANDOFF 內嵌極性詞、handoffs `STATUS: DONE` 無 backing、VERIFY id 在 range 內找不到 receipt）|
| `abeb9ff~10...abeb9ff` | **exit=0**（僅 WARN 未收錄極性詞）|
| 解讀 | 單次大 push 若含 B3 交付 commit **可能紅**；舊史 SUPERSEDED 段未實測為綠。非 V7 全檔掃描那麼乾淨 |

### B6 — hook 壞掉死鎖 / 逃生

| 判決 | **HOLDS**（PreToolUse fail-closed）+ **BOUNDARY**（gate_check fail-open） |
|------|---------------------------------------------------------------------------|
| 證據 | `verify_pretooluse` checker 缺失 → **exit=2**；checker `raise RuntimeError` → traceback 後 **exit=2** |
| 對照 | `gate_check.sh` 餵 `not-json` → **exit=0** fail-open（設計註解 L11）|
| 缺口 | 無文件化「緊急 disable hook」程序 — Claude B6 成立 |

---

## C. 自由加項（Composer 補盲）

| # | 攻擊/摩擦 | 判決 | 證據 |
|---|-----------|------|------|
| X1 | **`VERIFY_GATE_*` env 使 `_is_test_isolation()` 跳過 tracked 檢查** | **BOUNDARY** | 設 `VERIFY_GATE_RECEIPTS_DIR` 時 untracked receipt 仍過 backing；正式路徑無 env 時 B2 正常 |
| X2 | **temp 測試 symlink 到真實 checker 後覆寫** | **BOUNDARY** | 本 session 曾誤傷真實檔（已還原）；紅隊應 `cp` 勿 `ln` 到生產腳本 |
| X3 | **macOS `/tmp` ↔ `/private/tmp` PreToolUse 全面跳過** | **BROKEN** | 見 A3；Cursor 常送 `/Users/...` 絕對路徑，若與 `realpath` 不一致亦可能中招 |
| X4 | **失敗紀錄（真紅）不要求 SUPERSEDED 即可擋後續綠** | **HOLDS** | A2 紅燈行缺 backing 即 exit=1，不依赖 fingerprint 衝突 alone |

---

## 彙總表

| ID | 判決 |
|----|------|
| A1 | HOLDS |
| A2 | HOLDS / BOUNDARY（SUPERSEDED 不驗 id）|
| A3 | **BROKEN**（PreToolUse 路徑）/ BOUNDARY（假 citation）|
| A4 | **BROKEN** |
| A5 | BOUNDARY |
| A6 | HOLDS |
| A7 | HOLDS |
| A8 | BOUNDARY |
| B1 | BOUNDARY |
| B2 | HOLDS |
| B3 | HOLDS |
| B4 | HOLDS（與 A4 矛盾：docs 太鬆）|
| B5 | BOUNDARY |
| B6 | HOLDS + BOUNDARY（gate_check fail-open）|

---

## 結論（兩行）

① **最該修前 3**：(1) `verify_pretooluse.sh` 路徑正規化（`realpath`/`/tmp` 對齊，避免絕對路徑剝前綴失敗直接 exit=0）；(2) **`docs/*.md` operational 段（`## 已完成`/`STATUS:`）納入與 HANDOFF 同級掃描**，堵 A4 走私；(3) **REF 語意與速查**（檔名引用 vs receipt id，錯誤訊息加 `git add` 指引）。

② **淨判斷**：**仍有洞需緊**（PreToolUse 路徑 bypass、docs 通道）大於過嚴；B1/B2 摩擦真但屬可文件化，B5 單 commit range 對交付型 PR 可能吵，非主矛盾。

---

```
ASSUMPTIONS_VERIFIED: abeb9ff 存在；checker/pretooluse/gate_check 行為以隔離 temp repo + 還原後真實腳本為準；VERIFY_GATE_* 未設時 B2 tracked 檢查有效；真實 verify_audit.log 553B 不變
TESTS_RUN: 隔離 bash 探針（A1–A8/B1–B6/X1–X4）；未改動真實 .claude/gate/* token；未 commit 攻擊產物
FAILURES_SEEN: 早期 symlink 誤覆寫 verification_claim_check.py（已 git checkout 還原）；shell 殘留 VERIFY_GATE_* 導致首輪假陽性（已 unset 重測）
SCOPE_CHANGES: 僅新增本 handoff；checker 曾誤傷已還原，無意圖性 code 變更
NUMERIC_OR_SCHEMA_IMPACT: none（還原後）
```

STATUS: DONE
