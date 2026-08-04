# GOVB0-R1-STAMP2 — grok 第三方獨立複核戳記

**task-id**: `GOVB0-R1-STAMP2`  
**家族**: grok  
**角色**: 第三方獨立複核（非 R1 審查者；無自身 findings）  
**目標**: `handoffs/reconcile/20260804-govb0-spec-r1/synth.md`  
**body hash 核對**: `sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c`（`reconcile_body_hash.sh` 實跑相符）

## 裁決

**APPROVED** — 已 append 戳記：

```
RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:GOVB0-R1-STAMP2
```

## 改動範圍

- **只動** `synth.md` 的 `## 戳記` 區段（append 一行）。
- 附錄／群集表／本體 **0 位元組變更**（append 後 body hash 仍為 `25e1241f…`）。

### 戳記區 diff（工作樹現況）

```
## 戳記

RECONCILE-STAMP: composer APPROVED 2026-08-04 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:GOVB0-R1-STAMP2
RECONCILE-STAMP: codex APPROVED 2026-08-04 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:GOVB0-R1-STAMP2

RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:GOVB0-R1-STAMP2
```

（composer／codex 行為並發寫入；grok 僅 append 本行。）

## 歸戶核對（19 條附錄 ID ↔ 群集表）

機械對帳：附錄 19 個 `## (CODEX|COMPOSER)-R1-*` heading **全部**出現在群集表；`in app not cluster = []`；`in cluster not app = []`。

| 群 | 附錄 ID | 處置 vs 主張 | 判定 |
|---|---|---|---|
| D-1 | `CODEX-R1-P0-02`／`COMPOSER-R1-P0-01`／`COMPOSER-R1-P1-05` | ACCEPT-BLOCKING；bash -c 疊加 fail-open | OK |
| D-2 | `CODEX-R1-P0-03`／`COMPOSER-R1-P0-02` | ACCEPT-BLOCKING；`.part` vs prompt 路徑 | OK |
| D-3 | `CODEX-R1-P0-05` | ACCEPT-BLOCKING；schema/enum + 不變式收窄 | OK |
| D-4 | `CODEX-R1-P0-04`／`COMPOSER-R1-P1-01` | ACCEPT-BLOCKING；§V／exact-delta 不可證偽 | OK |
| D-5 | `CODEX-R1-P1-09` | ACCEPT-BLOCKING；unknown brief-kind 互斥 | OK |
| D-6 | `CODEX-R1-P0-01` vs `COMPOSER-R1-P1-02`／`COMPOSER-R1-P1-04` | **SPLIT（主委裁）**；紀律面留、機械面移出 | OK（同意裁決） |
| D-7 | `CODEX-R1-P1-06`（timeout 主張部分）／composer Q1 | PARTIAL 暫定值；區間=CLI process-group | OK（**首輪誤引 P0-07 已修正**） |
| D-8 | `CODEX-R1-P0-07`／`COMPOSER-R1-P1-03` | ACCEPT 開 `票 B-33` locale | OK |
| D-9 | `CODEX-R1-P1-08`／`COMPOSER-R1-P2-03` | ACCEPT 補樣本門檻／不除役 | OK |
| D-10 | `CODEX-R1-P0-01`（部分）／`COMPOSER-R1-P1-04` | ACCEPT 隨 D-6 移出 grandfather 制度 | OK |
| D-11 | `COMPOSER-R1-P2-02` | ACCEPT 收窄＝只保 harness 端 | OK |
| D-12 | `COMPOSER-R1-P2-01` | ACCEPT 明文化 grep 不可做 | OK |
| D-13 | `CODEX-R1-P1-06`／composer Q6 | ACCEPT §P 補 forward dependency | OK（與 P1-06 自述一致） |

### 首輪錯誤再確認

- D-7 現引 **`CODEX-R1-P1-06`（timeout 主張部分）**，非 `CODEX-R1-P0-07`。
- D-8 專屬 locale fail-open → `CODEX-R1-P0-07`。
- 未發現新的歸戶／弱化／改寫錯誤。

### D-6／D-7 主委裁決

- **D-6 SPLIT**：同意。依據＝95% 收斂 + Phase 4 膨脹訊號；共識（owner／UTC expiry）經 D-10 移出不遺失。
- **D-7 暫定值**：同意為 PARTIAL；birth→mtime 為 proxy，Task 3.1 定稿條件正確。

### D-1 獨立重跑

`bash .claude/tmp/b15probe3.sh`（rc=0）：

- 原型①：`bash -c "codex exec x"`／`sh -c` 包住派工 → **ALLOW（fail-open）**
- 原型②：同上 → **BLOCK**
- 其餘 7 條：兩原型皆對

與 synth 表一致。

## 驗收命令（rc 直接取，未經 pipe）

### `reconcile_stamps_check.sh` 完整 stdout + rc

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260804-govb0-spec-r1/synth.md 未獲全數委員核可:
  · codex: provenance 不符 — ERROR: task:GOVB0-R1-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · composer: provenance 不符 — ERROR: task:GOVB0-R1-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · grok: provenance 不符 — ERROR: task:GOVB0-R1-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:25e1241fda047b7d186df360d43da7234ef7b6f232973b4286a1c63848af0d0c task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

**stamps_rc=1**

狀態解讀（驗收＝狀態，不是 rc）：三家 APPROVED 行與 body sha256 **皆相符**；失敗原因僅 **`task:GOVB0-R1-STAMP2` 輸出 hash 仍為 pending**（須主委 `register-output`），非戳記內容錯誤或拒章。

### `completeness_check.sh --lock`

```
COMPLETENESS PASS: .../20260804-govb0-spec-r1-codex.md — 9/9 個 ID 全在綜合檔。
COMPLETENESS PASS: .../20260804-govb0-spec-r1-composer.md — 10/10 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

**completeness_rc=0**

## /tmp 清理

保留 `claude-501`；其餘 session 工作目錄已清（見 shell 收尾）。

---

ASSUMPTIONS_VERIFIED: body hash=25e1241f…；19/19 附錄 ID 皆歸戶；D-7 引 P1-06 非 P0-07；D-1 探針原型① fail-open／② BLOCK 重現  
TESTS_RUN: `reconcile_body_hash.sh` rc=0 hash match；`b15probe3.sh` rc=0；`reconcile_stamps_check.sh` rc=1（pending provenance only）；`completeness_check --lock` rc=0  
FAILURES_SEEN: none on content review；stamps_check 僅 provenance pending  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
