# GOVB0-R4-STAMP — grok（第三方複核歸戶正確性）

**task-id**: `GOVB0-R4-STAMP`  
**家族**: grok（implementer；R4 review 角色閘外，本輪僅審群集／處置忠實度 + 三類主委修改）  
**標的**: `handoffs/reconcile/20260805-govb0-spec-r4/synth.md`  
**body sha256**（`## 戳記` 前）: `ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa`  
**判定**: **APPROVED**

---

## 改了哪一行（diff）

僅在 `## 戳記` 區段之後 append 一行；本體位元組未動（body hash 前後一致）。

```diff
 ## 戳記
 
 RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:GOVB0-R4-STAMP
+
+RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:GOVB0-R4-STAMP
```

（composer 行在本輪開工時已存在；本 agent 只 append grok 行。）

---

## 檢查器完整 stdout 與 rc

### `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md`

```
ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa
```
rc=0（與 brief 戳記格式內 sha256 一致）

### `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md`

（本輪為第一次戳記輪；蓋章後仍缺 codex APPROVED，預期 FAIL）

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r4/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```
rc=1

（append 當下首次跑時另見 composer／grok `provenance … pending（須 register-output）`；複跑後僅剩 codex 缺章。register-output 屬 harness／主委側，非本輪改碼範圍。）

### `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r4/sources.lock`

```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r4/sources/20260805-govb0-spec-r4-codex.md — 3/3 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r4/sources/20260805-govb0-spec-r4-composer.md — 5/5 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```
rc=0（**維持 0**）

### `python3 scripts/verification_claim_check.py --files handoffs/reconcile/20260805-govb0-spec-r4/synth.md`

（stdout 空）  
rc=0（**維持 0**）

---

## 1. 逐 ID 歸戶核對（附錄 vs 群集表）

方法：`awk` 自附錄抽「ID → 斷言首句」，再逐列對表「對應 finding」欄（byte-level ID，非只看語意）。

| 附錄 ID | 附錄主張（首句摘要） | 群集 | 歸戶 |
|---|---|---|---|
| `CODEX-R4-P0-01` | heredoc 無可執行 delimiter/body 邊界；valid 後真派工可漏掃 | G-1 | **OK** |
| `COMPOSER-R4-P1-03` | 契約第 10 項 heredoc 未定義機械起訖規則 | G-1 | **OK**（與 P0-01 同題合群；嚴者 ACCEPT-BLOCKING 合理） |
| `CODEX-R4-P0-02` | lock 未閉合外部刪／outer-timeout／跨裝置／stale owner-safe release | G-2 | **OK** |
| `COMPOSER-R4-P2-02` | lock 被外部刪但 attempt 仍活 → 可能第二派工 | G-2 | **OK**（子集併入 G-2 寬主張；處置含「存活中＝lock∪進程」對得上） |
| `CODEX-R4-P2-01` | §A 已驗證事實計數 vs FACT-RECEIPT 數不一致 | G-3 | **OK** |
| `COMPOSER-R4-P1-01` | Task 2.1／3.3 交叉引用 P1-01↔P1-02 對調 | G-4 | **OK** |
| `COMPOSER-R4-P1-02` | F-7／B-36 具名殘留只寫 backlog、SPEC 漏記 | G-5 | **OK** |
| `COMPOSER-R4-P2-01` | Task 3.3 改法有 PROVISIONAL，驗證段無狀態斷言 | G-6 | **OK** |

- 附錄 8 ID 與群集表 8 ID **差集皆空**（無漏、無多）。
- **本輪未再現 R1–R3 的 ID 錯位**。主委「先 awk 對照表再填」作法在本檔有效（至少此一次）。
- 機檢仍盲：`completeness_check --lock` rc=0 只證明「ID 出現」，**不能**代替語意歸戶（`票 B-36`／`B-13` 殘留仍真）。

---

## 2. 對三類主委修改的攻擊

### 修改 1：移除假豁免 `VERIFY-EXEMPT:doc-summary:*`

**屬實，無掩飾。**

實讀 `scripts/verification_claim_check.py:97-99`：

```
EXEMPT_RE = … VERIFY-EXEMPT:(typo|doc-example|migration-note|template-drift|tooling-blocked|spec-ambiguity):…
```

`doc-summary` **不在六類** → 原 token 自始無效。現行檔僅在敘事中點名「假豁免已移除」，**未再寫任何 VERIFY-EXEMPT**；改為「不自證／待 R5」屬誠實降級，非換皮豁免。

### 修改 2：G-3／G-4 真 receipt；G-1／G-2／G-5／G-6 不自證

| 群 | 本輪複驗 | 結論 |
|---|---|---|
| G-3 | `grep -c '^- FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` → `10`；§A 標題寫 10 並附同命令 | receipt 真 |
| G-4 | `grep -n 'COMPOSER-R3-P1-0' …` → Task 2.1 語境 `P1-02`（:239）、Task 3.3 語境 `P1-01`（:417） | 與表一致；**以 Task 定位正確** |
| G-5 | `grep -n 'B-36' docs/GOVB0_FRICTION_SPEC.md` → :492／:495／:497 有「ID 錯位無機械防線」 | **現在就能有 receipt**，標「不自證」偏保守 |
| G-6 | Task 3.3 驗證段已有 ①PROVISIONAL ②未完工 ③B-14 未定稿／任一缺 FAIL（約 :436-437） | 補丁存在；本檔不自證＝未在收斂檔重跑，非假修 |
| G-1 | SPEC 契約第 10 項已有五條機械規則＋5 組語料（約 :191-199） | 文字在；深度可執行性仍宜 R5 確認 |
| G-2 | owner-safe release／8 路徑狀態斷言已寫入 Task 3.2 區（約 :360-391） | 文字在；路徑完整性宜 R5 確認 |

**攻擊結論**：四條「不自證」**不是**把責任推給無人驗——主委已明訂 **R5 確認輪**為驗證關。  
G-5（及可部分 grep 的 G-6）**便宜 receipt 可現做**；未做＝程序偏懶，**不構成掩飾「未修」**（grep 已見補丁）。**不因此拒章。**

若主委要消掉「推責」觀感：R5 前可補  
`VERIFY:govb0-r4-g5-b36 — grep -n 'B-36' docs/GOVB0_FRICTION_SPEC.md → 非空`。

### 修改 3：行號 → Task 定位

群集段**不再用行號當定位主鍵**；僅在病史段保留「初稿 :237/:398 → 漂移 :239/:417」作為病型敘事（`票 B-17`／`B-13` 第 8 次）——合理。  
附錄內行號屬 byte-faithful 委員原文，**不得改**，非本檔回歸。

**殘留易腐引用（非拒章級）**：

1. 附錄內 `:230`／`:387` 等（byte-faithful；已知易腐）。
2. 趨勢數列「19→17→11→8」與「2 P0」——未鎖來源命令；若只作敘事可接受，但**勿當 claim 背書**。
3. VERIFY 區 `template_check`／Task=11 等為本輪背景，非 G 列主鍵。

---

## 3. `E-SCOPE` 立場

**維持接受，不重開。**

四項（截斷 oracle `B-35`／`B-34` 語意閉合／`B-24` 機械強制面／`B-15` FP-2 定位）已於 R2 戳記輪接受；R4 附錄**未**再提異議。本輪無失效路徑主張。

---

## 4. 是否還需要 R5 — 表態 **(a) 有必要**

理由：

1. 主委已裁「以 codex 較嚴版」開 R5；出場判準「新 P0 機制缺口 <2」在 R4 收斂敘事中仍指 G-1／G-2 兩道機制。
2. G-1／G-2 處置寫「已修」但收斂檔**無機械 receipt**——確認輪是唯一命名的關閉關卡；省 R5 會讓 P0 契約修補只靠主委自述。
3. 選 (b) 若要把確認併入 TODO 審查輪：須明說併入 **TODO 生成後的 TODO adversarial 輪**，且 G-1／G-2 須在該輪列為 **blocking 確認項**。憲法「完整管線不得跳步」下，**(b) 不是跳過審查**；但本批機制風險仍以 **獨立 R5 確認輪**較乾淨。
4. G-5／G-6 本輪第三方已 spot-check 文字存在；R5 可快速關閉，預期新增 P0 類型＝**契約規則與語料／狀態斷言是否真可機檢**，而非再重開 E-SCOPE。

---

## 5. /tmp 清理

本輪**未**建立專用 workdir。  
`/tmp/claude-501` **保留**。  
未刪 `/tmp/frtest.*`／`/tmp/sessions`（時間戳屬其他程序／較早 session，歸屬不明，避免誤清）。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: EXEMPT_RE 六類無 doc-summary；body hash=ae304eeb…；8/8 ID 歸戶正確；G-3 count=10；G-4 Task2.1=P1-02／Task3.3=P1-01；G-5 B-36 已在 SPEC；G-1/G-2/G-6 文字補丁存在
TESTS_RUN: reconcile_body_hash rc=0；reconcile_stamps_check rc=1（缺 codex，預期）；completeness --lock rc=0；verification_claim_check rc=0；grep FACT-RECEIPT→10；grep COMPOSER-R3-P1-0／B-36 見上
FAILURES_SEEN: none（歸戶無錯位；stamps_check 全綠非本輪目標）
SCOPE_CHANGES: none（只 append ## 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
```

產出檔: `handoffs/20260805-govb0-r4-stamp-grok.md`  
標的戳記行: `RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:ae304eeb2dd9b22d24070ce12d8dedf1f2dd574e522a7ca8d942ec9ddf88b3fa task:GOVB0-R4-STAMP`

STATUS: DONE
