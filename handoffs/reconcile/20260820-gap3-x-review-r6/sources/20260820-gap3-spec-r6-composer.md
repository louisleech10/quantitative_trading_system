# GAP-3 事件型 SPEC R6 終輪閉合（V1 忠實度＋sentinel）— COMPOSER

family: composer  
task-id: 20260820-GAP3-X-REVIEW-R6  
scope: `docs/GAP3_EVENT_SPEC.md` @ `db85611a`（sha256 `09b05b39aa138055558c45c64b01a7d4f9ae3ded5482317f8e22b35eb107282f`）；對照 R5 synth V1；禁改碼  
brief: `handoffs/20260820-gap3-spec-r6-BRIEF.md`  
reconcile: `handoffs/reconcile/20260820-gap3-x-review-r5/synth.md`

---

## 前提挑戰（§0）

| brief 前提 | 判定 | 本輪核對 |
|---|---|---|
| R5 reconcile completeness PASS（3/3）＋債銷帳 | fact-verified（brief） | 未重跑 `--lock`；以 synth V1 正文＋`git diff a8bb7634..db85611a` 對照為準 |
| R5 修訂版 `template_check spec` PASS | **fact-verified** | 本輪重跑 → `TEMPLATE PASS (spec)`，rc=0 |
| assumed: mode-scoped 錨定義與 D2-1 label 鏈、D1-3 條件必填、§G-2 oracle 全文一致 | **本輪攻後＝成立** | D1-5 三 mode 錨表與 D2-1 `label_start` 機械表同構；D1-3 `≠close_to_close`⇒`label_price_mismatch` 仍成立；§G-2「各 mode exact」＋`next_open×close_to_close` 旗標案例未破 |
| assumed: §A 兩題登記足以擋「裁決前偷跑實作」 | **本輪攻後＝成立** | §A 標題「未確認前不得實作」＋題②「裁決前 B1.0 契約不得凍結」；題① `drop_threshold default=null` fail-closed（B1.5 同文） |

VERIFY（本輪實跑）:
```
shasum -a 256 docs/GAP3_EVENT_SPEC.md
→ 09b05b39aa138055558c45c64b01a7d4f9ae3ded5482317f8e22b35eb107282f（＝brief）
git diff --check a8bb7634..db85611a -- docs/GAP3_EVENT_SPEC.md → rc=0
bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md → TEMPLATE PASS，rc=0
git diff a8bb7634..db85611a -- docs/GAP3_EVENT_SPEC.md → 恰三處契約：D1-2／D1-5／§A（±「已確認結果」標頭無關契約）
rg -n 'entry_at[[:space:]]*[≤<=]+[[:space:]]*label_start' docs/GAP3_EVENT_SPEC.md → 唯 L30「廢除」敘述
```

---

## V1 寫回忠實度（對照 R5 synth）

| 落點 | synth V1 處置要點 | SPEC 落點 | 忠實？ |
|---|---|---|---|
| D1-5 mode-scoped 錨 | `label_return_mode` 機械唯一；c2c⇒t₀ close；open_*⇒entry 進場價；與 decision_offset／entry 脫鉤；同一輸入起點唯一；join 禁限 c2c 路徑 | D1-5 L26 | **忠實** |
| D1-2 scope 註記 | 「一律相對 t₀ close」＝**預設模式下**；U4b「一律」是否全禁＝§A② | D1-2 L23 | **忠實** |
| §A 兩題白話閘 | ①`drop_threshold` x；②U4b 一律範圍；裁決前 B1.0 不得凍結 | §A L71-73 | **忠實** |

**漂移**：無須阻擋收斂之語意漂移。非升級殘差（不列 finding）：檔頭來源段仍止於 R3 收斂敘事；D1-4 兩數並排仍寫預設 t₀ close 基準——屬 U4b 預設路徑敘事，open_* 保留與否＝§A② 白話閘（brief 不受理替使用者作答）。

---

## 消歧後同一輸入 label 起點唯一（V1 原反例面）

| 輸入（mode × entry） | D1-5 錨 | D2-1 `label_start` | 唯一？ |
|---|---|---|---|
| `close_to_close` × `next_open` | t₀ close | t₀ bar close_time | **唯一**；`entry_at`＞`label_start`⇒`entry_after_label_start=true` |
| `close_to_close` × `trigger_open` | t₀ close | t₀ bar close_time | **唯一**（兩數並排合法） |
| `open_to_close` × `next_open`（若 §A②裁保留） | entry 進場價 | entry bar entry 時點 | **唯一**（不同 mode＝不同契約輸入） |
| `open_to_horizon_close` × 任一 entry | entry 進場價 | entry bar entry 時點 | **唯一** |

原 V1 衝突（D1-5 無條件 t₀ close **同時** D2-1 open_*＝entry）已消。RULING-CONFLICT 面（U4b「一律」是否全禁非 c2c）已登記 §A② 轉白話閘——本家判此登記方式**可接受**（fail-closed：未裁前不得實作／不得凍 B1.0）。

---

## 新錯掃描（V1 寫回 vs X/Y/Z/W）

| 面 | 結果 |
|---|---|
| W1 三段鏈／receipt 三欄／§G-2 | diff **未觸**；D2-1／D2-4／§G-2 原文仍在 |
| X2 label 錨脫鉤 decision | 保留；c2c 路徑禁 `decision_at` join；B2.3 邊界③仍引用 |
| Y1 entry 映射 D1-6 | 未觸；`entry_at`↔`label_start` 仍無強制序 |
| Z1 兩層 receipt | 未觸 |
| Z2 `drop_threshold` | 升格 §A① 白話閘；B1.5 仍 `default=null` |
| D1-3 條件必填 | 與 mode-scoped 相容 |
| U／AR／X／Y／Z／W 已裁 | 無碼證直接衝突 |

§1 十一類（本輪焦點＝V1 寫回面）：**無新 BLOCKING/MAJOR**。

---

## 閉合表

| 項 | 狀態 |
|---|---|
| V1／`CODEX-R5-P1-01` 原反例 | **CLOSED**——mode-scoped 寫回後同一輸入 label 起點唯一 |
| W1／`CODEX-R4-P1-01` | **CLOSED**（R4 已閉；本 diff 未觸 W1 落點） |
| `CODEX-R1-P0-01` | **最終 CLOSED via W1** |

---

## 必答

1. **忠實度＋新錯掃描**：V1 三落點對 synth **忠實**；mode-scoped 與 D2-1／D1-3／§G-2 一致；§A 兩題＋B1.0 凍結閘在場；與 X/Y/Z/W **無新碼證衝突**。
2. **可以進「三家 RECONCILE-STAMP＋使用者白話閘」嗎？** **可以**——本家 **0 findings**（sentinel 如下）。

---

## COMPOSER-R6-P3-00

**斷言**: 本輪逐項核對後無 finding；V1 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r5/synth.md`（D1-2 預設模式 scope／D1-5 mode-scoped 錨／§A 兩題＋B1.0 不得凍結），消歧後同一輸入之 label 起點唯一，mode-scoped 與 D2-1 label 鏈／D1-3／§G-2 全文一致，與 X/Y/Z/W 無新碼證衝突。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `09b05b39aa1380…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff a8bb7634..db85611a -- docs/GAP3_EVENT_SPEC.md` → 僅 D1-2／D1-5／§A；讀檔錨點 D1-2=:23、D1-5=:26、D2-1 label 鏈=:32、D1-3=:24、§A=:71-73、§G-2=:113；`rg` 殘留單一鏈探針 → 唯 L30「廢除」；手推 `close_to_close`×`next_open` ⇒ `label_start`=t₀ close 唯一且 `entry_after_label_start=true`；對照 synth V1 三處置 0 漂移。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#09b05b39aa13; handoffs/reconcile/20260820-gap3-x-review-r5/synth.md#4df00ce824b6; handoffs/20260820-gap3-spec-r6-BRIEF.md#34b671f7a4ca

sentinel：0 findings（實質）；上列為 R6 V1 忠實度＋同一輸入唯一性手推＋D2-1／D1-3／§G-2 相容攻擊＋X/Y/Z/W 新錯掃描之機械複驗摘要。

---

## Verdict：可進三家 RECONCILE-STAMP＋使用者白話閘

R5 V1 單縫寫回可證偽對照 synth；消歧後 label 起點唯一；§A 兩題為白話閘議題、不阻擋 stamp 流程啟動。白話裁決前不得凍結 B1.0 契約。

---

## 被當成事實的未驗證假設（§0 殘列）

| 宣稱 | 判定 |
|---|---|
| mode-scoped ↔ D2-1／D1-3／§G-2 一致 | 本輪攻後 **fact-verified** |
| §A 兩題足以擋偷跑實作 | 本輪攻後 **fact-verified**（文面閘） |
| template_check PASS | **fact-verified**（本輪重跑） |
| V1 寫回無語意漂移 | **fact-verified**（非升級殘差見上） |

ASSUMPTIONS_VERIFIED: SPEC @db85611a sha256=brief；template_check PASS；V1 三落點 0 漂移；同一輸入 label 起點唯一；mode-scoped↔D2-1/D1-3/§G-2；§A 凍結閘在場；X/Y/Z/W 未破  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → PASS rc=0；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → brief 相符；`bash scripts/completeness_check.sh --single handoffs/20260820-gap3-spec-r6-composer.md --family composer` → 見下行  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only；禁改碼）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r6-composer.md`  
TMP_CLEANUP: `/tmp` 與 `/private/tmp` 無 `*workdir*` 目錄；`claude-501` 已保留

STATUS: DONE
