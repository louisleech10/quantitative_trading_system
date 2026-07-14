# ROADMAP — 量化交易系統戰術路線圖
> 單一現役戰術 roadmap。**即時任務狀態**看 `HANDOFF.md`；**決策理由**看 memory；本檔=中長期 epic 排序與範圍。
> 維護:完成項移到「已完成」、新需求加到對應優先級、範圍/決策變更標日期。**每次 commit 一併更新本檔**(2026-06-26 使用者定)。最後更新看 git log(手寫日期欄已廢,SCAR 2026-07-13)。

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
    - **1a 第二刀主體(cross_sectional 防洩漏)✅ 完成(2026-07-07,三方數據正確性簽核全 PASS)**:**F1** `_append_cross_sectional_labels` kline int64-ts→datetime 對齊(修第一刀 row_index 回歸暴露的橫截面標籤全 NaN,實測 0/5088→5085/5088 真 3sym×12h);**F4** per-symbol 覆蓋守衛 fail-closed(all-NaN/短序列無條件擋,推導下界非 magic floor);**F2** 單軸 labels_path fail-closed(symbol-aware/事件驅動 labels→Phase2 epic);**F3** 全域同步時間邊界 OOS holdout+purge+embargo(非 per-symbol 比例切,test-only 覆蓋全部 report 輸出)。**雙家族 adversarial SPEC review→reconcile D-1~D-4→雙 RECONCILE-STAMP APPROVED→freeze;Composer 實作→Codex code review 抓 F4 邊界 BLOCKING→fix-round→原提出方複驗閉合→三方 DATA-CORRECT PASS**;Claude 自跑 18 passed。docs/IC_PHASE1_1a_CUT2_XSECTIONAL_{SPEC,TODO}。
    - **剩餘刀順序已裁定(2026-07-08 三方委員會一致+使用者裁定,出處 handoffs/IC1A-CUTS-ORDER-{claude,codex,composer}.md)**:① 1-align 前瞻硬閘 ✅ 完成(2026-07-09,三方 DATA-CORRECT 簽核全 PASS;B1-B3+fixture 遷移 4 commit;重大破案=cut1 golden 舊 baseline 凍到 rolling IC join 0 列壞行為,已重凍;殘留見 HANDOFF)→ ② 1e HAC+1b FDR 合刀「顯著性正確化」✅ **完成(2026-07-11,B1-B5 入版 cfcf08e+e433500;假陽率 0.43→0.06;三方簽核全 PASS 閉合〔R4 codex DATA-CORRECT PASS〕;審計鏈 handoffs/IC1EB-*;殘留=1a cut1 golden 4 檔 provenance 閉合拆入 P2 債票 5,見 HANDOFF)**(大;**SPEC v2.2+TODO v2.2 已凍結 2026-07-09**:三方偵察→R1 雙家族 adversarial 雙 REJECT(4 BLOCKING 含 xsec `_label` horizon 丟失)→R2/R3 全 CLOSED→**使用者質疑觸發嚴謹度委員會**三腿 FREEZE-OK(HAC+BH=本層標準工具;M-B 增相關 null 實測把 PRDS 從假設變被測性質)→雙 RECONCILE-STAMP sha256:b77932d8;docs/IC_PHASE1_1E1B_SIGNIF_{SPEC,TODO}.md;baseline 快照 ✅(2026-07-10 v4:14 腿+xsec/full/event×2/labels-raise receipt;三家四輪 adversarial 複驗全 PASS;handoffs/ic1eb_baseline/+IC1EB-BASELINE-RECONCILE.md)→**B1 起 Grok 4.5 實作**(批次階梯,同批兩輪斷路器換 Codex)+Codex/Composer 雙審→三方簽核——2026-07-10 分工二調見 ORCH §1)→ 【使用者 2026-07-11 裁定:③ 之前先插一個獨立 P2 債 session(governance 9 紅 fixture 遷移 ✅ **完成(2026-07-11,151 passed 0 failed,完整中型管線+斷路器換手一次,docs/P2DEBT_T1_GOVFIX_{SPEC,TODO}.md)**/legacy 測試 data_cache tmp redirect ✅ **完成(2026-07-12,e6825d9;process-global patch+S1-S11 seam manifest+逐檔 digest oracle;final7 五 set 全綠 exit0;finding 鏈 C-1~C-5+雙家族審 CE8 全閉合;C-5 digest 抓到真洩漏證守衛可證偽;label horizon 既有紅拆票6)**/tsc 全部既存 errors ✅ **完成(2026-07-11,492c4cc;實測 11→0,vitest 31 綠,grok+composer 雙審)**/codex 沙箱卡死 ✅ **完成(669c6fa/59c691e;繞法固化 ORCH+根因=macOS workspace-write 族 #18243 非 #7852,Grok X 搜尋修正,A′ 避管線首選;持續蒐集 log)**/1a cut1 golden provenance ✅ **完成(2026-07-12,27fdb00;票5:誠實補史三事由+移 float64+append-only events+content-addressed reuse guard fail-closed〔6 mutation raise〕;replay Gate A 語意〔pytest golden〕/Gate B 因 gitignored 降手動限制;完整管線 SPEC→codex+grok 雙 BLOCK〔6+4 洞〕→R2 雙戳→實作→Gate B concur→三方 GOLDEN DATA-CORRECT PASS〔Claude+grok+composer〕)。**P2 債五票全清**);細目=HANDOFF Session 排程節)】→ **【IC-API-TEST-MODERNIZATION epic(票6 升級,使用者 2026-07-12「現在就做」)**:23 個 API IC 測試用 rng.normal 合成 fixture 違反真-kline 鐵律+多層 stale;三方共識=真 kline 衍生共用 session fixture(ETHUSDT/12h/~512,return_5+尾NaN)+分層 L0/L1/L2+去重 3;test_ic_e2e.py 同病 Phase2;RISK-HIT a/d 大完整管線;審計 handoffs/P2DEBT-T6-TESTSTRATEGY-*】→ **Phase 1 ✅ 完成(2026-07-12,56a9566;tests/fixtures/ic_api_real_kline.py 真 ETHUSDT/12h 衍生共用 fixture,31 passed,PIT 三方 DATA-CORRECT PASS〔Claude+grok+composer〕;完整管線 SPEC→雙BLOCK→R2 reconcile 雙戳+composer CONCUR→實作〔主委探診 warmup off-by-2〕;去重3+分層 L0/L1/L2;票6 23 nodeid 消化)** → **Phase 2/3 ✅ 完成(2026-07-12,a39dc6c;三方 scope 分類=遷移空集,5 momentum IC 合成測試全 LEGIT〔護欄/FDR/OOS/mutation 探針+管線煙測〕;Phase3=docs/IC_API_TEST_LAYERING.md 分層判準)。epic 三 Phase 全閉合。follow-up=票2 v6_baseline 可縮〔23 API 紅已由 epic 修綠+去重3〕** → ③ 1c Net IC 量綱(大;net_ic_analyzer.py:34 相關係數減報酬率;獨立 session 開)——**使用者參數已訪談(2026-07-14)**:①交易成本**不得寫死**(crypto/台股期/美股期各異)→ 前端使用者輸入+「是否啟用成本」勾選,全棧接線(後端+API+前端+wiring,防幽靈開關);②持倉頻率不定(1h~1w 皆可能)→ 成本分析一律情境掃描、不綁單一 timeframe 假設;③capacity 分析(participation_rate 1%)使用者不用→維持現狀標未校準、低優先。量綱修法(同單位化 vs 拆報告+損益平衡點)=委員會裁決。分工=Grok 實作/Codex+Composer 審查(2026-07-14 三調)→ ④ 1d attribution 正名+NaN fail-closed(中/大開工定;真 residual IC 歸 Phase 2B)→ ⑤ 1f 空圖 schema flatten+grouped schema 殘留併入(小-中,最後收尾)。**grouped_ic 崩潰止血已於 Phase 0 11507f5 完成,自清單移除**。1e+1b 若拆必 1e 先(反對先 FDR 接高估 p 值)。治理修補(SCAR):SPEC consumer-map 須含所有 reindex/merge 下游 + 真路徑 red-on-break 測試。
    - **✅ IC SPEC conformance pass 完成(2026-07-06)**：4 份 `IC_*_SPEC` 過 `template_check`（補 RISK-HIT+FACT-RECEIPT，不改設計/數值；受查發現 4 份皆對應已落地工作）。
    - **✅ IC 測試定向重驗完成(2026-07-06,含 Codex adversarial review)**：SPEC conformance 後重跑 51 個 Phase0/1 測試曾 45/6；6 紅根因＝goldens/run_selector 釘死舊 config_hash 未註冊 + run-selector 硬化(643c5c2)把「明確給 features_path 卻要求 config_hash 註冊」的 golden replay 路徑弄斷。**修法**：`ic_analysis_service` fail-closed 收斂到 registry 解析路徑（features_path 缺席才 raise；明確給 path 不擋），run-selector 靜默錯 run 保證不變（golden byte-equal + 2 hermetic 契約測試 + mutation 證偽 pin 住）；run_selector 4 測試改 is_materialized skip-guard（12h 資料 gitignored，誠實 skip 非造綠）。終態 **49 passed/4 skipped/0 failed**（VERIFY:20260706T052454Z-ic-reverify-final）。Codex [P1]（skip 掩蓋契約）已補 hermetic 測試閉合；殘留 [P2]：features_path 與 config_hash 不一致未校驗（pre-existing，另立）。FF 測試資料已就緒（3 sym×1h+12h 對齊、max_lag 後、`data_cache/features/`）。
    - **✅ run_selector 重凍完成(2026-07-06,含 Codex review)**：使用者補生兩套競爭 12h run（e53e2290+f754aad4，同 tf 不同 config、row 同 feature 異），重凍 generator/baseline/mini_registry/測試常數+防漂移不變式+3 sibling 測試改 hash；targeted 19 passed/1 xfailed（VERIFY:20260706T135518Z-ic-runselector-final）。
    - **✅ 第二刀首項 bug 修復完成（2026-07-07，全三方數據正確性簽核 PASS）**：`feature_library._attach_row_index`（鏡像 `_attach_cgsa_row_index`）在 V2 load 路徑貼回 `load_row_index_v2` 真時間軸；無 sidecar→no-op，長度不符→ValueError；只改 index，值/欄/列/檔大小不變（G-1 值守恆 + G-2 時間軸 byte-equal，真 12h run e53e2290/f754aad4 皆驗）。追蹤測試由 full-analyze xfail retarget 至失敗邊界斷言（218k 特徵 full analyze>17min 屬正交效能問題，歸「79 測試換真資料」epic）。清 bug 期中毒 ingest cache。**三方 PASS 零 BLOCKING**：Claude 自產 + Codex adversarial（語義時間 oracle 交叉驗列序 0 mismatch）+ Composer 資料正確性；RECONCILE-STAMP codex+composer APPROVED。docs/IC_PHASE1_1a_CUT2_ROWINDEX_{SPEC,TODO}。follow-up：ingest cache 版本化、1d 頻率地圖、conftest scoped-collect clobber golden。
  - Phase 2A(事件 case-control 主戰場)/Phase 3(430K 串流)/2B/4/5 未啟動。詳 phasing-CONVERGED 七 Phase。

### P0.5 — IC 效能 + grouped_ic 崩潰止血(已盤點,可立即動)
- **為何**:使用者實測選 run 跑 analyze 卡死+崩潰;三方 reconcile 完成。
- **Epic**:`handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md`(IC-CRASH/IC-FEATURE-GUARD/IC-UX-ERR=P0;IC-PERF=P1)。**狀態**:grouped_ic 崩潰止血已完成(Phase 0 11507f5);其餘(IC-PERF 等)未啟動(2026-07-11 校正,原「實作未啟動」與 L42 矛盾)。

### P2 — FF preset 移除盤點（2026-07-03 使用者排入,IC 正確性紅線之後做）
- **為何**:使用者從未用過/測過 professional_full 等 preset（2026-06-29 明示想移除）;現行測試/生成一律 base/full 全特徵不綁 preset,preset 定義成死碼+誤用風險。
- **範圍**:盤點所有 preset 定義與引用點（config/前端/文件）→ 確認零真實使用者 → 移除或明確 deprecate;涉 config schema 下游,走「中」型管線。
- **狀態**:已排程未啟動;不擋 IC。

### P2 — 文檔簡化 epic(2026-07-12 三家研究收斂+使用者定案兩批次,出處 handoffs/DOCDRIFT-SIMPLIFY-{STUDY-*,RECONCILE}.md)
- **為何**:ARCH(2044)+DEV_GUIDE(2434)=4478 行,漂移面大、假綠濃縮;真 ROI=抗漂移+消假綠(非省 token)。
- **範圍(兩批)**:A=修 TGF 斷鏈+建 ARCH `## Feature Factory 架構` 穩定 H2+刀1 已實現 853→能力索引(修假綠狀態欄)+刀3 目錄→~80+README 假行數;B=刀2 DEV 8 通用章→300-450+解耦枚舉→pointer(留 Artifact Contract/V2V3 why)+修 §1277+ 損壞 markdown。預期全檔→~2200-2500(−44〜−51%)。
- **鐵律**:驗收看資訊類型非硬行數;抽 contract 非整批上移;單檔 A/B/C 不拆 appendix;先建後刪 anchor。
- **狀態**:**批次 A 完成(2026-07-13)**——A00 manifest LOCKED→A0.1 FF H2→A0.2 DEV rename+TGF 斷鏈修復→A1 能力索引(853→表,native-tf drift+CAP-14 stage 舊錯一併正名)→A2 目錄+README;anchor checker(`scripts/check_doc_anchors.sh`+11 tests)入庫;§V 全套 gate PASS;ARCH 2044→935 行。每步 Codex 實作+composer/grok 對抗審+閉合重驗(4 輪 BLOCK 全閉)。**批次 B 完成(2026-07-13)**——B00 manifest LOCKED→B0 修損壞(byte==target view,被吞三章重見)→B1 八章壓縮(2382→823)→B2 解耦節收斂(935→643);post-state validator 全量 PASS。**epic 收官:全檔 4478→1466 行(-67%)**,契約全留可機檢、假綠清零、TGF 斷鏈修復。

### P2 — 解耦 Rule 4 既存違規修復(2026-07-12 doc 漂移施工揪出,使用者裁定立票、code 暫不動)
- **問題(不只 Rule 4,doc review 揭更廣)**:`check_decoupling.sh` 2026-07-12 實跑報 **R2=5、R3=12、R4=1** 全紅:
  - R4:`api/services/feature_factory_batch_adapters.py:9` service→service import(1 筆)。
  - R2:`momentum/Analysis/*` 直接 import `momentum/FeatureEngineering`(warmup_lookup/consumer_gate/feature_reader,5 筆)。
  - R3:api/services、api/routes 直接 import `momentum/FeatureEngineering` 具體工具未走 factory(run_locks/run_paths/hardware_utils…,12 筆)。
  - **phase4 scanner 只窄查特定檔**(R2 僅 strategy_backtest、R3 僅 2 factory、且不查 R4),故長期被誤報全綠。
- **待判定**:上述 R2/R3 是**真違規**還是 `momentum/FeatureEngineering` 應**豁免為共用基礎設施**(如 momentum.core)?屬架構判斷,須三方 triage(不是 doc 能定)。
- **Claude 初判(2026-07-13,待三方 triage 確認,勿當定案)**:被 import 的多為**共用基礎設施/唯讀介面**——`run_paths`(路徑 helper)、`run_locks`(per-run lease)、`hardware_utils`(tier 偵測)、`feature_reader`/`feature_library`(唯讀消費介面)、`consumer_gate`(fail-open 契約 helper)、`warmup_lookup`(warmup 查表)。性質接近已被 scanner 白名單的 `momentum.core`,**多半是良性共用底層**,非跨域伸手進別域內部業務邏輯。**風險低**(不碰數值/回測正確性 a/d、系統運作正常、無實際壞行為);**難度多為輕**:預期 triage 結論=把這批 shared-util/interface **納入 scanner 白名單或移入 momentum.core**(scanner 設定+doc 決策,非重寫);唯 R4 的 1 筆 service→service 需一個小 protocol/factory 間接(contained 改動)。它之所以「看起來嚇人」只是被半套 phase4 蓋住而靜默累積,非真的壞掉。
- **範圍**:triage 後,真違規者改走 protocol/factory 或明確把共用工具納入 scanner 白名單;動 api/services + momentum/Analysis 共用路徑(RISK-HIT b),走完整管線+驗證。
- **Triage 完成(2026-07-13,四家委員會,reconcile 雙 v2 戳記 PASS,見 handoffs/20260713-DECOUPLE-TRIAGE-RECONCILE.md)**:最終裁決=**白名單豁免 13、修 code 後豁免 1(R2-4 去 private)、真違規改碼 3(R3-9/R3-10/R4-1)**;白名單機制 3:1 採用(Codex 少數意見存檔,吸收 symbol 級註記+scanner `import momentum.*` 盲區+R4-1 composition-root 必填注入)。**Claude 初判「17 豁免」被實證修正**:R3-10 實為現行 bug(`ic_analysis_service:1002` `FeatureLibrary()` 必炸 TypeError 被吞,永遠 fallback);consumer_gate docstring「fail-open」誤標(實為混合契約);hardware_utils=FF 運維政策表非純硬體。落地=三段:①即修小票(R3-10/R4-1/R3-9/R2-4)②白名單+scanner 機制票(單一機讀來源+精準匹配+戳記機檢)③P3(route 下沉/hardware 收斂/`_registry` 穿透)。
- **附帶**:scanner 覆蓋自身也要校準——`check_decoupling.sh` 的「Rule 6」只查 api/services 的 lambda monkeypatch(非所有 callback bypass),也不查 canonical R6/Rule 8;納 CI 前須先確立各檢查真實覆蓋範圍,勿再宣稱「查全」。ARCHITECTURE/PRODUCT_VISION 已據實標。
- **落地(2026-07-14,兩票完成)**:①DECOUPLE-FIX4——R3-10(ic_analysis 死碼 bug)/R3-9/R4-1/R2-4 四筆修復,4 commits,G1 等值+G2 run 選擇+M1-M4 mutation receipt,Composer+Grok 雙 PASS;②DECOUPLE-ALLOWLIST——R2/R3 改 **AST import 掃描器**(`scripts/check_decoupling_imports.py`,全 import 形式/縮排/同行覆蓋)+白名單 manifest(`scripts/decouple_allowlist.md`,module+symbol+owner+contract,**戳記機檢 fail-closed 內建 scanner**,CLI 無 bypass)+永久 regression 矩陣 31 tests+ARCH 單源 pointer。
- **P2 — DECOUPLE-TRIAGE-2(follow-up,2026-07-14 立票;07-14 使用者裁定拆兩段)**:①**pending 5 筆退場=綁 Optuna 重啟 epic**(2026-07-14 使用者定:Optuna 功能休眠至 IC/ML 完成後才開發測試,屆時整條鏈重驗,triage 順路做、驗證成本共享;manifest pending 表持續亮著防遺忘);②掃描死角修復=**DECOUPLE-SCAN2 完成(2026-07-14)**:R4 由 AST 接管(routes 面/相對 import resolve/nested package 通用化,grok code review 抓出 nested 假綠退修後閉合)+api/models 入 R3 掃描根(triage:DataSourceEnum 死 import 刪除、SUPPORTED_TIMEFRAMES 白名單 2:1 多數決,codex relocate-to-core-constants 少數意見存 manifest contract P3 註記+timeframe 重複副本債);manifest 10 條重戳 PASS;scanner ALL RULES PASS;矩陣 55 tests;另 `api/models/` 不在 R3 掃描根=已知缺口,擴根前須 triage 新紅字;**R4 grep 亦有 import 形式盲區**(`import api.services.x`/`from api import services` 不被 `check_decoupling.sh:60-65` 抓,codex 2026-07-14 實證,DECOUPLE-P3 以 T1d AST allow-set 對新檔手動 gate,系統性修法歸本票)。未啟動;不擋 IC。
- **P3 整理完成(2026-07-14,DECOUPLE-P3 票)**:①route hardware 組裝全量下沉 `api/services/hardware_info_service.py`(route 變薄,golden JSON 修前後逐欄相等);②hardware_utils docstring 正名 FF tier 政策表(AST dump 等值=零邏輯變更);③FeatureLibrary 唯讀轉發 façade(`get_entry`/`find_latest_materialized`),api 零 `_registry` 穿透。3 commits,Composer+Grok 雙 PASS。
- **狀態**:主票+P3 全部完成;殘餘=**DECOUPLE-TRIAGE-2**(pending 3 筆 triage/api-models 掃描根/R4 grep import 形式盲區)。

### P2 — 統計嚴謹度後續登記(2026-07-09 嚴謹度委員會三腿一致,出處 handoffs/IC1EB-RIGOR-{claude,codex,composer}.md)
- **策略層 data-snooping epic**:White RC/Hansen SPA/Deflated Sharpe/PBO=回測/策略選擇層,與特徵級 FDR 互補不互代;未啟動。
- **FDR 方法升級選項**:`fdr_by`(任意相依保證)/`romano_wolf`(resampling stepdown);M-B 相關 null 實測帶外時 BY 為既定升級路徑。
- **monotonicity long-short `ttest_ind`(i.i.d.)**:現未入閘故風險受限;若未來接 p 閘須先 HAC/block 化(P2)。
- **描述性指標正名**:ic_mean/icir/hit_rate/monotonicity/ic_decay/grouped=描述性門檻非檢定,文件標明即可(P3-P4);grouped 子樣本加 n 顯示歸 1f 刀順手。

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
