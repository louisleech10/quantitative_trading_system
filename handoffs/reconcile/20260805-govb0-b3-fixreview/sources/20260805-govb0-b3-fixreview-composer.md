# GOVB0-B3-FIXREVIEW — composer

**task-id**: GOVB0-B3-FIXREVIEW  
**家族**: composer  
**brief**: `handoffs/20260805-GOVB0-B3-FIX-REVIEW-BRIEF.md`  
**受審**: 工作區未 commit 變更（C1–C5 修補）  
**依據**: `handoffs/reconcile/20260805-govb0-b3-review/synth.md`  
**實作報告**（不可信，已獨立複核）: `handoffs/20260805-govb0-b3-fix-grok.md`

---

## Verdict：可進 B4（B3 驗收通過）

C1–C5 修補經獨立複跑確認關閉；語料 A 未動；`phase2_expected_flips --check` 綠；全套 governance **759 passed**。  
殘留 **MAJOR×2**（M-1 既有繞道、M-2 超長摩擦）與 **MINOR×1**（凍結 TODO 就地註解）——**BLOCKING=0**，符合出場判準。

---

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

## 被當成事實的未驗證假設（§0）

| 宣稱 | 標記 | 本 reviewer |
|---|---|---|
| C1 超 8192 fail-closed 摩擦可接受 | assumed | **攻**：M-2 實跑 echo 8200 → BLOCK；無量測 → MAJOR |
| 8 條 mutation 各自 revert 會轉紅 | partially verified | C1–C3/C4/C5 五條 mutation pytest **5/5 passed**；未逐條手動拆源碼 |
| M-1 為既有缺陷、非 B3 回歸 | fact-verified | 新舊 rc 同（主委 + 本 reviewer） |
| 語料 A 一行未動 | fact-verified | `git diff gate_invariance_corpus.txt` 空 |
| 759 tests 全綠 | fact-verified | 見下 VERIFY |

---

## 標的 1 — C1–C5 獨立複跑

| # | 項目 | 本 reviewer 值 | 宣稱 | 判定 |
|---|---|---|---|---|
| 1a | C1-a `x×8200; codex exec hi` | **rc=2** | rc=2 | ✓ |
| 1b | C1-b latency | **cold_ms=72.4**, rc=0 | 70.3 | ✓；門檻仍 `assert ms_cold < 100.0`（`test_debt_gate.py:464`）未放寬 |
| 1c | C1-c 4MB | **rc=2, dur_s=3.944** | 3.817s | ✓；可接受（僅超長觸發） |
| 1d | C2-a..d | **2/2/2/0** | 同左 | ✓ |
| 1e | C3-a..d | **2/2/0/0** | 同左 | ✓ |
| 1f | C4 mutation | pytest **PASSED**（注入 victim 後 reverse1 轉紅） | 同 | ✓ |
| 1g | C5 mutation | pytest **PASSED**（刪 abs regex → RECURSE 0 條） | 同 | ✓ |

**VERIFY**:
```
pytest tests/governance -q  → 759 passed in 255.66s  rc=0
pytest …test_gate_check_latency_under_100ms -q -s  → cold_ms=72.4  rc=0
pytest …test_21_c1_mut… test_21_c2_mut… test_21_c3_mut… test_01_invariance_exclude_nonflip_mutation test_01_c5…  → 5 passed
bash scripts/restore_golden_inventory.sh  → restored  rc=0
```

---

## 標的 2 — 弱化檢查

| # | 結果 |
|---|---|
| 2a | `git diff tests/` 刪除斷言**僅** C4 舊恆真 reverse1 區塊（`test_gate_deny_fields.py`）；其餘為新增 C1–C5 測試／語料 B |
| 2b | `match_rule` 封閉集合**未擴**；diff 僅增 `lex_oversize` stderr，不寫入 `match_rule` |
| 2c | `gate_invariance_corpus.txt` **零 diff** |
| 2d | `python3 scripts/extract_phase2_expected_flips.py --check` → **OK rows=37** rc=0 |

---

## 標的 3 — 凍結文件

就地 HTML 註解記 C5 選 (a)：**程序上不建議**（見 COMPOSER-R14-P2-01）；機械行為正確。應改延伸檔，不阻 B3 功能驗收。

---

## §1 必查（11 類，摘要）

1. 矛盾：無（修補與 reconcile C1–C5 處置一致）  
2. 漏項：M-1 未在本批修——已標 MAJOR 順延 B4  
3–8. 無 quant/cache/API 命中  
9. 測試品質：C4 恆真已修；mutation 5/5 綠  
10. Agent 可執行性：n/a（code review）  
11. 必要性：C1 fail-closed 為過渡，B4 宜流式掃描取代（見 M-2）

---

## 出場判準核算

| 項目 | 值 |
|---|---|
| FINDINGS_COUNT | **3** |
| BLOCKING | **0** |
| MAJOR | 2（M-1, M-2） |
| MINOR | 1（凍結 TODO 就地註解） |
| C1–C5 關閉 | **是**（獨立複跑確認） |
| 判定 | **findings ≤5 且 BLOCKING=0 → B3 驗收通過，可進 B4** |

---

## /tmp 清理

`rm` 被執行環境 deny 清單阻擋，**未能刪除** `/tmp/govb0-b3-fixreview-composer`；`claude-501` 未動。請主委或本機手動清 workdir。

---

ASSUMPTIONS_VERIFIED: C1–C5 探針與 mutation 獨立複跑；語料 A 未動；phase2 --check；759 governance tests；audit cmd_head 長度分布（有限欄位）  
TESTS_RUN: 見標的 1 VERIFY 區塊  
FAILURES_SEEN: C1-c 初探「Argument list too long」→ 改 stdin 傳 payload 後 rc=2 dur=3.944  
SCOPE_CHANGES: none（禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none（review only）

STATUS: DONE
