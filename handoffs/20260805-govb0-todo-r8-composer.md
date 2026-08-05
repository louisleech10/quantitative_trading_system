# GOVB0-TODO-R8 — composer 確認輪審查報告

**家族**: COMPOSER　**task-id**: GOVB0-TODO-R8　**日期**: 2026-08-05
**標的**: `docs/GOVB0_FRICTION_TODO.md`（確認輪 R8；不重開已裁決事項）

## Verdict：需修補後派工

9 條主委修法**絕大多數已關閉**；B0 批次拓撲無新矛盾。但本輪修補引入 **2 條 P1**：`TEST-3.3-PROVISIONAL` 條件②自引用導致 `grep -c` 恆為 2（規格要求 ==1）；`TEST-3.3-B24-PARTIAL` 未給 bounded section 錨點且預設 `^## B-24 ` 區間內無「部分完成」。兩條皆可在 TODO Task 3.3 驗證欄就地修，無需重開 SPEC。

---

## §0 前提宣告

### fact-verified（本輪復跑）

| 宣稱 | 命令 | 結果 |
|---|---|---|
| TODO 範本合規 | `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` | `TEMPLATE PASS` rc=0 |
| Task 數對齊 | `grep -c '^\*\*Task ' docs/GOVB0_FRICTION_SPEC.md` / `grep -c '^### Task ' docs/GOVB0_FRICTION_TODO.md` | 11 / 11 |
| `_bc_kv` 為 mktemp 路徑 | `grep -n '_bc_kv' scripts/cx_run.sh` | `:39/:44/:45/:46/:47` |
| caller 方向 | `grep -n '_prepare_and_run\|_run_cli_and_emit' scripts/cx_run.sh` | `_prepare_and_run`(:501) 呼叫 `_run_cli_and_emit`(:513)；caller `:518/:521/:524` |
| B-14 未定稿 | `LC_ALL=C grep -c 未定稿 handoffs/20260801-GOV-AMEND-BACKLOG.md` | 4 |
| PROVISIONAL 字樣 | `grep -c PROVISIONAL docs/GOVB0_FRICTION_TODO.md` | 14（≥1 ✓） |
| 「未完工」字串出現次數 | `grep -c '本 Task 於本 TODO 產出時標記為「未完工」' docs/GOVB0_FRICTION_TODO.md` | **2**（規格要求 ==1，見 finding） |
| B-14 bounded 未定稿 | `awk '/^## B-14 /{f=1;n=0} f{print} /^## B-/{if(f&&n++)exit}' handoffs/20260801-GOV-AMEND-BACKLOG.md \| LC_ALL=C grep -c 未定稿` | 4（≥1 ✓） |
| B-24 bounded「部分完成」 | `awk '/^## B-24 /{f=1;n=0} f{print} /^## B-/{if(f&&n++)exit}' handoffs/20260801-GOV-AMEND-BACKLOG.md \| LC_ALL=C grep -c '部分完成'` | **0**（見 finding） |
| H-2 殘留字樣 | `grep -c 'reclaim 孤兒回收未實作' docs/GOVB0_FRICTION_TODO.md` | 1 |

### assumed（本輪優先攻，未實作驗證）

- 9 條修補彼此不衝突 — **B0 拓撲已查，無矛盾**；測試規格有 2 處自引用／錨點缺失（見 findings）。
- 追溯 100% — **§T 表內 ID 全覆蓋**；SPEC 另有 7 個具名 ID 未在 TODO 逐字出現（見逐項核對表 §3），多數為 E-SCOPE 殘留或語意已內嵌。
- 5 個新 Test ID 可構造 — **4/5 可證偽**；`TEST-3.3-B24-PARTIAL` 錨點未定義（見 finding）。

---

## 逐項核對表

### §1 上輪 9 條修補關閉確認

| 原 finding | 修法摘要 | 判定 | 本輪驗證 |
|---|---|---|---|
| codex P0-02 `_bc_kv`／caller 寫反 | Task 1.1 改用 `${_bk}`；修改 `_prepare_and_run`(:501-513)；caller `:518/:521/:524` | **CLOSED** | `grep -n` 實測與 TODO L190-218 一致 |
| codex P0-03 B5 排序悖論 | B0 前置批；B3 依賴 B0；B0→B3 硬 Gate；Task 2.5 只消費 snapshot | **CLOSED** | TODO L79-92、L410-413；B0 在 B3 前、B5 在 B3/B4 後，拓撲一致 |
| codex P1-04 §0 三項不可機械讀 | B-14 補未定稿；bounded section；manifest schema；5 個新 Test ID | **NOT-CLOSED** | B-14 條件③已修；但 `TEST-3.3-PROVISIONAL` ②自引用（finding P1-01）、`TEST-3.3-B24-PARTIAL` 錨點缺失（finding P1-02） |
| codex P1-01／P1-05 | 併入 P1-04 | **NOT-CLOSED** | 同上 |
| composer P1-01 OPEN-2／D-8 漏列 | §0.2 新增＋ASCII 錨點指引 | **CLOSED** | TODO L39-45 含 `[OPEN-2]`／`[D-8]`／`票 B-33` |
| composer P1-02 E-9 無 Test ID | 新增 `TEST-3.2-E9-ORDER`＋反向 mutation | **CLOSED** | TODO L578-583；先 wait 再 publish、計數==1、競態維持② |
| composer P1-03 PROVISIONAL 無機械錨點 | 併入 codex P1-04 | **NOT-CLOSED** | 同 P1-04（②自引用） |
| composer P2-01 Task 2.5 無 mutation | 新增 `TEST-2.5-MUT` 三 mutation | **CLOSED** | TODO L433-437；sha／標註／空語料各一＋要求貼 rc |

### §2 B0 引入矛盾複查

| 檢查點 | 結果 |
|---|---|
| B0 必須在 B3 前 vs B5 在 B3/B4 後 | **無矛盾** — B0 凍結舊版 `gate_check.sh`；B5 差集在所有 Phase 2 改動後執行，消費 B0 產物 |
| B0 Gate（`git ls-files`＋sha256）vs Task 2.5 fail-closed | **一致** — L90-92 與 L412-413 同語意 |
| B5 列「語料 B snapshot」用語 | **輕微歧義**（非 blocking）— 實際指 `gate_check_pre_phase2.sh.snapshot`（L410-411），非語料 B 檔本身；建議主委改措辭，不計 finding |
| Task 1.1 偽碼 `unknown` 分支用 `$kind` 非 `${_bk}` | **實作風險** — TODO L206；不計 finding（措辭／可讀性 OUT-OF-SCOPE） |

### §3 全量 SPEC 具名 ID 追溯（36 個去重 ID）

| SPEC ID | TODO 落點 | 狀態 |
|---|---|---|
| Task 0.1–3.3（11） | 各 Phase Task 段落 | ✓ |
| `E-SCOPE` | §0.2 L38；Task 3.2 要點 5 L524-525；§T L670 | ✓ |
| `H-1` | Task 2.0 要點 4 L278-280；Phase 0 前置 L118 | ✓ |
| `H-2` | §0.1 L20-24；Task 3.2 要點 8 L547-549；§T L672 | ✓ |
| `OPEN-1` | §0.2 L37；Task 3.3 L607-615 | ✓ |
| `OPEN-2`／`D-8` | §0.2 L39-45 | ✓ |
| `OPEN-3` | §0.2 L38 | ✓ |
| `E-10` | §0.1 L26-33；Task 3.3；§T L674 | ✓ |
| `E-9` | Task 3.2 `TEST-3.2-E9-ORDER` L578-583 | ✓ |
| `E-2`/`E-3`/`E-7`/`E-8` | Task 1.1 L232；Task 2.1 L316-349；Task 0.1 L146 | ✓ |
| `D-1`–`D-13`（除下） | 各 Task 內嵌 | 多數 ✓ |
| `D-4` | Task 2.5 語意已落（子集＋標註）但**未逐字標** | 隱式覆蓋 |
| `D-6` | §0.1 B-24 拆分語意；**未逐字標 D-6** | 隱式覆蓋 |
| `F-1` | `TEST-0.1-INVARIANCE` 承載；**未標 F-1** | 隱式覆蓋 |
| `F-3` | Task 3.2 lock 協定 L527-593；**未標 F-3** | 隱式覆蓋 |
| `F-6` | Task 2.1 `TEST-2.1-1B` L322 | ✓ |
| `F-7` | SPEC §N 殘留；TODO 未列 | OUT-OF-SCOPE（E-SCOPE／B-36 錯位債） |
| `B-14`/`B-15`/`B-24`/`B-30`/`B-32`/`B-33`/`B-35`/`B-37` | 各處 | ✓ |
| `B-13`/`B-34`/`B-36` | SPEC §N 殘留票；TODO 未列 | OUT-OF-SCOPE（E-SCOPE 四項） |

### §4 新增 5 個 Test ID 可證偽性

| Test ID | 可證偽？ | 說明 |
|---|---|---|
| `TEST-3.1-MANIFEST` | **是** | 49 筆→PROVISIONAL／50 筆 3 session→FINAL；`TEST-3.1-MANIFEST-MUT` 手填 FINAL 轉紅 |
| `TEST-3.2-E9-ORDER` | **是** | ①先 wait ②計數==1 ③競態；反向：publish 前移／移除計數守衛 |
| `TEST-3.2-LOCK-⑬` | **是** | deterministic SIGKILL 於 ③→④；斷言孤兒＋EEXIST；修法 (a/b/c) 時改斷言③＋mutation |
| `TEST-2.5-MUT` | **是** | 三 mutation（sha 守衛／標註守衛／空語料）各須貼 rc |
| `TEST-3.3-B24-PARTIAL` | **否（現狀）** | 未給 `^## …` 錨點；預設 `^## B-24 ` 區間 `grep -c 部分完成`==0；「部分完成」在 L1507 拆分裁決節 |

---

## COMPOSER-R8-P1-01

**斷言**: `TEST-3.3-PROVISIONAL` 條件②要求 `grep -c '本 Task 於本 TODO 產出時標記為「未完工」' docs/GOVB0_FRICTION_TODO.md` **== 1**，但該字串同時出現在條件②自身的規格行（L639），實測 **count=2**，條件恆 FAIL。

**碼證**: `grep -c '本 Task 於本 TODO 產出時標記為「未完工」' docs/GOVB0_FRICTION_TODO.md` → **2**；落點 L600（宣告）、L639（測試規格自引用）。RECHECK: 同上命令；或改為錨定 `^\- \*\*🔴 本 Task 於` 唯一標記行。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High。實作者按字面實作 `TEST-3.3-PROVISIONAL` 會在條件②永久轉紅，與 codex P1-04「三項可機械驗證」修法目標相悖。

**修法**: Task 3.3 驗證欄 `TEST-3.3-PROVISIONAL` 條件②改為唯一錨點（例 `grep -c '^\- \*\*🔴 本 Task 於本 TODO 產出時標記為「未完工」'` **== 1**），或將測試規格移至不污染 grep 目標的附錄；同步避免在 `docs/GOVB0_FRICTION_TODO.md` 內嵌可被 `grep -c` 誤數的原文。

---

## COMPOSER-R8-P1-02

**斷言**: `TEST-3.3-B24-PARTIAL` 要求 `票 B-24` bounded section 含「部分完成」，但未像 `TEST-3.3-PROVISIONAL` ③那樣定義 `^## …` 錨點；若實作者沿用 `^## B-14 ` 同型式取 `^## B-24 `，該區間 **不含**「部分完成」（實測 count=0），測試恆 FAIL。

**碼證**: `awk '/^## B-24 /{f=1;n=0} f{print} /^## B-/{if(f&&n++)exit}' handoffs/20260801-GOV-AMEND-BACKLOG.md | LC_ALL=C grep -c '部分完成'` → **0**。「部分完成」在 `## 📌 票 B-24 的拆分裁決`（backlog L1507-1522）。RECHECK: 同上 awk+grep；對照 `TEST-3.3-PROVISIONAL` ③的 bounded section 寫法（TODO L640-642）。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#ce88bc97db0f

[MAJOR] 信心度=High。B-24 紀律面邊界無法機械驗收，與 §0.1 第 1 條及 codex P1-04 五測試補強目標不一致。

**修法**: Task 3.3 驗證欄 `TEST-3.3-B24-PARTIAL` 補齊 bounded section 錨點（建議 `^## 📌 \`票 B-24\` 的拆分裁決` 至下一 `^## `），並明寫 `grep -c '部分完成'` **≥1** 且 `grep -c '全綠'` **==0**（於該區間內）。

---

## 出場判準核算

| 項目 | 值 |
|---|---|
| findings 總數 | **2** |
| BLOCKING（P0） | **0** |
| MAJOR（P1） | **2** |
| 出場條件 `findings ≤5 且 BLOCKING=0` | **數值滿足** |
| 建議 | **先修 2 條 P1 再標 Internal Frozen** — 否則 Task 3.3 驗收欄自引用／錨點缺失會在實作階段製造假紅 |

FINDINGS_COUNT: 2

---

RECONCILE-STAMP: composer APPROVED 2026-08-05 sha256:ce88bc97db0f task:GOVB0-TODO-R8

---

ASSUMPTIONS_VERIFIED: template_check rc=0；Task 11/11；_bc_kv/_prepare_and_run grep；B-14 未定稿 count=4；9 條修補 6 CLOSED / 3 NOT-CLOSED（併入 2 條新 P1）；B0 無拓撲矛盾；SPEC 36 ID 追溯表已列；5 新 Test 中 4 可證偽
TESTS_RUN: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` rc=0；多組 grep/awk（見 §0 表）
FAILURES_SEEN: TEST-3.3-PROVISIONAL ② count=2≠1；TEST-3.3-B24-PARTIAL 預設 bounded section 部分完成=0
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
