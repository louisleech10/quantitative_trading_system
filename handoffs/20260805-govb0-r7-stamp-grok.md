# GOVB0-R7-STAMP — grok 第三方複核戳記

**family**: grok（implementer；角色閘擋在 R7 review 之外，`票 B-34` 權宜第三方）  
**task-id**: `GOVB0-R7-STAMP`  
**date**: 2026-08-05  
**stamp-target**: `handoffs/reconcile/20260805-govb0-spec-r7/synth.md`  
**body sha256**: `b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd`  
**verdict**: **APPROVED**

---

## 改了哪一行（diff）

只 append 到 `## 戳記` 區段之後，本體 0 位元組變動（`reconcile_body_hash.sh` 前後同值）。

```diff
 ## 戳記
 RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP
 
 RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP
+
+RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP
```

最終戳記行（逐字）：
```
RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd task:GOVB0-R7-STAMP
```

---

## 1. 歸戶正確性（逐條 ID 對照附錄）

| 群 | synth 主張 | 附錄 finding ID | 附錄斷言核心 | 歸戶 |
|---|---|---|---|---|
| H-1 | ⑥(c) 允許清單非完整 shell-word grammar；`~{}[]!*?` 合法 delimiter 未列 ⇒ ⑦ 誤擋 | `CODEX-R7-P1-01` | unquoted allowlist 不完整；列 `~` `{` `}` `[` `]` `!` `*` `?` 會被⑦誤擋 | **正確** |
| H-1 | （同） | `COMPOSER-R7-P2-01` | 允許清單未收 `~` `{` `}` `[` `]` `!` `#` 等 ⇒ ⑦ 誤擋（非 fail-open） | **正確**（composer 多提 `#`，語意仍屬同一主張） |
| H-2 | reclaim lock 孤兒：③後④前 crash ⇒ 路徑鎖死 | `CODEX-R7-P1-02` | stale takeover ③後④前 crash 留永久 reclaim；後續 EEXIST | **正確** |
| H-2 | （同） | `COMPOSER-R7-P2-02` | ③後不 `rmdir` reclaim ⇒ 後續 takeover ① EEXIST | **正確** |

4/4 ID 皆出現於附錄；**無交叉對調**（H-1≠reclaim、H-2≠allowlist）。  
機械：sources 的 4 個 `##` heading 與 synth 附錄一致；`completeness_check --lock` rc=0。

---

## 2. 攻擊 H-1 的 SPEC 改動理由（⑥(c) 補入 8 字元）

**SPEC 現況**（`docs/GOVB0_FRICTION_SPEC.md:202`）：
`(c) ([A-Za-z0-9_.:+=,%@^~{}\[\]!*?-]+)` — 已含 `~{}[]!*?`。

### 2a. 「delimiter 位置只做 quote removal、不做展開」是否正確？

本機 bash 3.2.57 實跑（`/tmp/govb0-r7-stamp-grok-work/probe_delim.sh`）：

| 向量 | pure unquoted delimiter rc | body 是否 literal 完成 |
|---|---|---|
| `~` `{` `}` `[` `]` `!` `*` `?` 各 1 字 | **0** | BODY+AFTER 正常 |
| `{a,b}` | 0 | 無 brace expand（closing 須 literal `{a,b}`） |
| `~/` | 0 | 無 tilde expand |
| `*` pure | 0 | 無 glob |
| `$(echo DELIM)` 開、literal `$(echo DELIM)` 關 | 0 | 無 command-sub 於 delimiter |
| `$(echo DELIM)` 開、`DELIM` 關 | 0 但 heredoc 吞到 EOF | 證明 closing **不**認展開後字串 |

⇒ **主委理由成立**：這 8 字元在 delimiter 位置作 literal word，不做 glob／brace／tilde／cmd-sub 展開。  
（`!` history expand 在 non-interactive bash 預設關閉；gate 路徑為腳本／掃描字串，非互動 histexpand。）

### 2b. 補入 8 字元是否引入 fail-open？

- **開 span 前提**：scanner 與 shell 對 delimiter 邊界一致。上表證實 8 字元雙方皆 literal 接受 ⇒ **開 span 正確**，body 不掃描＝與 shell 一致。
- **原 fail-open 攻擊**（`EOF-1` 不開 span → body 內 `<<INNER` 錯開 span 吞真派工）屬「**欠列**」問題；補列是**收斂**該方向，不是放寬到 shell 不認的 delimiter。
- **反方向殘留**（欠列字元走⑦ BLOCK）＝過擋，見 §3。

⇒ **未觀察到 fail-open 引入**。

### 2c. 主委未納入 `#` — 是否恰當？

| 形 | bash rc（本機） | ⑥(c) 現況 |
|---|---|---|
| pure `<<#` | **2** syntax error（`#` 當 comment） | 不在 allowlist；⑦ BLOCK — **正確**（shell 本身不接受） |
| `<<'#'` quoted | 0 | 走 (a) 引號形，與 `#` 是否在 (c) 無關 |
| `<<EOF#` | 0（合法） | `#` 不在 (c) ⇒ ⑦ **誤擋** — 殘留過擋 |

⇒ **不納入 pure `#` 是對的**（shell 非法）。  
`EOF#` 等含 `#` 的 token 仍過擋 — 落在 H-1 具名殘留「枚舉非完整 grammar」，方向安全。composer 點名 `#` 已被「殘留一」覆蓋，無需拒章。

---

## 3. 殘留分類（獨立驗證，不因兩家同意而跳過）

### H-1 殘留：允許清單仍非完整 grammar

- 未列字元（含 `#` mid-token、`$`、`` ` ``、`()`、空白等）一律 ⑦ **BLOCK**。
- 方向＝**過擋（false positive）**，不是漏放（false negative）。
- 不會讓真派工穿過 gate；最壞＝合法罕見 heredoc 被擋 → friction，與 deliverable-invalidating 定義（漏放真派工／雙 CLI）不符。
- **分類 named-residual：接受。**

### H-2 殘留：reclaim 孤兒

- SPEC:411–417 步驟①–④ 無 crash recovery／TTL／orphan reclaim。
- ③後④前 crash：`reclaim.lockdir` 殘留 + 主 lock 已建或半完成 ⇒ 後續① EEXIST 拒絕。
- 最壞＝**單一 `<out>` 暫時不可用**（需人工 `rmdir` reclaim）。
- **不會**雙 CLI 並存：reclaim 互斥仍擋其他 takeover；主 lock 若已建則 ownership 仍在（或 pid 死等 stale，但 reclaim 卡住導致無法接管＝仍單路徑鎖死）。
- **不會**漏放真派工：拒絕＝fail-closed 可用性缺口。
- **分類 named-residual：接受。** 若判 deliverable-invalidating 須證明雙 CLI 或漏放路徑 — **本輪找不到**。

---

## 4. E-SCOPE 與既有殘留

`票 B-35`／`B-34`／`B-24` 機械面／`B-15` FP-2／`B-36` ID 錯位：R7 synth 未重開，SPEC §N 仍列為本批不受理。  
**立場不變，不拒章。**

---

## 三支檢查器（完整 stdout + rc，直接取）

### 1) `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md`
```
RECONCILE-STAMP PASS: handoffs/reconcile/20260805-govb0-spec-r7/synth.md 已獲 codex,composer,grok 全數 APPROVED 且本體雜湊相符(sha256:b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd)。
  使用者反偽造稽核:核對各戳記 task:<id> 對應的 harness 輸出確為該委員真跑真 APPROVED。
```
**rc=0**

### 2) `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r7/sources.lock`
```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r7/sources/20260805-govb0-spec-r7-codex.md — 2/2 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r7/sources/20260805-govb0-spec-r7-composer.md — 2/2 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```
**rc=0**

### 3) `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md`
```
TEMPLATE PASS (spec): docs/GOVB0_FRICTION_SPEC.md 含全部必填錨點，且無明顯空殼。
```
**rc=0**

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - H-1←CODEX-R7-P1-01+COMPOSER-R7-P2-01、H-2←CODEX-R7-P1-02+COMPOSER-R7-P2-02（附錄逐字對照）
  - SPEC:202 允許清單已含 ~{}[]!*?；§N R7 殘留表 ID 與 synth 一致
  - bash 3.2.57 實測 8 字元 unquoted delimiter rc=0 且無 expand；pure # 非法；EOF# 合法但走⑦
  - body sha256 = b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd（stamp 前後不變）
TESTS_RUN:
  - bash scripts/reconcile_stamps_check.sh …/synth.md → PASS rc=0（codex,composer,grok）
  - bash scripts/completeness_check.sh --lock …/sources.lock → PASS rc=0（4/4）
  - bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md → PASS rc=0
  - 本機 heredoc delimiter probe（8 字元 + # + expand 反例）→ 如上
FAILURES_SEEN: none
SCOPE_CHANGES: none（只 append 戳記一行）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**STATUS: DONE**
