# SPLITUNIFY b9 — review-r27（Task 9.2b／B9C 審碼）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R27`  
**family**: composer  
**findings-round**: R27  
**審查標的**: commit `a1e9680e`；current block＝brief 所列 `split_projection.py`／`pipeline.py`／`freeze_splitunify_golden.py`／三測試檔／golden v8  
**禁改碼**：review-only。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六路回歸 721 passed | **fact-verified（子集）** | 本輪重跑 derive＋wiring＋golden → **129 passed** rc=0；全六路未重跑（brief VERIFY-EXEMPT） |
| brief fact-verified: golden 換錨零位移＋`GOLDEN OK` | **fact-verified** | `venv/bin/python scripts/freeze_splitunify_golden.py` → `GOLDEN OK` rc=0 |
| brief fact-verified: SPEC v21 戳記 rc=0 | **fact-verified** | `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0（body `755f3d53…`） |
| brief assumed: `test_multi_feature_tf_opposite_sides` fixture 遷移 | **成立** | 見必答 3(3a)① |
| brief assumed: 三道 `AlignmentViolationError` 可達性 | **成立（防禦＋接線足夠）** | 見必答 3(3a)② |
| brief assumed: 三條改寫舊測試非刪測換綠 | **成立** | 見必答 3(3a)③；破壞驗見必答 4 |
| brief assumed: `label_end_ms.max()` 正確性 | **部分成立（非阻擋）** | 見必答 3(3a)④ |

---

## 必答 1 — 重跑 review-r26 sentinel（§B8）

### (1a)

| 項目 | 判定 |
|------|------|
| `COMPOSER-R26-P3-00`（v21 重簽＋換詞表掃描無 live 互斥） | **CLOSED** |

### (1b)

```bash
bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md
# → 755f3d53c1f350d894220f97629fca658b21699b0daa2d6517456af2ae443e1f rc=0

bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md
# → RECONCILE-STAMP PASS（codex,composer,grok 全 APPROVED）rc=0

# r26 換詞表（摘錄）
WORDLIST='producer.*metadata|context handoff|完整記帳|資料流交接|…'
awk '…排除沿革…' docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md | grep -nE "$WORDLIST"
# → 正文命中皆為 v18–v21 更正註／刪節線內追溯，無 live 三層/metadata 交付互斥
```

觀測特徵：body hash 與 r26 一致；戳記仍有效；metadata 兩層掃描結論未被 r27 程式碼 diff 推翻。

---

## 必答 2 — `Task 9.2b` 六要點與四不可做（對照碼）

### (2a)

| # | 條目 | 判定 |
|---|------|------|
| 1 | 步驟 0：`EventSamplePipeline.run` 在 derive 前呼叫 `validate_split_pair_integrity`；`ts` naive datetime64 | **已落地** |
| 2 | 三段式＋界外 raise（非第四分支）；`train_last_ms` 新增 | **已落地** |
| 3 | 事件級廣播；`feature_cutoff_ms` 不參與 `split_label` | **已落地** |
| 4 | 答案窗 purge 按事件側一次決定並廣播 | **已落地** |
| 5 | `(3.2)` 同側分組 → `AlignmentViolationError` | **已落地** |
| 6 | 跨表互斥 `assignments`∩`purged` event_id 為空 | **已落地** |
| — | 不可做①：不得以 `feature_cutoff_ms` 定 `split_label` | **已遵守** |
| — | 不可做②：界外不得寫成第四分支 | **已遵守**（706–714 獨立 raise，`_side_of` 僅三態） |
| — | 不可做③：不得在 (3.2) 前保留 per-cutoff 判側 | **已遵守** |
| — | 不可做④：不得在 `derive_*` 內呼叫 `validate_split_pair_integrity` | **已遵守** |

### (2b)

N/A（無未落地項）。

碼證摘要：`pipeline.py:784-789` 步驟 0；`split_projection.py:657-760` 錨定＋三段式＋廣播＋`_assert_event_level_side_consistency`；`freeze_splitunify_golden.py:158-188` decision-oracle；`--write` 拒寫 v8（`:418-429`）。

---

## 必答 3 — 四條 assumed

### (3a)

① **`test_multi_feature_tf_opposite_sides_must_fail_closed` 遷移** → **成立**。事件級錨定後，舊 fixture（同事件兩列 cutoff 分落 train／test 段）在 `derive_*` 路徑**結構上造不出異側**；SPEC §V `:270` 反例形狀為「**直接構造 `assignments`** THEN raise」。現測試改打可單獨呼叫之 `_assert_event_level_side_consistency`（`test_splitunify_derive.py:1662-1667`），node id 未改、xfail 已解除，仍釘 `AlignmentViolationError`＋`e_x`。正面廣播由 `test_event_level_anchor_broadcasts_side_to_all_feature_tf` 覆蓋。**TODO「解除 xfail」與 SPEC 形狀衝突時，以 SPEC 反例形狀為準**——本處置正確，無需改 TODO。

② **三道 `AlignmentViolationError` 可達性** → **成立（防禦碼＋接線測試足夠）**。
- **錨點不唯一**（692–697）：正規路徑 `man_dupes`（563–568）先擋重複 `event_id` ⇒ 多數情況為 `ValueError` 而非本道；若日後 manifest 合流帶 per-TF 列，本道為唯一 `AlignmentViolationError` 落點。**經 derive 公開入口常態不可達，但 helper 單測可達**。
- **同側分組**（415–421）／**跨表互斥**（422–430）：廣播後正規路徑結構上不可產生異側／跨表混態；**故意構造反例測試**（`test_opposite_sides_raise_alignment_violation`、`test_purged_and_assignments_event_id_disjoint`）與 **接線測試**（`test_side_consistency_check_is_wired_into_derive`）證明呼叫點存在。刪呼叫行 ⇒ 接線測轉紅（本輪破壞驗，見必答 4b）。
- **結論**：三道作為 (3.2) 可單獨打反例的入口＋生產接線 spy，組合**足夠**；不必改為 inline-only。

③ **三條改寫舊測試** → **成立，仍有鑑別力**。
- `test_membership_set_not_interval`：洞裡事件須 train 非 purged（破壞驗見 4b）。
- `test_dual_membership_raises_not_silent_pick`：重疊 plan 須 `ValueError`「兩段在時間上重疊」。
- `test_unmatched_timestamp_is_purged_not_train`：界內非網格點須 train 非 purged。
- **殘留弱點（非本條否定）**：`test_splitunify_wiring.py:106-117` 仍以 `feature_cutoff_ms ∈ train_ms/test_ms` 對證側別——在 wiring fixture 全為 `decision==cutoff` 時**鑑別力弱**；由 `bnd_shift` golden 與 §9.2b 具名測試補洞。

④ **`label_end_ms.max()`** → **部分成立，現階段不阻擋**。`label_end_ms` 語意為事件級（`receipts.event_level`）；同事件同值時 `max` 退化。實跑同事件兩列不同 `label_end_ms` ⇒ 取 max、不 raise（靜默吞不一致）。**建議**（非 9.3 前置）：可選加 `manifest.table`/`event_keys` 按 `event_id` 的 `label_end_ms` 唯一性閘，對標 `decision_at_ms` 閘；現行取 max 對答案窗 purge **偏保守**（較寬窗更易觸發 purge）。

### (3b)

僅 ④ 有改法建議（可選，不阻擋 9.3）：在 `_derive_single_symbol` 答案窗段前，對 `event_keys.groupby("event_id")["label_end_ms"].nunique()>1` fail-closed（`ValueError` 或 `AlignmentViolationError`，與 `decision_at_ms` 閘同型）。

---

## 必答 4 — 空殼獵殺（破壞驗）

### (4a)

抽兩處實際改壞：**未發現「改壞仍綠」之空殼**（所抽兩處均轉紅）。

### (4b)

| 測試 | 改壞內容 | 觀測 |
|------|----------|------|
| `test_membership_set_not_interval` | `assert plan.purged.empty` → `assert not plan.purged.empty` | **紅** rc=1；`AssertionError: 9.2b 後不得再以「cutoff 不在集合中」判 purged…` |
| `test_side_consistency_check_is_wired_into_derive` | 刪 `monkeypatch.setattr(..., _spy)` | **紅** rc=1；`AssertionError: …沒有呼叫同側／跨表互斥檢查（M-SU-D2-14）` |
| `test_validate_split_pair_integrity_is_called_before_derive` | `assert "validate" in order` → `assert "derive" in order and False` | **紅** rc=1；`AssertionError: 步驟 0 之 validate_split_pair_integrity 沒被呼叫` |

（改壞後均已還原。）

---

## 必答 5 — 契約面掃描（自立詞表）

### (5a)

**本輪詞表**（避開 r26 `metadata.split_unify`／`三層`／`整鏈`）：

`decision_at_ms 命中|逐列取.*feature_cutoff|cutoff in train_ms|現行碼在此案例|現況碼證.*命中數為 0|:530-553|以 cutoff 判側|per-cutoff 判側|集合成員判定迴圈|feature_cutoff_ms.*split_label`

**命令**：

```bash
WORDLIST='decision_at_ms 命中|逐列取.*feature_cutoff|cutoff in train_ms|現行碼在此案例|現況碼證.*命中數為 0|:530-553|以 cutoff 判側|per-cutoff 判側|集合成員判定迴圈|feature_cutoff_ms.*split_label'
for f in docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md; do
  awk '/^## 沿革與追溯索引$/{exit} /HISTORY-BEGIN/{skip=1} /HISTORY-END/{skip=0;next} skip{next} {print NR":"$0}' "$f" | grep -nE "$WORDLIST"
done
```

**SPEC 逐段**：

| 行 | 互斥？ | 結論 |
|----|--------|------|
| `:46` (3.1) 事件級 `decision_at_ms` | 否 | 權威契約，與實作一致 |
| `:170` (G-4) 舊路徑 cutoff 判側 | 否 | 歷史對照／換錨說明，非現行施工指令 |
| `:216-217` §P Task 9.2b「現況碼證」 | **是（與已落地碼）** | 仍寫「`decision_at_ms` 命中 0」＋`:530-553` per-cutoff——**實作已改**；見 `COMPOSER-R27-P2-01` |
| `:231` 不可做 per-cutoff | 否 | 禁止句，與現行一致 |
| `:261` §V「現行碼會給出 1h=test／4h=purged」 | **是（時態）** | 描述 9.2b **前**行為，易誤讀為現況；同 finding |
| `:301` M-SU-D2-22 應紅 | 否 | mutation 意圖正確 |

**TODO 逐段**：

| 行 | 互斥？ | 結論 |
|----|--------|------|
| `Task 9.2b` `:592-634` | 否 | 與碼一致 |
| `:615` 不可做 per-cutoff | 否 | 禁止句 |

**碼內 docstring**（掃描外附註）：`split_projection.py:462-464` 仍寫「`feature_cutoff_ms ∈ feature_index` 決定 train／test」——與 9.2b 行為不符，建議隨 `COMPOSER-R27-P2-01` 同步（非 SPEC/TODO 正文）。

### (5b)

**SPEC `:216-217` 建議替換字面**（保留刪節追溯）：

```markdown
- 🔴 **本 Task 是 `(3.1)` 的唯一落地處**（**v22 更正，R27 composer**：原「現況碼證：decision_at_ms 命中 0／:530-553 per-cutoff」為 9.2b **前**快照，已過期）。現行：錨點讀 `manifest.table["decision_at_ms"]`（`split_projection.py:677-701`），三段式＋廣播（`:716-756`），`feature_cutoff_ms` 不參與 `split_label`。
- 檔案：`split_projection._derive_single_symbol` 之事件級錨定與 `_assert_event_level_side_consistency`（`:392-430`、`:760`）。
```

**SPEC `:261` 建議替換字面**：

```markdown
- `Task 9.2b`：`ASSERT WHEN 同 event 之 1h cutoff 落 train 區、4h cutoff 落 test 區 且 decision_at_ms 落 test 區 THEN 兩列 split_label 皆為 test`（**9.2b 落地後**之正例；9.2b 前現行碼會給 1h=test／4h=purged）。
```

---

## 必答 6 — 可否進 `Task 9.3`（B9D）

### (6a)

**可以**——無 BLOCKING 程式缺陷；`COMPOSER-R27-P2-01` 為 SPEC 時態／現況碼證過期（doc-literal-only），不阻擋消費面 9.3 施工。

### (6b)

已檢查：六要點＋四不可做全落地（必答 2）；129 條回歸＋`GOLDEN OK`；破壞驗兩處轉紅；四 assumed 無否證；多 symbol 分支仍走同一 `_derive_single_symbol` 廣播路徑（`split_projection.py:850`）；NaN `decision_at_ms` 由 `assert_epoch_ms_array` fail-closed（非靜默落側）。

---

## COMPOSER-R27-P2-01

**斷言**: SPEC §P `Task 9.2b` `:216-217` 與 §V `:261` 仍以「9.2b 前」碼態為**現況**，與 commit `a1e9680e` 已落地之事件級錨定互斥，可能誤導後續讀者。

**碼證**: `rg -n 'decision_at_ms' momentum/Analysis/event_samples/split_projection.py | wc -l` → **28**（非 0）；`split_projection.py:720-725` `_side_of` 僅讀 `decision_ms`；SPEC 掃描命令見必答 5a → `:216`、`:261` 命中。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#755f3d53c1f3

doc-literal-only；信心度=High。行為已由碼與測試鎖定，戳記 v21 仍有效；**建議下一 doc 同步輪**更新上述兩處字面（修法見必答 5b），不阻擋 B9D impl。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R26-P3-00

ASSUMPTIONS_VERIFIED: body/stamps rc=0；129 pytest + GOLDEN OK；四 assumed 逐條核對；破壞驗 3 處；SPEC/TODO 詞表掃描
TESTS_RUN: `pytest tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py tests/momentum/Analysis/test_splitunify_golden.py -q` → 129 passed；`scripts/freeze_splitunify_golden.py` → GOLDEN OK；破壞驗 3 組（見 4b）
FAILURES_SEEN: none（破壞驗預期紅，已還原）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r27-composer.md

STATUS: DONE
