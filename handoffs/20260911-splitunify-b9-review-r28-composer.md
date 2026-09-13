# SPLITUNIFY b9 — review-r28（M1–M9 閉合再驗證 ＋ v22 重簽）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R28`  
**family**: composer  
**findings-round**: R28  
**brief-kind**: review  
**審查標的**: commit `b1ec3d0c`；current block＝M1–M9（`handoffs/reconcile/20260911-splitunify-b9-review-r27/synth.md`）  
**禁改碼**：review-only（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六路 728 passed | **fact-verified（子集）** | 本輪重跑 derive＋wiring＋golden → **136 passed** rc=0；全六路未重跑（brief VERIFY-EXEMPT） |
| brief fact-verified: doc_format_precheck 雙檔 rc=0 | **fact-verified** | 本輪複驗 rc=0/0 |
| brief fact-verified: 主委三道 golden 探針 | **fact-verified（間接）** | 對應測試 `test_v8_baseline_has_external_anchor_in_code`／`test_golden_carries_hand_expected_side_third_judge`／`test_versioned_v9_keys_present` 全綠；M1 護欄碼證見必答 1b |
| brief assumed: M1 等效於 codex 原修法 | 見必答 3(3a)① | |
| brief assumed: M3 第三份判準非第三份推導 | 見必答 3(3a)② | |
| brief assumed: M6 未動錯誤型別契約 | 見必答 3(3a)③ | |
| brief assumed: M5 唯一性不擋合法輸入 | 見必答 3(3a)④ | |

---

## 必答 1 — 重跑 review-r27 反例（§B8）

### (1a)

| 項目 | 判定 |
|------|------|
| `COMPOSER-R27-P2-01`（SPEC §P／§V 仍以 9.2b 前碼態為現況） | **CLOSED** |

### (1b)

```bash
bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md
# → dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132 rc=0

rg -n 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py | wc -l
# → 18（非 0）

rg -n '現況碼證|現行碼在此案例|現行碼會給' docs/SPLITUNIFY_SPEC.D-002.md
# → :216/:261 命中皆在 v22 更正刪節線內（~~…~~），正文已改為「9.2b 前快照／B9C 已落地」

rg -n '9\.2b 前' momentum/Analysis/event_samples/split_projection.py
# → :455/:466 docstring 已標 9.2b 前舊描述並禁據以實作
```

觀測特徵：M9 四處（§P `:216-217`、§V `:261`、§G (G-4c)、docstring）均已更正；`decision_at_ms` 碼命中 18 處；舊「命中 0」字面僅存於刪節追溯。

---

## 必答 2 — v22 body 重簽

### (2a)

**APPROVED**（body `dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132`）。

### (2b)

N/A。

---

## 必答 3 — 四條 assumed

### (3a)

① **M1 等效性** → **成立（就 codex 實跑之攻擊向量）**。該家原修法「主檔凍 v8 值、只增 v9 鍵」與 `main()` 拿現行投影比對主檔之設計**不可共存**（主委 r27 synth 已具名）；現行組合：**M1** 超集護欄擋住 sentinel 靜默丟鍵（`scripts/freeze_splitunify_golden.py:512-517`）；**M2** 三層外部錨擋同步改寫 v8＋旁檔（`:408-431`、`:442-449`）；v9 版本化鍵並存（`test_versioned_v9_keys_present`）。🔴 **誠實邊界**：`--write` 仍允許在鍵集超集前提下**改值**（重凍正當用途），SPEC §V (vii)「11 鍵逐值不變」字面與實作不完全一致——此為 r27 主委具名偏離，非 r28 新洞；正常模式 `GOLDEN MISMATCH` 先擋漂移。

② **M3 第三份判準** → **部分成立**。`_hand_expected_membership`（`:145-152`）僅讀 `expected_side` 欄、無 `if`／比較，**側別**確實是人手字面而非第三份推導；但 `_event_keys()` 之 `feature_cutoff_ms`／`decision_at_ms` 時刻仍共用 `_plans()` 邊界索引——若邊界常數算錯，三份**可能一起錯**。此限已具名（`:109`、§G (G-4e)）；G-4e 要抓的是「投影＋oracle 同一次錯誤解讀」，不是 fixture 邊界常數錯；`test_golden_carries_hand_expected_side_third_judge` 確認 `bnd_shift∈train`。

③ **M6 錯誤型別契約** → **成立**。錨點不同之重複 ⇒ `AlignmentViolationError`（`test_anchor_uniqueness_guard_is_reachable_before_duplicate_id_guard`）；逐欄相同之重複 ⇒ 裸 `ValueError`（`test_duplicate_manifest_with_same_anchor_still_raises_value_error`）；`decision_at_ms` 整欄缺失 ⇒ `:707-711` `ValueError`（在錨點閘之後仍 fail-closed）；NaN ⇒ `assert_epoch_ms_array`（`:713-716`）。未發現第三種 manifest 形態落到非預期病名。

④ **M5 唯一性不擋合法輸入** → **成立**。`build_event_keys` 以 `many_to_one` merge 廣播 `event_level` 之 `label_end_ms`（`split_projection.py:349-352`）⇒ 合法路徑下同事件各 feature TF 列**同值**；不一致只會來自上游壞資料，應 fail-closed（`:753-760`）；`test_inconsistent_label_end_ms_is_fail_closed` 實跑 PASS。

### (3b)

無需新修法（② 之誠實邊界已具名保留，不阻擋 B9D）。

---

## 必答 4 — 契約面改動後強制掃描

### (4a)

**本輪詞表**（避開 r26 metadata 三 token、r27 decision 掃描、codex r24 大表）：

`in_train_ms|membership.*cutoff|530-553|集合成員判定|界外即 purged|逐列.*in_train|row_index_local.*決定|cutoff in train_ms`

**命令**：

```bash
WORDLIST='in_train_ms|membership.*cutoff|530-553|集合成員判定|界外即 purged|逐列.*in_train|row_index_local.*決定|cutoff in train_ms'
for f in docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md; do
  echo "=== $f ==="
  awk '/^## 沿革與追溯索引$/{exit} /HISTORY-BEGIN/{skip=1} /HISTORY-END/{skip=0;next} skip{next} {print NR":"$0}' "$f" | grep -nE "$WORDLIST" || echo "(no hits)"
done
```

**SPEC 逐段**：

| 行 | live 互斥？ | 結論 |
|----|------------|------|
| `:216-217` | 否 | v22 更正＋刪節線；舊 per-cutoff 僅追溯 |
| `:218-230` | 否 | 現行改法／設計 rationale（含「不再逐列 in_train」之**禁止**句） |
| `:312` M-SU-D2-24 | 否 | mutation 目錄「應紅破壞點」，非施工指令 |

**TODO 逐段**：

| 行 | live 互斥？ | 結論 |
|----|------------|------|
| `:208-228` Task 2.2 | 否 | SUPERSEDED 開頭＋刪節線；要點 1/2/4 已標 |
| `:40-41` §0 | 否 | B2 時代「先答案窗再判定」序；與 9.2b 事件級錨定**不互斥**（9.2b 仍做答案窗 purge，只是按事件側廣播） |
| `:618` Task 9.2b | 否 | 與契約一致 |

**同型第八次**：**未發作**——命中皆為 SUPERSEDED／刪節／mutation 表／歷史 rationale，無 live 祈使句要求 per-cutoff 定 `split_label`。

### (4b)

N/A（4a 無 live 互斥）。

---

## 必答 5 — 可否進 `Task 9.3`（B9D）

### (5a)

**可以**——M1–M9 閉合可驗；v22 body APPROVED；無 BLOCKING finding。

### (5b)

已檢查：r27 本家 finding CLOSED（必答 1）；四 assumed 無否證性反例（必答 3）；136 條回歸＋`GOLDEN OK`；M5/M6 成對測試 PASS；golden 三防護測試 PASS；換詞表全檔掃無第八處 live 互斥（必答 4）；`git show b1ec3d0c` 契約面 diff 限 M1–M9 群集（無夾帶 consumer 9.3 施工）。

---

## COMPOSER-R28-P3-00

**斷言**: 本輪逐項核對 M1–M9 閉合與 v22 body 後無需阻擋收斂的 finding；r27 本家 `COMPOSER-R27-P2-01` 已由 M9 關閉。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132` rc=0；`pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py tests/momentum/Analysis/test_splitunify_golden.py -q` → **136 passed** rc=0；`python scripts/freeze_splitunify_golden.py` → `GOLDEN OK` rc=0；換詞表 awk+grep（必答 4）無 live per-cutoff 施工句。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#dece985e17e9; handoffs/reconcile/20260911-splitunify-b9-review-r27/synth.md#b1ec3d0c

doc-literal-only；信心度=High。M1 之「允許改值重凍」與 SPEC §V (vii) 字面差為 r27 已裁定偏離，不阻擋 B9D。

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: composer APPROVED 2026-09-14 sha256:dece985e17e9b8459a8df35387f0e3926f3f355f16557d4965fa134c7aa0e132 task:20260911-SPLITUNIFY-B9-REVIEW-R28
```

（舊戳記行已保留。）

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R27-P2-01

ASSUMPTIONS_VERIFIED: body hash dece985e…；doc_format_precheck 0/0；COMPOSER-R27-P2-01 CLOSED；四 assumed 逐條；136 pytest + GOLDEN OK；換詞表無第八處
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`doc_format_precheck.sh` SPEC/TODO rc=0/0；`pytest …derive+wiring+golden… -q` → 136 passed；`freeze_splitunify_golden.py` → GOLDEN OK；M5/M6 成對測試 3+1 passed
FAILURES_SEEN: none
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r28-composer.md

STATUS: DONE
