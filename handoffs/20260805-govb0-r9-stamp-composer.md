# GOVB0-R9-STAMP — Composer 第三方複核

**家族**: composer  
**task-id**: GOVB0-R9-STAMP  
**審查對象**: `handoffs/reconcile/20260805-govb0-todo-r9/synth.md`  
**日期**: 2026-08-05

---

## synth.md 變更（僅 `## 戳記` 區段）

```diff
+
+## 戳記
+
+RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b task:GOVB0-R9-STAMP
```

**body-hash 複核**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260805-govb0-todo-r9/synth.md` → `bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b`（與 brief 逐字一致）

---

## 1. 歸戶正確性（逐條核對）

| 群 | brief 指定 mapping | synth 表「對應 finding」欄 | 判定 |
|---|---|---|---|
| J-1 | `CODEX-R9-P1-02`＋`COMPOSER-R9-P1-01` | `CODEX-R9-P1-02`／`COMPOSER-R9-P1-01` | ✅ 正確 |
| J-2 | `CODEX-R9-P1-01` | `CODEX-R9-P1-01` | ✅ 正確 |
| J-3 | `CODEX-R9-P2-03` | `CODEX-R9-P2-03` | ✅ 正確 |
| J-4 | `COMPOSER-R9-P2-01` | `COMPOSER-R9-P2-01` | ✅ 正確 |

附錄 5 個 `##` heading 與 sources.lock（codex 3 + composer 2）一致；completeness_check 5/5 全在綜合檔。

---

## 2. 四項修法獨立實跑驗證

### J-1 — Task 2.0 sidecar producer

`docs/GOVB0_FRICTION_TODO.md` Task 2.0：
- 輸出欄 L267–272 列 `gate_decision_corpus.txt` **＋** `.sha256` sidecar，producer＝本 Task、同 commit
- 修改檔案 L297–298 列語料 **及其 `.sha256` sidecar**（同一 commit）

✅ 修法已關閉「無 producer」缺口。

### J-2 — bounded awk 擷取

```bash
awk '/^## B-24 /{p=1} p && /^## B-/ && !/^## B-24 /{exit} p' handoffs/20260801-GOV-AMEND-BACKLOG.md | grep -c '^TICKET-STATUS: PARTIAL'
# → 1

awk '/^## B-14 /{p=1} p && /^## B-/ && !/^## B-14 /{exit} p' handoffs/20260801-GOV-AMEND-BACKLOG.md | grep -c '^TICKET-STATUS: PROVISIONAL'
# → 1
```

TODO L679–687 逐字命令與上式一致。✅ 獨立複跑與主委宣稱一致。

### J-3 — §T literal ID 落點

§T in-scope 表 L734–738 已列 `D-4`／`D-6`／`F-1`／`F-3` 及對應 TODO 位置；L741 註明 R9 補列。✅

### J-4 — Gate ⑨～⑬ 五條

- §B B6→B7 L110：`⑨`～`⑬` **五條**
- Phase 3 Gate L701–702：同上

✅ 兩處均已更新。

---

## 3. 收斂訊號攻擊

### 計數是否屬實

| 輪次 | synth 宣稱 findings | 獨立核對 | blocking 宣稱 | 獨立核對 |
|---|---|---|---|---|
| R8 前輪（TODO-REVIEW） | 9 | codex 5 + composer 4 = 9 unique ID ✅ | 2 | codex `CODEX-TODO-P0-02`／`P0-03` 兩條 `[BLOCKING]` ✅ |
| R8 | 6 | r8 synth 6 群 I-1～I-6 ✅ | 1 | 附錄僅 `CODEX-R8-P0-01` 標 `[BLOCKING]` ✅ |
| R9 | 5 | codex 3 + composer 2 = 5 ✅ | 0 | 五條皆 `named-residual`，無 `[BLOCKING]` ✅ |

**「首次修補引入 blocking 歸零」**：R9 五條確為追溯／文案殘差，非邏輯矛盾或測試恆 FAIL——**計數屬實**。

### 修補品質 vs 僅未被抓到

- **改善面**：R9 缺口類型從 R8 的「測試自引用／snapshot 所有權矛盾」收斂為「§T 索引／Gate 文案／sidecar 產出欄漏列」——嚴重度與可機械驗證性皆下降。
- **未根治面**：`J-4` 仍是 `票 B-17` 同型（手寫計數引用漂移，本 session 第 10 次）；`J-1` 是 R8 `I-4` 修 corpus mutation 時「新增依賴檔未指定 producer」的第三次同型。**主委修補模式未消失，只是本輪未再產生 blocking 級矛盾。**
- **code review 建議**：實作階段仍須 **雙家族 + 機械門**（`^` 錨定 grep、producer 對帳、bounded awk 複跑、⑨～⑬ 計數），不可因 R9 `blocks-implementation=0` 降 review 強度。

---

## 4. 拿這份 TODO 能否直接開寫？（第三方 + 即將實作者視角）

**結論：可以開工。** 11 Task 均有「修改檔案」精確到路徑／函式（例：Task 0.1 → `gate_check.sh:_append_gate_deny_audit`；Task 1.1 → `cx_run.sh:_prepare_and_run`；Phase 2 → `gate_check.sh:86` 各段；Phase 3 → `cx_run.sh` lock／publish 路徑）。R9 五條修補均已落入 TODO 正文。

**無「看完不知改哪個函式」的 Task。** 冷啟動仍須遵守 B0→B3 硬 Gate 與 Phase 依賴圖，但規格層面已可執行。

**殘留認知負擔（不阻擋、實作時注意）**：
- Task 2.0 契約 11 項中第 4、5、7、8、9、10 項須補齊（原型只覆蓋 2、3）
- `E-SCOPE`／`B-35`／`B-34`／`B-24` 機械面／`B-15` FP-2／`F-7`／`B-36` 等本輪 OUT-OF-SCOPE，實作不得偷渡

---

## 5. 三支檢查器完整 stdout

### `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-todo-r9/synth.md`

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-todo-r9/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · composer: provenance 不符 — ERROR: task:GOVB0-R9-STAMP 輸出 hash 仍為 pending（須 register-output 補記）
  · grok: provenance 不符 — ERROR: task:GOVB0-R9-STAMP 輸出 hash 仍為 pending（須 register-output 補記）
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:bb0090a6f0ed753ad5a9f57b95dc65701c34505539b882d293a095c2f4a9223b task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

rc=1（預期：codex 未戳；composer／grok 待 `register-output` 後 provenance 才綠）

### `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-todo-r9/sources.lock`

```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-todo-r9/sources/20260805-govb0-todo-r9-codex.md — 3/3 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-todo-r9/sources/20260805-govb0-todo-r9-composer.md — 2/2 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

rc=0

### `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md`

```
TEMPLATE PASS (todo): docs/GOVB0_FRICTION_TODO.md 含全部必填錨點，且無明顯空殼。
```

rc=0

---

## /tmp 清理

- 保留：`/tmp/claude-501`
- 嘗試刪除 `/tmp/sessions`：shell 權限拒絕（非本 agent 可清項目）；其餘 `/tmp` 無額外 workdir

---

ASSUMPTIONS_VERIFIED: J-1～J-4 歸戶；四項修法讀碼＋awk 實跑；收斂表對照 TODO-REVIEW／R8／R9 附錄 BLOCKING 標記；body-hash 與 brief sha 一致
TESTS_RUN: reconcile_stamps_check rc=1；completeness_check --lock rc=0；template_check todo rc=0；B-24/B-14 awk grep -c 各得 1
FAILURES_SEEN: stamps_check 全綠需 codex 戳記 + register-output（預期）
SCOPE_CHANGES: 僅 synth.md `## 戳記` append 一行 composer APPROVED
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
