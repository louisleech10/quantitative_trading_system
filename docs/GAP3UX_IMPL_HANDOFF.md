# GAP-3 事件型 UAT 缺口修補 — **實作交接**（2026-08-24）

> **給下一個 session 的完整交接。** `HANDOFF.md` 只放指標，細節全在本檔。
> 讀完本檔即可開工，不必回頭問。

---

## §0 一句話狀態

**SPEC 🔒 凍結、TODO 🔒 凍結 v1.0、實作 ⬜ 42 個 Task 全部未開工。使用者已裁定「新 session 開始實作」。**

| 文件 | 路徑 | 狀態 | commit |
|---|---|---|---|
| SPEC（語意權威） | `docs/GAP3_EVENT_UX_SPEC.md` | 🔒 FROZEN，3,547 行／42 Task | `4ce3d6d9` |
| TODO（操作依據） | `docs/GAP3_EVENT_UX_TODO.md` | 🔒 FROZEN v1.0，1,618 行／42 Task | `afa70967` |
| TODO 延伸檔 | `docs/GAP3_EVENT_UX_TODO.D-001.md` | ⚠️ **未過戳記** | `f466a23b` |
| 施工看板（給使用者看） | `白話說明/GAP-3施工看板.md` | 42 Task 全 ⬜ | `f466a23b` |
| 階段 1 索引（追溯基準） | `handoffs/20260824-gap3ux-todo-stage1-index.md` | Phase 7／Task 42／§V 20／§G 3／§A 4 | 未版控 |

🔴 **層級**：**操作依據＝TODO；語意權威＝SPEC（衝突以 SPEC 為準並回報）；
讀 TODO 必須並讀 D-001**（凍結後修訂只走延伸檔，不就地改 TODO）。
🔴 **驗收字面之唯一來源＝SPEC 各 Task 之「驗證」欄**；TODO 只給可執行命令＋條目下限＋SPEC 行號。
**不得把 SPEC 斷言字面抄成第二份副本**——本 epic 三十四輪之自傷絕大多數出自副本漂移。

---

## §1 開工前稽核（逐條跑，全部要對；不對先修再開工）

```bash
git log --oneline -3
bash scripts/debt_ledger.sh --has-open          # 期望 rc=0（無未清委員會債）
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.md        # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-001.md  # 期望 rc=0
shasum -a 256 docs/GAP3_EVENT_UX_TODO.md        # 期望 c222f188… 之後續值；與 D-001 之 BASE 對照
grep -c '^### Task ' docs/GAP3_EVENT_UX_TODO.md # 期望 42
for r in r1 r2 r3; do bash scripts/reconcile_stamps_check.sh \
  handoffs/reconcile/20260824-gap3uxtodo-x-review-$r/synth.md codex,composer,grok; done   # 三份皆 PASS
```

---

## §2 B1 是什麼（**四個** Task，不是兩個）

🔴 **TODO 之 §B 表格 B1 列寫「1.1、1.10」是錯的**，已由 **D-001 A-001** 更正為：

| B1 含 Task | 為什麼在 B1 |
|---|---|
| **Task 1.1** 契約先行 | 定 reason／derived 欄／typed `receipt_schema`；後續每個 Phase 都讀 |
| **Task 1.10** 欄位級 lookahead 契約 | D-7 三層防線之根（L1）；1.11／1.12／2.1b 皆只讀它 |
| **Task 2.1b** 由篩選條件導出答案窗下界 | 建立**唯一深度函式** `depth_by_timeframe()`；**B3 之 1.9 與 B7 之 4.1 都消費它** |
| **Task 4.2**（**僅 §G S-9 參考實作部分**） | 建立 `canonical_serialize.py::canonical_event_table_bytes()`；**B2 之 1.3 需要它**。其 horizon 曲線部分留在 B7 |

**若照 TODO 表格只做兩個** ⇒ B2 開工時 `canonical_serialize.py` 不存在、
B3／B7 開工時 `depth_by_timeframe()` 不存在 ⇒ **那幾批當場停擺**。

### B1 四個 Task 之關鍵座標（詳細內容一律回讀 TODO 該 Task 全文）

| Task | 主要落點 | 驗收命令 |
|---|---|---|
| 1.1 | `momentum/Analysis/contracts/event_import_contract.json`；`momentum/Analysis/event_samples/import_contract.py`（`load_event_import_contract()`／`validate_event_import()`／新增 `flatten_receipt_schema()`）；新增凍結 fixture `tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json` | `pytest tests/api -q -k gap3_contract_reason_registry` **≥8 條** |
| 1.10 | 新增 `momentum/Analysis/contracts/future_column_lookahead.json`；新增 `momentum/Analysis/event_samples/lookahead_registry.py`（`load_lookahead_registry()`／`resolve_lookahead_bars()`／`unregistered_future_columns()`） | `pytest tests/momentum/event_samples/ -q -k lookahead_registry_complete` ＋ `pytest tests/api -q -k lookahead_rename_attack` **≥2 條** |
| 2.1b | 新增 `momentum/Analysis/event_samples/lookahead_depth.py`：`def depth_by_timeframe(referenced_columns, declared_window_bars, timeframes) -> dict[str,int]`（**唯一 exported 深度函式**）；`frontend/src/app/search/page.tsx`（下界鎖定 UI） | `pytest tests/api -q -k gap3_lookahead_depth` **≥4 條** |
| 4.2（S-9 部分） | 新增 `momentum/Analysis/event_samples/canonical_serialize.py::canonical_event_table_bytes()` ＋ S-9 之 **6 條驗收** | S-9 六條；horizon 曲線部分（`pipeline.py:98` 之 `analyze_tables` 呼叫點）**留 B7** |

🔴 **Task 1.1 之第一個動作**（在動任何契約欄位**之前**）：位元組拷貝出 baseline fixture，
跑 `cmp -s` 與 `shasum -a 256`，三條輸出入 commit message。
先改再拷、或產生 sanitized／重排版之副本 ⇒ 差集失去改前語意，屬違規。

---

## §3 派工管線（**大任務**，不得跳步）

命中高風險 (a) 數值/資料品質 ＋ (b) 跨模組 ⇒ **大任務**。SPEC／TODO 皆已凍結、已過 adversarial
⇒ **實作階段之管線為**：

1. **實作＝Claude 主委自任**（`docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行，2026-08-17 使用者五調逐字：
   「SPEC/TODO 初稿＝Claude 主委一律起草；**中/大實作＝Claude(Fable 5/Opus)主委自任**；
   討論/code review/adversarial＝**Codex＋Grok＋Composer 三家全員**；簽核 quorum＝三家」）。
   🔴 **派工前必先重讀該行**——選層是動態的，以使用者當下指示為準。
2. **每批收尾必派 code review**：三家全員，**實作者不自審**；機器強制
   `scripts/review_quorum_check.sh`（接在 `gate.sh` 派下一批前驗前批 quorum，不足即拒發 token）。
3. **開門**：`bash scripts/gate.sh dispatch --task-id … --risk high --intent … --facts-asked … --review-role … --template …`
   （委派與創建治理文件都需 fresh token；900 秒）。
4. **前後**：`bash scripts/agent_preflight.sh` → 派工 → `bash scripts/agent_postflight.sh`，PASS 才驗收。
5. **委員派工一律走** `scripts/cx_run.sh`（brief 放 repo 內、用絕對路徑、**禁 `&`**）。
6. **兩輪斷路器**：任何問題自己弄 ≤2 輪仍失敗 ⇒ 立即開委員會，禁 solo 硬幹。

---

## §4 「完成」的判準（不得放寬）

一個 Task 標 ✅ 的條件：
1. 該 Task「驗證」欄之命令**全部 rc=0**，且條目數 ≥ TODO 所列下限；
2. **該 Task 之 mutation 已實跑**——故意改壞 ⇒ 對應斷言**轉紅**；還原 ⇒ 轉綠；
3. **receipt 路徑寫進 commit message**。

🔴 **只有測試綠、沒有 mutation receipt ⇒ 仍是 🔧，不是 ✅。**
理由：測試綠只證明「現在沒壞」，mutation 才證明「壞了測得出來」。

**批次間 Gate**：上一批全部 mutation 轉紅並還原轉綠、receipt 入 commit，才可開下一批。

**每批收尾固定動作**：更新 `白話說明/GAP-3施工看板.md`（每完成一個 Task 改一列、更新「一眼看完」三個數字）
＋ 更新 `docs/ROADMAP.md` ＋ 更新 `HANDOFF.md` ＋ commit ＋ **背景 push**（使用者在外看進度）。

---

## §5 未辦事項（開工前／收 epic 前要處理）

| # | 事項 | 何時 |
|---|---|---|
| 1 | 🔴 **D-001 尚未取得委員戳記**。A-001 是主委自查所得之互斥更正，已附 mutation 與驗證命令，但**未經三家核可** ⇒ **開工 B1 前須補跑一次戳記輪**（與 TODO 定版同一程序：brief-kind `stamp`、單一 `stamp-target`、三家 append `RECONCILE-STAMP`） | **開 B1 前** |
| 2 | 本 session 動過 `scripts/plain_docs_sync_check.sh`（登記看板 WATCHED）⇒ 依規約 **收 epic 前**須跑 `bash scripts/gov_check.sh --no-probe`（**丟背景**，十分鐘級）。⚠️ **跑它時主控端不得動檔**（治理測試比對工作區 dirty 數） | 收 epic 前 |
| 3 | **GAP-3 B5 之 UAT B 段簽字**仍在使用者手上（`docs/GAP3_UAT_CHECKLIST.md`），與本批實作無依賴 | 使用者 |

---

## §6 地雷（本 epic 專屬，逐條是實際踩過的）

### 6.1 🔴 「比對範圍過寬」——主委在本 epic 犯了**四次**，形狀完全相同

| # | 形態 | 後果 |
|---|---|---|
| 1 | Phase Gate 之測試層標籤與 Task 欄位**同字面** | 機械閘分不出來 |
| 2 | 以**行號**注入修補，行號取自修補**前**之掃描輸出（中間檔案已位移） | 三處落到**錯的 Task**（1.3／1.10／7.0b 被塞了別人的 selector） |
| 3 | 判斷 Task 有無 mutation 時掃**整個區塊** | 被區塊尾端別人的字樣騙過（1.2／2.3 假跳過） |
| 4 | 同步斷言只驗**子字串存在**，散文卻宣稱「參數名序列逐字相等」 | **假綠**，改參數名照樣過 |

**共同形狀＝拿比目標更大的範圍去比對，然後把命中當成目標命中。**
🔴 **對策（照做）**：①錨點落在**真正要判斷的那個東西**上——不是它的段落、不是行號、不是附近的字
②**一律字面錨點，禁行號** ③檢查寫完要用**已知會紅的輸入**試一次，只看綠不算驗過。

### 6.2 產出端閘會擋你，而且多半擋對了

- `doc_format_precheck.sh`：驗證欄須**逐行**含可證偽 token（`pytest`／`==`／數字／`.py`…）；
  含「驗證」二字的 bullet **該行自身**要有 token（多行寫法會被判空殼）。
- commit message：operational claim 需 backing；`VERIFY:<path>`**冒號後不能有空格**，
  且該檔須含 `CLOSED`／`APPROVED`／`RECONCILE-STAMP` 等閉合判詞。
- 計數字面稽核：說明文字裡的「一支」「一筆」也會被當計數字面 ⇒ 改措辭。
- 白話狀態檔（`README.md`／`接下來要做什麼.md`）**禁純檔尾追加**，須改寫現況段。
- 延伸檔命名須 `<BASE>.D-00N.md`（`*_AMENDMENTS.md` 會被誤判為 todo 型別）；
  且 dext 必含 `BASE:`／`PREDECESSOR:`／`## 觸及面宣告`／`## 內容`／`## 戳記`。

### 6.3 工具與環境

- **本機 bash 3.2.57** ⇒ **無 `declare -A`**；`sed` 為 BSD ⇒ **BRE 不支援 `\|`**，一律用 `sed -E`。
  跨平台差異多半**不報錯，只是安靜地做錯**（曾使字尾沒切掉、到數字比較才炸）。
- **絕不寫 `cd <專案路徑>` 前綴**；瑣事別用 `python3 -c`；改檔用 Edit／Write 工具。
- `pytest tests/governance` 與 `govb1_final_gate.sh` 全跑皆**十分鐘級** ⇒ **一律丟背景**。
- `gov_check` 之 **G-7 為紅**（27 條「未宣告即修改」路徑多屬他 epic；commit `51d8ac7f` 已裁「接受」），
  但它會讓 `gov_check` 在第 4 段中止、**後面的全套 pytest 跑不到** ⇒ 需要時直接跑
  `pytest tests/governance -q`（約 44 分鐘；最近 **1743 passed / 6 failed**，6 條皆既有帳）。
- 委員會清 `/tmp` ⇒ 自己導到 `/tmp/x.log` 的檔可能被刪；重要輸出看 harness task output 檔。
- `handoffs/` **未入版控**（勿清）。

---

## §7 🔴 不要碰的東西

### 7.1 治理（使用者 2026-08-24 定死）

逐字：「當初就是發現你做治理是無解才不做」「你這樣岔題去問委員，永遠沒完沒了」。
⇒ **遇治理工具壞掉：繞過並具名記錄，不修、不開票。要動須使用者明示。**
⇒ **落地出錯就抄仔細**，不要「做一支工具來量自己」——那正是 SPEC 階段燒掉六輪的原因
（R28 新建對證工具 → 六輪修那支工具 → 把工具問題寫進派工單 → 委員回更多治理 findings → 自我餵養）。
⇒ **治理／工具問題不得寫進派工單**，那是迴圈的燃料。

### 7.2 已具名封存之殘留（**不排工、不另立票**）

- **SPEC 末節 F-1..F-4**：同輪重派死鎖／補丁包檔名碰撞／編排草圖含 illustrative 佔位不通過
  `compile()`／`gap3ux_apply_patch.py` 包側 VERIFY 缺陷。
- **TODO（R3 reconcile）四條**：前端 directory-only 路徑 10 處／Task 5.0 驗證 defer SPEC／
  五 Task（1.10／3.3／4.3／7.3／7.5）之 mutation 全文 defer SPEC（**composer 已交 exact mutant 補丁包**
  `handoffs/patches/20260824-gap3ux-todo-r2-composer-mutation-five.md`）／B1 須並讀 FROZEN SPEC。

---

## §8 檔案地圖（實作會碰到的）

| 用途 | 路徑 |
|---|---|
| 事件樣本模組（新邏輯放這） | `momentum/Analysis/event_samples/`（17 檔：`alignment.py`／`event_split.py`／`ic_feed.py`／`pipeline.py`／`tables.py`／`dedupe.py`／`import_contract.py`／`types.py`…） |
| 契約（欄位／枚舉／reason 之 SoT） | `momentum/Analysis/contracts/event_import_contract.json`、`ic_report_contract.json` |
| case 匯入端點 | `api/routes/case.py`（`import_events_file`／`import_events_json`／`get_event_import`／`analyze_event_import`／`_rejected` `:132`） |
| 匯入服務 | `api/services/case_import_service.py::EventImportService` |
| IC 分析端點 | `api/routes/ic_analysis.py`（`@router.post("/analyze")` `:34`） |
| IC 分析服務 | `api/services/ic_analysis_service.py::_run_analysis` |
| feature runs 端點 | `api/routes/feature_factory.py::list_runs()` `:60-62`（回傳來自 `feature_factory_service.list_runs()`） |
| 前端匯出 | `frontend/src/lib/eventExport.ts`（`EventExportOptions` `:9-17`；寫死值 `:92`／`:102`／`:104`；呼叫端 `frontend/src/app/search/page.tsx:522-525` **現況一個都沒傳**） |
| 搜尋引擎（future 欄之來源） | `momentum/DataExtraction/case_search_engine.py`（`periods_{H}h` `:1385-1387`；⚠️ `periods_72h` 亦用於**過去 3 天 lookback** `:1028-1046`，同名不同義） |
| 三輪審查之 reconcile | `handoffs/reconcile/20260824-gap3uxtodo-x-review-r{1,2,3}/synth.md`（三份皆三家 APPROVED） |
| 過程與教訓（給使用者） | `白話說明/治理進度日誌.md`、`白話說明/流程摩擦記錄.md` |
