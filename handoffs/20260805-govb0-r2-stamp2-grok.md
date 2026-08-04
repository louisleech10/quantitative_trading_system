# GOVB0-R2-STAMP2 — grok 第三方複核戳記（第二輪）

**task-id**: `GOVB0-R2-STAMP2`  
**家族**: grok  
**角色**: 第三方複核歸戶正確性（implementer；非 R2 審查者，無自身 findings）  
**目標**: `handoffs/reconcile/20260805-govb0-spec-r2/synth.md`  
**body hash**: `sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6`（`bash scripts/reconcile_body_hash.sh` 實跑相符；與 brief 逐字一致）

## 裁決

**蓋章（APPROVED）** — 已 append：

```
RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6 task:GOVB0-R2-STAMP2
```

## 改動（僅 `## 戳記` 區段）

相對蓋章前：在 `## 戳記` 之後 **append 一行**（本家族）；未改 body 任何位元組。  
並發收斂後 `## 戳記` 三家皆在（composer／codex／grok），hash 與 task-id 一致。本家族只 append 了 grok 那一行。

```
RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6 task:GOVB0-R2-STAMP2
RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6 task:GOVB0-R2-STAMP2
RECONCILE-STAMP: grok APPROVED 2026-08-05 sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6 task:GOVB0-R2-STAMP2
```

## 機械對帳：附錄 ID ↔ 群集表（自檢複核）

方法：`## 附錄` 後 `^## (CODEX|COMPOSER)-R2-…` heading 集合 vs 附錄前 backtick ID 集合。

| 集合 | 結果 |
|---|---|
| 附錄 heading 數 | **17** |
| 群集表引用 unique ID 數 | **17** |
| in app not cluster | **[]**（空） |
| in cluster not app | **[]**（空） |

⇒ 主委「17/17 皆在群集表」自檢 **可靠**（本輪機械複核一致）。  
第一輪漏戶的 `COMPOSER-R2-P1-01` 已掛 **E-13**。  
`completeness_check --lock` 仍只驗「ID 在檔案」⇒ 附錄 byte-faithful 使 rc=0 **不**證明群集歸戶；盲點描述屬實。

### 逐條歸戶結果

| 附錄 ID | 群集 | 主張 vs 附錄 | 判定 |
|---|---|---|---|
| `CODEX-R2-P0-01` | E-5 → E-SCOPE | terminal marker ≠ 完整性 oracle；PARTIAL 不受理截斷 oracle | OK |
| `CODEX-R2-P0-02` | E-6 | 並發雙成功 vs 單一 final；**改設計＝序列化拒絕** | OK |
| `CODEX-R2-P0-03` | E-7 | schema 與「判定不變」矛盾；分離 decision/audit | OK |
| `CODEX-R2-P0-04` | E-3 **與** E-4 | unquoted `-c`／遞迴／escape 主在 E-4；E-3 因文中亦提 eval 外層而雙掛 | 可辯；非拒章 |
| `CODEX-R2-P0-05` | E-1 | 11 Task vs §V 10 Task | OK |
| `CODEX-R2-P0-06` | E-11 → E-SCOPE | B-34 roster vs 角色閘 | OK |
| `CODEX-R2-P1-07` | E-10 | 定稿門檻採 codex ≥50＋≥3 session／日期；暫定值取捨見下 | OK（見 E-10） |
| `CODEX-R2-P1-08` | E-9 | publish vs timeout/kill 順序 | OK |
| `CODEX-R2-P1-09` | E-2 | §V「非 rc」不實 | OK |
| `CODEX-R2-P1-10` | E-8 | Phase0 vs Phase2 baseline | OK |
| `COMPOSER-R2-P0-01` | E-3 | eval／`$()`／反引號／子 shell fail-open | OK；探針相符 |
| `COMPOSER-R2-P1-01` | **E-13**（本輪補） | 契約 3–5 項 vs 原型落差；禁止照抄原型即完工 | OK |
| `COMPOSER-R2-P1-02` | E-4 | heredoc 假陽性 | OK |
| `COMPOSER-R2-P1-03` | E-11 → E-SCOPE | 同 B-34 | OK |
| `COMPOSER-R2-P1-04` | E-10 | timeout 樣本門檻 | OK |
| `COMPOSER-R2-P2-01` | E-2 | §V 過度宣稱 | OK |
| `COMPOSER-R2-P2-02` | E-12 | 紀律面＋機械面 SPLIT | OK |

### 殘餘觀察（不拒章）

群集表 **E-10 處置欄**仍寫「採 composer Q4 門檻」，而 **E-10 正文**已改採 codex ≥50＋≥3 session／日期，composer ≥20 僅作中途 sanity。  
正文為可執行裁決且明示取捨；表頭短標過時。屬文件一致性瑕疵，**不**使歸戶失效，亦不推翻 MISMATCH_2 的正文修正。R3 起草應以 **E-10 正文**為準，勿只抄表頭四字。

## E-10 暫定值取捨立場

**同意**主委：未達門檻時機制上線並標 `PROVISIONAL`、Task 3.3 不得宣稱完工。  
理由：無 timeout 正是 `B-14` 空等 2h20m 的成因；「有暫定 timeout」嚴格優於「無 timeout」。定稿門檻本身已採 codex 較嚴者，與「未達門檻不得把暫定值當完工」在語意上可並存（PROVISIONAL 標籤＝未完工）。

## E-3 探針獨立重跑

### `bash handoffs/govb0_probes/b15probe4.sh` → rc=0

四向量在**現行 gate** 與 **proto2** 皆 fail-open（`CURRENT=ALLOW`／`proto2=ALLOW`，want=BLOCK）：

- `eval "codex exec x"`
- `out=$(codex exec x)`
- 反引號
- `(codex exec x)`

### `bash handoffs/govb0_probes/b15probe5.sh` → rc=0

- `proto3=ok` 列數 = **26**；`proto3=XX` 列數 = **0** → **26/26 全對**（與 synth 宣稱一致）。

## E-6 改設計立場

**同意**序列化拒絕第二 attempt：消除「兩份成功皆不得遺失」與單一 final `<out>` 的矛盾；比仲裁／雙 archive 簡單且不進入「遺失」問題。

## E-SCOPE 四項不受理立場

| 不受理項 | 立場 | 使本批交付物失效？ |
|---|---|---|
| 產出截斷偵測 oracle（`CODEX-R2-P0-01`） | 接受。B-14 原始病＝不退出；attempt-scoped publish 已蓋 stale／覆蓋／未完成 | **否** |
| `B-34` 語意閉合 | 接受本批權宜 `brief-kind:stamp`；結構洞已開票 | **否** |
| `B-24` 機械強制面 | 接受 R1 D-6 SPLIT；E-12 強制 TODO 標部分完成 | **否** |
| `B-15` FP-2 定位 | 接受待 Phase 0 紀錄 | **否** |

四項皆不夠完美而非交付失效 ⇒ 依使用者 95% 取捨接受。

## 驗收命令（rc 直接取，未經 pipe）

### body hash

```
$ bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260805-govb0-spec-r2/synth.md
8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6
hash_rc=0
```

### `reconcile_stamps_check.sh` 完整 stdout + rc（三家章齊後重跑）

```
RECONCILE-STAMP FAIL: handoffs/reconcile/20260805-govb0-spec-r2/synth.md 未獲全數委員核可:
  · codex: provenance 不符 — ERROR: task:GOVB0-R2-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · composer: provenance 不符 — ERROR: task:GOVB0-R2-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  · grok: provenance 不符 — ERROR: task:GOVB0-R2-STAMP2 輸出 hash 仍為 pending（須 register-output 補記）
  → 委員須各審後 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:8b8d0a948782f9d8ef04117bcd17b6d94c1f6a62c10e56e6d6f547b8bd1e88a6 task:<harness-task-id>'。
  → 使用者稽核反偽造:對照 task:<id> 的 harness 輸出(tasks/<id>.output)與 .claude/gate/audit.log,確認委員真跑真核可。
```

**stamps_rc=1**

狀態解讀（驗收＝狀態，不是 rc）：  
- 三家 APPROVED 行皆已就位（hash／task-id 正確）。  
- rc=1 **僅**因 `register-output` 仍 pending（主委側補記），非內容或缺章。

### `completeness_check.sh --lock` 完整 stdout + rc

```
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r2/sources/20260805-govb0-spec-r2-codex.md — 10/10 個 ID 全在綜合檔。
COMPLETENESS PASS: /Users/louis/Desktop/quantitative_trading_system/handoffs/reconcile/20260805-govb0-spec-r2/sources/20260805-govb0-spec-r2-composer.md — 7/7 個 ID 全在綜合檔。
COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層): 全來源 heading ID 皆在綜合且 body/digest/lock 合法。
```

**completeness_rc=0**

## /tmp 清理

刪除本任務 `/tmp/b15probe4.out`、`/tmp/b15probe5.out`、`/tmp/stamps_check.out`、`/tmp/completeness_check.out`、`/tmp/govb0_ids_*`、`/tmp/app_ids.txt`、`/tmp/clu_ids.txt`。**保留** `claude-501`。不碰 `data_cache/`、不 git restore、不 commit。

---

ASSUMPTIONS_VERIFIED: body hash=8b8d0a94… 與 brief 相符；附錄 17 ID 機械差集空；E-13 掛 COMPOSER-R2-P1-01；b15probe4 四向量現行 fail-open；b15probe5 26/26  
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`b15probe4.sh` rc=0；`b15probe5.sh` rc=0；`reconcile_stamps_check.sh` rc=1（三家 APPROVED 齊；僅 register-output pending）；`completeness_check --lock` rc=0  
FAILURES_SEEN: 第一輪漏戶／E-10 弱化已在本版正文修正；表頭 E-10 短標殘餘不拒章  
SCOPE_CHANGES: none（只 append 戳記一行）  
NUMERIC_OR_SCHEMA_IMPACT: none  

OUTPUT_PATH: handoffs/20260805-govb0-r2-stamp2-grok.md  
STATUS: DONE
