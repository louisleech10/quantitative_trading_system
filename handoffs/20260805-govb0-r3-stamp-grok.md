# GOVB0-R3-STAMP — grok（第三方複核歸戶正確性）

**task-id**: `GOVB0-R3-STAMP`  
**家族**: grok（implementer；R3 review 角色閘外，本輪僅審群集／處置忠實度）  
**標的**: `handoffs/reconcile/20260805-govb0-spec-r3/synth.md`  
**body sha256**（`## 戳記` 前）: `edda2ccd9f1cbc38622f564826fbec654a29ac23135f634ad9feaa3153c91be7`  
**判定**: **REJECTED**（不寫 APPROVED）

---

## 改了哪一行（diff）

僅在 `## 戳記` 區段之後 append 一行 REJECTED 戳記；其餘位元組未動。

```
+ RECONCILE-STAMP: grok REJECTED 2026-08-05 sha256:edda2ccd9f1cbc38622f564826fbec654a29ac23135f634ad9feaa3153c91be7 task:GOVB0-R3-STAMP — F-4/F-6 COMPOSER ID 對調：E-10 群誤掛 COMPOSER-R3-P1-02、1b 語料群誤掛 COMPOSER-R3-P1-01（應互換）
```

---

## 檢查器完整 stdout 與 rc

### `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260805-govb0-spec-r3/synth.md`

```
edda2ccd9f1cbc38622f564826fbec654a29ac23135f634ad9feaa3153c91be7
```
rc=0（與 brief 戳記格式內 sha256 一致）

### `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r3/synth.md`

（本輪為第一次戳記輪；拒章後仍缺三家 APPROVED，預期 FAIL）

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r3/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · composer: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: composer APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · grok: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: grok APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:edda2ccd9f1cbc38622f564826fbec654a29ac23135f634ad9feaa3153c91be7 task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```
rc=1

### `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-spec-r3/sources.lock`

```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r3/sources/20260805-govb0-spec-r3-codex.md — 5/5 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r3/sources/20260805-govb0-spec-r3-composer.md — 6/6 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```
rc=0（**維持 0**；附錄有 ID ≠ 群集表歸戶正確，`票 B-36` 盲點再證）

---

## 1. 逐 ID 歸戶核對（附錄 vs 群集表）

| 附錄 ID | 附錄主張（摘要） | 現行群集 | 歸戶正確？ |
|---|---|---|---|
| `CODEX-R3-P0-01` | Task 0.1 不變式 vs 全 JSON diff 互斥 | F-1 | **OK** |
| `CODEX-R3-P0-02` | 契約 4 項未定結果 + 1b 與 shell/sed 衝突 | F-2 | **OK** |
| `CODEX-R3-P0-03` | lock ownership/release/retry/被拒狀態 | F-3 | **OK** |
| `CODEX-R3-P1-04` | E-10 ≥50／≥3 session 未落 SPEC；10–19 未定義 | F-4 | **OK**（codex 半） |
| `CODEX-R3-P1-05` | B-36 併 B-13、產出端預列 ID | F-7 | **OK** |
| `COMPOSER-R3-P0-01` | 同 F-1 互斥 | F-1 | **OK** |
| `COMPOSER-R3-P1-01` | **E-10 ≥50／≥3 session／不得宣稱完工未落 SPEC** | **F-6**（表寫 1b 語料） | **錯** |
| `COMPOSER-R3-P1-02` | **Task 2.1 未列 1b／b15probe6 具名語料** | **F-4**（表寫 E-10） | **錯** |
| `COMPOSER-R3-P1-03` | 逾時 failed 後同 out 重派生命週期 | F-3 | **OK** |
| `COMPOSER-R3-P2-01` | 契約「10 項」vs 1+1b+2–10＝11 | F-5 | **OK** |
| `COMPOSER-R3-P2-02` | B-36 產出端預列 | F-7 | **OK** |

**拒章根因（byte-level ID 對調，非語意模糊）**

- 附錄 `## COMPOSER-R3-P1-01` 斷言首句＝E-10 定稿門檻；表 F-4 卻掛 `COMPOSER-R3-P1-02`，F-6 卻掛 `COMPOSER-R3-P1-01`。
- 附錄 `## COMPOSER-R3-P1-02` 斷言首句＝1b 具名語料；與 F-6 主張一致，但表把該 ID 寫在 F-4。
- 來源 `sources/20260805-govb0-spec-r3-composer.md` 與附錄一致（P1-01＝E-10、P1-02＝1b）。
- 主委自陳已修「P1-02／P2-01／P2-02 誤寫成 P0-02／P1-04／P2-01」；**現行表對 P2-01／P2-02 正確，但 P1-01↔P1-02 仍對調**——同病根第五次現形。

**應改正（主委修表後再戳；本輪不改群集段）**

| 群 | 對應 finding 應為 |
|---|---|
| F-4（E-10） | `CODEX-R3-P1-04`／`COMPOSER-R3-P1-01` |
| F-6（1b 語料） | `COMPOSER-R3-P1-02` |

其餘 F-1／F-2／F-3／F-5／F-7 歸戶與處置方向與附錄一致；11 條皆有入表（無漏 ID），問題是 **2 條 COMPOSER ID 交叉錯掛**。

---

## 2. 主委三組裁決表態

### F-2 契約四項 — **同意**（實質）

| 項 | 主委判定 | grok |
|---|---|---|
| unquoted `-c` | BLOCK | 同意：語意＝執行該命令 |
| 遞迴深度 | 上限 3、逾限 fail-closed | 同意：派工嵌套極淺；fail-closed 與 gate 方向一致 |
| 跳脫引號 | 不終止 span；邊界不定 fail-closed | 同意：與未閉合引號同向 |
| heredoc | 本體＝引號 span；外層照常 | 同意：避免 heredoc 內容誤擋（對齊 R2 heredoc 教訓） |

### F-2 第二半放寬至 awk — **同意**（實質）

- CODEX-R3-P0-02 要求明文解除「純 shell/sed」並附 latency receipt。
- 主委引用 `bash handoffs/govb0_probes/awk_hotpath_bench.sh` → +5 ms／次（vs 正常 ~80 ms、分類器 2.3–3 s）⇒ 熱路徑可接受量級。
- 維持禁 python 正確。
- 殘留「R4 brief 再請委員裁定」屬可選加固，不構成拒章理由。

### F-3 lock 生命週期 — **同意**（實質，含「被拒不寫 result_state」）

| 子項 | 裁決 | grok |
|---|---|---|
| ownership | attempt id（pid＋UTC 起始） | 同意 |
| release | `_emit_family_result` 後必定釋放（不依賴 publish） | 同意：避免永久鎖死 |
| stale | pid 死 **或** 逾（家族 timeout＋外層安全閥） | 同意 |
| failed 後同 out 重派 | 正常放行 | 同意：對齊 COMPOSER-R3-P1-03 |
| 被拒 attempt | **不寫 `result_state`**，只記拒絕 audit | **同意且自洽** |

**「被拒不寫 result_state」自洽說明**：`result_state` 三值語意＝CLI 已啟動後的終態；被拒＝未啟動 ⇒ 不應進 duration／三值分母。Task 3.1 統計與 Task 3.3 定稿樣本應定義為「已啟動 attempt」；「每 attempt 恰一筆 result_state」須改寫為「每**已啟動** attempt 恰一筆」，被拒另計 audit 事件。此為文字閉合，非隱藏掉項。

**三組裁決本身無隱藏掉項**；拒章僅因 F-4／F-6 ID 對調，裁決內容可在修 ID 後沿用。

---

## 3. E-SCOPE — **維持接受**（不改立場）

四項（截斷 oracle B-35／B-34 語意閉合／B-24 機械強制面／B-15 FP-2）不使本批交付物本身失效；R3 codex 已 OUT-OF-SCOPE。無拒章依據。

---

## 4. 攻擊「accretion 已中止」

**部分同意、有條件。**

- **支持中止說**：R3 11 條中 F-1／F-4／F-5 確為「A 改 B 未同步」漏改；F-2／F-3 為 R3 只列項目未定結果（閉合型，非新機制分叉）；F-6／F-7 為驗收語料與治理債歸屬。未見與 R1/R2 同量級的**新機制**缺口（例如再發明第三套 gate 語意）。
- **攻擊點**：本輪仍出現 **ID 對調**（主委自陳修完後仍錯），證明交叉引用病根未解。若 R4 只閉合文字卻再漂計數／漏掛 finding，可能再出 P0 **計數／驗收自相矛盾**（F-1 病型），而非新演算法。
- **是否再開 R5 的建議**：R4 若嚴格只做 F-1～F-7 閉合＋「N 項旁註 `grep -c` 導出命令」紀律，**預期不必 R5**；若 R4 又引入未定結果的新契約列或再漏同步，才升級。本輪 **ID 錯掛本身不構成新 P0 機制**，但足以拒章至主委修表。

---

## 產出與清理

- 產出：`handoffs/20260805-govb0-r3-stamp-grok.md`
- synth：僅 `## 戳記` append REJECTED 一行
- `/tmp`：移除本輪 `govb0_r3_*_grok.out`；保留 `claude-501`

---

ASSUMPTIONS_VERIFIED: body hash = edda2ccd…；附錄 COMPOSER-R3-P1-01＝E-10、P1-02＝1b（與 sources/composer 一致）；F-4/F-6 表 ID 對調
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`reconcile_stamps_check.sh` rc=1（預期，無 APPROVED）；`completeness_check --lock` rc=0
FAILURES_SEEN: none（拒章為實質發現，非腳本故障）
SCOPE_CHANGES: none（未改群集／附錄）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
