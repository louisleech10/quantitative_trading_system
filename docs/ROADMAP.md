# ROADMAP — 量化交易系統戰術路線圖
> 單一現役戰術 roadmap。**即時任務狀態**看 `HANDOFF.md`；**決策理由**看 memory；本檔=中長期 epic 排序與範圍。
> 維護:完成項移到「已完成」、新需求加到對應優先級、範圍/決策變更標日期。**每次 commit 一併更新本檔**(2026-06-26 使用者定)。最後更新 2026-07-02。

當前階段:**V1.0 工具階段** — crypto 單市場研究管線(探索 → 發現 Pattern → ML 優化 → 回測)。願景 V1→V2→V3 見 `PRODUCT_VISION.md`。

---

## 🔥 進行中 / 下一步（優先序）

### P0 — 制度層總審查 epic（憲法＋流程＋任務分類三層合審；2026-07-05 立案，**使用者定 P0：完成後才回其他任務**）
- **緣起**：TGF epic 證實「prose 規則靠記性必再犯、閘門規則違反不了」（驗證保真度鐵律在 context 內仍三防全破 vs 機檢上線後連編排者派工都被連擋）。使用者 2026-07-05 明示：鐵律非其偏好、是 agent 重複犯錯逼出的補丁，他無法判斷增刪——**裁決權交委員會證據裁決**（見 memory feedback-rules-are-scar-tissue）。
- **範圍三層**：①憲法內容/架構/儲存（CLAUDE.md 每 session 全載=最大固定 token 支出；四源重疊已實證分叉一次；copilot-instructions 739 行停在 2026-04-26；ARCHITECTURE/DEV_GUIDE 疑似漂移）②派工流程管線（本次實測摩擦：戳記輪×4、claim-check 擋 commit×5、provenance 流程中途才學會、同檔並發只能序列化）③小中大分類規則（多層補丁散在 CLAUDE.md＋記憶兩處）。
- **方法**：每條規則四選一證據裁決——機械化（再犯且可寫成 gate/hook/checker）／留核心原則／合併去重／淘汰（已被機檢取代）；判準=出生事故＋violation 紀錄（audit.log/handoffs/git），不靠感覺。委員會三方裁決＋白話簡述給使用者否決權；「不可砍清單」先行＋雙家族 adversarial 防瘦身誤傷。
- **時機（2026-07-05 使用者定案）**：P0 立即執行、完成後才回 IC 等其他任務；建議新 session 起跑（本立案 session context 已滿載 TGF 歷史）。流程=委員會 read-only 審查輪（三層各出 findings＋violation 證據考掘）→ 白話決策簡述給使用者否決 → 依裁決走完整管線實作。
- **裁決（2026-07-05 使用者）**：D-1/2/3/5/6 同意預設；**D-4 否決固定制**→執行端選層動態、以使用者當下指示為準（usage 切換、未來或加 Grok），文件只留單一可變「現行分工」行。附帶：否決點以後須彈窗（AskUserQuestion）+推播；總審查頻率=事件觸發+每季保底。→ **下一步=依裁決走完整管線實作（Phase A 憲法重構起）**。
- **狀態（2026-07-05）＝Phase A（憲法重構＋合約補齊）✅ 完成待 commit**：走完整大任務管線——SPEC/TODO（`docs/INSTREV_PHASEA_{SPEC,TODO}.md`，三道機檢過）→ 雙家族 adversarial（Codex 3+Composer 12 findings，含 2 BLOCKING）→ reconcile R2 雙戳記 APPROVED（sha256:6a14a0f6…）→ Composer 2.5 實作 → Codex code review 抓 2 BLOCKING（ORCH §6/§7 殘留 Codex 主力、三方鐵律過度壓縮掉義務）→ Composer 修 → Codex 閉合重驗雙 CLOSED。**成果**：copilot 739→8 行 pointer；CLAUDE.md 216→128 行（敘事移新檔 `docs/SCAR_LEDGER.md`，規則零刪減 grep 驗）；任務分派決策表單一化；執行端選層 ORCH §1 單一「現行分工行」（動態，現行=Composer 實作+Codex review）；合約補齊 5 項制度（兩輪斷路器/register-output/VERIFY claim/STAMP-BLOCKED/產物非指令）；輪詢統一 10 分鐘、debug 統一 2 輪（含 BOOTSTRAP 第 5 分叉源）；ARCH/DEV banner。**待辦**：無（Phase C 之 U-13 已完成；U-20/21 裁決本身=先別做，屬長期觀察項）。read-only 審查輪 reconcile=`handoffs/20260705-INSTREV-RECONCILE.md`（sha256:ee8c9fab…，含 U-3 errata）。
- **狀態（2026-07-06）＝Phase C（U-13 批次戳記慣例）✅ 完成**：批次戳記（一次派工審多檔逐檔 append）+同檔並發序列化+不可自我認證原則不動，寫進 `docs/MULTI_AGENT_ORCHESTRATION.md` §戳記後（第二階段「包單一命令」暫緩）。**U-20**（共用路徑 hook 警示）/**U-21**（Codex vs Composer 長期主力）裁決＝先別做、累積證據 → 長期觀察項。**∴ 制度層 epic 可實作項全完成（A 憲法＋B 腳本＋U-13）；實質下一站＝IC Analysis（P0，FF 測試資料已就緒，見下）。**
- **狀態（2026-07-06）＝Phase B（治理腳本補強 U-9/12/14/15）✅ 完成待 commit**：走完整中任務管線——SPEC/TODO（`docs/INSTREV_PHASEB_{SPEC,TODO}.md`，template_check PASS）→ Codex adversarial（8 findings，2 BLOCKING，REJECT）→ 全數 ACCEPTED+修訂 → Codex 閉合重驗 8 全 CLOSED → reconcile 雙戳記（sha256:1e919edd）→ Composer 實作 → Codex code review（3 findings）→ Composer 修 → 閉合重驗全 CLOSED。**成果**：U-9 sync 兩層 token（CONTRACT_REQUIRED/PLANNER_REQUIRED）+選層單一來源反向檢查+A-12 新 token；U-12 gate DENY（no_fresh_token/token_expired）落 audit.log；U-14 pre-commit index-only 尾空白 auto-fix（binary-safe，排除 fenced/hard-break/表格）+checker 缺 backing 提示；U-15 gate.sh 用法模板+新 `scripts/dispatch.sh`（碰撞 fail-closed+透傳）。governance 140 passed/9 pre-existing（非本批，舊 spec/fixture 不符演進規則，技術債另記）。

### P0 — 驗收防偽閘 verify-gate（2026-07-01 FF 驗收捏造事故後立,擋「宣稱已驗≠真驗」）
- **範圍**:`docs/VERIFY_GATE_SPEC.md` v2.1(P0-FF-3「align mutation真紅」不實事故 → run receipt + claim checker + enforcement 三層)。
- **狀態(2026-07-02)= epic B1-B5 全落地**:B1 receipt(`d3870c4`)、B2 claim checker(`a1d3638`,V7誤報=0)、B4+B5 provenance/RESULT硬欄位(`6c0a6b0`,Codex 6 BLOCKING 閉合)、B3 enforcement 三層+health(本次 commit;Codex 4 BLOCKING 閉合檔載「FINAL VERDICT: APPROVED」;governance 75 tests VERIFY:20260701T235954Z-governance-b3-final)。PreToolUse hook 已生效;git hooks 用 `bash scripts/install_verify_hooks.sh` 安裝。殘餘=誠實邊界(careless-proof+tamper-evident,非防惡意)。
- **全系統紅隊 ✅(本次 commit)**:三方(Claude+Codex+Composer)紅隊抓 7 洞(env-prefix繞閘/docs走私/模糊洗白/假歸屬自我認證/路徑正規化/無逃生程序/provenance未接線),全修+Codex閉合R1-R7 CLOSED;淨判斷「仍有洞需緊>過嚴」。88 governance tests。
- **接續**:FF P0-FF-3 收尾完成(mutation 全探針輪 receipt log 檔載「5 passed」,出處:handoffs/run_receipts/20260702T125150Z-mutation-test_ff_multitf_truncation_mr.log;⚠️舊 receipt 020806Z 那輪的 align 為假綠 shape 已作廢;B2 回歸出處:20260702T042627Z-ff-b2-regression.log;Codex final review 檔載「APPROVED」出處:20260702-FF-P0FF3-FINAL-REVIEW-CODEX.md)。**P1-FF-5/7 ✅ 完成(2026-07-03,本次 commit)**:跨 symbol 值隔離+wrapper 路徑正確性兩測試檔落地(Codex 實作+Composer adversarial 7 BLOCKING→4 輪修復閉合→CLOSURE/INCREMENTAL 皆檔載「APPROVED」,出處:20260702-FF-P1-57-REVIEW-composer.md);slow 全鏈實跑 receipt 檔載「1 passed in 992.47s」(出處:run_receipts/20260702T203429Z-p1ff57-slow-fullchain-v3.log)。殘餘待辦:B-5 兩污染面 defer(batch checkpoint/RunLease、L7 path-map deep)。**GOV-O3EXT-R7 ✅ 完成(2026-07-03)**:R7-emitter 全 task-id 留痕+register-output+委員會過程檔 sha256 綁定豁免(Composer adversarial F1-F7 全 CLOSED+code review 檔載「FINAL VERDICT: APPROVED」出處:20260703-GOV-O3EXT-R7-REVIEW-composer.md;11 份委員會過程檔已註冊過 checker 補 commit);跟進=review B1-B5 NON-BLOCKING。**次站=fracdiff max_lag 大 epic(P1-FF-6 併入,見下方 P1 節;新 session 起手)**。

### P0 — IC Gatekeeper 開發 + 真實端到端測試
- **為何**:FF 已收尾,pipeline 下一站。現況 79 IC 單元測試**全合成資料**,從未真實 kline 端到端驗證。
- **範圍**:限 crypto(三方 2026-06-17 定,見 [[project-datasource-ff-ic-assessment]]);真實 kline 跑 IC Gatekeeper(12+10 模組) 端到端 + 驗證。
- **★施工藍圖(2026-06-24 四家委員會地圖)**:`handoffs/20260624-ic-map-WHOLEMAP.md`(5 階段 28 種分析全棧盤點 + 系統性發現 A-H)。盤出主流程**幾乎無防偽護網**:
  - **🎯 絕對優先(正確性紅線/生死)**:事件 case-control 套件(主戰場全缺)、train/test 切分(主路徑無)、FDR 接線(幽靈,43萬≈21,500假陽性)、Net IC 量綱錯誤、factor_attribution NaN 繞過。
  - **🚨 P0 止血**:grouped/decay 崩潰、幽靈開關群(feature_filter/turnover/slippage)、靜默空圖、大尺度 cap。
  - **大尺度(430K)架構**:見 `handoffs/20260624-ic-optimization-CONVERGED.md`(串流分塊不物化全矩陣)。每優先項走完整 SPEC 管線。
- **分階段執行計畫(四家收斂)**:`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md`(七 Phase,contract-first+雙軌)。
- **決策**:walk-forward/CPCV **复用 ML 孤島**非重寫;contract-first 不硬接舊全 DataFrame 路徑。
- **狀態(2026-06-26)**:
  - **Phase 0 止血+正確性硬閘 ✅ 完成**(commit `11507f5`):CRASH/TIMEAXIS/BYVOL/FEATURE-GUARD/DECAY-LOG/UX-ERR 六 epic + 實機 45k smoke。
  - **Phase 1 正確性 kernel + contract 🔵 進行中**:
    - **1-contract ✅ 完成**(commit `e857834`):契約 DTO + 洩漏紅線(三方簽核,8 LEAK 全閉)+ Parquet artifact + API 版本化。
    - **1a 第一刀(單幣縱向接線)✅ 完成**:契約紅線接進 IC 主流程 `analyze()`——holdout 切分 + train-only fit(winsor/std/coverage/constant)+ OOS 報告 + purge≥horizon 防前瞻 + allowed_symbols/expected_freq 落實。**兩輪雙家族 adversarial(9 BLOCKING)+ 三方數據簽核 PASS(R1 抓 2 LEAK→修→R2)+ G-NEW 真實全 run 抓 2 整合 bug→修。default ON,OOS 不可行時分因回退(資料不足→full-sample 標記;時間軸壞→fail-closed)**。docs/IC_PHASE1_1a_CUT1_{SPEC,TODO}。
    - **下一段 = 1a 第二刀(cross_sectional `analyze_cross_sectional` 防洩漏)**;續 1-align/1b FDR/1c Net IC/1d attribution/1e HAC/1f 空圖。
    - **⚠️ 恢復 IC 前第一子步驟＝IC SPEC conformance pass**：實測 4 份 `IC_*_SPEC`（PHASE0/1a_CUT1/CONTRACT/RUN_SELECTOR）過不了現行 `template_check`（缺 `RISK-HIT:` 宣告行；PHASE0/CONTRACT 另缺 §A FACT-RECEIPT）；TODO 全過。非 A/B/C 造成（template gate 早於 INSTREV 演進），但不補則 `gate.sh dispatch --spec` fail-closed 擋派工。修＝結構補錨點（RISK-HIT 反映 IC 真實風險 (a)+(d)；FACT-RECEIPT 附真跑 receipt，禁塞假），**不改設計/數值**，逐檔帶 context 做。FF 測試資料已就緒（3 sym×1h+12h 對齊、max_lag 後、`data_cache/features/`）。
  - Phase 2A(事件 case-control 主戰場)/Phase 3(430K 串流)/2B/4/5 未啟動。詳 phasing-CONVERGED 七 Phase。

### P0.5 — IC 效能 + grouped_ic 崩潰止血(已盤點,可立即動)
- **為何**:使用者實測選 run 跑 analyze 卡死+崩潰;三方 reconcile 完成。
- **Epic**:`handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md`(IC-CRASH/IC-FEATURE-GUARD/IC-UX-ERR=P0;IC-PERF=P1)。**狀態**:reconcile 完成,實作未啟動。

### P2 — FF preset 移除盤點（2026-07-03 使用者排入,IC 正確性紅線之後做）
- **為何**:使用者從未用過/測過 professional_full 等 preset（2026-06-29 明示想移除）;現行測試/生成一律 base/full 全特徵不綁 preset,preset 定義成死碼+誤用風險。
- **範圍**:盤點所有 preset 定義與引用點（config/前端/文件）→ 確認零真實使用者 → 移除或明確 deprecate;涉 config schema 下游,走「中」型管線。
- **狀態**:已排程未啟動;不擋 IC。

### P2 — IC 輸出 Agent-readable + 顧問層(V2 願景地基)
- **為何**:使用者要 AI Agent 直接讀 IC 輸出、像委員會討論、回饋「哪些特徵/參數真的較好」+ 點破盲點。**前提=先修上面正確性**(否則 Agent 讀到污染數字會自信推薦過擬合假因子)。
- **範圍**:① IC 輸出結構化可機讀(穩定 schema);② 輸出含 FDR/OOS/DSR 嚴謹度指標(讓 Agent 分辨真好 vs 過擬合);③ Agent 解讀/委員會式討論層。**依賴**:P0 正確性紅線。**狀態**:概念,未規劃。

### P1 — fracdiff max_lag 截斷不變修復（2026-07-02 三方委員會立案,使用者定序）
- **根因**:`max_lag = min(max(2, len(df)//10), 252)` 以整段長度推導,把總長度洩進 d* 計算(600→60,590→59)→ 截斷不變性破壞。**非 look-ahead**(d* 校準只吃 first-500 prefix),量化因果安全,但屬真實作缺陷。三腿檔 `handoffs/20260702-FF-DSTAR-GATE-{CLAUDE,CODEX,COMPOSER}.md`;B2 回歸 receipt 20260702T042627Z(8 passed/2 fracdiff failed 揭露)。
- **順序(使用者 2026-07-02 定)**:FF 深稽全完成(護網完工)→ 本 epic 修 max_lag(改由 calibration/固定推導;**會改全部 fracdiff 特徵值**,命中 (a)(d) 走完整管線+三方值守恆)→ 修完 2 個 strict-xfail 截斷測試應轉綠 → **重新生成 FF 定版給 IC**。併 P1-FF-6(d*/fracdiff probe)避免重工。
- **現況（2026-07-03 epic 主體完成,詳見 handoffs/20260703-FRACDIFF-MAXLAG-*）**:
  ①max_lag 缺陷已修（`_resolve_fracdiff_max_lag` calibration-derived=50+config 顯式欄位）並經 golden 等價鏈證明（receipt 085226Z:修後 auto ≡ 修前 pin50 全欄 digest 0 差異、非 fracdiff 欄 0 差異、G2' config 路徑 ≡ R）;
  ②附帶修復:fracdiff FFT 卷積尾擾捨入洩前綴（`_hurst_prior._convolve_1d`+孿生 `_frac_diff_convolve` 改 direct）;發現並修復 pydantic 靜默丟棄 config max_lag（逃生口本是幽靈）;
  ③**兩 MR 維持誠實 xfail（reason 已換）**:卡在 pre-existing storage codec bug（見下一節）,轉綠時點=storage epic 完成後;max_lag 面護網=d\* gate+3 mutation 探針+full_fit/calibration(單邊重設計)控制;
  ④P1-FF-6 cache key mutation 探針落地（7 mutant 對準 v3 guard）。

### P1 — FF storage codec 截斷變異（2026-07-03 R3 委員會確認根因立案）
- **根因（已確認,非假說）**:L7 raw per-column parquet codec（float16/32）依**全窗值域**選型（feature_storage.py:2554-2588）→ 窗長/尾值變化使同欄跨 run 選型翻面 → 儲存精度不可比。症狀:①近零分母大值 float16 溢出→inf→sanitize NaN（截斷 MR idx508 artifact）;②ULP 級 2^-7 值差（尾擾 MR dtype dump）。證據鏈:`handoffs/20260703-FRACDIFF-MAXLAG-{MRFAIL,R3}-*.md`+receipts 054245Z/094044Z 差分。
- **修向**:codec 選型決定論化（不依全窗 stats,如固定 dtype 或依 calibration 段選型）;修完兩 fracdiff MR xfail 應轉綠。命中 (a)(b),走完整管線。

### P1 — Productionization Epic（全棧參數持久化）★上線前置
- **為何**:任一特徵/模型要上線推論前必做,否則 train/serve 分布偏移、模型靜默失效。三方三輪盤點 CONVERGED。
- **權威範圍清單**:`docs/FEATURE_STATEFUL_PARAM_AUDIT_FINAL.md`(全棧三層)。
- **子項(優先序)**:
  1. **fracdiff d\* 持久化 / 固定參考**(最高;同時解 cross-window 可重現 + train/serve;見 [[project-dstar-first500-optiona]])。大任務,命中 (d),走完整管線。
  2. A-schema:訓練特徵清單 pin(上線同欄位)。
  3. A4 safe_denominator 改 causal;A5 labels winsor 改 train-split 或棄用。
  4. B 累積(OBV/AD/ADOSC/SAR)一致 reset + state;C L5 reference 可得性。
  5. IC/ML 層:模型權重 + scaler 統計 + 選中特徵集 + 校準映射 隨模型留存。
  6. Optimization 層:Optuna best params 隨部署留存。
- **狀態**:盤點完成(inventory),修法未啟動。V1 未上線故非急,**上線觸發即啟動**。守則已加 serving-parity 判斷樹(`FEATURE_DEVELOPER_CHECKLIST.md`)防新組件再引入未留存參數。

---

## 🅿️ 已決定擱置（非急,有觸發再啟）
- **B7 L6.5 並行**(P2):MTF 細→粗罕見,ThreadPool 需 nogil 才 4.3x。見 [[project-mtf-direction-b7-parked]]。
- **T-A per-layer 串流釋放**(P1,磁碟):scaffold 已存,砍 RSS 峰值根本解。磁碟再緊則啟。
- **T-B float16 暫存 / T-D 28GB 取證 / gstack 清理**:低優先。
- 既有壞測試:`frontend/src/__tests__/strategy-components.test.tsx` 缺 SignalTooltip(可另開小修)。

---

## 🔭 未來 Epic（更遠,待 V1 穩固）
- **FF preset 盤點/移除**（2026-06-29 使用者提,B2 後啟）：未用/未測 preset(professional_full / ml_optimized / trend_focused / intermediate_research / fibonacci_full / basic_essential…)= 死碼/可能 config bug 的未測路徑。使用者從沒用過 professional_full、想移除但未討論。**範圍**:盤點每 preset 有無真 caller、前端真送哪些、哪些從沒被測 → 給清單再決定移除。命中跨模組共用路徑(config_manager/前端 toggle)→ 走完整管線。B2 因果測試已改 base/full 全特徵(不綁 preset)。
- **多資產擴充**:台指期 / 美指期 + 基本面/總經/月季報/籌碼/三大法人。核心=**PIT 對齊**(公告時戳 + vintage),幾乎全「粗→細」(見 [[project-mtf-direction-b7-parked]])。新數據源另立 epic。
- **V2.0 對話式研究** / **V3.0 自主研究員**(見 PRODUCT_VISION)。

---

## ✅ 近期已完成（2026-06 / 2026-07）
- **TEMPLATE_GATE_FIX epic（2026-07-05）**:派工品質防線修補——四方委員會(Claude+Codex+Composer+Gemini)審 template/機檢,實證 2 BLOCKING 繞過(FACT-RECEIPT/§G 逃逸)+多處範本↔機檢漂移;修=§A 段級狀態機+RISK-HIT 宣告制+per-Task 分段檢+RESULT 交叉規則+gate --reconcile 閉合鏈+adversarial 實核義務+TODO prompt 憲法瘦身(省每次 ~5,100 行)。驗收=14 fixture 矩陣+4 mutation+5 gate fixture+Codex 總 review 戳記。文件=docs/TEMPLATE_GATE_FIX_{BRIEF,SPEC,TODO,MANIFEST,GRANDFATHER}.md;現役文件 grandfather(僅新文件適用)。**新寫 SPEC 須帶 RISK-HIT: 宣告與 FACT-RECEIPT**。
- **FF 一致性整併**:Q5/B1/B2/B3/B5/B6/B4/B8(觀測性 + 批次日期修復 + warmup-then-trim + 批次刪除/保留 UX)。每項走完整管線。
- **Feature Explorer 圖表修復**:Y 軸貼合線 + Shift+滾輪 Y 縮放(rolling band 不撐爆 domain)。
- **d\* 實證量化**:三方證 Option A 非二階(cross-window selection 不穩),固定參考為修法(納入 P1 epic)。見 [[project-dstar-first500-optiona]]。
- **上線須留存參數盤點**:三方三輪 CONVERGED,產出 P1 epic 的精確範圍清單。見 [[project-stateful-param-audit]]。
