# GOVB0-R7-STAMP — composer 第三方複核戳記

task-id: GOVB0-R7-STAMP
family: composer
brief: handoffs/20260805-GOVB0-R7-STAMP-BRIEF.md
stamp-target: handoffs/reconcile/20260805-govb0-spec-r7/synth.md

## Verdict

**APPROVED** — 已 append RECONCILE-STAMP 至 synth.md `## 戳記` 區段。

## synth.md diff（唯一改動）

```diff
 ## 戳記
+
+RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP
```

## 1. 歸戶正確性（逐 ID 機械核對）

| 群 | 對應 finding | 附錄斷言主題 | 核對 |
|---|---|---|---|
| H-1 | `CODEX-R7-P1-01` | ⑥(c) 允許清單缺 `~{}[]!*?` ⇒ ⑦ 誤擋 | ✓ 一致 |
| H-1 | `COMPOSER-R7-P2-01` | ⑥(c) 缺 `~{}[]!#` 等 ⇒ ⑦ 誤擋（非 fail-open） | ✓ 一致（`#` 見 §2） |
| H-2 | `CODEX-R7-P1-02` | ③後④前 crash ⇒ reclaim 孤兒 ⇒ EEXIST 鎖死 | ✓ 一致 |
| H-2 | `COMPOSER-R7-P2-02` | 同上，③後不 rmdir ⇒ NEXT_TAKEOVER blocked | ✓ 一致 |

**無 ID 對調、無未分群 ID。** `completeness_check --lock` 4/4 ID 全在綜合檔（見下）。

## 2. SPEC 改動攻擊（H-1 補入 `~{}[]!*?`）

### 「不做展開」是否正確？

實跑 `bash /tmp/govb0-r7-delimiter-probe.sh` 與 `bash /tmp/govb0-r7-expansion-attack.sh`：

- 八字元 `~{}[]!*?` 作 unquoted delimiter 皆 `rc=0`（與 codex probe 一致）。
- 邊界探針：`<<*MARKER` … `*MARKER` 後外部 `echo EXTERNAL_EXECUTED` 正常執行 ⇒ span 邊界與 bash 一致，**未吞假 marker**。
- `set -H` 下 `<<!DELIM` 仍 `rc=0`；`~user`／lone `~`／`{DELIM` 皆 `rc=0` 且 delimiter 字面匹配。
- **反例（邊界語意，非 fail-open）**：`$`、`\` 亦為合法 delimiter（probe `rc=0`），**未納入允許清單** ⇒ 仍走⑦ BLOCK（過擋）。主委「只做 quote removal、不做展開」對已補 8 字元**可接受**；未宣稱 grammar 完整。

### 補入 8 字元是否引入 fail-open？

**否。** 原狀：合法 bash delimiter 被⑦誤擋（過擋）。現狀：與 bash 對齊開 span。**未列字元仍走⑦ BLOCK**（方向 fail-closed）。與 R5/R6 的 fail-open 攻擊鏈（⑥不匹配 ⇒ 吞外部派工）**正交且已關**。

### `#` 未納入是否恰當？

**是。** probe：`BASH_UNQUOTED[#] rc=2`（`<<#DELIM` 語法錯誤；`<<#EOF` 亦 rc=2）。`#` 在 delimiter 位置觸發 comment 語法，**非 bash 可完成 consume 的 delimiter**。composer 原列 `#` 屬「可能字元」枚舉，實跑證偽；維持⑦ BLOCK 與 shell 行為一致，**非誤擋**。

## 3. 殘留分類獨立驗證

| 群 | 分類 | 獨立判定 | 失效路徑（若 deliverable-invalidating） |
|---|---|---|---|
| H-1 | named-residual | **同意** | 未列字元 ⇒ ⑦ BLOCK ⇒ **過擋**；不會漏放真派工、不會雙 CLI。最壞＝額外 friction，與兩家一致 |
| H-2 | named-residual | **同意** | 最壞＝**單一 `<out>` 路徑** reclaim 孤兒鎖死至人工清；主 lock 已重建、① EEXIST 拒絕後續 takeover ⇒ **不會雙 CLI 並存**、不會吞派工 |

**deliverable-invalidating = 0** — 不拒章。

## 4. E-SCOPE

`票 B-35`／`B-34`／`B-24`／`B-15` FP-2`／`B-36` — **維持不變**，本輪未改立場。

## 三支檢查器（完整 stdout + rc）

### reconcile_stamps_check.sh

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r7/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · composer: provenance 不符 — ERROR: task:GOVB0-R7-STAMP 輸出 hash 仍為 pending（須 register-output 補記）
  · grok: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: grok APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
rc=1
```

（預期：僅 composer 一家已戳；待 codex／grok 戳記 + register-output 後全綠。）

### completeness_check.sh --lock

```
COMPLETENESS PASS: .../20260805-govb0-spec-r7-codex.md — 2/2 個 ID 全在綜合檔。
COMPLETENESS PASS: .../20260805-govb0-spec-r7-composer.md — 2/2 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
rc=0
```

### template_check.sh spec

```
TEMPLATE PASS (spec): docs/GOVB0_FRICTION_SPEC.md 含全部必填錨點，且無明顯空殼。
rc=0
```

## 附加 probe（本輪實跑）

`bash /tmp/govb0-r7-delimiter-probe.sh` rc=0；`bash /tmp/govb0-r7-expansion-attack.sh` rc=0。

---

ASSUMPTIONS_VERIFIED: H-1/H-2 ID 歸戶逐條對照附錄；八字元 bash rc=0；# bash rc=2；span 邊界 EXTERNAL_EXECUTED 未誤吞；殘留方向 fail-closed／單路徑鎖死非雙 CLI。
TESTS_RUN: reconcile_stamps_check rc=1（缺他族戳記）；completeness_check --lock rc=0；template_check rc=0；delimiter/expansion probes rc=0。
FAILURES_SEEN: reconcile_stamps_check 缺 codex/grok 戳記 + provenance pending（stamp 輪預期）。
SCOPE_CHANGES: none（僅 synth.md `## 戳記` append 一行）。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_OUTPUT: handoffs/20260805-govb0-r7-stamp-composer.md
/tmp 清理：環境權限拒絕 `rm -rf`；**請手動刪除** `/tmp/frtest.*`、`/tmp/govb0-r6-composer-work`、`/tmp/govb0-r7-*`（**保留** `/tmp/claude-501`）。

STATUS: DONE
