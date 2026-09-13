# SPLITUNIFY b9 — review-r16 V1–V5 閉合再驗證 ＋ D-002 v16 重簽 — composer 交件

**task-id**: `20260911-SPLITUNIFY-B9-REVIEW-R16`  
**family**: composer  
**findings-round**: R16  
**審查標的**: v15→v16 diff `79b66dd1`；current block＝`M-SU-D2-38`／`39`／`40`、`Task 9.3`（含 `tables`／`ic_feed` 表與 receipt 閘第 5 點）、`Task 9.4`  
**禁改碼**：review-only；戳記 append 除外。

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: M-SU-D2-38 seam 可達 | **fact-verified** | `PYTHONPATH=. python scratchpad/r16-composer/hash_probe.py` → `drift=True`（重複 `event_id` 使 `manifest_hash` 變） |
| brief fact-verified: M-SU-D2-40 與 pandas 相符 | **fact-verified** | `PYTHONPATH=. python scratchpad/r16-composer/pandas_probe.py` → 重複索引 `reindex` 皆 `ValueError: cannot reindex on an axis with duplicate labels` |
| brief fact-verified: 40 列／29 register／§C-9 40/40 | **fact-verified** | `scratchpad/r16-composer/counts.txt` → mutations=40 register=29 forty_literal=1 c9_claims=40 |
| brief fact-verified: doc_format rc=0 | **fact-verified** | `doc_format_rc=0` |
| brief assumed: keyed 對證無可行繞過 | **推翻（部分）** | v16 第 5 點對 **9/29** 列可機械 keyed；**20/29** 列 register 落點欄無可抽取之 `repo/path.ext:line` ⇒ keyed **無從執行**（見必答 2、`COMPOSER-R16-P2-01`） |
| brief assumed: C5-25 施工點與 M-SU-D2-38 破壞點同一行 | **推翻** | register `C5-25`＝「`ic_feed` survivor **餵入端**」（無行號）；mutation seam＝`ic_feed.py:56-65`；現行 caller＝`pipeline.py:406`（見必答 3、`COMPOSER-R16-P2-02`） |

---

## 必答 1 — review-r15 反例閉合

### (1a) verdict

| finding | 提出方 | verdict |
|---------|--------|---------|
| `CODEX-R15-P1-01`／`COMPOSER-R15-P2-01`／`GROK-R15-P2-01`（receipt keyed 對證） | codex／composer／grok | **CLOSED**（同-line 至 `docs/` 對有 `path:line` 之列已失效；無 path 列殘留見 R16-P2-01） |
| `CODEX-R15-P1-02`（M-SU-D2-38 可達） | codex | **CLOSED** |
| `CODEX-R15-P1-03`（M-SU-D2-39 計數斷言） | codex | **CLOSED** |
| `CODEX-R15-P1-04`（M-SU-D2-40 pandas 反例） | codex | **CLOSED** |

### (1b) CLOSED 者重跑命令與觀測

**keyed receipt（U1）**  
`grep -n '逐列 keyed 對證' docs/SPLITUNIFY_TODO.md` → L652-655 已落地。  
對 **C5-29**：register 落點＝`tables.py:372`；receipt 若填 `docs/SPLITUNIFY_SPEC.D-002.md:96` ⇒ keyed **檔路徑不符**（應 FAIL）。  
對 **C5-01**：register 僅 `receipts.event_level`（無檔）⇒ keyed 字面**不可執行**（殘留見 P2-01）。

**M-SU-D2-38（U2）**  
`PYTHONPATH=. python scratchpad/r16-composer/hash_probe.py` → `unique_hash=c3d3087c…`／`dup_hash=f152cc84…`／`drift=True`；`ic_feed.py:56-59` 未按 `event_id` 去重即組 `rows`。

**M-SU-D2-39（U3）**  
`rg -l 'def test_tier_min_test_events_counts_unique_event_ids' tests/` → 零命中（Task 9.4 待建）；`docs/SPLITUNIFY_TODO.md:703-706` 已具名 `per_symbol_n`／`per_symbol_test_n` 去重計數斷言。

**M-SU-D2-40（U4）**  
`PYTHONPATH=. python scratchpad/r16-composer/pandas_probe.py` → 同值／衝突重複索引皆 `ValueError`；`tables.py:372` 現為 raw `reindex`（無 reducer）。  
`rg 'assignments 消費去重|同值去重' tests/momentum/event_samples/test_tables.py` → rc=1（成對測試待 Task 9.3 建立，符合 §V）。

---

## 必答 2 — register 落點欄 keyed 可執行性

### (2a) 不足以支撐 keyed 對證之列（逐列）

**A 類｜無 repo 相對 `path.ext:line`（10 列）**：`C5-01` `C5-02` `C5-03` `C5-07` `C5-10` `C5-11` `C5-12` `C5-20` `C5-22` `C5-25`

**B 類｜僅模組名＋`:line` 或 `ic_feed:109` 縮寫、無完整檔路徑（6 列）**：`C5-04` `C5-05` `C5-06` `C5-08` `C5-09` `C5-24`

**C 類｜有檔路徑但無行號（4 列）**：`C5-15`（`frontend/src/lib/types.ts`）`C5-16` `C5-17` `C5-18`

**可 keyed（9 列）**：`C5-13` `C5-14` `C5-19` `C5-21` `C5-23` `C5-26` `C5-27` `C5-28` `C5-29`

機械分類：`awk` 輸出見 `scratchpad/r16-composer/keyed_class.tsv`（`HAS_REPO_PATH`=9；其餘 20 列不足以 keyed）。

### (2b) 最小修補字面（可貼進 `Task 9.3` 驗收第 6 點）

> 對 register 第 2 欄**無**可抽取之 `momentum/`／`frontend/`／`tests/` 下 `*.py`／`*.tsx` 路徑之 `C5-NN` 列：碼證須為該列 mutation 欄（第 6 欄）所掛 `M-SU-D2-NN` 在 §V 應紅欄所列之**第一個** `tests/…py` 或 `momentum/…py` 路徑（行號須存在且 ≤ 檔案總行數）。🔴 **優先補齊 register 落點字面**（例：`C5-25` 改為 `` `pipeline.py:406` 呼叫 `event_context_from_windows` 前之 windows 去重 `` 或 `` `ic_feed.py:56-65` ``），補齊後該列改回 keyed 對證 register 同列檔路徑。

---

## 必答 3 — `M-SU-D2-38` 破壞點 vs `C5-25` 施工點

### (3a)

**不是同一行碼。**  
- `C5-25` register：「`ic_feed` survivor **餵入端**」（語意＝caller 側餵入）。  
- 現行 caller：`pipeline.py:406` `event_context_from_windows(prepared.windows, …)`，**未**去重。  
- `M-SU-D2-38` v16 seam：`event_context_from_windows` 內 `ic_feed.py:56-65` 組 `rows` 算雜湊。  
- 測試字面：直接呼叫 `event_context_from_windows`（函式內 seam），與 register「餵入端」字面**不對齊**。

### (3b) 最小修補字面

**register（`C5-25` 第 2 欄）**：

> `` `pipeline.py:406` 餵入 `event_context_from_windows` 之 `prepared.windows`（須先按 `event_id` 去重）／破壞 seam 同 `M-SU-D2-38` ``

或將 `M-SU-D2-38` 應紅測試改為經 `EventSamplePipeline.event_context_for_analysis` 間接驗證（與 register「餵入端」一致）。二者擇一，不可並存歧義。

---

## 必答 4 —「應紅之測試已存在但不會紅」

### (4a)

**零條。** `M-SU-D2-38`／`39`／`40` 之具名測試**尚未建立**（Task 9.3／9.4 交付物）；未發現應紅欄指向**錯誤**既有 node id。

### (4b) 可重跑命令

```bash
# 1) v16 三條具名測試是否存在
for t in test_tier_min_test_events_counts_unique_event_ids; do
  rg -l "def $t" tests/ || echo "MISSING $t"
done
rg -n 'event_context_from_windows|餵入去重|assignments 消費去重|同值去重' \
  tests/momentum/event_samples/test_gap3_conditional_ic.py \
  tests/momentum/event_samples/test_tables.py; echo rc=$?
# 實跑：test_tier_min… → MISSING；rg → rc=1（零命中）

# 2) 40 條應紅欄抽出（機械清單）
awk -F'|' '/^\| `M-SU-D2-/ {gsub(/`/,"",$2); print $2, substr($3,1,60)}' \
  docs/SPLITUNIFY_SPEC.D-002.md | head -5
# → 40 行；無錯引他檔之機械反例
```

---

## 必答 5 — 停輪判準（r15 收斂段）

### (5a)

本輪 findings 屬 **「P2 級字面」**——非 register mutation 欄錯配、非 40 條／29 列條數不一致；為 v16 keyed 閘對 20/29 列不可執行，以及 `C5-25` 與 `M-SU-D2-38` 施工／破壞字面未對齊。

### (5b)

依 r15 停輪判準 ⇒ **進 `Task 9.1` 實作**；上述 P2 於 `Task 9.3` 驗收補洞（register 落點補行號或驗收第 6 點 fallback）。

---

## 必答 6 — v16 body `8607f2b7…`

### (6a)

**APPROVED**（附 2 條 P2：`COMPOSER-R16-P2-01`、`COMPOSER-R16-P2-02`；不阻擋領 impl token）。

### (6b)

N/A（非 REJECTED）。

---

## COMPOSER-R16-P2-01

**斷言**: v16 receipt 第 5 點「逐列 keyed 對證 register 落點檔」對 **20/29** register 列**無法執行**，該子集仍只剩「檔存在＋行號合法」，同-line 假完成風險未全關。

**碼證**: `scratchpad/r16-composer/keyed_class.tsv`（`NO_PATHLINE` 10 列＋`REL_LINE_ONLY` 6 列＋無行號 4 列）；`docs/SPLITUNIFY_TODO.md:652-655`；R15 探針 `scratchpad/r15-composer/receipt_same_line_bypass.txt` 對 `C5-29` 在 keyed 下檔路徑不符，對 `C5-01`／`C5-25` keyed 字面不可判。

**來源摘要**: docs/SPLITUNIFY_TODO.md#8607f2b770fb

[P2] doc-literal-only。修法：見必答 2b（Task 9.3 驗收第 6 點 fallback ＋ 優先補 `C5-25` 等待補列之 `path:line`）。可行性：`awk` 分類已實跑。信心度=High。不阻 v16 戳記與 `Task 9.1`。

---

## COMPOSER-R16-P2-02

**斷言**: `C5-25` register 寫「survivor **餵入端**」而 `M-SU-D2-38` v16 鎖定 `event_context_from_windows` 函式體（`ic_feed.py:56-65`），施工點（`pipeline.py:406` caller 去重）與 mutation／測試 seam **可能落在不同行**，實作者依 register 在 caller 去重時直接測函式仍可能漏紅。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:120`（`C5-25` 無行號）vs `:315`（M-38 seam）；`momentum/Analysis/event_samples/pipeline.py:406` 未去重；`ic_feed.py:56-59` 組 `rows` 不去重。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#8607f2b770fb

[P2] doc-literal-only。修法：見必答 3b。可行性：實讀三處碼。信心度=High。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R15-P2-01

<!-- 主委（claude）2026-09-13 之**唯一**改動，依 scripts/debt_clear.sh:394 之設計路徑
     「cx_run 拒收裁決塊 ⇒ 主委修檔後 gate.sh register-output」：
     原字面另列了 CODEX-R15-P1-01..04 與 GROK-R15-P2-01 五個**他家**的 finding ID。
     依契約「CLOSED 之 ID 只在同 root 同家歷史產出查」，閉合只能由**原提出方**宣告
     （章程 §B8），故只保留本家自提之 COMPOSER-R15-P2-01。
     🔴 本家對他家 finding 的獨立複驗結論**原文仍完整保留在本檔正文**，未刪一字；
     被移除的只是機器可讀 CLOSED 欄中不屬於本家的 ID。除本行外本檔一字未動。 -->


ASSUMPTIONS_VERIFIED: body sha256 8607f2b7…；40/40／29 register；hash_probe drift=True；pandas ValueError；keyed 20/29 不可執行；C5-25≠M-38 同行  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`；`bash scripts/doc_format_precheck.sh`（兩檔 rc=0）；`scratchpad/r16-composer/verify_r16.sh`（部分）；`hash_probe.py`；`pandas_probe.py`；`rg` 具名測試掃描  
FAILURES_SEEN: verify_r16.sh 初跑 hash_probe 缺 PYTHONPATH（已以 `PYTHONPATH=.` 重跑通過）  
SCOPE_CHANGES: none（`docs/SPLITUNIFY_SPEC.D-002.md` 戳記 append 除外）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）

STATUS: DONE
