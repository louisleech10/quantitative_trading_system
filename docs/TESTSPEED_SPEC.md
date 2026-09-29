# TESTSPEED — 測試加速（全專案通用、零維護）— SPEC

> 來源：`handoffs/reconcile/20260929-testspeed-x-consult-r1/synth.md`（諮詢 r1 已銷帳）、`scripts/fact_keys.json` 之 RM-TESTSPEED　|　日期：2026-09-29　|　對應 TODO：`docs/manifests/TESTSPEED.json`（SPEC 定案後生成）
> 版本：v2（審查 r1 三家皆 blocked、19 條，`handoffs/reconcile/20260929-testspeed-x-review-r1/synth.md`：刪 Phase 3 精簡設定〔規模與執行路徑觸發之程式碼走不到、且漏抓補規則即逐任務維護〕；本票暫停，去留交使用者裁定）
> 版本：v1（主委起草，交三家審查）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大（共用測試框架層、全專案測試皆經此；多 phase）。
- **命中高風險原則**：(b) 跨模組共用路徑——`tests/conftest.py` 與特徵生成入口為全部測試之必經；(c) 多 phase；(d) 測試正確性——快取誤命中或精簡設定鑑別力不足會使驗收假綠。
- RISK-HIT: b,c,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已確認結果**：
  - `2026-09-28 使用者「測試加速那個，你跟委員討論，你們覺得可以加速又不會影響品質，那就可以」`。
  - `2026-09-29 使用者「我要的是真的能加速又維持品質，不要給我看沒用的統計數字」`——驗收以同一套驗收加速前後之實際耗時對比為準，對使用者只報真實縮短時間。
  - `2026-09-29 使用者「做好你要確保會用」`——預設生效、接必經路徑，不得需手動啟用。
  - `2026-09-29 使用者「如果真的無法縮短就不要做下去」`——Task 0.1 實測可省比例未達整批驗收三成即結案；動工後一天內無實際縮短即停手回報。
  - `2026-09-29 使用者「反正你要生成測試加速的就要是通用性的，全專案通用，而且不能每次都要修正，不接受專項專用，如果每次任務都有在針對測試生成什麼檢查還要寫SPEC這種不能接受」`——一切機制於共用層；新任務零維護（不登記、不挑代表、不寫規格）。
  - `2026-09-29 使用者「看起來只能選B」`（審查 r1 三家 blocked 後之三擇一）——只做零風險部分：測試框架內建「上次失敗者先跑」預設生效（`tests/conftest.py::pytest_configure`，cacheprovider 停用時不動）；量測器改完整指紋（K 線檔內容、`momentum/` 產品碼、依賴版本）並標記 mutant 嫌疑（monkeypatch 測試以外之目標、扣除隔離用路徑重導），於 FF-STAT b4 收尾整批驗收時量「非 mutant 之真正重複生成」佔比；≥ 三成才帶數字請使用者裁定是否解決結果共用之安全問題，否則結案。
  - `2026-09-29 使用者否決「重測試限額閘」（「限額管制只是你蓋起來不看但問題還是在」）`——要的是測試本身變快，不是限制跑測試。
- **已驗證事實**（2 項）：
  - FACT-RECEIPT: `grep -n "force_regenerate=True" tests/feature_engineering/ffstat_helpers.py` → 印出 `run_stat`、`dual_start_report` 之生成皆強制重生成（主委 實跑 2026-09-29；codex r1 P1-03 同指）。
  - FACT-RECEIPT: `FFSTAT_GEN_LOG=… pytest tests/feature_engineering/test_ffstat_golden.py::test_dual_start_small_config_passes` → 印出兩列生成紀錄（各含粗指紋與秒數 3.29／2.81）（主委 實跑 2026-09-29）。
- **待使用者確認**：待確認：無

## §C 約束（不重抄，引用 + 只列本任務相關）
- 不得降低任何測試之判定力：不刪斷言、不放寬容差、不跳過測試；mutant 測試（以任何方式改動產品碼、依賴或輸出之測試）絕不取用或寫入共用結果。
- 通用性：全部機制位於 `tests/conftest.py`（或其匯入之共用模組）、特徵生成入口與提交閘；**不得**有逐測試、逐任務、逐 epic 之登記表、代表清單或設定。
- 每次都跑之檢查須秒級（提交閘只比對收據與指紋）；整批驗收不在此限。
- 不寫死加密貨幣、特定週期或特定標的。
- 本任務特別注意：CGSA 生成會落盤數 GB（預設全設定 4h 7,759 列 float32 約 2.7GB）；共用結果之儲存須有容量上限與清除。

## §G Golden / Baseline（高風險(a/d)必填；否則移 §N 標 N/A+理由）
- **reference**：動工前，以現行碼對「FF-STAT 施工清單所列八個測試檔」整批驗收跑一次（量測器開啟），存收據 `handoffs/run_receipts/<date>-testspeed-baseline.json`：每支測試之通過／失敗／略過狀態、耗時、總耗時、每次生成之指紋與耗時。
- **通過條件（可證偽）**：加速後同一套驗收：⓪命中共用結果之生成，其回傳 metadata 與落盤檔案之 sha256 與重生成者逐檔相等（抽樣比對；數值 atol=0、rtol=0）；①每支測試之狀態與 baseline 逐一相同；②全部 mutant 測試仍為預期之紅（以 `pytest.raises` 形式者仍通過）；③總實際耗時（冷啟一次＋改一處後重跑一次，兩情境）較 baseline 縮短 ≥ 30%，否則本票結案不上線。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### Phase 0 — 可行性實測（依賴：無）
**Task 0.1 — 可省比例實測（做／不做門檻）**
- 目標：以量測器收據統計「同一指紋之重複生成」與「精簡設定可替代之完整設定生成」之可省耗時佔整批驗收之比例。　檔案：`tests/feature_engineering/conftest.py::_testspeed_generation_log`（既有）、`handoffs/run_receipts/<date>-testspeed-baseline.json`。　既有 caller：無新增。
- 改法：只讀量測器 jsonl；不改測試。
- **驗證**：收據含 `saving_ratio_upper_bound` 與逐指紋之次數、秒數；`saving_ratio_upper_bound < 0.30` ⇒ 本票結案（派工閘以此收據為 Phase 1 實作許可之前提）。
- **邊界**：①量測器未開啟 ⇒ 收據無生成列 ⇒ 判無效、不得據以結案或開工；②同一指紋之兩次生成耗時差異大（冷／熱快取）⇒ 以較大者計。
- **存活至**：本票完工後仍保留（作為加速前後對比之 baseline）。
- **覆蓋風險**：無。
- 不可做：不得以粗指紋取用快取。

### Phase 1 — 生成結果共用（依賴：Task 0.1 達門檻）
**Task 1.1 — 完整指紋與共用儲存**
- 目標：`tests/conftest.py` autouse（預設生效）包 `FeatureFactory.generate_features`：以完整指紋查共用結果，命中則還原（含輸出目錄之檔案與回傳物件），未命中則生成後存入。　檔案：`tests/_shared/generation_cache.py`（新建）、`tests/conftest.py`。　既有 caller：全部呼叫 `generate_features` 之測試（不改其程式）。
- 改法：指紋＝請求參數正規化＋K 線來源檔內容雜湊＋全部 `FFACT_*` 與影響生成之環境變數＋`momentum/` 全部原始碼與資料檔（含 `warmup_table.yaml`）之內容雜湊＋依賴套件版本（numpy、pandas、TA-Lib、numba、polars、pyarrow）＋Python 版本；回傳物件與落盤檔案一併快取；容量上限（設定值）與 LRU 清除。
- **驗證**：ASSERT pytest 快取命中之測試 WHEN code_changed=false THEN rc=0；指紋任一成分改變（逐一變動之參數化測試）⇒ 必重生成；命中與重生成之輸出逐位元組相同（抽樣比對測試）。
- **邊界**：①輸出含時間戳或隨機性 ⇒ 列入指紋或排除共用（實測判定）；②磁碟不足 ⇒ 不存、照常生成、不失敗。
- **存活至**：本票完工後仍保留。
- **覆蓋風險**：無。
- 不可做：不得逐測試設定是否共用；不得改既有測試之呼叫方式。

**Task 1.2 — mutant 偵測（絕不共用）**
- 目標：測試期間任何「改動產品碼、依賴或其行為」之操作 ⇒ 該測試之生成一律不取、不存共用結果。　檔案：`tests/_shared/generation_cache.py`。
- 改法（交審：r1 兩家指現行 A⑤ 漏報，須選定完整機械法）：候選①包 `MonkeyPatch.setattr`／`unittest.mock.patch` 記錄目標，目標屬測試模組以外者即判 mutant；②生成當下比對 `momentum` 各模組函式物件身分與匯入時快照；③兩者併用。直接屬性賦值（如測試 helper 以 `module.attr = spy`）由②捕捉。
- **驗證**：`tests/test_generation_cache_mutant.py`——以現有全部 mutant 測試（`grep -n "monkeypatch.setattr\|mock.patch" tests/`）逐一執行：皆判 mutant、皆重生成、仍為預期之紅。
- **邊界**：①mutant 僅改環境變數 ⇒ 已在指紋內；②mutant 改輸出檔（生成後竄改）⇒ 快取存於竄改前，竄改不回寫共用。
- **存活至**：本票完工後仍保留。　**覆蓋風險**：無。
- 不可做：不得以白名單列舉 mutant 測試。

### Phase 2 — 只重跑失敗與受影響者（依賴：Phase 1）
**Task 2.1 — 失敗處接續**
- 目標：整批驗收以單一入口執行；重跑時只跑「上次失敗者」與「其所經產品碼指紋已變者」。　檔案：`scripts/run_tests.sh`（新建，全專案通用入口）。
- **驗證**：`tests/test_run_tests_resume.py`——改一處產品碼（`momentum/` 下一個 .py）後以 `scripts/run_tests.sh` 重跑，實際執行之 pytest 節點集合 == 上次失敗者 ∪ 覆蓋紀錄中經過該檔之測試；未受影響者執行數 == 0。
- **邊界**：①覆蓋紀錄缺失 ⇒ 全跑；②測試檔本身改動 ⇒ 該檔全跑。
- **存活至**：本票完工後仍保留。　**覆蓋風險**：無。
- 不可做：不得作為收批之依據（見 Task 2.2）。

**Task 2.2 — 收批完整重跑閘**
- 目標：提交第 N 批（`Ticket-Batch: <epic>/b<N>`）前，必須有「晚於最後改碼、同一產品碼指紋、完整跑完、全綠」之收據，否則拒絕提交（秒級）。　檔案：既有 pre-commit 閘（`scripts/` 內之 commit 閘）。
- **驗證**：ASSERT git commit WHEN receipt=missing THEN rc!=0；ASSERT git commit WHEN receipt=stale THEN rc!=0；ASSERT git commit WHEN receipt=partial THEN rc!=0；ASSERT git commit WHEN receipt=full_green_current THEN rc=0。
- **邊界**：①收據後又改碼 ⇒ stale；②僅部分測試檔 ⇒ partial。
- **存活至**：本票完工後仍保留。　**覆蓋風險**：無。
- 不可做：不得以旗標略過。

### Phase 3 — （v2 刪除：通用精簡設定無法保證不降鑑別力，見審查 r1）

## §V 驗證策略與邊界測試目錄
- mutation：Task 1.2 之驗證本身即 mutation 設計（全部既有 mutant 測試須仍紅）。
- 驗收總則：§G ①②③；對使用者只報 ③ 之實際耗時。
- 邊界目錄：磁碟不足 ✓（1.1）；時間戳／隨機性 ✓（1.1）；並發寫共用儲存 ✓（1.1：寫入原子化）；測試檔改動 ✓（2.1）。

## §R 回退
- 每 Phase 獨立 commit；共用結果機制可由單一設定鍵停用（僅作回退，不作預設）。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- 無。
