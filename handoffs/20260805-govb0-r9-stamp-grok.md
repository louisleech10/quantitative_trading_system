# GOVB0-R9-STAMP | family: grok | 第三方複核（implementer 立場）

brief-kind: stamp | stamp-target: `handoffs/reconcile/20260805-govb0-todo-r9/synth.md`
task-id: **GOVB0-R9-STAMP**（逐字；未採用 brief 內任何範例 task-id）

## Verdict

**APPROVED** — 歸戶正確、四項修法獨立實跑關閉、收斂訊號「0 blocks-implementation」屬實但「修補品質已穩」僅部分成立。

## Diff（僅動 `## 戳記` 區；本體 0 位元組變更）

```diff
 ## 戳記
+RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b task:GOVB0-R9-STAMP
```

body-hash 戳前後皆：`bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b`（`bash scripts/reconcile_body_hash.sh …`）。

**併發備註（事實）**：首輪 append 後，同檔 `## 戳記` 曾只剩 `composer` 一行（他家族並行寫入／覆蓋）；已**再次 append** grok 行。終態：

```
## 戳記
RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b task:GOVB0-R9-STAMP
RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b task:GOVB0-R9-STAMP
```

## 三支檢查器（完整 stdout + rc，rc 直接取）

### 1) `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-todo-r9/synth.md`

**中途（僅 composer+grok）** 曾 rc=1 缺 codex。**終態（三家齊後重跑）**：

```
RECONCILE-STAMP PASS: handoffs/reconcile/20260805-govb0-todo-r9/synth.md 已獲 codex,composer,grok 全數 APPROVED 且本體雜湊相符(sha256:bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b)。
  使用者反偽造稽核:核對各戳記 task:<id> 對應的 harness 輸出確為該委員真跑真 APPROVED。
```
**rc=0**

### 2) `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-todo-r9/sources.lock`

```
COMPLETENESS PASS: …/20260805-govb0-todo-r9-codex.md — 3/3 個 ID 全在綜合檔。
COMPLETENESS PASS: …/20260805-govb0-todo-r9-composer.md — 2/2 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```
**rc=0**

### 3) `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md`

```
TEMPLATE PASS (todo): docs/GOVB0_FRICTION_TODO.md 含全部必填錨點，且無明顯空殼。
```
**rc=0**

---

## 1. 歸戶正確性（逐條 ID 對照附錄）

| 群 | synth 對應 finding | 附錄原文主題 | 判定 |
|---|---|---|---|
| J-1 | `CODEX-R9-P1-02`＋`COMPOSER-R9-P1-01` | 兩者皆：`.sha256` sidecar 無 producer／Task 2.0 輸出與修改檔未列 | **正確**（兩家同題合併） |
| J-2 | `CODEX-R9-P1-01` | B-24 只給自然語言＋`grep -c`，無 bounded 擷取命令 | **正確** |
| J-3 | `CODEX-R9-P2-03` | `D-4`／`D-6`／`F-1`／`F-3` 無 §T literal | **正確** |
| J-4 | `COMPOSER-R9-P2-01` | Gate 仍寫 ⑨～⑫「四條」漏 ⑬ | **正確** |

5/5 ID 皆在附錄且無錯位／無未分群。completeness 機檢 5/5 與語意複核一致。

---

## 2. 四項修法獨立實跑驗證

### J-1 — sidecar producer（Task 2.0）

| 檢查點 | 結果 |
|---|---|
| 「輸入／輸出」列 `gate_decision_corpus.txt.sha256` | **是**（TODO L268） |
| 「修改檔案」列 sidecar | **是**（TODO L298：「及其 `.sha256` sidecar」） |
| producer + 同 commit ownership | **是**（L270–272：producer＝本 Task、與語料同 commit、內容＝sha256sum 單行） |

⇒ 原 finding 關閉。

### J-2 — `TEST-3.3-B24-PARTIAL` awk 實跑

TODO L682 命令逐字：
```
awk '/^## B-24 /{p=1} p && /^## B-/ && !/^## B-24 /{exit} p' handoffs/20260801-GOV-AMEND-BACKLOG.md
```

| 斷言 | 實跑 |
|---|---|
| `grep -c '^TICKET-STATUS: PARTIAL'` | **1** |
| `grep -c '^TICKET-STATUS: DONE'` | **0**（grep rc=1，count 0） |
| 同法 B-14 `^TICKET-STATUS: PROVISIONAL` | **1** |

⇒ 主委宣稱屬實；獨立複跑通過。

### J-3 — §T 四 ID 落點

`grep -nE '\bD-4\b|\bD-6\b|\bF-1\b|\bF-3\b' docs/GOVB0_FRICTION_TODO.md`：

- L734：`D-4` → Task 2.5 要點 1–3；`D-6` → §0.1 第 1 條
- L738：`F-1` → Task 0.1 `TEST-0.1-INVARIANCE`；`F-3` → Task 3.2 要點 7–10
- L741 註明為 R9 補列

⇒ 關閉。

### J-4 — Gate ⑨～⑬ 兩處

| 位置 | 文案 |
|---|---|
| B6→B7（L110） | `TEST-3.2-LOCK-⑨`～`⑬` **五條**（含 `TEST-3.2-E9-ORDER`） |
| Phase 3 Gate（L702） | 同：`⑨`～`⑬` **五條** |

Task 3.2 內確有 `TEST-3.2-LOCK-⑬`（L612）。⇒ 關閉。

---

## 3. 攻擊「收斂訊號」

synth 表：

| 輪次 | findings | 修補引入 blocking |
|---|---|---|
| R8 前輪 | 9 | 2 |
| R8 | 6 | 1 |
| R9 | 5 | 0 |

**可核部分**

- **R9 = 5、blocks-implementation = 0**：兩家 source 明寫；5 條皆 `named-residual`。**屬實**。
- **R8 = 6、其中 1 條 ACCEPT-BLOCKING（I-1）**：r8 synth 表與附錄 `[BLOCKING]` 一致。**屬實**。
- **R8 六條「全為修補引入」**：r8 synth 正文自承。**屬實**。

**不可輕易核／須打折扣的部分**

1. **「R8 前輪 2 BLOCKING」**：本 repo 無獨立 `govb0-todo` 前輪 reconcile session 可對表；codex-r8 寫的是「原 9 條修補中…2 條為**修補後**新缺口」——語意上那 2 條屬 R8 發現物，**不宜直接算進「R8 前輪」欄**。此格**未獨立驗證**。
2. **「修補品質改善」vs「本輪剛好沒抓到」**：
   - 嚴重度確降（blocking → named-residual）——**有改善訊號**。
   - 但 **J-1 仍是「修 A 引入 B」第三次**（R8 修 I-4 加 sidecar 依賴、未寫 producer）——**病型未消**。
   - J-2／J-3／J-4 皆屬「改一處未同步他處／規格寫半套」——與 R8 的 I-2／I-5 同族。
   - 兩家把 J-1 標 `named-residual` 的理由是「可從 Task 2.5 反推」；**冷啟動只讀 Task 2.0 仍會卡住**——分類偏寬，數字「0 blocking」略樂觀。

**實作 code review 嚴度建議**：維持**高嚴**——特別盯 (a) 新增依賴檔是否有 producer Task、(b) Gate 文案與 Test ID 計數、(c) 測試契約是否給可執行命令而非自然語言、(d) 跨 § 同步。**不要因「0 blocking」放寬。**

---

## 4. E-SCOPE／既有殘留

`票 B-35`／`B-34`／`B-24` 機械面／`B-15` FP-2／`B-36`／`H-1`／`H-2`：本輪 synth 未重開、§T 排除表仍在。**不重議。**

---

## 5. grok 另答：拿這份 TODO 能否直接開寫？

**能開寫**——以 §B 批次拓撲 B0→B7 冷啟動可行。

| 維度 | 判定 |
|---|---|
| 改哪個檔／函式 | 多數 Task 有「修改檔案」＋行號錨點（如 Task 0.1 `_append_gate_deny_audit`、Task 1.1 `_prepare_and_run`、2.1–2.4 `gate_check.sh:86`） |
| 仍需實作者裁量 | Task 3.2 reclaim 修法三擇一 (a)/(b)/(c)——§0 已具名，非缺口 |
| 風險（非 BLOCKING） | `cx_run.sh` 行號可能漂；Task 3.2／3.3 測試構造重；heredoc 契約 11 項原型只覆蓋 2–3 項——TODO 已紅字警告，可依契約補 |
| 本輪修後是否仍有「只讀一 Task 不知產物」 | **J-1 修後無**；sidecar 已在 Task 2.0 輸出＋修改檔雙列 |

**結論**：可直接依 TODO 開工；第一批建議 **B0 snapshot 凍結 → B1（0.1）→ B3（2.0／2.1）**，不跳過 B0。

---

## 收尾

- 產出：`handoffs/20260805-govb0-r9-stamp-grok.md`
- 戳記已 append：`handoffs/reconcile/20260805-govb0-todo-r9/synth.md`（僅 `## 戳記` 後）
- /tmp：已清 ephemeral（frtest.*、govb0-*.txt、stamps/completeness/template out、sessions）；**保留 `/tmp/claude-501`**
- 未 commit／未 push／未碰 `data_cache/`

ASSUMPTIONS_VERIFIED: body-hash=bb0090a6…；J-1～J-4 修法對 TODO 實檔與 awk 實跑；5 finding ID 歸戶；completeness/template rc=0；三家 stamp 終態 PASS
TESTS_RUN: reconcile_stamps_check 終態 rc=0（codex+composer+grok）；completeness_check --lock rc=0；template_check todo rc=0；B-24/B-14 awk bounded 計數 PARTIAL=1 DONE=0 PROVISIONAL=1
FAILURES_SEEN: 首輪 grok stamp 被並行寫入覆蓋 → 再 append 後恢復；其後 codex 亦 append（非本體改動）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
