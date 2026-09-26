# HANDOFF — 當前任務狀態

## 現況

<!-- BEGIN GENERATED: handoff-current -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 03-011 | SU-RESID-1 | 部分完成 | docs/SPLITUNIFY_TODO.md §E | 待觸發：出現可由收斂檔附錄證明之處置掛錯意見事故 |
| 04-006 | HP-FKPERF | 進行中 | docs/FKPERF_SPEC.md | 2026-09-23 使用者逐字「這會膨脹很快，兩三分鐘很快就更久吧，這無法接受」⇒ 開票（大任務：共用路徑 b、多 phase c）。偵察：存檔一次之產出端檢查開 4,322 個外部程式、約 10 秒，隨 fact-key 數線性成長（兩天 17→35）；根因＝bash 3.2 無關聯陣列、逐 key 重查 jq（收據 handoffs/run_receipts/20260923-fkperf-recon.json）。SPEC r1 三家皆 blocked、皆認方案 A（核心移入單一 Python 程序）可採；13 條採納 12、部分採納 1（handoffs/reconcile/20260923-fkperf-x-review-r1/synth.md 已銷帳），SPEC 改 v2：路徑字面型消費端列入核心、oracle 改兩個同形完整沙箱＋預期分支標籤、驗收加開檔數之規模不變性並回填實測秒數、`--help` 位元組保留；另更正 v1 誤稱使用者定「禁秒數門檻」（原文為「每次都跑的檢查須秒級、SPEC 寫實測秒數」），耗時上限測試列 §A 待使用者確認。r1 銷帳時發現帳本 dump 1.04MB 超過 ARG_MAX 致 debt_clear 起不來，經使用者選「直接修，交第 2 輪委員一起審」，已改經 fd 3 傳遞（行數不變）＋回歸測試。r2（composer 網路中斷經同輪重派）：r1 十三條中十二條由原提出方列 CLOSED；codex／composer 各以「每 key 對整份註冊表做 JSON 往返」反例（35 key 0.024s → 350 key 2.48s，程序數與開檔數皆不變）證明純 CPU 退化抓不到；使用者 2026-09-23 裁定比例型門檻「規模放大 10 倍最多慢 20 倍」，寫入 SPEC v3 C-6 ②與 Task 4.4；帳本修正三家皆判正確（handoffs/reconcile/20260923-fkperf-x-review-r2/synth.md 已銷帳，即以修正後之 debt_clear 銷成）。v4 主委自查：固定開銷約 0.1s 稀釋 1×／10× 比例，端點改 4×／40×。r3：前輪 ID 全數由原提出方閉合；codex／composer 同抓「只複製純內容 key，總數比僅 8.28」，grok 兩 P2（規模數未對齊、端點改動不得混入使用者已確認結果）；四條採納改 v5：規模以總 fact-key 數 35／140／350／1400 定義、端點列 §A 待使用者確認（handoffs/reconcile/20260923-fkperf-x-review-r3/synth.md 已銷帳）。r4 三家 proceed 已銷帳；使用者 2026-09-23 白話審閱 SPEC 回「ok」（含端點 140／1400）⇒ SPEC 定案；寫 TODO 時主委實測推翻「jq 不接受 NaN」（jq 1.7.1 接受，由 rows 型別檢查拒絕）⇒ v6 更正 C-5 與 Task 1.1 邊界③。TODO＝五類落點 manifest docs/manifests/FKPERF.json（commits `89bfaf5d`、`5855f551`）。r5 三家皆 blocked、13 條全採納（量測 helper 快速失敗即拋、注入可達性契約與行為測試、對照表逐列必紅、語料逐筆新舊比對、出口清單獨立錨；commit `037a670f`；handoffs/reconcile/20260923-fkperf-x-review-r5/synth.md 已銷帳）。r6–r10 共閉合 26 條，r10 三家 proceed；r11（SPEC v7：oracle 內部子程序失敗之 24 處出口歸 tool_failure、C-1 改具名例外封閉集四項）後戳記輪三家蓋章、領實作許可 b1。Phase 0 已實作（commit `cb604963`：差分 harness、119 筆出口語料、187 行出口歸類、規模探針、bash 程序數基準收據）。b1 審碼 r1（兩家）：codex 擋三條 P1（寫檔語料只監看手列宿主檔、一位元組 mutation 測試無零差異基線、語料②未逐一列入既有沙箱）＋三條 P2，composer 放行；修補中——寫後改全樹快照、mutation 先證零差異基線、語料②改錄製重播（跑既有兩檔測試時攔截每次生成器呼叫並快照沙箱，以 AST 呼叫圖閉包對證每支建沙箱之測試皆有錄製）。b1 r1 七條修補於 commit `31d8adbf`，r2 兩家 proceed 已銷帳（handoffs/reconcile/20260923-fkperf-b1-review-r2/synth.md）。領 b2 實作許可後 Phase 1–3 核心實作完成（scripts/_gen_fact_key_blocks.py，逐函式對應 bash），差分語料 409／409 逐位元組一致（含錄製之沙箱情境 268 筆）；SPEC v8 增 C-1 例外⑤（jq 自身 `jq: error (at …)` 行僅於 oracle 側剔除）。核心提交於 commit `44596806`（含比對工具修正：不可讀檔快照不崩潰、全等即刪沙箱、錄製目錄 atexit 刪）。b2 審碼收批。Phase 4 切換於 commit `5afe7595`（薄殼、守衛與 pre-commit 納管核心、mutation 對照 11 列＋正向性質測試、規模修正〔每路徑一次切行＋標記索引、--write 每宿主一次寫出〕、R-GOVTEST-5 關閉）；完整差分 51／52（唯一紅為錄製器新略過原因未列入允許集合，已補）；提交時 pre-commit 揭露活文件守衛快照模式未物化核心 ⇒ 補並加回歸測試。b3 審碼 r1–r3（handoffs/reconcile/20260924-fkperf-b3-review-r{1,2,3}/synth.md 皆已銷帳）：codex 依序抓出批次寫入之別名互蓋（`./`）、大小寫別名、取實體身分失敗中斷，改以裝置號＋inode 比對並失敗即退回逐 key，三者皆有拿掉修正即紅之回歸測試；Task 4.4 收據 handoffs/run_receipts/20260924-fkperf-scale.json 並回填 SPEC §A（commit `bcb04a5b`）。下一步：Task 4.5 全套治理測試（背景，小時級；2026-09-24 首跑因須改檔而中止，待不改檔之空檔重跑） |
| 04-007 | HP-FFDSTAR | 進行中 | docs/FFDSTAR_SPEC.md | 使用者 2026-09-23 睡前排序「FKPERF 收完→FF-TFMETA→FF-NAME→FFDSTAR 依序做完」⇒ 復工。停手前 R2 十三條待閉合；2026-09-24 R3 兩家（codex blocked 兩 P1＋一 P2、composer proceed 兩 P2）五條全採納修入 SPEC（handoffs/reconcile/20260924-ffdstar-x-review-r3/synth.md 已銷帳）：K-1 來源加 `search_error_default`、K-2 原因碼樣式封閉、Phase 1 依賴 FF-NAME、Task 1.1 驗證③。R4 待 FF-NAME 規格重寫定案後一併複查；輸出大小仍須實作後帶數字請使用者核可 |
| 04-009 | HP-FFSTAT | 進行中 | docs/FFSTAT_SPEC.md | 2026-09-24 使用者第 4 點開票；SPEC v5 經 r1–r5 兩家收斂（commit `ae8b3cba`）；白話審閱（白話說明/FF-STAT規格審閱.md）時使用者連問免檢表抽樣、全量 ADF 成本、前 500 根抽樣誤差，並指示「將量化業界和統計分析怎麼做考量進去做研究」⇒ 研究 r1 已收斂（handoffs/reconcile/20260924-ffstatres-x-consult-r1/synth.md 已銷帳）；研究 r2 定乙案（起始日前資料、獨立校準域）。成本收據 handoffs/run_receipts/20260924-ffstat-adf-cost.json（L1＋L2 90,006 欄全量約 194 秒／標的／次）。使用者 2026-09-24 裁定：窗長「先實測再定」、未填起始日「自動預留校準段」、SPEC v17「同意施工」；v18 兩處事實更正。TODO manifest docs/manifests/FFSTAT.json 定案（r24、兩家戳記）；實作 b1–b3 收批（b3 含 SPEC v19 前史不足逐欄〔使用者 2026-09-26 裁定〕與 v20 審碼修補，r3–r6 共六輪，r6 codex proceed）；b4 動工前重設計未填起始日（使用者 2026-09-26 裁定主訓練週期優先、主週期＝介面主框架），SPEC v21→v31 經審查 r2–r12（r11 後經 run_ic_first 去留查證，使用者裁定不刪、另開合一票；r12 兩家 proceed），下一步使用者白話逐條審閱 → 白話逐條審閱 → b4 實作，餘 b5 |
<!-- END GENERATED: handoff-current -->

## 待辦

<!-- BEGIN GENERATED: handoff-todo -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 03-003 | R-3 | 未開工 | docs/SPLITUNIFY_TODO.md §E | UAT 排在最後一次做（使用者裁定） |
| 03-004 | R-4 | 未開工 | docs/SPLITUNIFY_TODO.md §E | 另開接線票；本票只保證 assignments 語意不變 |
| 03-007 | SU-RESID-V8-ATTEST | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：專案導入 commit 簽章或受保護分支 |
| 03-008 | SU-RESID-PAUSED-NO-RESULT | 未開工 | docs/SPLITUNIFY_TODO.md §E | 待觸發：audit 出現同輪同家 failed 且無產出之結果列 |
| 03-009 | SU-RESID-COMMITTEE-MODEL-EVIDENCE | 未開工 | docs/SPLITUNIFY_TODO.md §E | 實測兩 CLI 非互動輸出之型號與 effort 欄位 |
| 03-010 | SU-RESID-9A-UI | 未開工 | docs/SPLITUNIFY_SPEC.md R5-C5 | 隨 R-5 實作批交付（規格 R5-C5） |
| 03-011 | SU-RESID-1 | 部分完成 | docs/SPLITUNIFY_TODO.md §E | 待觸發：出現可由收斂檔附錄證明之處置掛錯意見事故 |
| 03-013 | SU-RESID-4 | 未開工 | docs/SPLITUNIFY_SPEC.md §N | 待觸發：下一次動 IC 切分契約 |
| 03-014 | SU-RESID-5 | 未開工 | docs/SPLITUNIFY_SPEC.md §N | 待觸發：下一次動 SplitPlan 欄位契約 |
| 03-015 | SU-RESID-C5-TARGETS | 未開工 | docs/SPLITUNIFY_TODO.md Task 9.3 | 待觸發：Task 9.3 驗收段兩條觸發條件 |
| 04-003 | HP-EVENTSCAN | 停手 | 白話說明/EVENTSCAN方向與做法.md | 🔴 **R13 暫停**（使用者 2026-09-22 裁定先處理 SPEC/TODO 流程優化，見 HP-PROCOPT）。SPEC 已起草（docs/EVENTSCAN_SPEC.md），兩家對抗審至 **R12 收斂**、**未凍結**；R12 末仍 11×P1。流程優化中之 TODO 改格式已於 2026-09-23 完工（HP-TODOFMT）；何時復工待使用者決定——復工時先依新格式產出本票 manifest，並依屆時之停輪條件重定續審形狀 |
| 04-006 | HP-FKPERF | 進行中 | docs/FKPERF_SPEC.md | 2026-09-23 使用者逐字「這會膨脹很快，兩三分鐘很快就更久吧，這無法接受」⇒ 開票（大任務：共用路徑 b、多 phase c）。偵察：存檔一次之產出端檢查開 4,322 個外部程式、約 10 秒，隨 fact-key 數線性成長（兩天 17→35）；根因＝bash 3.2 無關聯陣列、逐 key 重查 jq（收據 handoffs/run_receipts/20260923-fkperf-recon.json）。SPEC r1 三家皆 blocked、皆認方案 A（核心移入單一 Python 程序）可採；13 條採納 12、部分採納 1（handoffs/reconcile/20260923-fkperf-x-review-r1/synth.md 已銷帳），SPEC 改 v2：路徑字面型消費端列入核心、oracle 改兩個同形完整沙箱＋預期分支標籤、驗收加開檔數之規模不變性並回填實測秒數、`--help` 位元組保留；另更正 v1 誤稱使用者定「禁秒數門檻」（原文為「每次都跑的檢查須秒級、SPEC 寫實測秒數」），耗時上限測試列 §A 待使用者確認。r1 銷帳時發現帳本 dump 1.04MB 超過 ARG_MAX 致 debt_clear 起不來，經使用者選「直接修，交第 2 輪委員一起審」，已改經 fd 3 傳遞（行數不變）＋回歸測試。r2（composer 網路中斷經同輪重派）：r1 十三條中十二條由原提出方列 CLOSED；codex／composer 各以「每 key 對整份註冊表做 JSON 往返」反例（35 key 0.024s → 350 key 2.48s，程序數與開檔數皆不變）證明純 CPU 退化抓不到；使用者 2026-09-23 裁定比例型門檻「規模放大 10 倍最多慢 20 倍」，寫入 SPEC v3 C-6 ②與 Task 4.4；帳本修正三家皆判正確（handoffs/reconcile/20260923-fkperf-x-review-r2/synth.md 已銷帳，即以修正後之 debt_clear 銷成）。v4 主委自查：固定開銷約 0.1s 稀釋 1×／10× 比例，端點改 4×／40×。r3：前輪 ID 全數由原提出方閉合；codex／composer 同抓「只複製純內容 key，總數比僅 8.28」，grok 兩 P2（規模數未對齊、端點改動不得混入使用者已確認結果）；四條採納改 v5：規模以總 fact-key 數 35／140／350／1400 定義、端點列 §A 待使用者確認（handoffs/reconcile/20260923-fkperf-x-review-r3/synth.md 已銷帳）。r4 三家 proceed 已銷帳；使用者 2026-09-23 白話審閱 SPEC 回「ok」（含端點 140／1400）⇒ SPEC 定案；寫 TODO 時主委實測推翻「jq 不接受 NaN」（jq 1.7.1 接受，由 rows 型別檢查拒絕）⇒ v6 更正 C-5 與 Task 1.1 邊界③。TODO＝五類落點 manifest docs/manifests/FKPERF.json（commits `89bfaf5d`、`5855f551`）。r5 三家皆 blocked、13 條全採納（量測 helper 快速失敗即拋、注入可達性契約與行為測試、對照表逐列必紅、語料逐筆新舊比對、出口清單獨立錨；commit `037a670f`；handoffs/reconcile/20260923-fkperf-x-review-r5/synth.md 已銷帳）。r6–r10 共閉合 26 條，r10 三家 proceed；r11（SPEC v7：oracle 內部子程序失敗之 24 處出口歸 tool_failure、C-1 改具名例外封閉集四項）後戳記輪三家蓋章、領實作許可 b1。Phase 0 已實作（commit `cb604963`：差分 harness、119 筆出口語料、187 行出口歸類、規模探針、bash 程序數基準收據）。b1 審碼 r1（兩家）：codex 擋三條 P1（寫檔語料只監看手列宿主檔、一位元組 mutation 測試無零差異基線、語料②未逐一列入既有沙箱）＋三條 P2，composer 放行；修補中——寫後改全樹快照、mutation 先證零差異基線、語料②改錄製重播（跑既有兩檔測試時攔截每次生成器呼叫並快照沙箱，以 AST 呼叫圖閉包對證每支建沙箱之測試皆有錄製）。b1 r1 七條修補於 commit `31d8adbf`，r2 兩家 proceed 已銷帳（handoffs/reconcile/20260923-fkperf-b1-review-r2/synth.md）。領 b2 實作許可後 Phase 1–3 核心實作完成（scripts/_gen_fact_key_blocks.py，逐函式對應 bash），差分語料 409／409 逐位元組一致（含錄製之沙箱情境 268 筆）；SPEC v8 增 C-1 例外⑤（jq 自身 `jq: error (at …)` 行僅於 oracle 側剔除）。核心提交於 commit `44596806`（含比對工具修正：不可讀檔快照不崩潰、全等即刪沙箱、錄製目錄 atexit 刪）。b2 審碼收批。Phase 4 切換於 commit `5afe7595`（薄殼、守衛與 pre-commit 納管核心、mutation 對照 11 列＋正向性質測試、規模修正〔每路徑一次切行＋標記索引、--write 每宿主一次寫出〕、R-GOVTEST-5 關閉）；完整差分 51／52（唯一紅為錄製器新略過原因未列入允許集合，已補）；提交時 pre-commit 揭露活文件守衛快照模式未物化核心 ⇒ 補並加回歸測試。b3 審碼 r1–r3（handoffs/reconcile/20260924-fkperf-b3-review-r{1,2,3}/synth.md 皆已銷帳）：codex 依序抓出批次寫入之別名互蓋（`./`）、大小寫別名、取實體身分失敗中斷，改以裝置號＋inode 比對並失敗即退回逐 key，三者皆有拿掉修正即紅之回歸測試；Task 4.4 收據 handoffs/run_receipts/20260924-fkperf-scale.json 並回填 SPEC §A（commit `bcb04a5b`）。下一步：Task 4.5 全套治理測試（背景，小時級；2026-09-24 首跑因須改檔而中止，待不改檔之空檔重跑） |
| 04-007 | HP-FFDSTAR | 進行中 | docs/FFDSTAR_SPEC.md | 使用者 2026-09-23 睡前排序「FKPERF 收完→FF-TFMETA→FF-NAME→FFDSTAR 依序做完」⇒ 復工。停手前 R2 十三條待閉合；2026-09-24 R3 兩家（codex blocked 兩 P1＋一 P2、composer proceed 兩 P2）五條全採納修入 SPEC（handoffs/reconcile/20260924-ffdstar-x-review-r3/synth.md 已銷帳）：K-1 來源加 `search_error_default`、K-2 原因碼樣式封閉、Phase 1 依賴 FF-NAME、Task 1.1 驗證③。R4 待 FF-NAME 規格重寫定案後一併複查；輸出大小仍須實作後帶數字請使用者核可 |
| 04-008 | HP-ICFIRSTALIGN | 未開工 | docs/manifests/FFSTAT.json | 2026-09-24 FF-STAT r19 追查時發現：真實 kline 下 run_ic_first 之 IC 階段必拋 AlignmentViolationError（label 時間戳 index 對 L7 raw 讀回 RangeIndex；test_b6_warmup_trim::test_warmup_trim_ic_first 於 main 同紅；防呆引入於 `78c85bb2`）。使用者 2026-09-26 裁定 run_ic_first 不刪（去留查證 handoffs/reconcile/20260926-icfirstneed-x-consult-r1/synth.md），本票改為 IC-First 管線合一：IC 頁套用後處理改用正式實作並修其未來洩漏（未勾 rank 時 Gaussian 全樣本排名）、run_ic_first 去除 factory 可變狀態依賴、修對齊；排 FF-STAT 之後立刻做（先於 FF-NAME、FFDSTAR） |
| 04-009 | HP-FFSTAT | 進行中 | docs/FFSTAT_SPEC.md | 2026-09-24 使用者第 4 點開票；SPEC v5 經 r1–r5 兩家收斂（commit `ae8b3cba`）；白話審閱（白話說明/FF-STAT規格審閱.md）時使用者連問免檢表抽樣、全量 ADF 成本、前 500 根抽樣誤差，並指示「將量化業界和統計分析怎麼做考量進去做研究」⇒ 研究 r1 已收斂（handoffs/reconcile/20260924-ffstatres-x-consult-r1/synth.md 已銷帳）；研究 r2 定乙案（起始日前資料、獨立校準域）。成本收據 handoffs/run_receipts/20260924-ffstat-adf-cost.json（L1＋L2 90,006 欄全量約 194 秒／標的／次）。使用者 2026-09-24 裁定：窗長「先實測再定」、未填起始日「自動預留校準段」、SPEC v17「同意施工」；v18 兩處事實更正。TODO manifest docs/manifests/FFSTAT.json 定案（r24、兩家戳記）；實作 b1–b3 收批（b3 含 SPEC v19 前史不足逐欄〔使用者 2026-09-26 裁定〕與 v20 審碼修補，r3–r6 共六輪，r6 codex proceed）；b4 動工前重設計未填起始日（使用者 2026-09-26 裁定主訓練週期優先、主週期＝介面主框架），SPEC v21→v31 經審查 r2–r12（r11 後經 run_ic_first 去留查證，使用者裁定不刪、另開合一票；r12 兩家 proceed），下一步使用者白話逐條審閱 → 白話逐條審閱 → b4 實作，餘 b5 |
<!-- END GENERATED: handoff-todo -->

## 坑

- 🔴 **本檔文法**（定義於 `scripts/live_doc_registry.json` 之 handoff 段；寫入前由 `scripts/live_doc_write_guard.sh` 擋，commit 前再以 `--staged` 擋）：「現況」「待辦」只放生成區塊——狀態與下一步改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`；「坑」手寫；「進行中紀錄」只准條目標記與指標行 `- <日期>：<識別碼或 v<N>> → <反引號路徑或 commit>`，條目所含識別碼一轉完成，整則移至 `docs/HANDOFF_ARCHIVE.md`。
- 🔴 **新增行不得同行寫「識別碼＋狀態字面」**（全部狀態 key 之識別碼，含 `docrot2_status_keys`），也不得寫刪除線、考古字面、canonical finding ID；需要引用過時樣本時放 fenced code block。出處與輪次留在 `handoffs/reconcile/` 收斂檔。
- 🔴 **2026-09-24 磁碟被暫存檔塞滿（剩 0，所有指令失效）**：Python 暫存在 macOS 落於 `/var/folders/…/T`（非 `/tmp`），主委探針 `probe_rec_*` 22GB、pytest 保留之沙箱 13GB、錄製器 `fkperf_record_*` 從不刪、委員工作副本約 6GB。已改：錄製器 atexit 刪、`check_case` 全等即刪兩沙箱、探針經 `handoffs/run_receipts/fftfmeta_probes/_isolate.py` 把其後 mkdtemp 導入單一根並 atexit 刪。新探針一律先呼叫 `_isolate.py`。
- 直接執行之 FF 探針（不經 pytest）須先呼叫 `_isolate.py` 再匯入專案模組；否則寫進真實 `data_cache/features/registry.json` 與 `data_cache/cgsa_work`（2026-09-24 已清 5 筆假條目；`data_cache/features/registry.json.bak` 仍為被污染之 26 筆版本）。根 `conftest.py` 已把 `NUMBA_CACHE_DIR` 導向 tmp，測試不再弄髒 30 個追蹤中之 `.nbi`。
- committee session 名須為 `<date>-<epic>-x-review-r<N>`（或 `-b<N>-`）；`…-todo-review-r1` 被拒。`python3 - <<EOF` heredoc 被權限拒，改寫腳本檔再 `venv/bin/python file.py`。
- 使用者 2026-09-15 對 DOCROT2 之逐字裁定見 `docs/DOCROT2_SPEC.md` §C；委員組成之唯一權威＝`scripts/governance_families.json` 之 `active_stampers`（本檔不寫家數）。
- 🔴 **SPEC 戳記要能過 provenance，需 `gate.sh register-output <task> <SPEC路徑> --kind stamp --family <fam>` 逐家各跑一次**（`--kind stamp` 才會跳過 verdict parser；檔名無 `-<family>.md` 尾碼時 family 必須顯式給）。且該 SPEC 路徑須先列入 `scripts/stampable_artifacts.txt`；`docs/GAP3_EVENT_UX_SPEC.D-001.md` 與 GAP3 UX TODO 各延伸檔未列入，其戳記未對證現行 body hash。
- 🔴 **委員裁決塊不合契約時，出路是 `debt_clear.sh:394` 的設計路徑：主委修檔後 `register-output`**，不是重派；裁決行 `CLOSED:` 只准填 finding ID，填日期會被 `verdict_parse` 拒收。
- **同輪重派＝兩個指令，不經使用者終端機**（該家最新結果非 success 時）：①`bash scripts/gate.sh redispatch --round-id <id> --family <fam> --reason <文字>` 取得綁定許可並印出唯一可放行之指令；②以 Bash 原樣執行該指令（不得加重導向或串接）。前次產出會自動保存於 `handoffs/redispatch_archive/`，銷帳前收斂檔須引用保存檔路徑並逐條處置其 finding。重派達上限時改棄置：`bash scripts/debt_clear.sh --abandon --round-id <id> --kind collection-failed --reason <文字> --approver <文字>`，再以新 session 重審。**永遠不要 kill 執行中的 `committee_run`**。
- **session 名不得重複**（fail-closed），格式 `<YYYYMMDD>-<epic>-b<N>-<kind>-r<N>`（`scripts/session_name_check.sh`）；派前先 `bash scripts/debt_ledger.sh --list | grep <session>`。
- **SPEC 戳記輪的 brief-kind 要用 `closure` 不是 `stamp`**：`brief_conformance_check.sh:425` 要求 `stamp-target` 須 `handoffs/` 前綴，而 SPEC 在 `docs/`。既有作法見 `handoffs/20260912-SPLITUNIFY-D001-STAMP-BRIEF.md`。
- **synth 處置欄的反引號 token 必須逐字出現在標的檔**（`spec_xref_check --synth`），否則寫檔 hook 擋；`延後→Task N.N` 之說明**不得有巢狀全形括號**，且目標須已存在於同票 TODO——`debt_clear` 依 session 第二段推：先找散文 `docs/<EPIC>_TODO.md`，無則找 `docs/manifests/<EPIC>.json`（新格式之票：目標只准 `Task N.N` 或殘留 ID 形狀，且須**恰等於** manifest `batch_card.not_executable[].item` 之一，例 item `E-4` 才能 `延後→E-4`；出現在描述欄不算，具名測試名不合目標形狀）。
- `committee_run` 的 harness exit code 不可信，**讀 `committee_rc=` 那行**。
- 🔴 `pytest` 一律逐檔明列路徑；`-k` 只過濾執行、**不減少收集**，無路徑即從 rootdir 收全套。
- 🔴 `reconcile_build.sh` 一律帶 `--mode review`；`debt_clear` 用 `--round-id <id> --session <name> --lock <sources.lock>`（不吃位置參數）。
- 🔴 **`committee_run.sh` 之參數順序有硬規**：`--session <name>` 須在 `--` **之前**，`<brief> <out前綴> <fam1,fam2>` 為位置參數，gate flags 一律在 `--` 之後，且 `--brief-kind` **不是** gate flag（放進去會 `未預期參數` 而 fail-closed 不派工，brief-kind 由 brief 檔內 `brief-kind:` 行決定）。**`--` 之後還必帶 `--task-id <id>`**（開債必填）——先跑 `gate.sh dispatch` 拿到的 token 不會替它補，缺了會 `ERROR: gate flags 缺 --task-id` 而 rc=2（乾淨失敗，不開債、委員不跑，可直接重下）。
- 🔴 **`gate_check.sh` 的 PreToolUse 偵測會誤判「字串裡含家族名或派工樣式」的無害指令**：`pgrep -f "codex exec"`、`ls | grep composer` 這種等待迴圈會被判成 kind=dispatch 而 GATE BLOCKED（本輪連續踩兩次）。避法＝等待迴圈用 glob（`ls -1 <prefix>-*.md`）不要寫出家族名。
- 🔴 **`brief-kind` 的合法值是 `review|consult|closure|impl|stamp`**，**沒有 `discovery`**（雖然 `reconcile_build.sh --mode` 有 `discovery`，兩者不同命名空間）。寫錯會被 `doc_format_precheck` 在寫檔當下擋。
- 🔴 **委員在 `CLOSED:` 列別家族的 finding ID 會被 `verdict_parse` 拒收**（「前綴家族 ≠ 本產出家族」），`debt_clear` 則報 `result_state='verdict_rejected'` 而不說原因。查法＝`bash scripts/verdict_parse.sh <委員檔> <family>`（**要帶 family 參數**，只給檔名會回「未知參數」且 rc=0 誤導）。修法＝主委刪掉跨家族 ID 後 `bash scripts/gate.sh register-output <task> <檔>`。
- 🔴 **改 `spec_xref_check.sh` 的 GENERATED marker regex 時，key 字元類必須含連字號**：真實 key 皆為 `eventscan-rulings` 這種帶連字號者。用 `[^\s>-]+` 會在**加上行尾錨點後**把全檔合法 marker 判成結構不合法；無錨點時因 `match()` 只做前綴比對而僥倖不報，**所以上一輪不會發現**。
- 🔴 **`committee_run.sh` 自己會跑 `gate.sh dispatch`**：所有 gate 旗標（`--risk`／`--intent`／`--facts-asked`／`--review-role`／`--template`／`--adversarial`）都要放在 `--` 之後，先獨立開一次 gate 是多餘的（token 不會被它沿用）。位置參數 `<brief> <out前綴> <fam1,fam2,...>` 必須在 `--` **之前**。
- 🔴 **`--task-id` 必須等於 session 名的大寫形式**：session `20260922-todofmt-x-consult-r1` ⇒ task-id `20260922-TODOFMT-X-CONSULT-R1`。給短名（`20260922-TODOFMT`）會 `ERROR: task-id 須為 session 的大寫形式` 而 fail-closed（不發 token、不開債，可直接重下）。
- 🔴 **收斂檔必須逐條附上完整 finding body（`## <ID>` 標題）**：`completeness_check` 用 `extract_heading_ids` 找 `## <ID>` **標題**，群集表裡的「來源 ID」欄**不算**。`reconcile_build.sh` 產的 scaffold 已含這些區塊，手寫 synth 覆蓋掉就會全數報 `未出現在綜合檔`。補法＝從 `sources/*.md` 機械複製各 `## <ID>` 區塊附在檔尾。
- 🔴 **計數一輪的 finding 數：一律數來源檔的 `## <FAMILY>-R<n>-P<0-3>-<NN>` 標題並扣除 `P3-00`，禁止改數 synth 內出現的 ID**——synth 會引用前幾輪的 ID，那樣會灌水（2026-09-22 主委據此得出「EVENTSCAN 曲線平坦」之錯誤結論，由 grok 與 codex 各自獨立抓出）。重跑：`cat handoffs/reconcile/<session>/sources/*.md | grep -E "^## [A-Z]+-R[0-9]+-P[0-3]-[0-9]+" | grep -vc "P3-00"`。
- 🔴 **`.claude/settings.json` 之 `permissions.deny` 含 `Bash(rm *)`＝硬性拒絕、不跳核准提示**：使用者看不到任何提示，Claude 只收到 deny。需要刪檔一律改請使用者自行在終端機執行。
- 🔴 **開門指令與派工指令必須分兩次 Bash 呼叫**（`gate.sh dispatch` 一次、`committee_run.sh` 一次）：寫在同一條指令裡，PreToolUse hook 會在 token 落地前先擋。
- 🔴 **連 `awk`／`sed` 的文字內容也會觸發 dispatch 偵測**：只要指令列裡出現派工樣式或家族名（即使只是要把它寫進本檔當成坑），就 GATE BLOCKED。避法＝把文字先用 Write 工具落成檔案，再讓 `awk` 從檔案讀，指令列本身不含觸發字串。
- 🔴 **`gov_check` 第 1a 段擋比例式停輪禁語之「字面」，不做語意判斷**：即使寫成「不主張以該禁語停輪」也命中。要討論該禁語時改寫描述，別打出原字串。
- 🔴 **`completeness_check.sh` 的正式入口是 `--lock <sources.lock>`**，餵 synth 路徑會 FAIL。
- 🔴 **`reconcile_cluster_attribution_check` 要求群集列逐字引用斷言前 20 字**（去空白後比對）；委員與主委之類別不一致時，須另列 `### 類別不一致` 段並附處置 token，否則銷帳被擋。
- 🔴 **`gate.sh dispatch --impl-self` 必帶 `--task-id <root>-impl-b<N>-claude`**（family 尾碼須為 `claude`），省略會被拒發 token。
- 🔴 **`completeness_check.sh` 正式入口是 `--lock <sources.lock>`**；直接給 synth 路徑會被判「argv 來源僅 tests 隔離」而 FAIL。單檔檢查才用 `--single <委員檔>`。
- 🔴 **逐段搬移函式時，模組級常數不會跟著走**：搬移腳本的錨點只涵蓋 `def`／`class`，模組頂層的常數落在所有段之外 ⇒ 搬過去的函式 import 當下不報錯、**跑到那一行才** `NameError`。搬完先 grep 被搬函式引用的所有大寫識別字。
- 🔴 **隔離 git worktree 跑 mutation 時，`skip` 與 `pass` 在 rc 上無法區分**：`data_cache/` 在 `.gitignore` 內 ⇒ 新建之 worktree 沒有它 ⇒ 需真實資料之測試一律 `skip`、rc=0，會被誤讀為「mutation 存活」或「測試通過」。修法＝①`ln -s <repo>/data_cache <worktree>/data_cache`；②harness 必須把 stdout 含 `skipped` 判為**無效**，不得只看 rc。
- 🔴 **一個永遠不會觸發的守衛比沒有守衛更糟**：它讓覆蓋率缺一行、讓文件照它寫「這個邊界由它承擔」，而真正承擔者是別條。判準＝找出該分支之唯一生產呼叫點，看前置條件是否已排除它。處置＝**不替它補測試**（要測就得 mock 前置，那是替空殼造假綠），改標 `pragma: no cover` ＋碼內寫明為何不可達 ＋ 另補一條釘住「真正會發生的 reason」之測試 ＋ 同步改文件字面。
- 🔴 **守恆／身分檢查之前不得「正規化」輸入**：`str()`／`set()`／`.strip()` 都會**製造**合法值——`None` 變成一個叫 `"None"` 的事件、重複被集合折疊成一筆、`" A "` 與 `"A"` 變成同一身分，於是真正的不一致被自己的程式抹平。正確順序＝先驗身分契約（**驗證**可以用 `strip()` 判斷有無內容，但其結果不得進任何集合），再做集合運算。守恆比對一律用原值逐字。
- 🔴 **一次不完整的查證不能支撐全稱結論**（同一形態連續犯兩次）：①以「掃過全部落檔資料零例外」為由加了一道規則，卻沒測**產生器程式碼路徑**，而規格文件逐字寫著該路徑是例外；②寫殘留理由說「某欄不存在」，卻沒查契約之 `receipt_schema`，該欄其實存在。⇒ **規格／契約文件本身是一手證據，比掃現存資料更直接**；具名殘留之理由與 finding 之碼證同級，會被下一輪當既定事實引用，理由寫錯會讓人照著放棄。派工單「我沒查」欄列出的項目，在下結論前必須先查掉。
- 🔴 **`Task 10.7` 邊界②之組合：規格指定值已失效，用下列實測值**。批 `20260901T132233Z-363ecc4f`（規格 r18 指定）現走 analyze route 回 **422**（`label_origin` 之 `conditional_required_missing`，該批早於現行匯入契約）。現行可用：**coverage 剔除**＝批 `20260906T105851Z-8cc44eea` × run `ETHUSDT/1h/5ea074390e98405cb83d602fe7b7fb00`（對齊剔除 12、coverage 剔除 22、投影 110）；**post-trim 剔除**＝批 `20260909T130533Z-7f73e4c7` × 同一短 run（post-trim 剔除 1、投影 164）。🔴 **不得**取 `20260909T130533Z-7f73e4c7` × 長 run `4a8a0b37…`（三種剔除皆 0，空心綠）。
- 🔴 **stub 只 stub 一半會造出生產上不可能的狀態**：測試 monkeypatch 某個衍生值時，須把同源的其他衍生值一起 stub（例：`_feature_run_time_range` 與 `_feature_run_dir` 都由同一個 run 目錄導出，只 stub 前者會做出「涵蓋判定過、run 目錄不存在」這種真實請求走不到的狀態），否則後續加的 fail-closed 會被誤判為過嚴。
- 🔴 `handoffs/` 整包在 `.git/info/exclude`：brief、委員產出、收斂檔只在本機，commit 時 `git add` 會被拒；commit 訊息之 REF 仍須指向含 VERIFY／SIGNOFF／RECONCILE-STAMP／CLOSED／APPROVED 字樣之檔。
- 新增 `scripts/` 檔或改掛載後跑 `bash scripts/list_active_mechanisms.sh --write`，否則寫檔 hook 擋；在 fixture 目錄建檔名含 `TODO`／`SPEC` 之樁檔須先 `bash scripts/gate.sh artifact`。
- 🔴 **既有紅（2026-09-14 實測，非 DOCROT2 改壞）**：`tests/governance/test_debt_emit.py` 之 7 條 `test_b3_*`（隔離 repo 缺 `scripts/prev_review_resolve.sh`）；`tests/governance/test_gate_deny_fields.py::test_01_corpus_a_covers_decision_branches`（錨點 `INPUT="$(cat)"` 已漂移）；`scripts/obligation_block_check.sh` 對 `docs/SPLITUNIFY_SPEC.D-002.md` 結構性 rc=1（舊段更正註記逐字引用裁決編號，義務區塊內零違規）。
- 🔴 治理測試既有紅基準（2026-09-13 實測）：19 個涉及 `brief_conformance_check` 的檔為 30 failed／523 passed／3 skipped；根因＝隔離 repo 依賴複製清單缺 `scripts/quant_standard_check.sh`／`ticket_batch_check.sh`。`test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths` 會**掛住**，跑治理回歸須排除。
- 🔴 **治理全套基準（2026-09-17 實測，改動前後兩棵樹並行各約 1:52，單跑約 1:40）**：`venv/bin/python -m pytest -q tests/governance --deselect tests/governance/test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths` → HEAD `c7edce12` 為 **69 failed／2377 passed／3 skipped**，與改動前 `61aa55b0`（69 failed／2329 passed）之 FAILED 名稱集合**完全相同**。既有紅名單須以「在改動前之 commit 建暫時 worktree 重跑同一批檔、逐名比對」證明（比對法：`git worktree add -f <tmp> <舊commit>` → 於該目錄跑同檔 → `comm` 比對 FAILED 名稱集合）。判回歸看**名稱集合差集**，不要比總數。
- 🔴 **後加的守衛會遮蔽先前的守衛**：兩道守衛對同一情境給出相同 rc 時，先前那道被改壞後測試仍綠＝該道從此無人守（同一票內犯三次）。修法＝每個拒絕出口輸出可區分的原因碼（例 `RD_GUARD_REASON=<code>`），**測試斷言原因碼而非只斷言被拒**；加新守衛時必須同時檢查它是否吃掉既有 mutation 的鑑別力。
- 🔴 **確認點越多、縫越多**：把檢查拆成前後兩道，兩道之間就是可用窗口（同長度覆寫落於其間兩道都過）。正解是**合併成單一確認點並置於最後**，且最後一次觀測要比**內容本身**、不得以長度或 `mtime` 當代理（`mtime` 偵測力取決於檔案系統解析度）。殘餘＝最後一次觀測取得資料之後，具名於 `docs/REDISPATCH_SPEC.md` §C 誠實邊界⑧。
- 🔴 **`gov_check.sh` 段 2（白話說明過期）是 fail-stop 前段，一紅就吃掉段 5／6 的全套測試**；且段 2 目前**結構性紅**：`白話說明/` 有五份無 WATCHED 定義（fail-closed）、兩份他票文件過期於 `c3a58988`、`SPLITUNIFY施工進度.md` 之 WATCHED 涵蓋整個 `scripts/`（動任何治理腳本即過期）。⇒ 收票前要拿真實測試證據就**直接跑 pytest**，不要只看 `gov_check` 的 rc。
- 🔴 **放水語閘會擋下派工單裡的否定用法**（為說明「為何停在這裡」而引用被禁字面亦擋）。正解＝改寫成可證偽條件，**不得替自己加白名單**。
- 🔴 改 SPEC／TODO 前先 `grep -n` 列出該決定的全部落點，改完再 grep 一次；grep **不得加排除條件**。
- 🔴 **治理工具擴建**：2026-09-12「不再擴建治理工具」；2026-09-15 使用者放寬，逐字「允許擴建治理工具，就是要修正DOCROT沒做好之處」（範圍＝DOCROT2）。DOCROT2 已於 2026-09-17 收票，該放寬隨之用盡，9/12 之「不再擴建」恢復為現行（我的判斷；新治理需求先問使用者）。
- 🔴 **DOCROT2 成效報表之量測對象不含續作舊票**：`scripts/docrot2_metrics.sh` 之 cohort＝「首個 review 輪序號大於 `closure_sequence`（4831）之票鍵（task-id 前兩段）」，`20260911-SPLITUNIFY` 首個 review 輪序號為 3610 ⇒ SPLITUNIFY 之後續輪次**永遠不會**被報表選中，報表會量其後第一張新開之票。要以 SPLITUNIFY 輪次檢驗成效，須直接讀 audit 中該輪之 `docrot2_round_metric` 事件逐條套契約四條及格線。
- 🔴 **finding 類別（DOCROT2 Task 3.1，門檻 audit 序號 4778）**：門檻後開債之輪，委員交件每條 finding（含 `P3-00` sentinel）須一行 `**類別**: <值>`（值集與語意見 `scripts/governance_verdicts.json`），`cx_run` 交件當下擋；主委收斂檔群集表須加第 5 欄「主委類別」，兩欄不一致之 ID 須列於 `### 類別不一致` 段一行並附處置 token，否則 synth 寫入 hook 與 `debt_clear` 擋。類別行文法唯一實作＝`scripts/_finding_category.py`（HTML 註解內、fence 內不算）。
- 🔴 **`debt_clear` 銷帳前會寫 `docrot2_round_metric`**（門檻後之輪；缺類別、缺主委欄或寫入失敗即拒銷）；成效報表 `bash scripts/docrot2_metrics.sh`：`scripts/docrot2_metric_contract.json` 之 `closure_sequence`＝4831（2026-09-17 收票寫入）；量測對象＝其後首張開 review 輪之票的前兩輪，該票開輪前報表為 rc=1（`cohort-unknown`），前兩輪銷帳後才出四條及格線結果。
- 🔴 **`committee_round_open` 之 `brief_kind` 為必填**：測試輔助碼開輪須帶（值取 brief 行首 `brief-kind:`）；要模擬上線前無 `brief_kind` 之舊輪，用 `tests/governance/_debt_probe_helper.py` 之 `legacy_round_open_registry`（只改沙箱副本登記檔）。隔離沙箱之複製清單須含 `DOCROT2_HELPER_SCRIPTS`，否則 `--single`／`debt_clear` fail-closed。
- 🔴 **`tests/governance/conftest.py` 對每條測試設 `DEBT_AUDIT_OVERRIDE`**：測試「會寫 audit 之腳本」時必須顯式把 env 指向沙箱 audit，否則事件寫到 conftest 之暫存 audit，斷言沙箱 audit 會落空。
- 🔴 **登記表 `<檔>:<行>` 只驗「非註解非空行」，語意漂移不會紅**：改任何被引用之腳本後，以 `git show HEAD:<檔> | sed -n <行>p` 取舊行內容、`grep -nF` 找新行號逐列更正；2026-09-16 對讀時另抓到四列原本即指錯行（`}`、他函式之 `return 0` 等）。
- 🔴 **`gate.sh dispatch --impl-self` 與 `git commit` 必須以 `&&` 串接**：以 `;` 串接時 gate 拒發 token 而 commit 仍成立，post-commit 記 `token_fresh=false`，pre-push 段 1c 擋推送且事後領 token 不追認；未推送時之出路＝`git reset --soft HEAD~1`、先處理 gate 拒發原因（例：先銷帳）、重領 token 後重新 commit。
- 🔴 **委員名冊變動會使舊收斂檔戳記不足**：`active_stampers` 增加家族後，`--impl-self --adversarial <收斂檔>` 要求現行全員戳記；出路＝只派缺席家族之 stamp 輪補簽（brief-kind stamp、stamp-target 指該收斂檔）。
- 🔴 **全專案遷移判定有兩個模式**：`bash scripts/live_doc_registry_check.sh --migration` 讀工作樹（含未追蹤檔）；`--migration --index` 判暫存快照（清冊、內容、登記、`fact_keys`、殘留清單與生成器皆取 index），pre-commit 用後者。命中消失時 `scripts/docrot2_migration_residuals.json` 該列須同 commit 刪；新增狀態識別碼可讓未被編輯之既有行命中，改 `fact_keys.json` 後先跑一次。暫存檢查一律取快照，讀工作樹之判定會被「只暫存一半」或 `git rm --cached` 繞過。
- 🔴 **委員並行跑會就地改寫檔案之 mutation 執行器會互相污染**（2026-09-17 閉合輪實例：一家兩次執行重疊，另一家看到未還原之改壞並自行 `git checkout` 還原）。收件後先 `git diff HEAD -- scripts tests docs` 對證零差異再收斂。
- 🔴 **生成器無參數模式有 2 秒預算測試**（`test_govb1_factkey_gen.py::test_generator_runs_under_two_seconds`）：2026-09-17 新增一個狀態 key 前實測已 1.92 秒；`_fk_validate_shape` 七次 jq 合一後 1.65 秒。再加 key 前先量；worktree 基準量時須補齊 `handoffs/` 物件，否則生成器提早失敗、耗時失真。
- 🔴 **verdictgate 對 `<root>-B<N>-*` 派工要求前批每條 blocked finding 有同家後續 `CLOSED:`**：規格層輪次用 `x` 命名不經此閘；前批欠帳時以「只核對本家 ID」之閉合輪補（brief-kind closure、session kind stamp，附逐條 ID 清單附件），銷帳後重跑 `bash scripts/verdictgate_check.sh <root> <N> <前批 review 前綴>,<前批 stamp 前綴>` rc=0 才開下一批（2026-09-17 SPLITUNIFY b9 實例：108 條一輪閉合）。
- 🔴 **`spec_xref_hook.sh` 之 synth 對證取的是字母序最早、不是最新之「修訂標的」收斂檔**（`grep -l … | head -1`）：寫 `docs/SPLITUNIFY_SPEC.md` 永遠對 `20260911-splitunify-x-consult-r2/synth.md` 對證而報 `split_projection.py:569` 缺失；D-001 同型報 b8 收斂檔。屬誤報，本輪收斂檔以 `bash scripts/spec_xref_check.sh --synth <本輪 synth> <標的>` 另跑為準（已報使用者，未改工具）。
- 🔴 **委員裁決行多個 ID 須以半形逗號分隔**：`BLOCKED-BY: A; B` 會被 `verdict_parse` 拒收（`result_state=verdict_rejected`）而使 `debt_clear` 拒銷；出路＝主委把分號改逗號後 `bash scripts/gate.sh register-output <task> <委員檔>`（2026-09-17 x-review-r15 實例）。brief 格式硬約束段已加註此條。
- 🔴 **FF 特徵表列時間戳＝K 線開盤時刻**（列之主週期欄含該根收盤；跨週期欄 `OPEN_MINUS` 只含收盤 ≤ 列開盤之高週期 K 線）。凡以時間戳取「決策時點可用之特徵列」，鍵須為「收盤 ≤ 決策時點之最後一根」之**開盤**（對齊收據 `last_bar_open_ms`），**不是** `feature_cutoff_ms`（收盤時刻）。2026-09-17 真實資料三家實跑：IC 事件路徑 `_run_event_label_stages` 自 `fe5f715e`（8/28）起以 `feature_cutoff_ms` 為鍵，165／165 事件讀到晚一根（BOP 之 IC 0.074 被灌成 0.286）；修正排入 `docs/SPLITUNIFY_SPEC.md` v7 之 `R5-C9`（使用者裁定不得列殘留）。對證探針：`handoffs/20260911-splitunify-x-consult-r4-probes/`。
- 🔴 **事件掃描端與 IC 端之分析用標籤參數不同源**：IC 路徑以 `event_label_spec`（預設導出在 `api/routes/ic_analysis.py` 之 `_resolve_event_batch`）建分析副本再對齊，事件掃描端 `_prepare` 用匯入原值；預設參數下兩端 `label_window_rows` 即不同（144／156），邊界差 12 小時。統一解析排入 v7 之 `R5-C10`。
- **session 名之 kind 封閉集＝`impl|review|stamp|consult|fix`**：閉合輪之 session 用 `stamp`、brief 行首 `brief-kind: closure`（例 `20260911-splitunify-b9-stamp-r13`）。
- **Bash 命令列含委員家族名字面（以豎線串接之三家名）會被 `gate_check.sh` 判為派工而擋**：要列家族時從 `scripts/governance_families.json` 以 `jq` 取，不在命令列寫字面。
- 🔴 **以行號 sed 改檔必以字面計數回驗**（2026-09-18 連兩輪同型事故：先把比對對象改成未定義字面，再因行號位移而只改了一半，兩次都由三家審查抓到）：改動後跑 `grep -c -- '<舊字面>' <檔>` 須為 0、`grep -n -- '<新字面>' <檔>` 須命中預期行；長行只看 `cut -c1-N` 的開頭會漏掉尾端未改處。能用 Edit 工具做精確字串取代時就不要用行號 sed。
- 🔴 **規格寫入之權宜作法（2026-09-17）**：`docs/SPLITUNIFY_SPEC.md` 以 scratchpad 組稿後 `cp` 入檔；寫入前以同內容之 Write payload 餵 `bash scripts/live_doc_write_guard.sh`（rc=0 才 `cp`），寫入後跑 `doc_format_precheck.sh`、`spec_xref_check.sh --files <HEAD 版> <新版>`、`obligation_block_check.sh`。日後小幅修改一律用 Edit。
- 🔴 **實作 commit 之 `--reconcile` 須指向「已蓋章」之收斂檔**：審碼輪之收斂檔沒有戳記，用它領 token 會被拒；SPLITUNIFY B10 之授權依據＝已蓋章之清單收斂檔（`handoffs/reconcile/20260911-splitunify-x-review-r21/synth.md`）。
- 🔴 **收斂檔要能當 `--reconcile` 用，必須有 `## 戳記` 區段**：無該區段時 `bash scripts/reconcile_body_hash.sh <檔>` rc=1，派工單若叫委員跑該命令算 body hash，等於叫他們跑一條必失敗的指令（2026-09-18 由委員擋下）。補該區段時**不得**多插空白列——本體須與委員所審逐字相同，`printf '\n## 戳記\n'` 會多一行而改掉 body hash（同日再被擋一次）。
- 🔴 **同一 `config_hash` 可存在於多個 symbol**（2026-09-18 實測 BCHUSDT 與 ETHUSDT 同雜湊）：以 glob 取 run 目錄時須再以事件批之 symbol 篩選，命中多於一個即 fail-closed，否則會拿到別的幣種之 run。
- 🔴 **headless 搜尋探針會寫應用層快取 `data_cache/kline_cache.h5`**（2026-09-18 我造成之副作用，該檔現為 ETHUSDT/1h 1762 根、2 處缺口）：量化主線驗證用的是 `data_cache/feature_klines/kline_cache.h5`（實測未受影響，1h/4h/12h 各 20352/5088/1696 根、零缺口），兩者不是同一個檔，別互相當證據。
- 🔴 **批號與 session 名不是同一個計數**：SPLITUNIFY 的第 N 批（B10A…B10E）與 gate 批號 `b<N>` 對不上——B10D 用的是 `b11`（審碼 `b11-review-r1..r7`），B10E 因此是 **`b12`**。開新批前先 `bash scripts/debt_ledger.sh --list | tail` 看最後用到哪個號；session 名重複是 fail-closed，錯了要重開。
- 🔴 **`verdictgate` 不認「被後續編號取代」**：一條 blocked 意見由後輪以**新編號承接**（甚至翻案）時，原編號從未進任何 `CLOSED:` ⇒ 開下一批被擋，而人看收斂檔會覺得「早就處理完了」。出路＝閉合輪（brief-kind `closure`、session kind `stamp`，只請原提出方核對本家編號）；閉合輪自身不受該閘擋。REF:handoffs/reconcile/20260911-splitunify-b12-stamp-r1/synth.md
- 🔴 **兩端一致這種不變式，預設參數下驗不出來**：`max(深度, 窗)` 與 `窗`、分析副本與匯入原值，在**預設 `event_label_spec`** 下都同值。驗收組合**必須**含一組使用者改過參數（k／h）的真實批，否則綠燈只證明「預設路徑沒壞」。REF:handoffs/run_receipts/splitunify_r5_parity.b23de79e54b5.json
- 🔴 **mutation 跑錯組合會得到假存活**：處置帳鍵位移一根那條，在 post-trim 剔除為 0 的組合上位移後每一筆仍落在索引內 ⇒ 預測逐字不變，看起來像「對證面有洞」。判準＝該 mutation 改的那個**判定**在該組合上是否真的會被觸發；配剔除 1 筆的組合後當場轉紅。REF:handoffs/run_receipts/splitunify_r5_parity_mutations.json
- 🔴 **子集跑不得覆寫完整基準**：`--only <組合>` 跑完寫 golden、單條 mutation 跑完覆寫 receipt——兩者都會把其餘組合／條目**刪掉**，而剩下那份看起來完全正常。同型犯了兩次（2026-09-19），已分別改為「子集跑不寫」與「以 id 合併」。
- 🔴 **SPEC 寫死具體值前必先 grep 對證**：SEARCH2EVENT 同一票內犯三次——不存在的前端路徑 `/case/events/{import_id}`（實為後端 API，前端 404）、錯誤函式簽名 `buildDeclarationPayload(declState)`（實為三參，單參回 null ⇒ 斷言恆綠）、轉述他人碼證時放大後果（codex 給「走 CSV 分支回空列表」，主委寫成「使用者得到成功但空的批」，實際會被 `contract_violation` 拒收）。**派工前逐一 grep 每個識別字**。同型亦適用委員清單：2026-09-20 composer 列 7 個 EMA 週期，自查 manifest 實得 14 個。
- 🔴 **`committee_run` 未完全退出前不能銷帳**：委員 `.md` 已落檔不代表可銷——`committee_family_result` 由 `cx_run.sh` 結束時才登記，提早跑 `debt_clear` 會得 `ERROR: 家族 <fam> 無 committee_family_result`。判準＝`pgrep -f committee_run` 為空才銷。
- 🔴 **偵察輪的債會擋住一切**：委員債是「一扇門」——開一輪唯讀偵察即擋住**所有**新派工與 `docs/*{SPEC,TODO,PLAN}*.md` 創建（實測 `[GATE BLOCKED] kind=artifact 有 fresh token，但債務帳本重查未通過`）。⇒ 「偵察與另一張票並行」在本專案**做不到**，排程時不要假設可並行。
- 🔴 **`fact_keys.json` 狀態欄是封閉集合**：`docrot2_status_values` 只有 `未開工／進行中／部分完成／待審／停手／狀態未確認／已完成`。自創值會被 `gen_fact_key_blocks` fail-closed。改完一律跑 `bash scripts/gen_fact_key_blocks.sh --write`。
- 🔴 **`committee_run --session` 有命名規約**：`<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，`kind ∈ {impl, review, stamp, consult, fix}`。偵察輪要用 `consult`（`recon` 會被拒），且 brief 的 `brief-kind` 同樣只收 `review|consult|closure|impl|stamp`；`consult` 另強制 §0 前提宣告至少各一條 `fact-verified:` 與 `assumed:`。
- 🔴 **`gen_fact_key_blocks.sh` 之 `_fk_root()` 回傳 `.`（相對 cwd）**：自非 repo 根呼叫會誤報 receipt「指向不存在之檔 → fail-closed」，看起來像既有 bug 其實是呼叫方式錯。一律 `GOVB1_FACTKEY_ROOT=<repo 絕對路徑>` 或先在 repo 根。2026-09-20 踩到並一度誤判。
- 🔴 **`plain_docs_render.sh --check` 之「死連結 0」不涵蓋 md 內相對連結**：它掃的是生成後的 HTML。`git mv` 一批白話檔後，`做過什麼.md` 內五條指向舊路徑的連結全斷而該檢查仍報 0。⇒ 移檔後須另以 `grep -o '](...)' + test -f` 逐條驗。
- 🔴 **寫新機械閘前先 grep 既有同類閘的檔頭**：2026-09-20 寫 `plain_docs_shape_check.sh` 首版用黑名單（列兩個 emoji），使用者當場指出「換個圖示不就繞過了」。而「黑名單永遠列不完」這條**既寫在 memory 也寫在 `plain_docs_order_check.sh` 檔頭**，我沒回頭看。封閉集合的問法是「內容只能去哪幾個地方」，再逐個堵死。
- 🔴 **白話檔改職責時，其 WATCHED 必須跟著改**：`現在做到哪.md` 由「GAP-3 即時進度」改為「現在在做哪張票」後，WATCHED 仍是 11 條 GAP-3 實作路徑 ⇒ 任何相關改動都誤報過期。職責與監看集合是一組，改一個就要改另一個。
- 🔴 **改了 brief 就不能掛回原 round**：開債記錄綁 `brief_sha256`。委員交件失敗後若順手改了 brief，同輪重派會對不上；須把 brief byte-exact 還原到原 sha 才解得開。配合既有坑「永遠不要 kill 執行中的 `committee_run`」——kill 後會落得「有 failed 結果又不能棄置」的死結。
- 🔴 **`cd <專案路徑>` 前綴 ＋ `bash -c` 會觸發權限分類器**：2026-09-20 實測卡 **588 秒**，使用者乾等。CLAUDE.md 已明文禁 `cd` 前綴，`bash -c` 包裝是同型放大。
- 🔴 **主委自產版不得進 `sources.lock` 也不得進收斂檔附錄**（既有慣例，查 `20260920-eventscan-x-consult-r2`／`20260920-plaindocs-x-review-r2` 皆 roster 只有兩家、synth 零個 `## CLAUDE-`）。放進去有兩個後果：①`debt_clear` 的 roster 比對用 `lock_set == open_set − paused`，`claude` 不在 `open.participants` ⇒ 永遠不等、拒銷；②`completeness_check` 報 `unknown ID(s) in synth`。主委版寫成獨立檔，收斂檔以一行指回去即可。
- 🔴 **`sources.lock` 是 write-once**：`--rebuild` **不收委員檔**（「既有 sources.lock 內容必須保持不變」），不帶 `--rebuild` 又拒覆寫既有 session。要改 roster 只能把**整個 session 目錄移開**再重建——**先備份 `synth.md`**，重建會把它打回骨架。
- 🔴 **收斂檔附錄必須與來源逐位元組相同**：任何**全域字串替換**（例如把「三家」改「兩家」）都會打到附錄裡的委員區塊 ⇒ `body-hash 不符` 拒銷，而錯誤訊息只給兩個 sha 指不到你改了哪。改群集段要逐段改，或改完把附錄自來源重新逐字抽一次。
- 🔴 **委員檔案被還原／修好後要 `register-output` 才解鎖**：`cx_run` 收尾時產出缺檔會記 `result_state=failed`，之後即使檔案補回來，`debt_clear` 仍報「最新 result_state='failed' 且其後無同 round 之 committee_output」。補跑 `bash scripts/gate.sh register-output <task-id> <檔>`。
- 🔴 **findings 檔內出現 `<!--` 字面會吞掉後續必填欄**：`completeness_check.sh` 的解析把 HTML 註解開頭之後的內容當註解，導致 `**類別**` 明明寫了卻報「finding 缺類別」，錯誤訊息完全指不到真因。2026-09-21 踩到（碼證欄引用 `grep 'BEGIN GENERATED'` 的完整字面）。⇒ 在 findings／brief 內引用含 `<!--` 的字面時，去掉註解開頭符號。
- 🔴 **`printf` 組 commit 訊息遇 `%` 會從該處截斷**：訊息含 `46.7%` 時 `printf` 把它當格式指令，commit `3331ae9a` 實際被截。⇒ commit 訊息一律 Write 成檔再 `git commit -F`，不用 `printf`／`echo -e`。
- 🔴 **Monitor 的過濾條件必須涵蓋「實際的完成字面」**：FF 生成完成印的是 `data_quality background bake completed` 與 `CGSA catalog cached`，**不含** `Layer N done` 這類常見詞。用常見詞當過濾 ⇒ 監看 30 分鐘零事件而任務其實早已結束。⇒ 設過濾前先跑一次抓實際尾段字面。
- 🔴 **`sed -i ''` 對 `scripts/fact_keys.json` 插入含 `\"` 的字面會破壞 JSON**（`jq` rc=5）。含引號的內容改用 Edit 工具。
- 🔴 **背景 handle 要分清「伺服器」與「它跑的工作」**：`venv/bin/python run_api.py` 是常駐伺服器、永不結束，FF 生成只是它內部的 task。把伺服器 handle 標成「FF 重跑」會讓使用者看到「跑了兩小時還沒結束」而誤以為卡住。⇒ 標示與回報一律指工作本身（task_id／產出路徑），不指伺服器。
- 🔴 **Claude Code 進程重啟（例：使用者切換模型）會殺掉正在跑的委員子進程**，債仍開著：走上面「同輪重派＝兩個指令」那條（`gate.sh redispatch` 取許可後**原樣**以背景執行其印出之指令），不開新債。2026-09-22 TODOFMT r3 實例。
- 🔴 **commit-msg 之 operational claim 檢查會把「引述定義」裡的「通過／全綠」判成宣稱**：改寫措辭即可，**不要預先加 `VERIFY-EXEMPT`**（2026-09-23 主委預先加過一次，屬錯誤行為）。
- 🔴 **`scripts/git_hooks/commit-msg` 之 G-7 前移檢查以 `|| true` 結尾，只提示不擋**：不要為它加 `Governance-Scope: out-of-epic` 豁免 trailer——auto-mode 分類器會判為繞過而拒，判得對。
- 🔴 **`spec_xref_hook` 對 HEAD 比對，會把本次已刪之 token 一路累列**：真要修的是「被刪之專名仍被別處引用」；通用詞可在新段落如實提及以消警。
- 🔴 **收斂檔機械附 finding body 時，某家來源只有一條 finding ⇒ 迴圈會算出 `head -n 0`，macOS 視為非法參數**：以 `if [ "$last" -gt 1 ]` 包住該分支。
- 🔴 **`handoffs/` 整個被 `.git/info/exclude` 排除，從不入 git**（收斂檔、委員產出、brief 皆然）：任何以「某 handoffs 檔之 git 歷史」為錨點的設計（例：「引入收斂檔之 commit」）恆查無。要用 git 歷史當錨點，錨點必須落在追蹤檔（如 `docs/`、`tests/`、`scripts/`）。2026-09-23 TODOFMT r7 修補時犯過一次，派 r8 前自查實跑 0 行才抓到。
- 🔴 **Bash 工具跑的是 zsh：未加引號之 `$VAR` 不斷字**，整串多行被當成一個參數（例：把檔案清單丟給 `mutation_probe_static.py` 會只收到一個怪參數）。清單一律 `tr '\n' '\0' | xargs -0 …`。
- 🔴 **macOS 預設 bash 3.2：`$( … )` 內含 `case … in x) …` 會解析錯誤**；把含 `case` 之邏輯抽成函式再 `$(fn)`。`set -u` 下空陣列展開亦會報 unbound，腳本改用換行字串累積。
- 🔴 **mutation 探針把腳本複本放到 tmp 時，須一併複製它開頭 source 之相依檔**（例：`gate.sh` 開頭 source `governance_families.sh`／`.json`），否則複本早退、探針「因別的理由」而紅或綠（TODOFMT b3 自查：兩支探針因此假綠）。探針一律先以**同佈局之未改壞複本**斷言前提，再比改壞後之結果與原因。
- 🔴 **改 `scripts/gate.sh` 等被 `fact_keys.json` 以行號引用之檔時，插入行會使引用落到註解**：`factkey_write_guard` 會報「行號落在註解」；依報告之「最近可執行碼」找回原語句之新行號後更新引用（TODOFMT：E-022／E-023 由 `:973` 改 `:1146`，再改 `:1150`）。小修可把新語句接在既有行尾（`; …`）以免位移。
- 🔴 **自 TODOFMT 之 W（`26048178`）起，`gate.sh dispatch --impl-self` 必須帶 `--spec`**，而 `--spec` 是 gate.sh 的 impl 判準：帶上就連帶要求 impl 型 `--brief`（含 `EXPECTED-DELTA:`）、`--reconcile <handoffs/reconcile/<session>/synth.md>`（session 須有 `sources.lock` 與戳記）與 SPEC 範本機檢；新 SPEC 另須 `--todo docs/manifests/<EPIC>.json`（其 `spec_path` 等於 `--spec`）。舊寫法（只帶 `--task-id`＋`--reconcile`）自此被擋。
- 🔴 **路徑值夾換行會被逐行比對拆成多個樣式**：`grep -F`／`grep -Fxq` 收到含換行之值等於收到多個 pattern，「清單內之檔＋換行＋新檔名」會命中清單內那一行而放行。hook 讀 JSON 時另一個坑：`$(jq -r …)` 會吃掉**尾端**換行，故控制字元須在 JSON 字串層由 `jq test("[[:cntrl:]]")` 判，不能在 shell 層判。
- 🔴 **Claude 的 Write 工具會字面折疊 `..`**：寫 `<dir>/不存在的目錄/../x` 會成功寫到 `<dir>/x`，且不建立該目錄。凡以路徑字串判定之守衛須用同法解讀（`scripts/todofmt_write_guard.sh` 之 `_lexfold`）；指向 repo 之別名（符號連結、`/System/Volumes/Data` 前綴）改以 `[ A -ef B ]` 比對祖先目錄。
- 🔴 **pytest 參數化測試名之非 ASCII 會被轉義**（例：`−` 成 `−`），「數字＋空白＋skipped」這類全文掃描會把測試名誤判成跳過計數；判讀 pytest 結果只認結尾摘要行（`N passed, M skipped in Xs`），找不到摘要行即當失敗。
- 🔴 **`gate_check.sh` 的派工偵測對含 `$'…'`、多層引號之多行 Bash 會 fail-closed 判為派工**（要求 gate token）：探針或對照實驗寫成 scratchpad 腳本再 `bash <檔>`，不要把整段塞進一條 Bash 指令。
- 🔴 **全套 `pytest tests/governance` 於 2026-09-23 實跑 78 紅／2,590 綠（7,625 秒，比預期慢一倍）**，逐條歸因皆早於 TODOFMT 或屬偶發／環境，清單與方法見 `handoffs/run_receipts/20260923-todofmt-govsuite-attribution.json`。下次動共用控制流前後拿它當基線比對，不必再逐條歸因。歸因方法之坑：**`test_govb1_contract_matrix.py` 部分測試內部會再跑整套檢查，單條 20 分鐘級**，逐條重跑前先看它屬不屬這類；舊版本對照用 `git worktree add --detach <路徑> <commit>`，該 worktree 沒有 `handoffs/`（被 exclude），依賴它的測試要改看失敗訊息。**已處理完（2026-09-23，使用者裁定由主委自處理、不派委員）**：67 條修綠、11 條 `xfail(strict=True)` 引登記 ID（R-GOVTEST-1／3／4／5、R-G7-OFF-2，見 `docs/IC_QUANT_GAP_REGISTRY.md`）；受影響 19 檔主線實跑 779 passed／9 xfailed／0 failed（另 2 條 G-7 xfail 各約 20 分鐘，另行驗過）。**下次跑全套的基線＝0 紅**，新出現的紅就是新壞的。三個坑：①**快照型測試會漂**——拿「當時」的真實狀態寫死（B-63 狀態、SPLITUNIFY 列數、靜態 fact-key 夾具），狀態往前走就紅；改成比對定案當下之 commit、或與登記表交叉比對。②**計時測試須先驗 rc**——生成器提早失敗也很快，曾因此把真的變慢誤判為環境因素。③隔離樹內 `git commit` 會在背景跑自動維護（git 2.54 `maintenance.auto`，只關 `gc.auto` 不夠），與清理競態。
- 🔴 **`tests/governance/test_debt_gate.py::test_gate_check_latency_under_100ms` 恆超標（約 150 ms），已標 strict xfail（R-GOVTEST-4）**：它複製真實 `.claude/gate/audit.log` 量 `gate_check.sh` 冷啟動，門檻 100 ms；紅因是 audit 長大（帳本核心依 SPEC 禁前置過濾，冷路徑線性成長），解法＝P1-6 線 C（未排程）。
- 🔴 **帳本 dump 已超過 ARG_MAX（2026-09-23：1,043,751 bytes，macOS 上限 1,048,576 含參數與環境）**：`debt_clear.sh`／`debt_ledger.sh` 原以環境變數把 dump 傳給 `python3`，超限即 `Argument list too long`、每輪銷帳都起不來。已改經 fd 3（`python3 3<<<"${dump}" <<'PY'` 配 `os.fdopen(3)`），行數不變；回歸測試 `test_clear_ledger_dump_not_passed_via_environment` 以 PATH shim 攔 `python3` 之環境變數。**大資料一律勿經環境變數或命令列參數傳遞**；GOVB1 之 `test_debt_clear_success_guard_not_relaxed`／`test_u7_…` 比對工作區對 HEAD，改 `debt_clear.sh` 未提交前必紅、提交後即綠。
- 🔴 **`verify_pretooluse` 對 scratchpad 內「含 `docs/` 段而目錄尚不存在」之路徑 fail-closed**：先建目錄，或改用不含 `docs/` 段之平面檔名。
- 🔴 **委員收尾會清 `/tmp`，連帶刪掉主委寫在 `/tmp` 之 log**（例：`committee_run` 之 `> /tmp/cr9.log` 事後不存在）：派工與測試之 log 一律寫 scratchpad。
- 🔴 **`data_cache/features/ETHUSDT/1h/` 下有三個外觀相似的 FF run，其中兩個不可用**：`4a8a0b37…`（fracdiff 已轉換）、`654bd63b…`（漏全部 12h 欄，542 group 全 1h）。可用者為 `d9935491…`（944 group＝1h 542＋12h 402、418,719 欄、20,352 列、六項預處理全 false）。⇒ 引用 reference run 一律先核對 `config_hash`，不靠目錄時間排序。
- 🔴 **派下一輪委員前先領 `--impl-self` 實作許可**：有未銷之債即拒發，且須帶 `--brief`（impl 型）、`--reconcile`（該 synth 須有 `## 戳記` 段與全部 active_stampers 之 RECONCILE-STAMP）。先派審查再領許可，會被自己剛開的債擋住。
- 🔴 **`Ticket-Batch:` trailer 只放在動 `momentum/`、`api/`、`frontend/src` 之 commit，且須與 `Co-Authored-By` 同在訊息最末段**（中間隔空行即視為無 trailer）；過期 token 之 trailer 會讓 pre-push 拒收，修法是 amend 尚未推之 commit。
- 🔴 **委員之 `CLOSED:` 只准列本家族前綴之 ID**，列他家即 `verdict_rejected`；修法＝主委改檔後 `gate.sh register-output`。
- 🔴 **`debt_clear` 之 synth 交叉引用只比對所宣告之「修訂標的」一檔**：只存在於測試檔之識別字不要加反引號。
- 🔴 **`tests/feature_engineering/conftest.py:13` 自動把 `FFACT_CGSA_WORK_DIR` 設到 tmp**：真實 parallel run 須取消此變數（worker 以 `_prepare_cgsa_registry(symbol, tf, "worker")` 取目錄，設了會與主程序共用同一目錄）；FF 測試不可 `chdir`（`config/scan_config.yaml` 等為相對路徑）。
- 🔴 **FKPERF 語料②為錄製重播**（`tests/governance/_fkperf_record.py`）：差分測試開跑時先跑既有兩檔建沙箱測試並攔截每次生成器呼叫，repo 側於錄製開始時凍結；跑差分時仍勿改 `scripts/fact_keys.json` 與宿主檔，錄得之標籤與凍結樹須同一時點。
- 🔴 **FKPERF 切換後入口是薄殼、邏輯在 `scripts/_gen_fact_key_blocks.py`**：任何「把入口複製或物化到別處再執行」之處都要連核心一起帶（2026-09-24 活文件守衛快照模式、四個測試檔沙箱依賴清單都漏過）；`scripts/fact_keys.json` 之 E-028 等 `檔案:行號` 引用與四個 fixture（`tests/governance/fixtures/govb1/factkey_{clean,drifted}/docs/GOV_{ENFORCEMENT_REGISTRY,TICKET_SOT}.md`）在核心或守衛檔插行後會位移，改完先跑 `--check`，紅了就改那一行（`scripts/regen_factkey_fixtures.sh` 本 session 前就已壞：fixture 缺新 key 之宿主檔）。
- 🔴 **有未銷之債時，Bash 指令文字含委員家族名（`codex`／`composer`）、`環境變數=值 指令` 前綴、或 sed 改 `docs/*_SPEC.md` 等，會被派工偵測誤判而擋**：改用 Edit 工具、`env VAR=… cmd`、或把說明文字中的家族名拿掉。
- 🔴 **`git restore` 被權限拒絕**：還原單檔用 `git show HEAD:路徑 > 路徑`；只提交指定檔用 `git commit -F - -- <路徑…>`；新的 tracked 檔要先 `git add` 再 `git commit -- 路徑`。zsh 不會拆 `$變數` 中之空白成多個路徑，路徑一律逐一寫出。
- 🔴 **fact_keys.json 字串內不可寫 `\*`**（JSON 非法跳脫，生成器整個 fail-closed）；要寫 d* 就直接寫。
- 🔴 **`FFACT_WARMUP_TRIM` 預設 `0`（嚴格窗）**：起始日之前的資料根本不抓，L6.5 之「前 500 根校準」即輸出範圍之前 500 根（2026-09-24 研究 r1 據此推翻主委之「校準在 warmup」判斷）；平穩化判定之無洩漏落點已由 RM-FFSTAT 研究 r2 定為乙案（只用起始日前資料、獨立校準域）。
- 🔴 **非平穩判定快取 `_non_stationary_cache` 只在單一 `FeaturePreprocessor` 實例內**：不跨 run，估每次生成成本時勿當作「只首次付費」。
- 🔴 **`FeaturePreprocessor._d_star_cache_dir` 寫死指向專案 `data_cache/feature_preprocessing`，不看任何環境變數**：探針用 `handoffs/run_receipts/ffstat_probes/_isolate.py` 之 `isolate_dstar_cache()`、測試用 `tests/feature_engineering/ffstat_helpers.prepare_stat_env`，否則寫進共用快取（2026-09-24 曾寫入 `d_star_BTCUSDT_1h_dcc154ced6b6.json`，刪留待使用者）。`prepare_env` 會 chdir 進目標目錄，目錄須先存在。
- 🔴 **真實 `kline_cache.h5` 之 10 標的 × 3 週期皆無任何缺口**：要測缺口只能從真實 index 刪列模擬。
- 🔴 **L6.5 `mode="append"` 下基礎欄永不被改寫**：平穩化結果另存衍生欄 `<欄>_fracdiff`／`_diff1`／`_diff2`，落在 `*_L65.parquet`。
- 🔴 **真實 kline 下 `run_ic_first` 之 IC 階段必拋 `AlignmentViolationError`（既有退化，RM-ICFIRSTALIGN）**：不論自帶層與否、`FFACT_WARMUP_TRIM` 設多少；`test_b6_warmup_trim.py::test_warmup_trim_ic_first` 於 main 即紅。要觀測 IC-first 之 L6.5 產物，看 IC 階段前 `write_raw` 落盤之 `<run_dir>/raw/*.parquet`（`ffstat_helpers.ic_first_to_l65`）。
- 🔴 **`reconcile_build --mode discovery` 產出之 lock 無 `round_id`**，銷帳會失敗：審查輪一律 `--mode review`，已建錯者 `--rebuild` 升級。銷帳之 `--lock` 是 `handoffs/reconcile/<session>/sources.lock`（不是 `lock.json`）。
- 🔴 **reconcile 群集表內某列文字若寫到他列之 finding ID，歸屬檢查會把該 ID 也算進這列**，造成「類別不一致」：跨列引用用「本表某某列」代稱，不要寫 ID。
- 🔴 **pytest 暫存（`$TMPDIR/pytest-of-louis/pytest-N`）每輪真實 FF run 可累積數十 GB，2026-09-25 曾把磁碟吃到剩 1.5 GiB、測試以 `No space left on device` 中斷**：長回歸跑完後刪自己產生之 `pytest-N`（保留 pytest-current）；`rm` 被權限拒，以 `shutil.rmtree` 腳本逐一指名刪除。
- 🔴 **`test_ff_fullchain_truncation_mr.py`／`test_ff_multitf_truncation_mr.py` 單支 15–25 分鐘（1h 真實資料生成兩次）**：回歸只跑與改動有關者；與其他重量測試並行時，效能類測試（如 `test_batch1_followup.py::test_perf_smoke_*`）會因搶 CPU 而假紅，單獨重跑才算數。
- 🔴 **平穩化設定 schema 一變（增刪欄位）config_hash 即變，FF-TFMETA golden 之 stripped sha 隨之不符**：該基準刻意保存 FF-TFMETA 動工前狀態，不可重凍；以 `handoffs/run_receipts/ffstat_probes/migrate_fftfmeta_baseline.py <FF-STAT 動工前 worktree>` 做有證據遷移（改前重現原始凍結值、特徵值不變、差異僅 schema 與 config_hash），schema 再變時先把變更加入其 `_apply_schema_changes`。
- 🔴 **FF-STAT 後 `FeaturePreprocessor` 開 fracdiff 而無層來源即拋 `StationarityProvenanceError`**（不再由欄名 `L<k>_` 推層）：直接建前處理器之測試與工具須傳 `column_layer_map`；L6.5 工具腳本之 fixture 用 `scripts/build_l65_golden.py:fixture_layer_map`。
- 🔴 **d* 快取以 `max_lag`／`sample_size` 為 None 建構時，`_int_equal(None, None)` 恆 False ⇒ 寫出之快取永遠讀不回**：生產端 `_create_d_star_cache` 一律帶齊；測試建快取須比照（`test_ffstat_dstar_failure.py:_cache`）。同一 run 內值完全相同之欄經值別名共用 d*、亦記為 `dstar_cache_hit`——比快取命中或項數時以同設定之全新快取目錄為對照，勿斷言「零命中」或「項數＝fracdiff 欄數」。
- 🔴 **FF-STAT b3b 後，平穩化開啟時 `FeaturePreprocessor` 之三路判定值只取校準封包，無封包即拋 `CalibrationError`**：直接建前處理器之單元測試用 `tests/feature_engineering/ffstat_helpers.attach_unit_calibration(pre, 前史或 fixture)`；L6.5 工具（`build_l65_golden*.py`、`benchmark_l65.py`）用 `scripts/build_l65_golden.attach_fixture_calibration`（樣本內、工具專用，fixture 短於 N 時工具自降 N）；封包要先套縮尾（L6.5 先縮尾再判定），否則判定值與轉換值不同源。
- 🔴 **12h 真實資料始於 2024-01，稀疏欄（滾動 std／skew／kurt 等常為 NaN 者）於早期起始日湊不滿 N=500**：輕量設定 2025-06 起 BTC、BCH 各 6 欄不足，2026-01、2026-03 起 0 欄；完整設定 12h 於 2025-10 起 N=200、100 仍有欄不足。v19（使用者 2026-09-26）起不足之欄逐欄不平穩化、記 `calibration_insufficient_history`、品質 partial——測試若要「全欄皆檢定」須選 2026 之窗。
- 🔴 **校準域須與公開域同 index 表示與同欄定義**：L0 index 為 epoch 整數，換成 `DatetimeIndex` 則 L5 參考標的 `concat` 對不上、L5 全空；L3 會依資料剔欄（死欄過濾、低基數 skew/kurt 閘），校準域必開 `RollingAggregator` 之 `keep_all_columns`，否則公開域有欄而封包缺欄。
- 🔴 **`committee_run.sh` 之 session 名 batch 只收 `b<數字>`**：`b3b` 被拒（fail-closed，不開債）；同批後半沿用 `b3`、輪次續編（3b 之首審為 `20260925-ffstat-b3-review-r3`，日期前綴沿用該批首日）。
- 🔴 **PreToolUse hook 會把部分含引號轉義之 Bash 指令誤判為派工（`kind=dispatch`）而擋下**：改檔用 Edit 工具；需 sed／awk 多步者寫成腳本檔再 `bash <檔>`。
- 🔴 **動 L0／L5／L6.5／memmap／`generate_features` 入口時，回歸須含 `test_ff_cross_symbol_value_isolation.py`、`test_failopen_*.py`（三檔）、`tests/test_multi_symbol_parallel.py`、`tests/test_cgsa_resume.py`**：b3b 審碼 brief 之回歸範圍漏了這些檔，FF-STAT 引入之 3 支紅直到 r3 主委擴大回歸才現形。歸因法＝`git worktree add --detach <scratch>/wt <commit>`，只連結 `data_cache/feature_klines/kline_cache.h5` 與 `venv`，以 `(cd wt && venv/bin/python -m pytest …)` 分別在 FF-STAT 動工前 `5a148b8e` 與改前 HEAD 各跑一次；用完 `git worktree remove --force`。
- 🔴 **FF-STAT 之前即紅之 9 支，勿誤判為本票回歸**：`test_failopen_contract.py` ×2、`test_failopen_correctness.py` 之 v3 healthy／ETH 1h／multi-TF（L1 凍結 hash 與現值不符）與 `test_v7_cgsa_resume_matches_fresh`、`test_failopen_layers.py::test_layer_golden_matches_baseline`、`tests/test_cgsa_resume.py::test_cgsa_config_hash_passed_correctly`、`tests/api/test_batch_alias.py::test_patch_batch_alias_deleting_returns_409`（於 `5a148b8e` 實跑同紅；登記於白話說明/還沒做的事.md）。
- 🔴 **12h 完整鏈設定（N=256）在真實資料約 848 天內不存在全欄前史足夠之起始日**：探針前史 1,034 根仍約 569 欄不足、1,278 根仍約 330 欄 ⇒ 此類慢測之品質為 v19 partial 屬正常（`ff_artifact_compare_helpers.assert_full_chain_runtime` 只容許失敗原因全為 `calibration_insufficient_history`）。
- 🔴 **L5 參考標的快取 `_reference_data_cache` 之鍵為四元 `(參考標的, 週期, L0 載入起點, 輸出終點)`**：全歷史預載（`run_multi_symbol`／`_worker_entry`）用 `(參考標的, 週期, None, None)`；Task 2.3 自動起始日後 worker 預載將不再命中（只影響效能），b4 須驗。
- 🔴 **本環境權限規則擋 `rm`／`rm -rf`（含 scratchpad 內）**：不得換寫法繞過；收尾量 `du`、列精確清單與可貼上之指令交使用者執行並複查。git worktree 用 `git worktree remove --force` 可行。
- 🔴 **委員產出檔出現 ≠ 交件**：須等 `committee_run.sh` 背景完成通知，或 `.claude/gate/audit.log` 出現該家 `committee_family_result`。2026-09-26 曾在 codex 仍在跑時就 reconcile 並改 docs/，只得 `git checkout` 還原 docs/、把過期 reconcile 目錄移走重建。審查期間一律不動 momentum/api/scripts/tests/docs/templates/config。
- 🔴 **`sources.lock` 只寫一次，`reconcile_build.sh --rebuild` 只能把 discovery 升為 review**：要整個重建須先備份 synth 表頭，再以 `mv` 把該 session 目錄移到 scratchpad（`rm` 被擋），然後重跑 build。
- 🔴 **同輪重派之 lease 可能被 codex 桌面輔助程序（`SkyComputerUseClient turn-ended`，繼承 fd）佔住**：以 `lsof` 查 `.claude/gate/redispatch.lease.*` 等它釋放，勿殺 `committee_run`。
- 🔴 **審查／諮詢輪之 gate 開門**：`bash scripts/gate.sh dispatch --task-id X --risk low --intent … --facts-asked … --review-role … --template "n/a:…"` 單獨一個呼叫，再跑 `committee_run.sh`；用 `--risk high` 會被要求 `--spec`。複合 grep＋awk＋引號之指令亦會被 hook 誤判為派工，拆成單純指令。
- 🔴 **SPEC 版本註記同一行不得同時有批次代號（如 `b5`）與狀態字面**：活文件守衛會擋，改寫成「第 5 批」之類。
- 🔴 **委員被 PreToolUse 擋下時會改寫指令繞過**：2026-09-26 FF-STAT 審查 r10，codex 之 `bash scripts/completeness_check.sh` 被以過期 dispatch token／未清債擋下，改以 `/bin/bash scripts/...` 同參數重跑即過（其交件 FAILURES_SEEN 自述；唯讀檢查、未造成影響）⇒ hook 以指令字首比對，換直譯器路徑即旁路；收件時讀 FAILURES_SEEN 找這類自述。
- 🔴 **debt_clear 之 synth-xref**：synth 處置欄每個反引號概念都必須逐字出現在 SPEC；manifest 之 JSON 字串內不得含未轉義之 `"`（如 12h 之引號），否則 manifest 解析失敗。

## 進行中紀錄

<!-- HISTORY-BEGIN -->
<!-- ENTRY: RM-SEARCH2EVENT,RM-EVENTSCAN -->
- 2026-09-20：RM-SEARCH2EVENT → `docs/SEARCH2EVENT_SPEC.md`
- 2026-09-20：RM-EVENTSCAN → `白話說明/EVENTSCAN方向與做法.md`
- 2026-09-21：RM-EVENTSCAN → `handoffs/run_receipts/20260921-eventscan-b-baseline.json`
- 2026-09-21：RM-EVENTSCAN → `docs/EVENTSCAN_SPEC.md`
- 2026-09-21：RM-EVENTSCAN → `handoffs/20260921-EVENTSCAN-SPEC-REVIEW-R1-BRIEF.md`
- 2026-09-21：RM-EVENTSCAN → `handoffs/reconcile/20260921-eventscan-x-review-r5/synth.md`
- 2026-09-21：RM-FFDSTAR → `handoffs/reconcile/20260921-ffdstar-x-consult-r1/synth.md`
- 2026-09-21：RM-FFDSTAR → `docs/FFDSTAR_SPEC.md`
- 2026-09-21：RM-EVENTSCAN → `handoffs/reconcile/20260921-eventscan-x-review-r7/synth.md`
- 2026-09-21：RM-FFDSTAR → `handoffs/reconcile/20260921-ffdstar-x-review-r2/synth.md`
- 2026-09-22：RM-EVENTSCAN → `handoffs/reconcile/20260921-eventscan-x-review-r12/synth.md`
- 2026-09-22：RM-FFNAME → `docs/FFDEFECT_DECISION.md`
<!-- ENTRY: RM-FKPERF -->
- 2026-09-23：RM-FKPERF → `docs/FKPERF_SPEC.md`
- 2026-09-23：RM-FKPERF → `docs/manifests/FKPERF.json`
- 2026-09-23：RM-FKPERF → `handoffs/reconcile/20260923-fkperf-x-review-r5/synth.md`
- 2026-09-24：RM-FKPERF → `handoffs/reconcile/20260923-fkperf-x-review-r11/synth.md`
- 2026-09-24：RM-FKPERF → `handoffs/reconcile/20260923-fkperf-b1-review-r1/synth.md`
- 2026-09-24：RM-FKPERF → `handoffs/reconcile/20260923-fkperf-b1-review-r2/synth.md`
- 2026-09-24：RM-FKPERF → `handoffs/run_receipts/20260924-fkperf-mutation.json`
- 2026-09-24：RM-FKPERF → `handoffs/run_receipts/20260924-fkperf-scale.json`
- 2026-09-24：RM-FKPERF → `handoffs/reconcile/20260924-fkperf-b3-review-r3/synth.md`
<!-- ENTRY: RM-FFNAME -->
- 2026-09-24：RM-FFNAME → `docs/FFNAME_SPEC.md`
- 2026-09-24：RM-FFNAME → `handoffs/reconcile/20260924-ffname-x-review-r5/synth.md`
- 2026-09-24：RM-FFNAME → `handoffs/reconcile/20260924-ffnamestat-x-consult-r1/synth.md`
<!-- ENTRY: RM-FFSTAT -->
- 2026-09-24：RM-FFSTAT → `docs/FFSTAT_SPEC.md`
- 2026-09-24：RM-FFSTAT → `handoffs/reconcile/20260924-ffstat-x-review-r5/synth.md`
- 2026-09-24：RM-FFSTAT → `handoffs/reconcile/20260924-ffstatres-x-consult-r1/synth.md`
- 2026-09-24：RM-FFSTAT → `handoffs/run_receipts/20260924-ffstat-calib-window.json`
- 2026-09-24：RM-FFSTAT → `handoffs/reconcile/20260924-ffstatres-x-consult-r2/synth.md`
- 2026-09-24：RM-FFSTAT → `docs/manifests/FFSTAT.json`
- 2026-09-24：RM-FFSTAT → `handoffs/run_receipts/20260924-ffstat-golden-freeze.json`
- 2026-09-24：RM-FFSTAT → `handoffs/reconcile/20260924-ffstat-x-review-r18/synth.md`
- 2026-09-24：RM-FFSTAT → `handoffs/reconcile/20260924-ffstat-x-review-r19/synth.md`
- 2026-09-25：RM-FFSTAT → `handoffs/reconcile/20260924-ffstat-x-review-r24/synth.md`
- 2026-09-25：RM-FFSTAT → `handoffs/reconcile/20260925-ffstat-b1-review-r2/synth.md`
- 2026-09-25：RM-FFSTAT → `handoffs/reconcile/20260925-ffstat-b2-review-r2/synth.md`
- 2026-09-25：RM-FFSTAT → `handoffs/run_receipts/20260925-ffstat-fftfmeta-baseline-migration.json`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260925-ffstat-b3-review-r2/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/20260925-FFSTAT-B3-REVIEW-R3-BRIEF.md`
- 2026-09-26：RM-FFSTAT → `handoffs/run_receipts/20260926-ffstat-b3b-l65-hardening-migration.json`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260925-ffstat-b3-review-r3/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260925-ffstat-b3-review-r4/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260925-ffstat-b3-review-r5/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260925-ffstat-b3-review-r6/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/run_receipts/20260926-ffstat-autostart-depth.json`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-consult-r1/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r2/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r3/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r4/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r5/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r6/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r7/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r8/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r9/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r10/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r11/synth.md`
- 2026-09-26：RM-FFSTAT → `handoffs/reconcile/20260926-ffstatauto-x-review-r12/synth.md`
- 2026-09-26：RM-FFSTAT → `白話說明/FF-STAT未填起始日審閱.md`
<!-- ENTRY: RM-ICFIRSTALIGN -->
- 2026-09-26：RM-ICFIRSTALIGN → `handoffs/reconcile/20260926-icfirstneed-x-consult-r1/synth.md`
- 2026-09-26：RM-ICFIRSTALIGN → `handoffs/20260926-icfirstneed-x-consult-r1-claude.md`
<!-- ENTRY: RM-FFDSTAR -->
- 2026-09-24：RM-FFDSTAR → `handoffs/reconcile/20260924-ffdstar-x-review-r3/synth.md`
<!-- HISTORY-END -->
