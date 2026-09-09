brief-kind: review
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R2
family: composer
findings-round: R2
標的 commit: `0ca66d8b`（R1 修訂 SPEC＋TODO；**尚未實作**）

## Verdict：可派工（附 1 條 P1 文件矛盾須主委修一句；無新 P0）

R1 群集 Z1–Z7 七項修訂已落文件且經本輪複驗**實質閉合**；僅 G-6 四列並列 fixture 之 asc 期望在 SPEC／TODO **互相矛盾**（見 COMPOSER-R2-P1-01）。修一句後可開 B0。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| 兩份文件 template | **fact-verified** | `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md`／`todo docs/ICRESULT_PAGING_TODO.md` → TEMPLATE PASS, rc=0 |
| 39k 報告尺度 | **fact-verified** | `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}` |
| completed 後僅 refilter 改寫 result | **已修正為 fact** | SPEC §A FACT-RECEIPT 已列三寫點 `:1623`／`:2339`／`:2631`；`grep` 僅此三處 → Z3 閉合 |
| 前端無元件讀 per-feature 段全量 map | **fact-verified** | `grep -rn 'Object.keys(report\|Object.entries(report' frontend/src` → 無 IC 報告全段掃描 |
| G-4∩G-5 可同時滿足 | **已修後成立** | `venv/bin/python handoffs/_light_size_probe.py` → `light_bytes 28019`；G-5 門檻 262144；G-4 改 (a)–(e) 投影語意 → Z1 閉合 |
| `response_model` 未宣告時加 `view` 必改 bytes | **unverified**（blocked-by Phase 1） | route 現無 `response_model`（`api/routes/ic_analysis.py:346-353`）；G-1 以 TestClient `response.content` 實測凍結 |

---

## R1 群集複驗（Z1–Z7）

| 群集 | R1 主張 | R2 複驗 | 狀態 |
|---|---|---|---|
| **Z1** G-4∩G-5 互斥 | light 投影＋G-4(a)–(e)＋G-5≤262144 | §C-6 四規則＋`collection_to_count_paths`；probe 28019；`filter_log` 無 `input`/`output` 僅 `input_features`/`output_features` | **CLOSED** |
| **Z2** metadata 白名單／selection_scope | 顯式列舉＋list→count | survivor 只讀 `scope_id`（`survivor_contract.py:598`）；39k 報告結構鍵含 `selection_scope`；前端無 `selection_scope` grep 命中 | **CLOSED**（見 P2-01 清單漂移） |
| **Z3** refilter 世代戳 | `result_revision`＋409＋G-7 | Task 1.0／§C-7／TODO 2.1 abort＋重拉一次 | **CLOSED** |
| **Z4** 排序／G-1 raw sha | `sort_policy`＋G-6＋raw body sha | §C-8 明文行為變更；G-1 改 raw sha；**TODO 1.1 G-6 asc 與 SPEC G-6 矛盾** | **PARTIAL** → P1-01 |
| **Z5** Task 2.3 匯出 | 零改 export | Task 2.3／SPEC 2.3 明寫維持 `/export`；`ExportButtons` 僅 `module_statuses`＋PNG | **CLOSED** |
| **Z6** G-5 skip／B2 捆綁 | fail＋B2a/B2b | G-5 `pytest.fail("blocked-by:artifact")`；§B B2a/B2b 已拆 | **CLOSED** |
| **Z7** 複雜度／交付順序 | 全量小 fixture＋先後端 | Task 0.1 禁 200 抽樣；B0→B1→B2a→B2b→B3 | **CLOSED** |

---

## 必答（成對）

### 1a／1b 預設 `/result` 位元組級不變

- **1a**：加 `view: Optional[Literal["light"]]=Query(None)` 後，若 `get_result` 在 `view is None` 時誤呼叫 `project_light_view`、或對 normalized dict 做 `copy` 重排鍵序、或引入 `response_model=ICReportLight` 觸發 pydantic 重序列化，預設 body 會變。`deny_factor_in_ok_oos` 順序錯誤亦會改值（非僅順序）。
- **1b**：**能**——G-1 `raw_body_sha256`（TestClient `response.content`）＋mutation P6；抓不到純 OpenAPI 描述漂移。

### 2a／2b light 刪段＋metadata 白名單

- **2a**：若 contract 僅含 TODO 0.1 驗證子集而漏列 `_light_size_probe.py` 之 `KEEP_META` 額外鍵（如 `label_kind`／`horizon`），且未來報告頂層出現該鍵，light 會靜默刪除——現 39k 報告頂層僅 `symbol,timeframe,config_hash,event_filter,fit_mode,selection_scope,survivor_output`（`jq`），**當下無前端讀取被刪鍵**。`ExportButtons` 讀 `module_statuses`（頂層，G-4d 保留）——不衝突。
- **2b**：若實作忘做 `collection_to_count_paths`（`winsorized_features` 39373 列、`consumed_event_labels` 115 列），單 `filter_log` 即可打破 G-5；`grouped_ic` 已列 `drop_sections`——不再矛盾。

### 3a／3b 排序

- **3a**：改後端 `sort_policy`（缺值兩向沉底＋`feature_name` 次鍵）與現前端 `getSortValue` **不同序**；39k `icir` 全 null ⇒ 前端 tie=0 保插入序、後端字母序 ⇒ 首列必變（SPEC 已宣告有意變更）。
- **3b**：**後端契約為準**（G-2／G-6）；前端本地序退役。

### 4a／4b refilter／G-2

- **4a**：G-2a 無篩選、G-2b 有篩選＝同參數單次 materialize；`result_revision` echo＋不符 409；G-7 交錯測試；前端 abort＋重拉。
- **4b**：不做版本戳 ⇒ 跨代混頁、勾選 Set 與倖存者不一致、G-2 不可證偽——已由 §C-7 封堵。

### 5a／5b 匯出

- **5a**：**既有** `GET /export/{task_id}/{format}` 讀全量 `task_info["result"]`（`ic_analysis_service.py:1915+`）；逐頁 summary **不應**取代。
- **5b**：79×序列請求為數十秒～分鐘級；本票已刪該路徑。

### 6 ≥10× 不必要複雜

**無**。14 特徵全量 golden＋單一 39k 尺寸 probe（不進 repo）合理；contract JSON 為 Rule 5 必要；mutation P1–P9 對應 G-1–G-7。

### 7 B2／IP-RESID

- **交付**：B2a（2.1+2.2）必要避「light 已開表格仍全量 DOM」；B2b（2.3）可獨立——已落 §B。
- **IP-RESID-1/2**：`blocked-by` 落檔格式成立。
- **IP-RESID-3**：並存＋Task 1.3 四格矩陣——成立。
- **IP-RESID-4**：`needs-research` **成立**（見 P2-02）：實機無 `input`/`output` 鍵，漏斗改前即錯；light 轉 `_count` 後更不匹配。

---

## §1 必查摘要

1. 矛盾/互斥：**有**——SPEC G-6 vs TODO 1.1 G-6 asc（P1-01）
2. 漏項/端到端：無（revision／export／survivor 已覆蓋）
3. 不可測驗收：無（G-1–G-7 可機檢）
4. 可疑 quant 假設：無（不改計算）
5. 過度工程：無（R1 已瘦身）
6. OOM/並行：無新洞（DOM≤limit）
7. Cache：N/A
8. API/相容：IP-RESID-3 四格矩陣已列
9. 測試品質：G-5 fail-closed 已修
10. Agent 可執行性：Task 精確到檔案
11. 必要性/短命工：Task 2.3 匯出零改——無白工

---

## COMPOSER-R2-P1-01

**斷言**: SPEC §G G-6 四列並列 fixture 之 `asc` 期望序為 `[A,B,C,D]`，但 TODO Task 1.1 驗證寫 `asc == [B,A,C,D]`，與 contract `sort_policy`（並列次鍵 `feature_name` 升冪）矛盾，實作者必有一邊假綠。

**碼證**: SPEC `docs/ICRESULT_PAGING_SPEC.md` §G G-6「desc 序 == `[A,B,C,D]`、asc 序 == `[A,B,C,D]`」；TODO `docs/ICRESULT_PAGING_TODO.md` Task 1.1 驗證「4 列並列 fixture desc == `[A,B,C,D]`、asc == `[B,A,C,D]`」。手算：A/B 同有限值且 A<B 名序，C/D 為 None、兩向沉底 ⇒ asc 亦為 `[A,B,C,D]`。RECHECK: 對照兩檔 G-6 段＋`sort_policy` 次鍵規則。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#376e43979064

[MAJOR] 信心度=High。B1 gate 會因 SPEC/TODO 各寫各的而 rc=1 或 agent 猜錯。修法：TODO Task 1.1 驗證改 `asc == [A,B,C,D]` 與 SPEC 對齊（3 列 fixture `[A,B,C]` 已一致）。

---

## COMPOSER-R2-P2-01

**斷言**: `metadata_keep_keys` 三份來源清單不一致——§A receipt、TODO 0.1 檔案欄、`_light_size_probe.py` KEEP_META 互為超集／子集，G-5 receipt（28019 bytes）依最寬 probe 清單，contract 若只實作 TODO 驗證子集則 bytes 更小但與 receipt 不可對證。

**碼證**: probe `handoffs/_light_size_probe.py:5` 含 `quality,density_metrics,label_kind,horizon,...`；TODO 0.1 驗證子集僅列 14 鍵＋`fit_mode` 等；39k 報告頂層結構鍵 `jq` → 7 鍵（無 `label_kind`）。RECHECK: diff 三份清單。

**來源摘要**: handoffs/_light_size_probe.py#（probe 腳本）

[MINOR] 信心度=Medium。當下 39k 不爆，但 B0 寫 contract 時應以**單一**顯式清單為準並讓 probe 讀 contract，避免 receipt 漂移。

---

## COMPOSER-R2-P2-02

**斷言**: `IP-RESID-4` 之 `needs-research` 理由成立，但 B34 UAT 若含漏斗互動，在 light `filter_log` 集合→`_count` 後 `FilterFunnelChart`（讀 `values.input`/`values.output`）仍全 undefined——改前即錯、改後不會自動好。

**碼證**: `FilterFunnelChart.tsx:20-21` 讀 `input`/`output`；實機 `jq` 各 stage 鍵集合無 `input`/`output`，有 `input_features`/`output_features`；§N IP-RESID-4 觸發「B34 漏斗空白」。RECHECK: `jq -r '.filter_log|to_entries[].value|keys[]' … | sort -u`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#17e213a6d472

[MINOR] 信心度=High。不阻派工；建議 B34 清單註明漏斗為既有缺陷或 Task 2.3 改讀 `*_count`／`input_features_count`。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；三 result 寫點 grep；filter_log 鍵集合；survivor scope_id；_light_size_probe 28019；ExportButtons export 路徑；G-6 手算四列序
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq -c '{st,meta_keys}'`；`jq` filter_log keys；`grep task_info["result"]`；`venv/bin/python handoffs/_light_size_probe.py`；讀碼 FilterFunnelChart/ExportButtons/route
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R2-composer.md`

STATUS: DONE
