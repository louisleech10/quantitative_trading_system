brief-kind: review
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R4
family: composer
findings-round: R4
標的 commit: HEAD（SPEC R3 修訂＋TODO；**尚未實作**）
SPEC-DIGEST: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241
TODO-DIGEST: docs/ICRESULT_PAGING_TODO.md#8e98dbd93418

## Verdict：可派工

R3 群集 X1–X5 均已落文件且本輪原反例重跑 **CLOSED**；X6（§C-9／§C-10／G-9）延遲預算經 39k 實機探針**可達**。本輪 **無 P0／P1**；2 條 P2（參數名殘留、§C-10 部分 UX 缺自動化測試）。**進 B0 前最後一件必做事**：修正 TODO Task 2.2 之 `order`→`sort_order`（P2-01，一行）；其餘 P2 可同輪或 B2 補 vitest。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| template_check 兩份 | **fact-verified** | `bash scripts/template_check.sh spec\|todo` → TEMPLATE PASS，rc=0 |
| 39k 報告尺度 | **fact-verified** | `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' …` → `{"st":39346,"meta_keys":39398}` |
| baseline 未漂移 | **fact-verified** | `shasum -a 256 -c handoffs/20260909-icresult-r4-baseline.sha` → 全 OK，rc=0 |
| §C-9 延遲在 39k 可達 | **fact-verified** | 見 X6 探針（paginate p50≈24ms、light JSON≈0.3ms、feature≈2KB） |
| G-9 TestClient 20× 可重現 | **assumed（設計合理）** | 探針尚未存在（Task 0.1）；純 Python 排序已遠低於門檻，TestClient 開銷主要是一次性 119MB 載入 fake task |
| §C-10 全項 vitest 可測 | **部分假** | skeleton／URL／跨頁勾選有 vitest；首屏 3s／舊圖遮罩／重試僅 B34（見 P2-02） |
| `order`／`q` 已清乾淨 | **假（殘留 1 處）** | `grep` 僅 pytest `-q` 與 Task 2.2 `order`（見 P2-01） |

---

## X1–X6 群集複驗

| 群集 | R3 處置 | R4 複驗 | 狀態 |
|---|---|---|---|
| **X1** AST 守衛 | SPEC/TODO 改 AST「helper 內==1、外==0」 | SPEC `:65`／TODO `:49` 一致；不再寫 regex「全域==0」 | **CLOSED** |
| **X2** `SIZE_GATE` 文法 | 統一 `SIZE_GATE=PASS\|FAIL\|BLOCKED`＋`SIZE_REASON=` | SPEC `:54`／TODO `:26`／`:18` 皆同一 token；gate 偽碼 `FAIL⇒rc=1` | **CLOSED** |
| **X3** `dict_count_key`＋funnel 順序 | §C-6 (iv) `count` 優先；先 funnel 再 counts | SPEC `:36` 明文「funnel 必須對計數**前** filter_log」；G-8 `stage5 output:0`；TODO `:100` 順序已改 | **CLOSED** |
| **X4** G-7b sentinel | `NEW__` 前綴＋feature sha | SPEC G-7b `:56`／TODO `:58` 斷言 rows／total／`feature_name` 無 `NEW__`＋各段 sha | **CLOSED** |
| **X5** page 六案例 | 表格 51 列＋排序 callback＋detail＋載入中＋六圖＋funnel null | SPEC Task 2.3 `:114`／TODO `:160` 六條齊；fixture 不含 `summary_table` | **CLOSED** |
| **X6** 效能／體驗 | §C-9／§C-10／G-9；FF 參數對齊 | 延遲探針 PASS 預算；LRU 8 組≈2.5MB/task 可接受；參數名 1 處殘留（P2-01）；UX 測試缺口（P2-02） | **CLOSED＋P2** |

### X6 延遲探針（VERIFY）

```
venv/bin/python /tmp/icresult_r4_perf_probe.py
→ rows=39346
→ paginate_cold_ms p50=24.3 p95=25.2  （§C-9 summary ≤100/200 ms ✓）
→ cache_hit_slice_ms p50=0.001          （≤20 ms ✓）
→ paginate_search_close_ms p50=11.4
→ light_bytes 28019                     （≤262144 ✓）
→ lru_8_index_lists_est_bytes=2518144   （≈2.4 MiB，8 組 sort 索引足夠）

venv/bin/python /tmp/icresult_r4_light_feature_probe.py
→ light_json_ms p50=0.3                 （§C-9 light ≤150/300 ms ✓）
→ full feature payload max=2198 bytes   （§C-9 feature ≤50/100 ms ✓）
```

**LRU 8 組／task**：涵蓋常見 `(sort_by, sort_order, pass_class, search)` 組合；8×39346×8B≈2.5MB 對 completed task 記憶體可忽略（報告本身 ~119MB 已在 `task_info`）。

**G-9 與 G-5 共用探針**：合理——同載入 39k artifact、同三態 `BLOCKED`（投影函式缺席）語意；`--latency` 分支印 `LATENCY_GATE=` 不污染 `SIZE_GATE=` 單行 gate。

---

## 必答（成對）

### 1a／1b 預設 `/result` 位元組級不變

- **1a**：`view` 預設誤走 light；`get_result` 加 `response_model` 重序列化；`deny_factor_in_ok_oos` 順序／突變改值；對 live dict `pop`（違 snapshot）。
- **1b**：**能**——G-1 `raw_body_sha256`＋mutation P6；抓不到純 OpenAPI 描述漂移。

### 2a／2b light 刪段＋metadata

- **2a**：**當下無**——§A receipt 前端鍵 ⊆ `metadata_keep_keys`；per-feature 段改走 `featureDetail`（B2 同批）。
- **2b**：漏刪七段或漏 `collection_to_count_paths`（`winsorized_features` 1.6MB 級）⇒ G-5 紅；無新漏段。

### 3a／3b 排序

- **3a**：後端 `sort_policy`（缺值沉底＋`feature_name` 次鍵）vs 現 `getSortValue`（`-Infinity`、無次鍵）**不同序**；39k `icir` 全 null ⇒ 字母序 vs 插入序。
- **3b**：**後端為準**（§C-8 明文行為變更）。

### 4a／4b refilter／競態

- **4a**：`result_revision`＋409；G-7a/b/c；snapshot lock 內取；前端 abort＋丟棄 revision 不符。
- **4b**：無戳 ⇒ 跨代混頁、G-2 不可證偽。

### 5a／5b 匯出

- **5a**：**既有** `GET /export/{task_id}/{format}`（`ic_analysis.py:649`）；Task 2.3 零改。
- **5b**：逐頁 39k 為分鐘級；本票不採。

### 6 ≥10× 不必要複雜

**無**。14 特徵全量 golden＋contract SoT＋mutation P1–P14 對應 §G；G-9 探針延伸 `--latency` 為必要收案。

### 7 B2／IP-RESID

- **B2 單批 cutover** 風險小於拆分（light 已開而圖表讀已刪段＝退化）。
- **IP-RESID-1/2/4**：`blocked-by` 落檔／Task 0.1 成立。
- **IP-RESID-3**：並存＋四格矩陣，不取代。

---

## §1 必查摘要

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | P2-01 `order` vs `sort_order` |
| 2 | 漏項 | 無 blocking |
| 3 | 不可測 | P2-02 §C-10 三項僅 B34 |
| 4–7 | quant/cache | 無 |
| 5 | 過度工程 | 無 |
| 6 | OOM | LRU ~2.5MB OK |
| 8 | API | FF 對齊除 P2-01 |
| 9 | 測試 | G-7b sentinel＋page 六案例足 |
| 10 | Agent | Task 精確 |
| 11 | 短命工 | 無 |

---

## COMPOSER-R4-P2-01

**斷言**: TODO Task 2.2 仍寫 `onParamsChange({sort_by, order, offset:0})`，與 §C 參數命名對齊 Feature Factory（`sort_order`）及同檔 `:144`／Task 2.3 `:160` 之 `{sort_by, sort_order, offset:0}` 矛盾，Agent 可能實作錯誤 query 鍵。

**碼證**: `docs/ICRESULT_PAGING_TODO.md:143` `SortButton ⇒ onParamsChange({sort_by, order, offset:0})`；同檔 `:144` URL query 用 `sort_order`；FF `api/routes/feature_factory.py:659-660` `sort_by`／`sort_order`；`grep -n 'sort_by, order' docs/ICRESULT_PAGING_TODO.md` → 1 命中；`grep -E '\?(q=|order=)' docs/ICRESULT_PAGING*.md` → 0。

**來源摘要**: docs/ICRESULT_PAGING_TODO.md#8e98dbd93418

[MINOR] 信心度=High。失敗：前端送 `order=desc` 而後端只收 `sort_order` ⇒ 排序無效或 400。修法：Task 2.2 `:143` 改 `sort_order`；加 vitest 斷言 callback 鍵名。

---

## COMPOSER-R4-P2-02

**斷言**: §C-10 要求「切換特徵保留舊圖＋loading 遮罩」「請求失敗可重試」「首屏 ≤3s 可互動」，但 Task 2.2／2.3 vitest 只覆 skeleton／URL／跨頁勾選，三項僅 Task 3.1 B34（`blocked-by:使用者`），回歸無機械 gate。

**碼證**: SPEC §C-10 `:42` 列七項 UX；Task 2.2 驗證 `:107`／TODO `:153` 含 skeleton／URL／勾選，**無**遮罩／重試／首屏；Task 3.1 `:121` 首屏＋遮罩靠使用者 UAT；page 六案例 `:114` 不含 chart 遮罩或 retry DOM。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#3b5bb3e1e241

[MINOR] 信心度=Medium。失敗：B2 gate 綠但切特徵閃白或失敗空白仍可能過 B3。修法：page 整合加 2 測（切 feature 舊圖仍在＋overlay；mock fetch fail⇒重試按鈕）；首屏 3s 保留 B34 即可。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha rc=0；39k paginate/light/feature 延遲探針；grep order/q；X1–X5 逐段對照 SPEC/TODO；FF browse 參數 `:653-663`
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq`；`shasum -a 256 -c handoffs/20260909-icresult-r4-baseline.sha` rc=0；`venv/bin/python /tmp/icresult_r4_perf_probe.py`；`venv/bin/python /tmp/icresult_r4_light_feature_probe.py`；`venv/bin/python handoffs/_light_size_probe.py`→28019；grep
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（文件審查；§C-9 門檻經探針支持可達）

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R4-composer.md`

STATUS: DONE
