# SPLITUNIFY b9 — review-r30（O1–O5 閉合再驗證 ＋ v24 重簽）— composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R30`  
**family**: composer  
**findings-round**: R30  
**brief-kind**: review  
**審查標的**: commit `fa0ca3f4`；current block＝O1–O5 落點 ＋ `SU-RESID-V8-ATTEST`  
**禁改碼／禁改 SPEC 正文／禁改 TODO**（戳記 append 除外）。

---

## §0 被當成事實的未驗證假設（挑戰前提）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 六路 736 passed | **fact-verified（子集）** | 本輪 `derive`＋`wiring`＋`golden` → **144 passed** rc=0；全六路未重跑（brief VERIFY-EXEMPT） |
| brief fact-verified: doc_format 雙檔 rc=0 | **fact-verified** | 本輪複驗 rc=0/0 |
| brief fact-verified: 主委四探针 | **fact-verified（本家重跑）** | 見必答 1b；輸出 `/tmp/r30_composer_probe2.out` |
| brief fact-verified: r29 `state=CLOSED` | **未驗證** | 本輪未跑 `debt_ledger.sh` |
| assumed 1: `SU-RESID-V8-ATTEST` 歸類正確 | 見必答 3(3a)① | |
| assumed 2: O1 digest 擋住習慣性全列 | 見必答 3(3a)② | |
| assumed 3: O3 不可變字面消除共因 | 見必答 3(3a)③ | |
| assumed 4: O5 已窮盡同型 | 見必答 3(3a)④／必答 4 | |

---

## 必答 1 — 重跑 review-r29 反例（§B8）

### (1a)

| 項目 | 判定 |
|------|------|
| `COMPOSER-R27-P2-01`（r29 本家唯一反例；M9 四處 9.2b 前快照） | **CLOSED** |
| codex 五探针（O1–O5 閉合；brief 要求重跑） | **CLOSED** |
| `COMPOSER-R29-P3-00`（r29 零 finding sentinel 之核對基線） | **CLOSED**（O1–O5 已落地，本輪複驗通過） |

### (1b)

**`COMPOSER-R27-P2-01`**

```bash
rg -n '現況碼證|現行碼在此案例|現行碼會給' docs/SPLITUNIFY_SPEC.D-002.md
# → 命中皆在刪節線／mutation 表，非 live 施工句
```

**探针 ①（O1 只給鍵名）** — `python scratchpad/r30_composer_probes.py o1`

```text
GOLDEN REFUSE: --accept-value-changes 之項目 'g4_per_symbol_n' 格式不合——須為 `<key>=<old8>:<new8>`（只列鍵名不算授權；fail-closed）
O1_KEY_ONLY_RC 1
```

**探针 ②（O2 HISTORY 假錨）** — `python scratchpad/r30_composer_probes.py o2`

```text
GOLDEN V8 ANCHOR MISSING: SPEC §V 缺（或有多於一個）逐字 `V8_BASELINE_SHA256=<64-hex>` 錨點行…
O2_ANCHOR_READ None
O2_HISTORY_RC 1
```

**探针 ③（O3 BASE+17ms）** — `python scratchpad/r30_composer_probes.py o3`

```text
✗ G-4e（錨點時刻對帳）: tr0: 人手=1700000000000 實際=1700000000017
…（13 筆全紅）
O3_BASE_SHIFT_RC 1
```

**探针 ④（O4 --init-v8）** — `python scratchpad/r30_composer_probes.py o4`

```text
✓ 已建立 v8 不可變基準（splitunify_golden.v8.json ＋ splitunify_golden.v8.sha256）；🔴 請把其 sha256 逐字寫入 SPEC §V 之 `V8_BASELINE_SHA256=` 錨點行
GOLDEN V8 TAMPERED: 旁檔宣告 … 與 SPEC §V 之外部錨 f270e007ca98… 不符
O4_INIT_RC 1
O4_INIT_CREATED True
```

**O5 fixture 探针** — `python scratchpad/r30_composer_probes.py o5`

```text
O5_EQUAL 12 [tr0..te4 共 12]
O5_NON_EQUAL ['bnd_shift']
```

---

## 必答 2 — v24 body 重簽

### (2a)

**APPROVED**（body `bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c`）。存在一條 **P2 文檔同步**（`COMPOSER-R30-P2-01`），不阻擋 B9D。

### (2b)

N/A。

---

## 必答 3 — 四條 assumed

### (3a)

① **`SU-RESID-V8-ATTEST` 歸類與邊界** → **成立**。

- 查過 `handoffs/run_receipts/`：現行只用於 G-3a 遷移報告（`freeze_splitunify_golden.py:14`），**同一 commit 可夾帶 receipt 與 SPEC／golden 變更**，不構成獨立信任根。
- 錨點放到 repo 外或另開 receipt 留痕，仍須**人工流程／外部儲存**，等同新建治理面，與 2026-09-12「不再擴建治理工具」同型。
- `--init-v8` 在刪檔後可重建（探针 `o4d`：`O4_DELETE_REBUILD_CREATES True`），但 **rc=1** 直到同步改 §V 錨——與殘留「同 commit 四檔齊改」同一攻擊面，已誠實具名。

② **O1 digest 擋「習慣性全列」；貼回錯誤訊息是否等價無閘** → **不成立（作為無閘攻擊）**。

- 只給鍵名：探针 ① rc=1。
- 貼回建議 digest：錯誤訊息給出 `g4_per_symbol_n=b7088eec:dd296919`（本輪實跑）；第二次帶該字串可授權——這是**明示兩步授權**，與 r28「只列鍵名即可任意改值」不等價；仍須先觸發 `GOLDEN REFUSE`、讀取 digest、再 commit。

③ **O3 不可變字面消除共因；字面來源若當初算錯** → **部分成立（誠實邊界），不阻擋 B9D**。

- **已消除 runtime 共因**：`BASE+=17` 探针 ③ 轉紅；`test_hand_decision_timestamps_are_immutable_literals` PASS。
- **殘餘**：13 筆字面若於撰寫時就算錯，仍可能與當時 `_feature_index()` 一致——屬**一次性人工錯誤**，非可重複 bypass。第三種形狀（可選）：freeze 時列印 `event_id→decision_at_ms` 對照表供人工核對後貼字面——文檔建議，非本輪必做。

④ **O5 已窮盡同型** → **不成立**——見必答 4 與 `COMPOSER-R30-P2-01`（第十處：§V `:265` 仍寫「逐筆手算」而 v24 碼已改不可變字面）。

### (3b)

`COMPOSER-R30-P2-01` 給出可直接貼入之 §V 修正字面；其餘 assumed 無需新修法。

---

## 必答 4 — 契約面改動後強制掃描（同型第十次）

### (4a)

**本輪詞表**（避開 r29 per-cutoff 詞表與 r26 metadata 詞表）：

`old8:new8|只列鍵名|空心通過|xfailed|逐筆手算|BASE.*H1|不可變字面|SU-RESID-V8|習慣性.*鍵|--init-v8|write-once.*覆寫|全部事件.*decision`

**命令**：

```bash
WORDLIST='old8:new8|只列鍵名|空心通過|xfailed|逐筆手算|BASE.*H1|不可變字面|SU-RESID-V8|習慣性.*鍵|--init-v8|write-once.*覆寫|全部事件.*decision'
for f in docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md; do
  awk '/^## 沿革與追溯索引$/{exit} /HISTORY-BEGIN/{skip=1} /HISTORY-END/{skip=0;next} skip{next} {print NR":"$0}' "$f" | grep -nE "$WORDLIST" || echo "(no hits)"
done
```

**SPEC 逐段**（live 區命中 6 處；沿革區不審）：

| 行 | live 互斥？ | 結論 |
|----|------------|------|
| `:264` | 否 | v24 O1 正句（old8:new8 授權） |
| `:271` | 否 | v24 O5 已更正空心通過註 |
| `:338` | 否 | `SU-RESID-V8-ATTEST` 殘留定義，與契約一致 |
| **`:265`** | **是（P2）** | 仍寫「值由 fixture 常數**逐筆手算**」，與 v24 O3 之「13 筆**不可變字面**、不得由 `BASE`／`H1` 推導」（`freeze_splitunify_golden.py:145-164`、`test_hand_decision_timestamps_are_immutable_literals`）互斥 → `COMPOSER-R30-P2-01` |
| `:258` metadata | 否 | 殘留／刪節上下文，非 live 施工矛盾 |
| `:182` 逐 symbol 相加 | 否 | 刪節更正句 |

**TODO 逐段**（命中 6 處）：

| 行 | live 互斥？ | 結論 |
|----|------------|------|
| `:574-596` | 否 | v24 三處 xfail→passed 更正，刪節保留 |
| `:638` | 否 | Task 9.2b 前置說明（空心通過指前置工作，非現況） |
| `:918` | 否 | `SU-RESID-V8-ATTEST` 表列與 SPEC 一致 |

**同型第十次**：**發作 1 處**（§V `:265`）；其餘命中為 v24 更正或殘留誠實邊界。

### (4b)

**§V `:265`（`COMPOSER-R30-P2-01`）** — 將

`值由 fixture 常數逐筆手算`

改為

`值為 13 筆不可變整數字面（逐 event_id 寫死），不得由 BASE／H1 或任何運算式在程式內推導`

（保留同句後半「不讀 feature_index、不經 holdout_boundary」不動。）

---

## 必答 5 — 可否進 `Task 9.3`（B9D）

### (5a)

**可以**——O1–O5 五探针全 CLOSED；`SU-RESID-V8-ATTEST` 已具名且邊界正確；唯一 P2 為 §V 敘述同步，**不構成 B9D 施工阻擋**。

### (5b)

已檢查：r29 本家反例＋codex 五探针重跑；四 assumed 攻擊；換詞表逐段掃；`git show fa0ca3f4` 契約面僅 O1–O5＋殘留（無夾帶）；144 pytest + `GOLDEN OK` + body hash 複驗。

---

## COMPOSER-R30-P2-01

**斷言**: §V `:265` 仍寫「fixture 常數逐筆手算」，與 v24 O3 已落地的「不可變字面、不得由 BASE／H1 推導」互斥，實作者依 SPEC 可能把共因公式寫回。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:265` 逐字含「逐筆手算」；`scripts/freeze_splitunify_golden.py:145-164` 為 `_hand_decision` 字面 dict；`pytest tests/momentum/Analysis/test_splitunify_golden.py::test_hand_decision_timestamps_are_immutable_literals -q` → **1 passed**。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#bc4a2b3ea78f; scripts/freeze_splitunify_golden.py#c8c5a46f6804

doc-literal-only；信心度=High。修法見必答 4(4b)；一次文件修訂可閉合，不動碼。

---

## 戳記（append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記）

```
RECONCILE-STAMP: composer APPROVED 2026-09-14 sha256:bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c task:20260911-SPLITUNIFY-B9-REVIEW-R30
```

（舊戳記行已保留。）

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R27-P2-01

ASSUMPTIONS_VERIFIED: body hash bc4a2b3e…；doc_format 0/0；五探针 `/tmp/r30_composer_probe2.out`；O1 貼回 digest 兩步授權（錯誤訊息 `b7088eec:dd296919`）；144 pytest + GOLDEN OK；換詞表第十處=§V:265
TESTS_RUN: `reconcile_body_hash.sh` rc=0；`doc_format_precheck.sh` SPEC/TODO rc=0/0；`pytest …derive+wiring+golden… -q` → 144 passed；`freeze_splitunify_golden.py` → GOLDEN OK；`scratchpad/r30_composer_probes.py all`
FAILURES_SEEN: 首版探针誤寫 golden（已 `git checkout` 還原）；修正後無
SCOPE_CHANGES: stamp append 至 `docs/SPLITUNIFY_SPEC.D-002.md` §戳記（brief 授權）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r30-composer.md

STATUS: DONE
