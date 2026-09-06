# GAP-3 事件分析頁 — 揭露與說明補完 SPEC

> 來源 PLAN/診斷：2026-09-06 使用者 UAT B21／B22／B23 回報（10 條）＋主委實跑定性　|　日期：2026-09-06　|　對應 TODO：`docs/GAP3_EVENT_DISCLOSURE_TODO.md`

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：**中**（接 CLAUDE.md 任務分派規則）。單一功能面（事件分析頁之揭露），動既有 caller（`_run_event_label_stages` 之回傳 dict、`EventBatchDisclosurePanel` 之 props），不新增計算路徑。
- **命中高風險原則**：**(b) 跨模組共用路徑** —— 需在 `ic_filter_orchestrator` 既有 metadata 與 `ic_analysis_service` 之揭露 dict 之間新增一條投影，兩者皆為共用路徑。
  - **不命中 (a)**：本 SPEC **不改任何數值計算**；所有要顯示的量（`train_rows`／`test_rows`／`min_test_rows`／`reason`／逐格 `k,h`）**都已經被算出來並寫進 log 或 report metadata**，本票只做投影與顯示。
  - **不命中 (c)**：單一 Phase，每 Task 獨立可 revert。
  - **不命中 (d)**：不動 ML／回測路徑之任何判定；`analysis_status`／`oos_guarantees` 之**判定規則一字不改**，只把已有的判定理由帶到前端。
RISK-HIT: b

## §A 假設與待使用者確認（事故：拿推論代替問人）

- **已驗證事實**（5 條 FACT-RECEIPT，皆 2026-09-06 主委實跑；`grep`／`sed` 輸出如下）：
  - `FACT-RECEIPT: grep -n "full-sample fallback triggered" /tmp/uat_be.log` → 印出 `reason=rolling_warmup_insufficient train_rows=82 test_rows=30 min_test_rows=131 fit_mode=full_sample`（主委 實跑 2026-09-06）
  - `FACT-RECEIPT: grep -n "min_test_rows" momentum/Analysis/ic_config_schema.py` → 印出 `164: min_test_rows: int = Field(default=30, ge=10)` 與 `420: min_test_rows: int = Field(default=131, ge=1)`（主委 實跑 2026-09-06）
  - `FACT-RECEIPT: sed -n '/def _run_scan_grid/,/def _run_scan_cell/p' api/services/ic_analysis_service.py` → 印出逐格 `cell_spec` 含 `"decision_offset_bars": int(k)` 與 `"horizon_bars": int(h)`（主委 實跑 2026-09-06）⇒ **掃描矩陣之逐格 k/h 計算正確，本票不修計算**
  - `FACT-RECEIPT: sed -n '168,182p' momentum/Analysis/event_samples/alignment.py` → 印出 `elif mode == "open_to_close": label_start = entry_at; end_idx = entry_idx`（主委 實跑 2026-09-06）⇒ **`open_to_close` 不使用 `horizon`**
  - `FACT-RECEIPT: sed -n '/data-testid="ic-param-scan"/,/ic-param-bounds/p' frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx | grep disabled` → 印出 `disabled={!kScanOn}`／`disabled={!hScanOn}`（主委 實跑 2026-09-06）⇒ **h 掃描之 disable 條件不含報酬量法**

- **待使用者確認**：`待確認：無`

- **已確認結果**：`2026-09-06 使用者 UAT B21/B22/B23 回報十條，並指示「我現在已經沒在執行任何作業，你可以直接開工」`

## §C 約束（不重抄，引用 + 只列本任務相關）

- 解耦 7 條：`momentum/` 不 import `api/`；服務不互 import（本票之新投影一律經 `ic_analysis_service` 讀 report metadata，**不得**讓前端或 route 直接讀 `ic_filter_orchestrator`）。
- **不可違反**：不弱化任何既有 gate；`analysis_status`／`oos_guarantees` 之**判定規則不得改動**（本票只讀不寫）。
- 本任務特別注意：
  - `_run_event_label_stages` 之回傳 dict 已有 8 個 consumer 鍵，新增鍵**只增不改**；
  - `EventBatchDisclosurePanel` 之 props 於 B-D4 曾發生「元件做好而無呼叫端傳值」之幽靈功能，本票**每個新 props 必須有攔 HTTP／攔 render 的接線測試**；
  - 文案字面凡屬**契約既有欄位**者一律取自契約 `doc`（`eventContractDocs.ts` 鏡像機制），**不得**在元件內另寫第二份。

> **本 SPEC 不定義任何新的 schema／枚舉／常數**：所有要顯示的欄位皆為既有 metadata 之投影；
> 唯一新增之前端字串（h／k 之教學說明、seed／鄰域／embargo 之說明）屬 **UI 文案**，
> 住 `frontend/src/lib/eventParamDocs.ts` 單一檔，不散在元件內。

## §P Phase 與依賴

### Phase 1 — 事件分析頁之揭露與說明補完（依賴：無）

**Task 1.1 — 當根（`open_to_close`）時停用 h 掃描**
- 目標：報酬量法為「當根」時，h 掃描之勾選與上限輸入一律 disabled 並顯示理由。　檔案：`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`（h 掃描之 `<input type="checkbox" data-testid="ic-param-scan-h-toggle">` 與 `ic-param-scan-h-max`）。　既有 caller：同檔之 `setScan`。
- 改法：新增 `hScanApplicable = spec.label_return_mode !== 'open_to_close'`；兩個控制項之 `disabled` 改為 `!hScanApplicable || !hScanOn`（toggle 為 `!hScanApplicable`）；`hScanApplicable === false` 時以 `setScan({ horizon_bars_max: undefined })` 清除既有值；旁列 `data-testid="ic-param-scan-h-inapplicable"` 說明「當根只看事件那一根，h 不參與計算，掃出來每一格都會一樣」。
- **驗證（可證偽）**：`cd frontend && npx vitest run icRandomControl icEventBatchDisclosure`
  - `ASSERT npx vitest run icEventBatchDisclosure WHEN preset=same_bar THEN rc=0`（斷言 `ic-param-scan-h-toggle` 之 `disabled === true` 且 `ic-param-scan-h-inapplicable` 存在）
  - 正向對照：`preset=hold` 時該 toggle `disabled === false` 且說明不存在
  - 切換對照：先 `preset=hold` 勾 h 掃描填 5，再切 `preset=same_bar` ⇒ 送出之 `event_label_scan.horizon_bars_max` 為 `undefined`（**不得**留著舊值）
- **邊界（≥2）**：①未選報酬量法（`labelSpec === undefined`）⇒ 視為不適用之**反面**（不 disable，因為尚未決定量法，disable 會讓使用者以為壞了）；②k 掃描不受本 Task 影響，`preset=same_bar` 時 k 掃描仍可用。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不得改 `_scan_axes` 或後端任何計算；不得因為「當根 h 無效」就把 h 從送出的 spec 拿掉（`horizon_bars` 為契約四鍵之一，缺鍵 normalizer fail-closed）。

**Task 1.2 — 主結果與掃描矩陣之關係揭露**
- 目標：畫面明說「主結果＝框裡的 (k,h)」，且矩陣中對應那一格有視覺標示。　檔案：同上（`ic-param-scan-result` 區）。　既有 caller：`ic-scan-cell-<k>-<h>` 之 render 迴圈。
- 改法：①矩陣區上方加一行 `data-testid="ic-scan-primary-note"`：「上方的主要結果＝k＝{k}、h＝{h}（分析參數框裡的值）。下表是另外跑的，沒有勾掃描的那一軸就用框裡的值。」②對 `c.k === spec.decision_offset_bars && c.h === spec.horizon_bars` 之格子加 `data-primary="true"` 與可見標記。
- **驗證（可證偽）**：vitest：①`ic-scan-primary-note` 之文字含當前 k 與 h 之實際值（改 k 之後該行跟著變）；②恰有**一格** `data-primary="true"`，且其 `k`／`h` 等於送出 spec 之值；③主結果之 (k,h) 落在掃描範圍**之外**時（例：k 框＝5、k 掃描 0～3）⇒ `data-primary` 之格子數為 **0**，且 `ic-scan-primary-note` 追加「主結果不在下表範圍內」。
- **邊界（≥2）**：①未開掃描 ⇒ 整區不 render（既有行為，不得因本 Task 而出現空表）；②掃描只開一軸 ⇒ 另一軸只有一個值，主格仍須唯一。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不得在前端重算任何一格之 IC；不得把主結果從矩陣「移進去」（兩者是分開跑的，合併顯示會讓人以為是同一次計算）。

**Task 1.3 — `degraded_full_sample` 之原因與門檻投影到畫面**
- 目標：使用者看得到「為什麼沒有 OOS 保證」與「還差多少」。　檔案：`momentum/Analysis/ic_filter_orchestrator.py`（**只讀**，把既有 fallback details 寫進 report metadata 之既有節點）、`api/services/ic_analysis_service.py`（投影進揭露 dict）、`frontend/src/components/ic-analysis/`（顯示）。
- 改法：①orchestrator 之 full-sample fallback 路徑已持有 `reason`／`train_rows`／`test_rows`／`min_test_rows`（見 §A receipt），將其寫入 `metadata["oos_downgrade"] = {reason, train_rows, test_rows, min_test_rows}`；**判定規則不動**。②`ic_analysis_service` 把該節點原樣投影至 task_info 之 `oos_downgrade`。③前端在既有的 `Full-sample research-only` 警語**之下**加一行具體說明。
- **驗證（可證偽）**：`venv/bin/python -m pytest tests/api -q -k "oos_downgrade or degraded"` 全綠，且逐條：
  - 對一個**真實**小事件批（115 筆）跑分析 ⇒ `oos_downgrade.reason == "rolling_warmup_insufficient"` 且 `min_test_rows == 131` 且 `test_rows < min_test_rows`
  - 正向對照：足夠大的樣本 ⇒ `analysis_status == "ok_oos"` 且 `oos_downgrade is None`（**不得**恆常出現）
  - `ASSERT venv/bin/python -m pytest tests/api -q -k oos_downgrade WHEN mutation=drop_downgrade_projection THEN rc!=0`
- **邊界（≥2）**：①`ok_oos` 時該節點為 `None`（不得寫空 dict，空 dict 與「沒有降級」在前端分不出來）；②非事件模式（全域 IC）同樣適用——本欄不綁事件路徑。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：**不得**改 `_resolve_root_status` 之任何分支；不得因為要顯示而放寬 `min_test_rows`；不得在前端自行推算「還差幾筆事件」（列數與事件數不是同一個量，換算需要對齊層資訊）。

**Task 1.4 — 參數說明文案（h／k／進階區／隨機對照三參數）**
- 目標：每個使用者要填的數字旁邊都說得出「這是什麼、影響什麼」。　檔案：新增 `frontend/src/lib/eventParamDocs.ts`；`EventBatchDisclosurePanel.tsx` 引用。
- 改法：單一檔匯出 `EVENT_PARAM_DOCS`（鍵＝參數名，值＝`{what, effect}` 兩句），涵蓋：`horizon_bars`、`decision_offset_bars`、`advanced_pair`（進階直改 entry／mode）、`seed`、`neighborhood_bars`、`embargo_bars`。元件以 `data-testid="ic-param-doc-<key>"` render。
- **驗證（可證偽）**：vitest：①六個鍵各自有非空 `what` 與 `effect`；②六個 `ic-param-doc-<key>` 皆出現在 DOM 且文字等於 `EVENT_PARAM_DOCS` 之值（**逐字相等**，不是「包含」）；③`EVENT_PARAM_DOCS` 之鍵集與元件實際 render 的集合**相等**（多一個沒顯示、少一個顯示不出來皆紅）。
- **邊界（≥2）**：①`k` 之控制項在 `/search` 已移除 ⇒ 該頁不得出現 `ic-param-doc-decision_offset_bars`；②文案不得與契約 `doc` 重複——契約已有 `doc` 的欄位（`entry_price_semantic`／`label_return_mode`）**不進**本檔。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不得把契約既有 `doc` 複製一份進本檔（第二份真相源）；不得在本檔寫任何數值門檻（門檻來自後端揭露）。

**Task 1.5 — 白話清單同步**
- 目標：`白話說明/GAP-3驗收清單.md` 之 B21／B22／B23 與本票交付一致。　檔案：該檔。　既有 caller：無。
- 改法：B21 補「當根時 h 掃描也會 disable」；B22 補「主結果＝框裡的 (k,h)、矩陣中會標出是哪一格」與「沒掃的軸用框裡的值」；B23 之三參數說明改指向畫面上的實際文案；新增一項 **B24**：驗 `degraded_full_sample` 的具體原因有顯示。
- **驗證（可證偽）**：`bash scripts/plain_docs_render.sh --check` rc=0；且清單所述之每個 testid 皆存在於元件：
  `grep -c "ic-param-scan-h-inapplicable\|ic-scan-primary-note\|ic-param-doc-" frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx` **≥ 3**；
  清單新增之 B24 段落必須含字串 `oos_guarantees`（否則使用者無從對照畫面）：
  `grep -c "B24" 白話說明/GAP-3驗收清單.md` **== 2**（一處內文、一處簽字表）。
- **邊界（≥2）**：①清單為使用者文件，**不得**出現 `rolling_warmup_insufficient` 這類字面而不附白話解釋；②不得刪除既有已標 OK 之項次。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不得把技術術語直接搬進白話清單。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：`RISK-HIT: b`，**不含 a/d** ⇒ 依範本可於 §N 標 N/A。**但本票不援引該豁免**：Task 1.1／1.2／1.3 各附至少一條 mutation（改壞→紅），理由是這三項的失敗形態都是「畫面看起來正常但資訊是錯的」，與 B-D4／B-D5 兩次幽靈功能同型，靠斷言存在性擋不住。
- 測試層級：前端 vitest（元件 render 與 disabled 狀態）／後端 pytest（metadata 投影）／既有 golden 不受影響（本票不改數值 ⇒ `gap3_label` 46 檔與 `gap3_random_control` 2 檔之值必須逐位元組不變）。
- **防假綠**：既有斷言不得放寬；`icEventBatchDisclosure.test.tsx` 之既有 fixture 若需加欄，以新增欄位為之，不得改動既有期望值。
- **邊界目錄**（本任務適用者）：空DF（未開掃描）／單值軸（只掃一軸）／主結果落在掃描範圍外／`ok_oos`（無降級）／未選報酬量法。

## §R 回退

- 每個 Task 獨立 commit，可單獨 revert。
- Task 1.3 之後端改動為**純新增 metadata 鍵**，revert 不影響任何既有判定。
- 前端三項皆為顯示層，revert 後回到現行行為（功能可用、只是不揭露）。
- golden FAIL ⇒ 不 merge（本票預期 golden 完全不變，一旦變即代表誤觸計算路徑）。

## §N N/A 登記

- **§G Golden / Baseline：N/A** — 本票不改任何數值／特徵計算／ML 路徑（`RISK-HIT: b`，不含 a/d）。既有 golden（`tests/golden/gap3_label/*.json` 46 檔、`tests/golden/gap3_random_control/*.json` 2 檔）之角色改為**回歸護欄**：本票完工時其值必須**逐位元組不變**，一旦變動即代表誤觸計算路徑 ⇒ 不 merge。此條列入 §V 驗證。

### 殘留（本票不做）

- **UAT #6 之「掃描與框裡的值不獨立」是否應改為獨立**
  `為何現在不做: needs-research:` 現行語意（沒掃的軸用框裡的值）是 `_scan_axes` 的既有設計，本票只**揭露**它。要改成「掃描與主結果完全獨立的兩組參數」是 UI 資訊架構問題（會多出一組輸入框），需先有使用者對兩種形態的偏好；在偏好未定之前改動會做出一個更難用的畫面。
- **`min_test_rows=131` 之預設值是否合理**
  `為何現在不做: needs-research:` 該值是 `ic_config_schema.py:420` 之既有預設，**與本票無關**（本票只顯示它）。要調它需先量「多少列的滾動 IC 才穩定」，屬 IC 主線的統計問題，不在事件揭露之範圍。
