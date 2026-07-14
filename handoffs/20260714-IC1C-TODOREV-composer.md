# IC1C-TODOREV — Composer Adversarial Review

> SPEC=`docs/IC1C_NETIC_SPEC.md` v1.0 Frozen(2026-07-14) | TODO=`docs/IC1C_NETIC_TODO.md` DRAFT | 範本=V13 | reviewer=composer | 2026-07-14

## Verdict：需修補後派工

TODO 在 Task 命名、§0 規則、M1–M10 測試清單與 §U profile 常數上大致對齊凍結 SPEC，但 **§C consumer-map 未完整落地**、**§B/Phase Gate 與 M 矩陣自相矛盾**、**G-NEW2 無可執行定義**、**mutation 驗收命令不可跑**。冷啟動 agent 會在 B1 誤標 PASS 或漏改 `ic_reporter` 導致 `net_ic` 殘留。修 4 項 BLOCKING 後可重審。

---

## Findings

### §0 挑戰前提（未驗證假設當事實）

**ADV-COMPOSER-0a** [MAJOR] 信心度:High  
證據:TODO L121「覆蓋追溯…7/7 Task; M1–M10 10/10; G-OLD/NEW/NEW2 3/3」；對照 SPEC §C L46–62 consumer manifest 16 項。  
RECHECK:`grep -n ic_reporter docs/IC1C_NETIC_TODO.md` → 0；`grep -n export_formats docs/IC1C_NETIC_TODO.md` → 0。  
會怎麼失敗:宣稱 100% 覆蓋，執行端略過 §C #4 `ic_reporter.py`、#16 `export_formats` 改寫，B3 全量 pytest 或 CSV 匯出仍帶 `net_ic`。  
修法:覆蓋表改為「SPEC Task 7/7；consumer 16 項中 TODO 明列 N/16」；補 Task（建議併 B1 或 B2）改 `ic_reporter`+`test_export_formats`。

**ADV-COMPOSER-0b** [MAJOR] 信心度:High  
證據:SPEC §V L139「phase26 factories/integration **預期綠**(模組名不變)」；TODO 無 phase26 驗收步驟。  
RECHECK:`grep net_ic tests/phase26/` → 僅模組名對照，無 schema 斷言（目前可能綠）。  
會怎麼失敗:把「模組名不變」當「輸出契約不變」；若日後 phase26 加 schema 斷言會事後爆炸。  
修法:TODO §B B3 Gate 明列 `pytest tests/phase26/ -q` 或註記「僅 smoke、不含 schema oracle」並降 SPEC 聲稱。

---

### §1 必查（10 類）

**1. 矛盾/互斥**

**ADV-COMPOSER-1** [BLOCKING] 信心度:High  
證據:§B L27「B1→B2 憑…M1–M3/**M5/M6/M8–M10**(Python 側)」；Phase 1 Gate L80 僅 `pytest tests/momentum/Analysis/test_net_ic_analyzer.py tests/momentum/test_turnover_analyzer.py`；SPEC §V M10 三層=T1+**T2 API**+**T5 config**。  
RECHECK:對照 SPEC §V L130 M10 列與 TODO Phase 1 Gate L80。  
會怎麼失敗:B1 宣稱 M10 閉合，但 Phase 1 不跑 T2/T5；或 agent 在 B1 強跑 API 測試（Task 2.1 尚未做 typed request）→ 假紅/假 BLOCKED。  
修法:§B 拆 M10-B1=僅 T1 層；M10 全三層移 B2 Gate；或 Phase 1 即建 T5 並寫入 Gate 命令。

**ADV-COMPOSER-2** [BLOCKING] 信心度:High  
證據:§B L27、Phase 1 Gate L80「`bash scripts/mutation_probe_check.sh` PASS」；`scripts/mutation_probe_check.sh` L20 `[ $# -ge 1 ]`。  
RECHECK:`bash scripts/mutation_probe_check.sh` → `用法: mutation_probe_check.sh <test_path>...` exit 1（已實跑 2026-07-14）。  
會怎麼失敗:Gate 字面不可執行；agent 跳過或空參失敗，無法證明 M1–M9 probe 有牙齒。  
修法:改為 `bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_net_ic_analyzer.py tests/momentum/test_turnover_analyzer.py`（B1）；B2 再加 T2/T5/T4 路徑。

**ADV-COMPOSER-3** [MAJOR] 信心度:High  
證據:Task 1.2 L64 驗證「T2 `test_net_ic_e2e_unavailable`」；Phase 1 Gate L80 不含 `tests/api/`；Task 2.1 才建 typed `NetICAnalysisRequest`。  
RECHECK:SPEC Task 1.2 L94 同引用 API 測試——TODO 沿襲但未解依賴。  
會怎麼失敗:Task 1.2 完成準則與 B1 Gate 脫鉤；agent 在 B1 不寫 T2 或寫了卻無 API 契約可測。  
修法:Task 1.2 驗證改 momentum 層 orchestrator 單測（直接 `_run_net_ic`）；T2 e2e 明確歸 Task 2.1/B2。

**2. 漏項/端到端**

**ADV-COMPOSER-4** [BLOCKING] 信心度:High  
證據:SPEC §C L50 `ic_reporter.py:150/:209/:631-634` 列 `net_ic` CSV 欄；現碼 `momentum/Analysis/ic_reporter.py:150,631-634` 仍 `"net_ic"`；TODO 全檔無 `ic_reporter`。  
RECHECK:`grep -rn net_ic momentum/Analysis/ic_reporter.py`；`grep ic_reporter docs/IC1C_NETIC_TODO.md`。  
會怎麼失敗:M1「全樹無 net_ic 鍵」在 analyzer 通過，CSV/AI JSON 仍輸出 `net_ic` 欄——使用者可見舊語意殘留。  
修法:新增子任務（B1 或 B2）改 `deep_columns`→`cost_drag_return`、`_build_deep_summary_columns` 改 §U union、alias `net_ic`→移除；附 red-on-break 測試。

**ADV-COMPOSER-5** [BLOCKING] 信心度:High  
證據:§B L27 B2→B3「G-NEW2」；Phase 2 Gate L104、Task 3.1 L116 僅「G-NEW2 重跑 byte 等值」；無腳本旗標/比對檔/命令。G-NEW 有 `scripts/ic1c_freeze_baseline.py --new`(L79) 但 Task 0.1(L35) 未定義 `--new`。  
RECHECK:`glob scripts/ic1c_freeze_baseline.py` → 不存在；TODO 無 G-NEW2 輸出路徑。  
會怎麼失敗:B2/B3 Gate 要求 G-NEW2 但無 oracle；agent 用口頭「byte 等值」假綠。  
修法:Task 0.1 或 1.1 定義 freeze 腳本 `--baseline old|new|new2`；G-NEW2=同 fixture 經 API `cost_bps=7` vs config 直開 7 的 feature dict sha256 等值；寫入 `handoffs/ic1c_baseline/g_new2.*`+Gate 命令。

**ADV-COMPOSER-6** [MAJOR] 信心度:High  
證據:SPEC §V L139「export_formats fixture(舊 schema)」；`tests/momentum/test_export_formats.py:73-74` 仍 `"net_ic": 0.04`；TODO 無改寫任務。  
RECHECK:讀上列 fixture。  
會怎麼失敗:B3 `pytest tests/momentum/` 可能仍綠（測試不斷言鍵集合），但 fixture 固化錯 schema，後續加嚴即假綠回歸。  
修法:併 Task 1.1 或獨立子任務改 fixture 為 §U profile+斷言 CSV 無 `net_ic` 欄。

**ADV-COMPOSER-7** [MAJOR] 信心度:Medium  
證據:SPEC §C L55 `ic_analysis_service.py:1198-1213` NaN→null；TODO Task 2.1 未列 serialization 對 discriminated union 的處理。  
RECHECK:讀 `api/services/ic_analysis_service.py::_to_json_compatible`。  
會怎麼失敗:analyzer 輸出正確物件，API 層仍可能把 nested float 變裸 null 破壞 §U 形狀。  
修法:Task 2.1 增「`_serialize_deep_report` 保留 conditional metric 三鍵；禁扁平化」+T2 斷言。

**3. 不可測驗收**

**ADV-COMPOSER-8** [MAJOR] 信心度:High  
證據:Phase 1 G-NEW L79「canonical numpy 重算全量 atol=1e-12」；SPEC §G L71 要求「**獨立實作**」；TODO 未禁止與 `NetICAnalyzer.compute_cost_drag` 同源。  
RECHECK:對照 SPEC §G.2 vs TODO L79。  
會怎麼失敗:freeze 腳本 import analyzer 重算→自指 oracle，公式錯仍綠（FF C1-2 類假綠）。  
修法:腳本內嵌 3 行獨立 numpy 重算；禁止 `from momentum.Analysis.net_ic_analyzer import`。

**ADV-COMPOSER-9** [MAJOR] 信心度:High  
證據:Task 0.1 L35「人工構造 turnover 缺與 gross_ic NaN 各 ≥1」；無 fixture 欄位/腳本步驟/預期 feature 名。  
RECHECK:讀 Task 0.1 實作要點。  
會怎麼失敗:冷啟動 agent 不知如何在真-kline 路徑注入 NaN gross_ic；G-OLD skipped 路徑缺失→G-NEW 不比對。  
修法:列具名步驟（如 post-process summary dict 注入 `feature_nan`/`feature_no_turnover`）+baseline JSON 片段範例。

**ADV-COMPOSER-10** [MINOR] 信心度:High  
證據:SPEC §G L73「必變欄 diff 表:全部列出」；TODO 無產出/維護 `handoffs/ic1c_baseline/diff_manifest.json` 或等價。  
RECHECK:grep `diff` `must_change` TODO → 無。  
修法:Task 1.1 或 G-NEW 步驟要求產出機器可讀 diff 表並納入 Gate。

**4. 可疑 quant 假設** — 無（B-strict 裁決已在 SPEC/TODO §0 對齊；1c-FR 拆票明確）。

**5. 過度工程** — 無。

**6. OOM/並行** — 無（邊界目錄 SPEC §V L141 已勾選不測並發/OOM，TODO 未擴張）。

**7. Cache 正確性** — 無（1c 不動 cache key）。

**8. API/型別/相容**

**ADV-COMPOSER-11** [MAJOR] 信心度:High  
證據:Task 1.1 L49 對 `capacity` 加 `"calibration":"uncalibrated"`；SPEC §U L37–38 僅列 `capacity` 鍵、未定子 schema。  
RECHECK:對照 §U SCHEMA_GROSS_ONLY 與 Task 1.1 L49。  
會怎麼失敗:profile equality 只驗頂層鍵，capacity 子欄漂移無 oracle；與「capacity 維持現狀」訪談裁決邊界模糊。  
修法:SPEC §U 或 TODO 明列 `capacity` 允許子鍵集合；G-NEW 對 capacity 做結構斷言或聲明 out-of-scope。

**ADV-COMPOSER-12** [MAJOR] 信心度:Medium  
證據:Phase 2 Gate L104「離線可 collect,fixture 層隔離 Binance ping」；`tests/api/test_ic_deep_analysis.py:13` `from api.main import app`；SPEC §V L140 提及 collection error。  
RECHECK:未實跑 collect（HANDOFF 稱套件既有紅）；TODO 無具體 mock/fixture 名。  
會怎麼失敗:CI/沙箱 collect 失敗→B2 假 BLOCKED 或 agent 弱化 import。  
修法:列具體 pytest plugin/fixture（如既有 `ic_persist_redirect`）+驗收 `pytest tests/api/test_ic_deep_analysis.py --collect-only`。

**9. 測試品質**

**ADV-COMPOSER-13** [MAJOR] 信心度:High  
證據:SPEC §U L39 `test_net_ic_schema_profiles.py::SCHEMA_*`；TODO L77 `test_schema_profiles` 在 `test_net_ic_analyzer.py`。  
RECHECK:對照兩檔路徑。  
會怎麼失敗:雙方 agent 各建一檔或漏常數。  
修法:統一 canonical 路徑（建議獨立 `test_net_ic_schema_profiles.py` 如 SPEC）。

**ADV-COMPOSER-14** [MINOR] 信心度:High  
證據:Task 1.1 L77「合併刪除 `tests/phase25/test_net_ic_analyzer.py`」；Task 1.1 修改檔案列表(L50)未列刪除。  
RECHECK:讀 Task 1.1「修改檔案」節。  
修法:修改檔案增「刪除 phase25 重複檔」+Gate grep 確認無殘留 import。

**10. Agent 可執行性**

**ADV-COMPOSER-15** [MINOR] 信心度:Medium  
證據:Task 3.1 L111「docs/(API_SPECIFICATION **或** ic 相關頁)」；SPEC §C 要求文件同步。  
RECHECK:讀 Task 3.1。  
修法:列唯一檔案路徑（如 `docs/API_SPECIFICATION.md` §Net IC 小節）。

---

### §2 範本錨點 + 獵空殼

**ADV-COMPOSER-16** [MAJOR] 信心度:High — §2 TODO §0  
證據:TODO §0 L6–16 含 B-strict/§U/§T/fail-closed/解耦/防假綠/真-kline——**完整**。  
獵空殼:Task 2.2 L102 `grep -n "useState(5)\|0.1"` 可執行；Task 0.1 skipped 路徑(L35)內容空殼（見 ADV-COMPOSER-9）。

**ADV-COMPOSER-17** [MAJOR] 信心度:High — RISK-HIT↔§G  
證據:SPEC RISK-HIT a,b,d + §G 有 G-OLD/NEW/NEW2；TODO Phase 1 有 G-NEW 要點但 G-NEW2 空殼（ADV-COMPOSER-5）。

---

### §3 不可違反原則

無直接矛盾（TODO 禁 fake/禁弱化 gate/禁 net_ic 鍵）。風險在**未覆蓋 consumer 導致實作漏改**（ADV-COMPOSER-4），非 TODO 明文違反。

---

## 覆蓋追溯審計（獨立重算）

| 錨點 | SPEC | TODO | 判定 |
|------|------|------|------|
| Task 0.1–3.1 | 7 | 7 同名 | PASS |
| M1–M10 | 10 | 10 具名於 Phase1/2 測試節 | **PARTIAL**（Gate 與 M10 分層矛盾，見 ADV-COMPOSER-1） |
| G-OLD/NEW/NEW2 | 3 | 3 提及 | **PARTIAL**（G-NEW2 不可執行，見 ADV-COMPOSER-5） |
| §U 三 profile | §U | §0 + test_schema_profiles | PASS（路徑漂移見 ADV-COMPOSER-13） |
| §C consumer 16 項 | 16 | **≤12 明確**（缺 ic_reporter、export_formats、ic_analysis NaN 路、部分 tests） | **FAIL** |
| 1c-FR 拆票 | §P | §0 + Task 1.2 不可做 | PASS |

---

## 被當成事實的未驗證假設（§0）

| 假設 | fact/assumption | 驗證狀態 |
|------|-----------------|----------|
| §A 混減 bug 四條 FACT-RECEIPT | fact | VERIFY:`sed -n '34p' momentum/Analysis/net_ic_analyzer.py` 仍為 `gross_ic - ... * 2.0` |
| `mutation_probe_check.sh` 可無參 PASS | **assumption** | **推翻**:無參 exit 1（ADV-COMPOSER-2） |
| 覆蓋追溯 100% consumer | **assumption** | **推翻**:ic_reporter 漏（ADV-COMPOSER-4） |
| phase26「預期綠」= schema 安全 | assumption | 僅模組名 smoke，未驗輸出契約（ADV-COMPOSER-0b） |
| G-NEW2「byte 等值」可口頭驗收 | assumption | 無腳本/檔案（ADV-COMPOSER-5） |

---

## Suggestions（非 Blocking）

- B1 標「大」含 1.1+1.2+1.3，建議派工 prompt 再拆子 commit 順序（analyzer→orchestrator→proxy）降低單批 diff 面。
- Task 1.1 `max(0.0,turnover)` 與 SPEC §T 原文未寫 clamp；若保留，§T 補一句與 turnover_analyzer 非負假設對齊。

---

ASSUMPTIONS_VERIFIED: net_ic 混減現碼仍在; mutation_probe_check 無參 exit 1; ic_reporter 仍輸出 net_ic; export_formats fixture 仍 net_ic; scripts/ic1c_freeze_baseline.py 尚不存在  
TESTS_RUN: `bash scripts/mutation_probe_check.sh`→exit 1; `grep ic_reporter docs/IC1C_NETIC_TODO.md`→0  
FAILURES_SEEN: none（審查任務）  
SCOPE_CHANGES: none（唯讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none  

STATUS: DONE

TODO-REVIEW: REJECT(4 BLOCKING)
