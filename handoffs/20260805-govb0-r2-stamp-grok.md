# GOVB0-R2-STAMP — grok 第三方複核戳記

**task-id**: `GOVB0-R2-STAMP`  
**家族**: grok  
**角色**: 第三方複核歸戶正確性（implementer；非 R2 審查者，無自身 findings）  
**目標**: `handoffs/reconcile/20260805-govb0-spec-r2/synth.md`  
**body hash 核對**: `sha256:4f659b945c6c7df23814f5c4ad80611f7e32bfea4645ea418838c39ba34428e3`（`bash scripts/reconcile_body_hash.sh` 實跑相符）

## 裁決

**拒章（不 append RECONCILE-STAMP）**

理由：群集表自稱「17 條全部歸戶，**無未分群 ID**」與機械對帳不符——附錄 17 個 finding heading 中，**`COMPOSER-R2-P1-01` 未出現在任一 E 群或 E-SCOPE 的「對應 finding」欄**。依 brief「任一條被歸錯群／遺漏 ⇒ 不要蓋章」。

## 改動範圍

- **未改動** `synth.md` 任何位元組（含 `## 戳記` 區段仍為空）。
- 本檔為產出說明；不 commit、不 push。

## 機械對帳（附錄 ID ↔ 群集表）

命令：對 `## 附錄` 後 `^## (CODEX|COMPOSER)-R2-…` heading 與群集段 backtick ID 做 set 差集。

| 集合 | 結果 |
|---|---|
| 附錄 heading 數 | 17 |
| 群集表引用 unique ID 數 | 16 |
| **in app not cluster** | **`COMPOSER-R2-P1-01`** |
| in cluster not app | `[]` |

### 逐條歸戶結果

| 附錄 ID | 群集 | 主張 vs 附錄主張 | 判定 |
|---|---|---|---|
| `CODEX-R2-P0-01` | E-5 → E-SCOPE | terminal marker ≠ 完整性 oracle；PARTIAL 不受理截斷 oracle | OK（見 E-SCOPE 立場） |
| `CODEX-R2-P0-02` | E-6 | 並發雙成功 vs 單一 final path；**改設計＝序列化拒絕** | OK（同意改設計） |
| `CODEX-R2-P0-03` | E-7 | schema 與「判定不變」矛盾；分離 decision trace / audit | OK |
| `CODEX-R2-P0-04` | E-3 **與** E-4 | 主斷言＝unquoted `-c`／遞迴 cap／escape／wrapper；E-4 正確。E-3 主斷言是 eval/`$()`／反引號／子 shell（主 ID 應為 `COMPOSER-R2-P0-01`）——**雙掛可辯，但 E-3 把本 ID 當主證偏鬆** | 次要瑕疵（非拒章主因） |
| `CODEX-R2-P0-05` | E-1 | 11 Task vs §V 10 Task | OK |
| `CODEX-R2-P0-06` | E-11 → E-SCOPE | B-34 roster vs 角色閘；明文化＋已開票 | OK（見 E-SCOPE） |
| `CODEX-R2-P1-07` | E-10 | 一次派工不足；門檻採 composer Q4（≥20／暫定）而非 codex 建議 ≥50 | OK（結構 ACCEPT；數值為主委裁） |
| `CODEX-R2-P1-08` | E-9 | publish vs timeout/kill 順序契約 | OK |
| `CODEX-R2-P1-09` | E-2 | §V「非 rc」不實；具名行號 | OK |
| `CODEX-R2-P1-10` | E-8 | Phase0 invariant vs Phase2 delta 共用 baseline | OK |
| `COMPOSER-R2-P0-01` | E-3 | eval／`$()`／反引號／子 shell fail-open | OK；E-3 探針獨立重跑相符 |
| **`COMPOSER-R2-P1-01`** | **（無）** | 契約第 3–5 項（引號路徑／路徑正規化／未閉合引號）原型②未實作、語料全 ALLOW | **漏戶 → 拒章** |
| `COMPOSER-R2-P1-02` | E-4 | heredoc 假陽性 | OK |
| `COMPOSER-R2-P1-03` | E-11 → E-SCOPE | 同 B-34 | OK |
| `COMPOSER-R2-P1-04` | E-10 | timeout 樣本門檻 | OK |
| `COMPOSER-R2-P2-01` | E-2 | §V 過度宣稱 | OK |
| `COMPOSER-R2-P2-02` | E-12 → E-SCOPE 機械面 | 紀律面標部分完成；機械面 SPLIT 外移 | OK |

### 漏戶細節：`COMPOSER-R2-P1-01`

- **附錄斷言**：Task 2.0 契約第 3–5 項要求測試，但主委原型②未實作多數項；`bash scripts/../scripts/cx_run.sh`、`"./my dir/codex" exec`、未閉合引號、`bash -c codex`、巢狀 `-c` 皆 ALLOW。
- **修法主張**：Task 2.0 驗證列出具名語料；Task 2.1 不得只寫「參考原型②」而不列缺口。
- **群集表**：E-3／E-4 只掛 `COMPOSER-R2-P0-01`／`CODEX-R2-P0-04`／`COMPOSER-R2-P1-02`，**無本 ID**。
- **E-3 正文／原型③ 26 條語料**亦未具名覆蓋路徑正規化／含空白引號路徑／未閉合引號等本 finding 語料。
- 結論：不是「語意可併入鄰群故省略 ID」可接受——brief 要求**逐條 ID 對應**；且 Verdict 的「無未分群 ID」為**客觀錯誤**。

**主委修復建議（僅建議，本輪不改 synth）**：新增 E 群或併入 E-4，明確掛 `COMPOSER-R2-P1-01`，處置至少 ACCEPT 並要求 R3 把該語料寫進 immutable corpus／Task 2.0 驗證；修正「17 條全部歸戶」句。

## E-3 主委探針獨立重跑

### `handoffs/govb0_probes/b15probe4.sh`（rc=0）

四向量在**現行 gate** 與 **proto2** 皆 fail-open（`CURRENT=ALLOW`／`proto2=ALLOW`，want=BLOCK）：

- `eval "codex exec x"`
- `out=$(codex exec x)`
- 反引號
- `(codex exec x)`

對照：`v=$(claude -p …)` 類「命令替換嵌 claude」→ CURRENT=BLOCK（子字串偶然命中）、proto2=ALLOW——與 synth 表「R2 收窄造成的回歸」方向一致。

### `handoffs/govb0_probes/b15probe5.sh`（rc=0）

- `proto3=ok` 列數 = 26；`proto3=XX` 列數 = 0 → **26/26 全對**（與 synth 宣稱一致）。
- TP 16（含 eval／`$()`／反引號／子 shell／xargs／絕對路徑等）BLOCK；TN 10 ALLOW。

E-3 處置 **ACCEPT-BLOCKING + 採原型③** 在探針層可支持；**不**因 E-3 拒章。

## E-6 改設計立場

**同意**主委裁決：並發「兩份成功皆不得遺失」與單一 final `<out>` 不相容；改為同 path **序列化拒絕第二 attempt** 比仲裁／雙 archive 簡單，且不進「遺失」問題。與 `CODEX-R2-P0-02` 的「須固定一種可執行規則」方向相容（選了第三條可執行路徑）。

## E-SCOPE 四項不受理立場

| 不受理項 | 立場 | 是否使本批交付物失效 |
|---|---|---|
| 產出截斷偵測 oracle（`CODEX-R2-P0-01`） | 接受。B-14 原始病＝不退出；attempt-scoped publish 已蓋 stale／覆蓋／未完成；截斷需 producer manifest，跨元件 | **否**（不夠完美；殘留開票即可） |
| `B-34` 語意閉合 | 接受本批權宜 `brief-kind:stamp`；結構洞已開票。本任務本身即該權宜路徑 | **否**（本批收斂可機檢通過後再獨立修 roster） |
| `B-24` 機械強制面 | 接受 R1 D-6 SPLIT；E-12 強制 TODO 標「部分完成」防假綠 | **否** |
| `B-15` FP-2 定位 | 接受待 Phase 0 紀錄；非 R2 新 finding | **否** |

四項皆**不足以**單獨構成「本批交付物本身失效」⇒ 若歸戶完整，**會**依使用者 95% 取捨接受 E-SCOPE 並蓋章。  
**本輪拒章唯一主因＝`COMPOSER-R2-P1-01` 漏戶 + Verdict 不實。**

## 驗收命令（rc 直接取，未經 pipe）

### body hash

```
$ bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260805-govb0-spec-r2/synth.md
4f659b945c6c7df23814f5c4ad80611f7e32bfea4645ea418838c39ba34428e3
hash_rc=0
```

與 brief 所列 sha256 **逐字相符**。

### `reconcile_stamps_check.sh` 完整 stdout + rc

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r2/synth.md 未獲全數委員核可:
  · codex: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: codex APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · composer: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: composer APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  · grok: 缺 APPROVED 戳記(須 '^RECONCILE-STAMP: grok APPROVED <YYYY-MM-DD> sha256:<hash> task:<id>')
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:4f659b945c6c7df23814f5c4ad80611f7e32bfea4645ea418838c39ba34428e3 task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

**stamps_rc=1**

狀態解讀（驗收＝狀態，不是 rc）：三家皆缺 APPROVED——本家族**有意拒章**；codex／composer 於本檢查時點亦尚未蓋章。預期 hash 已印出且與 body 一致。

### `completeness_check.sh --lock` 完整 stdout + rc

```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r2/sources/20260805-govb0-spec-r2-codex.md — 10/10 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r2/sources/20260805-govb0-spec-r2-composer.md — 7/7 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

**completeness_rc=0**（附錄 byte-faithful 層仍綠；**不**等於群集表歸戶完整。）

## /tmp 清理

保留 `claude-501`；刪除本任務產生之 `/tmp/b15probe4.out`、`/tmp/b15probe5.out`、`/tmp/stamps_check.out`、`/tmp/completeness_check.out`（及可識別的 session 工作檔）。不碰 `data_cache/`、不 git restore。

---

ASSUMPTIONS_VERIFIED: body hash=4f659b94… 與 brief 相符；附錄 17 ID 機械差集僅缺 COMPOSER-R2-P1-01；b15probe4 四向量現行 fail-open；b15probe5 26/26  
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`b15probe4.sh` rc=0；`b15probe5.sh` rc=0；`reconcile_stamps_check.sh` rc=1（三家缺章）；`completeness_check --lock` rc=0  
FAILURES_SEEN: 群集漏戶 COMPOSER-R2-P1-01（拒章原因）  
SCOPE_CHANGES: none（未改 synth）  
NUMERIC_OR_SCHEMA_IMPACT: none  

STATUS: DONE
