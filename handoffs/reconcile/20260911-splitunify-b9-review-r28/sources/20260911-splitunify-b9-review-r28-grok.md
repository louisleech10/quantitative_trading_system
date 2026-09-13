# SPLITUNIFY b9 — review-r28（M1–M9 閉合再驗證 ＋ v22 重簽）— grok 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R28`  
**family**: grok  
**findings-round**: R28  
**brief-kind**: review  
**審查標的**: commit `b1ec3d0c`；current block＝M1–M9（`handoffs/reconcile/20260911-splitunify-b9-review-r27/synth.md`）  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: body `dece985e…` | **fact-verified** | `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → 逐字相符；append 戳記後 hash **不變** |
| brief fact-verified: doc_format 兩份 rc=0 | **fact-verified** | SPEC／TODO 各跑一次 → 皆 rc=0 |
| brief fact-verified: 六路 728 passed | **fact-verified（子集）** | 本輪 `derive`＋`wiring`＋`golden` → **136 passed**；全六路未重跑（brief VERIFY-EXEMPT） |
| brief fact-verified: r27 `state=CLOSED` | **fact-verified** | `debt_ledger.sh --list \| grep review-r27` → `state=CLOSED` |
| brief fact-verified: 主委三道 golden 探針 | **fact-verified（本家重跑）** | M1 sentinel→`--write` rc=1 指名 `legacy_sentinel`；M2 雙改／缺席皆 rc=1；G-4e 三方相等見 `GOLDEN OK` |
| brief assumed: M1 與 codex 原修法等效 | 見必答 3① | |
| brief assumed: M3 人手側為第三份判準 | 見必答 3② | |
| brief assumed: M6 未動錯誤型別契約 | 見必答 3③ | |
| brief assumed: M5 唯一性不擋合法輸入 | 見必答 3④ | |

---

## 必答 1 — 重跑本家 review-r27 反例（§B8）

### (1a)

| ID | 判定 |
|----|------|
| `GROK-R27-P1-01`（TODO Task 2.2 live 集合成員祈使） | **CLOSED** |
| `GROK-R27-P1-02`（`SU-RESID-2` 仍列 9.2b 為阻擋者） | **CLOSED** |
| `GROK-R27-P2-01`（SPEC／docstring 四處仍以 9.2b 前為現況） | **CLOSED** |

### (1b)

```text
# P1-01 — Task 2.2 三處 SUPERSEDED
awk 'NR>=208 && NR<=250' docs/SPLITUNIFY_TODO.md | grep -c 'SUPERSEDED BY `Task 9.2b`'
# → 3

# P1-02 — 尚未關閉者只剩 9.3；blocked-by 無 live「9.2b／9.3」
grep -n '尚未關閉者\|blocked-by:Task 9\.3 尚未實作' docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md
# → TODO:904／SPEC:327 皆「尚未關閉者＝下游…Task 9.3」；9.2b 半句在 ~~ ~~

# P2-01 — 四處快照標註
sed -n '216,217p' docs/SPLITUNIFY_SPEC.D-002.md
# → 含「v22 更正…9.2b 前之碼態快照」＋舊現況碼證在 ~~ ~~
sed -n '261p' docs/SPLITUNIFY_SPEC.D-002.md
# → 「現行碼…1h=test／4h=purged」在 ~~ ~~；標 9.2b 前
grep -n '9\.2b 前' momentum/Analysis/event_samples/split_projection.py
# → :455／:466 docstring 已標 9.2b 前舊描述、禁據以實作

# 行為錨仍在
venv/bin/python -m pytest -q --tb=no \
  tests/momentum/Analysis/test_splitunify_derive.py::test_event_level_anchor_broadcasts_side_to_all_feature_tf
# → PASSED
```

反向：若修補未生效，Task 2.2 要點 1／2／4 會 live 出現無 SUPERSEDED 之「集合成員」祈使、`SU-RESID-2` 仍寫 `blocked-by:Task 9.2b／9.3`、§P「現況碼證…命中數為 0」無刪節——本輪未觀測到。

---

## 必答 2 — v22 body 重簽

### (2a)

**APPROVED**（body `dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132`）。

戳記已 append（舊行保留）：
`RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132 task:20260911-SPLITUNIFY-B9-REVIEW-R28`

### (2b)

N/A（未 REJECTED）。

---

## 必答 3 — 四條 assumed

### (3a)

① **M1 等效性** → **成立（就 codex 實跑之攻擊向量：靜默丟鍵）**。  
該家「主檔凍住 v8 值、只增 v9」與 `main()` 拿**現行投影**比對主檔**不可共存**（凍 v8 值 ⇒ 比對恆紅）。現行組合：M1 超集護欄擋丟鍵（本家探針：塞 `legacy_sentinel` 後 `--write` → rc=1，訊息指名該鍵會消失）；M2 三層外部錨擋「同步改寫 v8＋旁檔」（雙改 → `GOLDEN V8 TAMPERED…同步改寫…在此擋下`；缺席 → `GOLDEN V8 MISSING`）。🔴 **誠實邊界**：`--write` 在鍵集超集下**允許改值**（腳本註解明寫）；SPEC §G (G-4d)(vii)「既有鍵任一值被改動即 raise」字面**未**由 M1 實作——此為 r27 主委具名偏離之延續，非本輪新洞；正常模式 `GOLDEN MISMATCH` 先擋未審漂移。v8 歷史成員集保全在獨立 `.v8.json`（本家觀測：`g1_membership != v8.g1_membership`，`bnd_shift` 只在主檔 train）。

② **M3 第三份判準** → **側別欄成立；時刻共因之誠實邊界成立**。  
AST：`_hand_expected_membership` **無** `If`／`Compare`（只攤平 `expected_side`）。`bnd_shift` 之 `"train"` 為人手字面。🔴 事件時刻仍經 `_event_keys` 共用 `_plans()`／`index[pos]`——若填值者與投影對**同一錯誤邊界常數**達成共識，三方仍可同錯；此限已具名於腳本 `:109` 與 SPEC (G-4e)，G-4e 目標是擋「投影＋oracle 同一次錯誤解讀」，不是擋 fixture 邊界常數錯。

③ **M6 錯誤型別契約** → **成立**。  
成對測試：錨點不同之重複 → `AlignmentViolationError`；純重複 → 裸 `ValueError`（皆 PASSED）。第三種形態本家實跑：缺 `decision_at_ms` 欄 → `ValueError`（訊息含「缺 decision_at_ms 欄」）；NaN／None → `ValueError` via `assert_epoch_ms_array`（含 NaN／inf）。皆為具名 fail-closed，非裸 `AttributeError`／靜默落側。

④ **M5 唯一性不擋合法輸入** → **成立**。  
`build_event_keys` 以 `many_to_one` 自 `event_level` 廣播 `label_end_ms`（`:349-352`）⇒ 合法路徑下同事件各 feature TF **同值**；不一致只來自手造／污染之 `event_keys`，應 fail-closed（`test_inconsistent_label_end_ms_is_fail_closed` PASSED）。未發現「合法 many_to_one 產出異值」之構造。

### (3b)

無需新修法。① 之 (vii) 字面差與 ② 之時刻共因皆已具名／屬 Task 9.5 或散文紀律，**不阻擋** B9D。

---

## 必答 4 — 契約面強制掃描（自立詞表）

### (4a)

**本家詞表**（🔴 刻意不用主委 M7 之「集合成員／`feature_cutoff_ms ∈`／SUPERSEDED」為唯一依據；亦避開 composer r28 之 `in_train_ms|530-553` 主幹）：

| 類 | 詞／結構 |
|----|----------|
| 舊判側祈使 | `per-cutoff`／`per_cutoff`／`cutoff 判側`／`cutoff 定側`／`以 cutoff`／`依 cutoff`／`cutoff 決定`／`舊路徑以 cutoff` |
| 成員／集合殘留 | `成員判定`／`兩段式`／`cutoff in train_ms`／`in_train`（與 purge／側別共現） |
| 契約正向 | `不參與 split_label`／`退出 split_label`／`不參與側別`／`不參與判側` |
| 過期「現況」 | live 且無「9.2b 前／快照／v22 更正／~~」包裹之 `現況碼證`／`現行碼` |

**命令**（SPEC live＝`:1` 至 `HISTORY-BEGIN`＝`:337` 之前；TODO 全檔；HISTORY／沿革不列 finding）：

```bash
HB=$(awk '/HISTORY-BEGIN/{print NR; exit}' docs/SPLITUNIFY_SPEC.D-002.md)
awk -v hb="$HB" 'NR<hb' docs/SPLITUNIFY_SPEC.D-002.md \
  | grep -nE 'per-cutoff|per_cutoff|cutoff 判側|cutoff 定側|以 cutoff|依 cutoff|cutoff 決定|舊路徑以 cutoff|成員判定|兩段式|cutoff in train_ms|不參與 split_label|退出 split_label|不參與側別|不參與判側|現況碼證|現行碼'
grep -nE 'per-cutoff|per_cutoff|cutoff 判側|cutoff 定側|以 cutoff|依 cutoff|cutoff 決定|舊路徑以 cutoff|成員判定|兩段式|cutoff in train_ms|不參與.*split_label|退出.*split_label|現況碼證|現行碼' \
  docs/SPLITUNIFY_TODO.md
```

**逐段結論**（是否與「側別＝事件級 `decision_at_ms`；`feature_cutoff_ms` 不參與 `split_label`」**互斥**）：

| 段 | 互斥？ | 說明 |
|----|--------|------|
| SPEC `(3.1)` `:46` | **無** | 正向契約：側別由 `decision_at_ms`；cutoff 不參與側別 |
| SPEC (G-4c) `:167` | **無** | 「目前」已改「9.2b 前」；oracle 已 decision-anchored |
| SPEC (G-4e)／(G-4a) `:168-170` | **無** | 換錨／第三份判準敘事；舊路徑以 cutoff 判側被標為缺陷 |
| SPEC §P Task 9.2b `:216-218` | **無（本輪已閉）** | 現況碼證刪節＋現行「不參與 `split_label`」 |
| SPEC §P `:230` | **無互斥** | 「現行 `:540-542` 逐列 `in_train`」為**已完成 Task 之改法前情**（答案窗廣播，非 cutoff→`split_label`）；語意過期但不與側別錨定互斥 |
| SPEC §V `:261` | **無（本輪已閉）** | 「現行碼會給出…」刪節 |
| SPEC §V `:263` | **無互斥** | 「現行 fixture 全部 `decision==cutoff`」已因 `bnd_shift` **事實過期**，但主張的是 (G-4d)② 空心與否，**不是**要求用 cutoff 判側 |
| SPEC mutation／不可做 | **無** | 禁回 cutoff 判側／禁逐列 `in_train` purge |
| TODO Task 2.2 `:209-247` | **無（本輪已閉）** | 要點 1／2／4 三處 `SUPERSEDED BY Task 9.2b` |
| TODO Task 9.2b `:617-628` | **無** | live「不參與 `split_label`」／禁 per-cutoff |
| TODO §E `SU-RESID-2` `:904` | **無（本輪已閉）** | 9.2b 已關；阻擋者只剩 9.3 |
| diff 夾帶 | **無超範圍契約改動** | `git show b1ec3d0c --name-only` 契約面＝M1–M9 落點（＋handoffs／site／白話；後者不在審查範圍） |

**第八處（同型 live 祈使要求 cutoff→側別）**：本家詞表下 **0**。`:230`／`:263` 為過期「現行」敘事，**不**構成與側別錨定契約之互斥，不另開 finding。

### (4b)

N/A（無須可貼修正字面之互斥項）。

---

## 必答 5 — 可否進 `Task 9.3`（B9D）

### (5a)

**可以（本家側）**。無本家 P0／P1；r27 三條全 CLOSED；v22 body 本家 APPROVED；四 assumed 無否證性反例需先修。

### (5b)

已檢查：本家反例重跑（必答 1）；M1／M2 探針＋`GOLDEN OK`；M3 AST＋誠實邊界；M4 mapping 具名拒；M5／M6 成對＋缺欄／NaN 探針；換詞表掃描無第八處 live 互斥；136 pytest；body hash 相符。**不重開** `Task 9.3`–`9.5` 設計。進 B9D 仍須三家戳記齊＋領 impl token（本家只完成本家一枚）。

---

## §1 必查（11 類摘要）

1. 矛盾/互斥：本家 r27 三條已閉；換詞表無新 live 互斥。  
2. 漏項：無本輪新增。  
3. 不可測：無。  
4. 可疑 quant：不重開。  
5. 過度工程：無。  
6. OOM：無。  
7. Cache：無。  
8. API／相容：M4／M6 錯誤型別契約維持。  
9. 測試品質：成對測試＋golden 三防護有鑑別力。  
10. Agent 可執行：Task 2.2／`SU-RESID-2` 不再誤導。  
11. 必要性／短命工：無本輪新增短命工。

---

## 攻擊面補答（brief「我沒查」）

| 面向 | 本家結論 |
|------|----------|
| M1 是否等效 | 對「靜默丟鍵」等效；對「主檔凍 v8 值」不等效且不可實作；v8 保全改由 M2（見必答 3①） |
| M2 外部錨被改／v8 缺席 | 改常數須動被 review 碼（現於 diff）；缺席 fail-closed（本家探針 rc=1） |
| M3 共因 | 側別無人手推導；時刻共因＝具名誠實邊界 |
| M4–M6 | 見必答 3③④；成對測試 PASSED |
| M7–M9 第八處 | 詞表掃描無 live cutoff→側別祈使 |
| diff 夾帶 | 契約面限 M1–M9 |

---

## GROK-R28-P3-00

**斷言**: 本輪逐項核對後無 finding——本家 `GROK-R27-P1-01`／`P1-02`／`P2-01` 反例已 CLOSED；M1–M9 修補與四條 assumed 經探針／成對測試／自立詞表掃描後，無與「側別由事件級 `decision_at_ms` 錨定、`feature_cutoff_ms` 不參與 `split_label`」互斥之 live 阻擋項；可進 `Task 9.3`（B9D）之前提在本家側已滿足。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132`；Task 2.2 之 `SUPERSEDED BY Task 9.2b` 計數＝3；`SU-RESID-2` 尚未關閉者＝Task 9.3；M1 `--write` 拒 `legacy_sentinel`（rc=1）；M2 缺席／雙改皆 rc=1；`python scripts/freeze_splitunify_golden.py` → `GOLDEN OK`；pytest derive＋wiring＋golden → **136 passed**；M5／M6 成對＋缺欄／NaN 探針皆具名 fail-closed；詞表 `grep` live 互斥命中＝0（見必答 4 表）。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R28-BRIEF.md#afddb78295dd; docs/SPLITUNIFY_SPEC.D-002.md#32fccef8d08a; docs/SPLITUNIFY_TODO.md#b9fbd797573a; handoffs/reconcile/20260911-splitunify-b9-review-r27/synth.md#b1ec3d0c

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: grok APPROVED 2026-09-14 sha256:dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132 task:20260911-SPLITUNIFY-B9-REVIEW-R28
```

（舊戳記行已保留；composer 本輪 APPROVED 行亦已在檔內。）

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R27-P1-01,GROK-R27-P1-02,GROK-R27-P2-01

ASSUMPTIONS_VERIFIED: body dece985e…；doc_format 0/0；r27 CLOSED；本家三條 CLOSED；四 assumed 逐條；詞表無第八處 live 互斥；可進 B9D（本家側）
TESTS_RUN: `reconcile_body_hash.sh` → dece985e…；`doc_format_precheck` SPEC／TODO → rc=0；`pytest …derive+wiring+golden…` → 136 passed；`freeze_splitunify_golden.py` → GOLDEN OK；M1 sentinel `--write` rc=1；M2 missing／dual-tamper rc=1；M5／M6 成對 3 passed＋缺欄／NaN 探針
FAILURES_SEEN: none（首輪無 venv 時 import 失敗已改用 venv 重跑）
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r28-grok.md
STAMP_APPENDED: docs/SPLITUNIFY_SPEC.D-002.md（舊戳記保留；APPROVED）

STATUS: DONE
