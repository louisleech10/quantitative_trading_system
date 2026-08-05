# GOVB0 TODO Adversarial Review — Composer

**家族**: composer  
**task-id**: GOVB0-TODO-REVIEW  
**審查對象**: `docs/GOVB0_FRICTION_TODO.md`（DRAFT）  
**基準 SPEC**: `docs/GOVB0_FRICTION_SPEC.md`（R7，`sha b502bac9…0f82fa4bd`）  
**日期**: 2026-08-05

RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-TODO-REVIEW

---

## Verdict

**可派工**（exit 公式：findings=4、BLOCKING=0 ≤5）——建議主委在標 Internal Frozen 前補 4 項 MAJOR 追溯／可測性缺口（皆為 TODO 小 patch，不動 SPEC）。

---

## §0 前提宣告

**fact-verified**：

- `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0
- SPEC Task 11 == TODO Task 11（`grep -c` 各 11）
- `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md` rc=0

**攻擊 §0 四條假設**：

| 假設 | 結果 |
|---|---|
| §T 宣稱 100% 但 finding ID 未逐條核對 | **部分成立**——Task 級完整；具名 ID 有 4 處 §T 未列但正文有落點；`OPEN-2`／`D-8` 正文亦缺 |
| 實作要點足夠冷啟動 | **大致成立**——11 Task 皆 ≥3 要點、含偽碼／檔案／函式；Task 2.5 缺 mutation 條目 |
| B1–B7 同檔不衝突 | **成立**——`gate_check.sh:86` 與 `_emit_family_result` 衝突點已合併同批；B3→B4 序貫改 `:86` 可 merge |
| `TEST-3.3-PROVISIONAL` 三條件可機械讀 | **③ 不成立**——`票 B-14` backlog 無「未定稿」字樣（見 finding P1-03） |

---

## 逐項核對表

### 1. 追溯完整性（SPEC 具名 ID → TODO 落點）

**grep 方法**：`rg '`[DEGFH]-[0-9]+[a-z]?`' docs/GOVB0_FRICTION_SPEC.md` ＋ `OPEN-[0-9]`／`E-SCOPE`／R7 殘留表。

| SPEC ID | TODO 落點 | 狀態 |
|---|---|---|
| `D-1` | Task 2.0 目標／Task 2.1 標題 | ✅ |
| `D-2` | Task 3.2 要點 2 | ✅ |
| `D-3` | Task 0.1 要點 4 | ✅ |
| `D-4` | Task 2.5 驗證／改法 | ✅（§T 未列） |
| `D-5` | Task 1.1 要點 3 | ✅ |
| `D-6` | §0.1① `B-24` 部分完成；§T `B-24` 紀律面 | ✅（機械面 SPLIT 出批，合理合併） |
| `D-8` | — | ❌ **缺**（見 P1-01） |
| `D-11` | Task 1.1 誠實邊界 | ✅ |
| `D-12` | Task 0.1 要點 1 | ✅ |
| `D-13` | Task 2.5 要點 2；§B 依賴 | ✅ |
| `E-2` | Task 1.1 `TEST-1.1-UNKNOWN-NOSIDEEFFECT` | ✅ |
| `E-3` | Task 2.1 `TEST-2.1-E3`；Task 2.2 REGRESS | ✅ |
| `E-7`／`E-8` | Task 0.1 要點 4（語料 A／B 分離） | ✅（§T 未列） |
| `E-9` | — | ❌ **缺驗證落點**（見 P1-02） |
| `E-10` | §0.1③；Task 3.3；`TEST-3.3-PROVISIONAL` | ✅ |
| `F-1` | Task 0.1 `TEST-0.1-INVARIANCE`（R4 改寫語意） | ✅（§T 未列） |
| `F-3` | Task 3.2 要點 7–10／LOCK ①–⑫ | ✅（§T 未列） |
| `F-6` | Task 2.1 `TEST-2.1-1B` | ✅ |
| `F-7` | — | ⚠️ §N 具名殘留未入 §0／§T（文檔債，非執行阻塞） |
| `H-1`（允許清單殘留） | Task 2.0 要點 4；§T | ✅ |
| `H-2`（reclaim 孤兒） | §0.1②；Task 3.2 要點 8；§T | ✅ |
| `OPEN-1` | §0.2；§0.1③；Task 3.3 | ✅ |
| `OPEN-2` | — | ❌ **缺**（見 P1-01） |
| `OPEN-3` | §0.2（E-SCOPE 補查） | ✅ |
| `E-SCOPE` 四項 | §0.2；Task 3.2 要點 5；§T | ✅（brief 不受理範圍，已具名合併） |

**缺失摘要**：`D-8`／`OPEN-2` 正文缺；`E-9` 驗證缺；§T 表缺 `D-4`／`E-7`／`E-8`／`E-9`／`F-1`／`F-3`／`F-7` 行（正文多處已覆蓋，表不完整）。

### 2. 深度紅線（逐 Task）

| Task | ≥3 要點 | 偽碼／檔案／函式 | 邊界 ≥2 | 驗證具體 | 判定 |
|---|---|---|---|---|---|
| 0.1 | 4 | ✅ `_append_gate_deny_audit`／`:86` | 3 | ✅ 6 Test ID | PASS |
| 1.1 | 3 | ✅ `cx_run.sh:512` case | 2 | ✅ 含 NOSIDEEFFECT | PASS |
| 2.0 | 4 | ✅ heredoc 七規則偽碼 | 4（契約項） | ✅ ≥22＋MUT | PASS |
| 2.1 | 3 | ✅ `:86` 前處理 | 3 | ✅ 5 狀態＋MUT | PASS |
| 2.2 | 3 | ✅ 第二段 alternation | 3 | ✅ 5 狀態＋MUT | PASS |
| 2.3 | 3 | ✅ 第一段 alternation | 3 | ✅ 3 狀態＋MUT | PASS |
| 2.4 | 3 | ✅ `:86-90` | 3 | ✅ E2E＋MUT | PASS |
| 2.5 | 3 | ✅ `gate_decision_delta.sh` | 3 | ⚠️ 無 MUT 條目 | **FAIL**（見 P2-01） |
| 3.1 | 3 | ✅ `_emit_family_result` | 2 | ✅ 3 狀態＋MUT | PASS |
| 3.2 | 10 | ✅ lock 協定偽碼 | 4 | ⚠️ 缺 E-9 斷言 | **FAIL**（見 P1-02） |
| 3.3 | 5 | ✅ timeout 公式 | 3 | ✅ 含 PROVISIONAL | PASS（③ 見 P1-03） |

### 3. §0 三項狀態宣告可機械驗證

| 宣告 | 可執行斷言 | 判定 |
|---|---|---|
| ① `B-24` 部分完成 | 無自動測試；依 §0.5 紀律＋code review | 散文可執行（審查義務） |
| ② reclaim 孤兒需人工清理 | 無 orphan 自動清理測試；§0 誠實邊界 | 散文可執行（運維義務） |
| ③ `PROVISIONAL` 三條件 | `TEST-3.3-PROVISIONAL` ①②可測；③ backlog 無錨點 | **③ 不可測**（P1-03） |

### 4. 批次切分 B1–B7

| 檢查 | 結果 |
|---|---|
| 依賴拓撲 | B1→B3→B4→B5；B2→B6→B7；與 SPEC §P 一致 |
| 同檔衝突 | B4 合併 2.2–2.4（`:86`）；B6 合併 3.1–3.2（`_emit_family_result`）；B3 的 2.1 與 B4 序貫改 `:86` 無並行衝突 |
| Gate 可執行 | 各批 `pytest tests/governance/…` 或 `bash scripts/*.sh` 具名；rc 直接取 |
| 隱藏衝突 | `audit_events.json`：0.1（B1）與 3.1（B6）序貫改同一檔——已分批 |

### 5. `rc` 斷言配對（SPEC §V `B-24` 紀律）

| Task | `ASSERT … rc` 條目 | 同 Task 狀態斷言 | 判定 |
|---|---|---|---|
| 0.1 | `TEST-0.1-RC-BLOCK`／`RC-ALLOW` | `INVARIANCE`（語料級）＋`FIELDS`／`ENUM`（deny 事件） | ⚠️ `RC-ALLOW` 與 `INVARIANCE` 非同一輸入綁定，配對偏弱 |
| 1.1 | CONSULT／STAMP／UNKNOWN | 各 rc 條均含 prompt 狀態或 NOSIDEEFFECT | ✅ |
| 3.3 | `TEST-3.3-HANG` | `TEST-3.3-FAILED`（result_state／檔案） | ✅ |
| 2.0–2.5／3.1–3.2 | 無裸 `ASSERT … rc` | — | ✅ |

**違反者**：無硬性「僅 rc 無狀態」條目；Task 0.1 配對可再明示綁定（建議非 blocking）。

### 6. 測試可證偽性

| 區域 | 判定 |
|---|---|
| 各 Task mutation | 2.0–2.4／3.1／3.3 有 MUT；3.2 以 LOCK ⑨–⑫ **反向 mutation** 代替頂層 MUT——可證偽 |
| Task 2.5 | **無 mutation 條目**（P2-01） |
| 恆真／廉價綠 | 未見「只驗 rc=0 不驗內容」之新測試設計 |
| `TEST-3.3-PROVISIONAL` | ①②可證偽；③跨檔且錨點缺失 |

---

## COMPOSER-TODO-P1-01

**斷言**: SPEC §N 要求 `OPEN-2`／`D-8`（locale 守衛，`票 B-33`）寫入 TODO §0 已知 MAJOR 債，但 TODO §0.2 僅列 `OPEN-1`／`OPEN-3`，實作者冷啟動看不到此債。

**碼證**: `docs/GOVB0_FRICTION_SPEC.md`「`票 B-33`；TODO §0 須列為已知 MAJOR 債」；`docs/GOVB0_FRICTION_TODO.md` §0.2 無 `OPEN-2`／`D-8`／`B-33`

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#b502bac9981d

[MAJOR] 信心度=High；冷啟動執行端可能 unaware locale 漂移風險，與 SPEC 交付契約不符。

**修法**: `docs/GOVB0_FRICTION_TODO.md` §0.2 增一行：`[OPEN-2]` locale 守衛漂移 → `票 B-33` MAJOR，本批不併入（SPEC `D-8` SPLIT）。

**RECHECK**: `rg 'OPEN-2|B-33|D-8' docs/GOVB0_FRICTION_TODO.md` 應命中 §0.2。

---

## COMPOSER-TODO-P1-02

**斷言**: SPEC Task 3.2 具名 `E-9` 要求 publish／timeout 順序契約（CLI wait 後才 format check／publish；每 attempt `committee_family_result` 計數 == 1），TODO Task 3.2 驗證欄完全未列對應 Test ID。

**碼證**: SPEC `docs/GOVB0_FRICTION_SPEC.md` Task 3.2「狀態斷言（publish 與 timeout 的順序契約，`E-9`）… audit 中該 attempt id 的 `committee_family_result` 計數 == 1」；TODO Task 3.2 驗證列至 `TEST-3.2-LOCK-⑫`，無 `E-9`／publish-order 條目

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#b502bac9981d

[MAJOR] 信心度=High；實作者可漏實作「timeout 不涵蓋 publish 階段」與單筆 result_state，回歸 `B-14` 誤判路徑。

**修法**: Task 3.2 **驗證**欄增 `TEST-3.2-E9-ORDER`（狀態）：mock CLI 已返回且 publish 進行中 ⇒ 外層 timeout **不得**判 `failed`；audit 該 attempt 的 `committee_family_result` **恰 1 筆**。附反向 mutation（timeout 涵蓋 publish ⇒ 斷言 FAIL）。

**RECHECK**: `rg 'E-9|TEST-3.2-E9' docs/GOVB0_FRICTION_TODO.md` 應命中 Task 3.2 驗證段。

---

## COMPOSER-TODO-P1-03

**斷言**: `TEST-3.3-PROVISIONAL` 第三條件要求 `票 B-14` 票面含「未定稿」，但 backlog 票面無該字樣 ⇒ 條件③無機械錨點，與 TODO 宣稱「三者任一缺失即 FAIL」矛盾。

**碼證**: TODO Task 3.3「③`票 B-14` 票面**含「未定稿」**」；`handoffs/20260801-GOV-AMEND-BACKLOG.md` B-14 節（L316–333）有修法／繞法，**無「未定稿」**；`rg '未定稿' handoffs/20260801-GOV-AMEND-BACKLOG.md` 在 B-14 語境僅 B-35 交叉引用

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#b502bac9981d

[MAJOR] 信心度=High；實作者寫 `TEST-3.3-PROVISIONAL` 時③無法實作，或測試恆綠／恆紅。

**修法**（二擇一，主委定）：(a) backlog `票 B-14` 票面增「**未定稿**（timeout 值／截斷偵測）」；或 (b) TODO `TEST-3.3-PROVISIONAL` ③改讀可機械欄位（例 backlog 表頭 `B-14` 行狀態欄＋固定子字串 `截斷偵測未解` 已存在於 B-35 交叉引用）。

**RECHECK**: `rg '未定稿' handoffs/20260801-GOV-AMEND-BACKLOG.md` 應在 B-14 節命中；或 TODO ③改指向可 grep 錨點。

---

## COMPOSER-TODO-P2-01

**斷言**: SPEC §V 要求全部 11 Task 皆有 mutation 自證，Task 2.5 驗證欄無任何 `MUT`／mutation 條目，與 §0.4／Phase 2 其他 Task 不一致。

**碼證**: SPEC §V「全部 11 個 Task… mutation 必附」；TODO Task 2.5 驗證列 `TEST-2.5-SUBSET-*`／`CORPUS-SHA`／`EMPTY`，**無** `TEST-2.5-MUT`；對照 Task 2.4 有 `TEST-2.4-MUT`

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#b502bac9981d

[MAJOR] 信心度=High；差集報表邏輯可 silently 退化（例放寬「非預期」判定）而無回歸測試轉紅。

**修法**: Task 2.5 **驗證**增 `TEST-2.5-MUT`：revert「非預期⇒rc≠0」或 sha 標頭綁定 ⇒ `TEST-2.5-EXTRA` 或 `TEST-2.5-CORPUS-SHA` 轉紅（貼實跑 rc）。

**RECHECK**: `rg 'TEST-2.5-MUT' docs/GOVB0_FRICTION_TODO.md` 應命中。

---

## 出場判準核算

| 項目 | 數值 |
|---|---|
| findings 總數 | **4** |
| P0 | 0 |
| P1（MAJOR） | 3 |
| P2（MAJOR） | 1 |
| BLOCKING | **0** |
| exit 公式 `≤5 且 BLOCKING=0` | **滿足** |
| 建議 | 補 4 項 MAJOR 後標 Internal Frozen；**不需第二輪** adversarial（除非 patch 後主委要求複核） |
| 第二輪？ | **否**（缺口明確且局部） |

FINDINGS_COUNT: 4

---

ASSUMPTIONS_VERIFIED: template_check rc=0；Task 11==11；reconcile_stamps rc=0；B-14 無「未定稿」字樣（`rg`）；SPEC 具名 ID grep 清單逐條對照 TODO  
TESTS_RUN: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` PASS rc=0；`grep -c` Task 11/11；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md` PASS rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  

產出檔: `handoffs/20260805-govb0-todo-review-composer.md`

STATUS: DONE
