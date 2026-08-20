# GAP-3 事件型 SPEC R5 終輪閉合（W1 忠實度＋sentinel）— COMPOSER

task-id: `20260820-GAP3-X-REVIEW-R5`  
審查標的: `docs/GAP3_EVENT_SPEC.md` @ `a8bb7634`（sha256 `57a429d18129ad15c0e0eba5d3d6e2a96d820b9b8e335972c22fa23c95879098`）  
R4 收斂權威: `handoffs/reconcile/20260820-gap3-x-review-r4/synth.md`（W1＋sentinel 節）  
brief: `handoffs/20260820-gap3-spec-r5-BRIEF.md`

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標注 | R5 複核結論 |
|---|---|---|
| R4 reconcile completeness PASS（3/3）＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 synth W1 正文＋`git diff 3b254e2f..a8bb7634` 對照為準 |
| R4 修訂版 `template_check spec` PASS | fact-verified | 本輪重跑 `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0 |
| assumed: 三段鏈拆分後無其他條文仍隱含 `entry_at ≤ label_start` | **本輪攻後＝成立** | 全文掃：SPEC 唯一含該子串處＝D2-1 L30「單一鏈…廢除」敘述；D1-6／AR-1／§G-2 皆改三段鏈或「無強制順序」；B1.0 L131「六時間欄」為衍生欄總稱、未復活舊序 |
| assumed: `label_start` 依 mode 機械定義與 D1-5 label 錨不變式相容 | **本輪攻後＝成立** | D1-5「錨」＝**價格／主線 join 參照點**（t₀ close、不隨 `decision_offset_bars` 移動）；D2-1 `label_start`＝**時間窗起點**（mode 機械表）。預設 `close_to_close` 兩者同落 t₀ close；`open_*` mode 刻意以 entry 為窗起點，D1-3 已要求非 c2c 沿用主線 label ⇒ `label_price_mismatch=true`——非同一維度衝突 |

**跨家族註記（非本家 finding）**：codex `CODEX-R5-P1-01` 將 D1-5 與 D2-1 mode 表標為 mode/anchor 衝突；本家獨立攻後判定為**文面層次可讀性**議題、非 W1 新引入之碼證矛盾，且 D1-3／§G-2 各 mode exact oracle 已提供實作閘，不升級為 COMPOSER finding。

## W1 寫回忠實度（對照 R4 synth）

| synth W1 落點 | SPEC 落點 | 忠實？ |
|---|---|---|
| D2-1 三段鏈（PIT／label／持有）；廢單一鏈 | D2-1 L30-34 | **忠實** |
| `label_start` mode 機械定義 | D2-1 L32 | **忠實** |
| D1-6 `entry_at`↔`label_start` 無強制序 | D1-6 L27 | **忠實** |
| receipt 三新欄 `label_start_ms`／`label_end_ms`／`entry_after_label_start` | D2-4 L37 | **忠實** |
| §G-2 各 mode exact＋`next_open`×`close_to_close` 組合案例 | §G-2 L111 | **忠實** |
| AR-1 指針改三段鏈 | AR-1 L75 | **忠實** |
| 禁用組合＝無（兩數並排合法） | D2-1 明文 U4b 合法語意 | **忠實** |

`git diff 3b254e2f..a8bb7634 -- docs/GAP3_EVENT_SPEC.md` → 43 行；hunk 恰落 D1-6／D2-1／D2-4／AR-1／§G-2，與 synth W1 處置 0 漂移。

## 殘留單一鏈全文掃（brief assumed #1）

| 探針 | 結果 |
|---|---|
| `rg -n 'entry_at[[:space:]]*[≤<=]+[[:space:]]*label_start' docs/GAP3_EVENT_SPEC.md` | 僅 L30「廢除」敘述 |
| D1-6 validator | 僅 `decision_at ≤ entry_at`＋無強制序註記 |
| §G-2 oracle | 要求三段鏈全過，非舊單一鏈 |
| B1.1／B1.2 Tasks | 引用 D2 不變式，無復活 `entry_at ≤ label_start` |

## 新錯掃描（W1 vs X/Y/Z）

| 面 | 結果 |
|---|---|
| X1 t₀−k／不設 ms 覆寫 | AR-1 改指 D2-1 三段鏈＋`decision_at ≤ t0_open_ms`；未破 |
| X2 label 錨不隨 decision | D1-5 未改；B2.3 邊界仍引用 |
| Y1 entry 五語意映射 | D1-6 保留；僅解除對 `label_start` 強制序 |
| Z1 兩層 receipt | 事件級**擴**三欄，per-TF 層不變；§G-2 仍驗兩層 |
| Z2/Z3/Z4/M8 | diff 未觸及 |
| U4b 兩數並排 | W1 明確 `entry_after_label_start`＋允許 `next_open`×`close_to_close` |

§1 十一類（本輪焦點＝W1 面）：**無新 BLOCKING/MAJOR**。

## 閉合表

| 項 | 狀態 |
|---|---|
| W1／`CODEX-R4-P1-01` | **CLOSED**——D2-1 三段鏈、receipt 三欄、§G-2 組合 oracle 均已字面寫回 |
| `CODEX-R1-P0-01` | **最終 CLOSED via W1**（codex 本輪同判；本家只驗寫回忠實） |
| R4 Z1–Z4 | 未在本 diff 觸及；R4 sentinel 結論仍成立 |

## 必答

1. **忠實度＋新錯掃描**：W1 七落點對 synth **忠實**；全文無殘留強制 `entry_at ≤ label_start`；D1-5↔mode 表相容（見 §0 攻擊結論）；與 X/Y/Z 無碼證衝突。
2. **可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？** **可以**（本家 0 findings；codex `CODEX-R5-P1-01` 留待 reconcile 合併，不阻擋本家 sentinel）。

## COMPOSER-R5-P3-00

**斷言**: 本輪逐項核對後無 finding；W1 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r4/synth.md`（D2-1 三段鏈／receipt 三新欄／§G-2 組合案例），全文無殘留強制 `entry_at ≤ label_start`，D1-5 價格錨與 D2-1 mode 時間窗定義相容，與 X/Y/Z 無新碼證衝突。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `57a429d18129ad15c0e0eba5d3d6e2a96d820b9b8e335972c22fa23c95879098`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff 3b254e2f..a8bb7634 -- docs/GAP3_EVENT_SPEC.md` → 僅 D1-6／D2-1／D2-4／AR-1／§G-2；`rg -n 'entry_at[[:space:]]*[≤<=]+[[:space:]]*label_start' docs/GAP3_EVENT_SPEC.md` → 唯 L30「廢除」；手推 `next_open`×`close_to_close`：t₀ open＜t₀ close＜next open ⇒ `entry_at > label_start`、`entry_after_label_start=true`、三段鏈全過；對照 synth W1 七落點表 0 漂移。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#57a429d18129; handoffs/reconcile/20260820-gap3-x-review-r4/synth.md#089874745d80; handoffs/20260820-gap3-spec-r5-BRIEF.md

sentinel：0 findings（實質）；上列為 R5 W1 忠實度＋殘留單一鏈全文掃＋D1-5↔mode 相容攻擊＋X/Y/Z 新錯掃描之機械複驗摘要。

## Verdict：可進三家 RECONCILE-STAMP＋使用者白話閘

W1 單縫寫回可證偽對照 synth；本家 **0 findings**。codex `CODEX-R5-P1-01`（mode/anchor 文面消歧）留 reconcile 合併，不構成本家阻擋。

---

ASSUMPTIONS_VERIFIED: SPEC @a8bb7634 sha256=brief；template_check PASS；W1 七落點 0 漂移；殘留單一鏈全文掃僅「廢除」敘述；D1-5↔D2-1 雙維度相容；X/Y/Z 無衝突  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS rc=0；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → 57a429d18129…；`bash scripts/completeness_check.sh --single handoffs/20260820-gap3-spec-r5-composer.md --family composer` → 見下行  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r5-composer.md`  
TMP_CLEANUP: `/tmp` 與 `/private/tmp` 無 `*workdir*` 目錄；`/private/tmp/claude-501` 已保留

STATUS: DONE
