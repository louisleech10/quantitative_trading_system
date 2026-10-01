# ICPOSTLEAK B1 review r3 — CODEX

task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R3
brief-kind: review
family: codex
brief: handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R3-BRIEF.md

本輪標的為 commit `4733b743` 之 SPEC v5 版本頭與 §N 第一條、r2 收斂處置；產品碼與既有測試沿用 r2 已完成之審查。本輪只讀收據與碼證，未重跑數值探針、未另加容差。指定交件為唯一主樹寫入。

## CODEX-R3-P3-00

**斷言**: 本輪逐項核對後無 finding；§N 改寫忠實保留 r2 已成立之數值差異與研究觸發，沒有把 registry 候選全等誤寫為全部分支已修復。

**碼證**: `git show 4733b743 -- docs/ICPOSTLEAK_SPEC.md` 顯示只改版本頭與 §N 殘留第一條；`git diff --name-only 40f863d4 HEAD -- momentum api frontend tests` → rc=0、空輸出。`jq '.rows[] | select(.branch=="polars")' handoffs/run_receipts/20261002-icpostleak-branch-diff.json` 與 locate 對應列的實際讀取，支持下列逐句對照。三家 r2 交件及收斂檔全文對讀；沒有新增未來洩漏或意外漂移之操作反例。

**來源摘要**: docs/ICPOSTLEAK_SPEC.md#ee2da5b1c527;handoffs/reconcile/20261001-icpostleak-b1-review-r2/synth.md#ae5b75d61c80;handoffs/run_receipts/20261002-icpostleak-branch-diff.json#8fcb13eb146f;handoffs/run_receipts/20261002-icpostleak-branch-diff-locate.json#6c037695529b

**類別**: other

### 必答 (1a)：§N 改寫是否忠實反映 r2 碼證？

是，依 r2 收斂後之處置而非把三家不同建議當成全數採納。保留 `needs-research`、量級數字、具名待研究項、已成立觸發與排序諮詢；主委原「改 registry 並標已處理」立場已撤回。composer 的立即改核心提案與 grok 的 `blocked-by` 理由沒有被偽稱採納；收斂檔均列部分採納及理由。codex 的 r2 只有 sentinel，沒有本家實質 finding 待閉合，因此末段 CLOSED 留空，亦不代簽 grok 的 ID。

### 必答 (1b)：逐句對照與收據欄位

以下 `diff` 指 `handoffs/run_receipts/20261002-icpostleak-branch-diff.json`，`locate` 指同日期 `branch-diff-locate.json`；數字為本輪讀檔值，未冒稱本輪重新計算。

| §N 子句 | 對照來源及限制 |
|---|---|
| 「各分支 zscore 數值核心不一致」 | r2 三家均記錄 registry 累積核心與 pandas／Polars 不同；SPEC Task 1.1 仍採逐分支 oracle，沒有新增跨分支全等要求。 |
| 「觸發已成立、最大相對差 58.8」 | diff `summary.max_rel_diff_overall=58.82005852248459`、`max_rel_diff_at=registry_parallel_split\|rank+zscore`、`residual_trigger_rel_gt_1e-3=true`；沒有改分母或移除近零格。 |
| 「legacy 近零、絕對差約 2e-6」 | grok r2 (2a)/(3b) 重算該相對差最大格：row 2843、col 3、legacy 約 3.456e-8、abs 約 2.033e-6。locate 僅定位最大絕對差，不含這個最大相對差格；此句來源是 grok r2，不是 locate 的該列。 |
| 「最大絕對差 0.0975」 | diff `summary.max_abs_diff_overall=0.09747552871704102`；`rows[branch=polars,combo=rank+zscore].max_abs_diff` 同值，`max_rel_diff=1.0`。locate 同列是 EMA21、row 1053、legacy=-3.0092341899871826、branch=-3.1067097187042236。這是生產預設 Polars 臂之組合差，沒有被單步 4.7e-5 替代。 |
| 「registry 單步最大 0.038、p99 0.009、與改前逐格相同」 | locate `rows[branch=registry,combo=zscore].abs_diff=0.03847217559814453`、`abs_diff_p99=0.009199649095535254`；改前全等依 grok r2 (3b) 的 d31c170e 對照。本輪沒有重跑該 baseline，兩份改後 JSON 本身不能證明改前全等。 |
| 「Polars 單步最大 4.7e-5、同 float32 輸入仍非零」 | diff Polars/zscore `max_abs_diff=4.738569259643555e-5`、`max_rel_diff=0.00761911304103904`；locate row 903 同 abs。codex r2 同 float32 比較另為 3.629922866821289e-5；兩數分屬不同輸入，文案沒有宣稱同 float32 仍恰為 4.7e-5。 |
| 「候選七組合全等；大群組成本待研究」 | codex r2 (3b)：同 float32 真實輸入、候選七組與 legacy 數值與 NaN 位置全等；不是 float64 任意輸入／全部分支全等。成本同家 (2b) 約 10.4× 時間、3.0× tracemalloc 配置，grok 約 8.8×／3.3×；§N 約 9–10 倍／3 倍為概略量級，沒有當硬門檻、RSS 或 full-scale 收據。 |
| 「Polars 臂剩餘差之下游影響待研究」 | 涵蓋上述 float64 輸入 rank+zscore 0.0975、codex r2 同 float32 該組合 1.52587890625e-5（max_rel=1.0），以及單步／其他組合；未縮限為單步 zscore。diff Polars/zscore+gaussian 的 0.027424335479736328、gaussian 的 0.015746355056762695 亦在該剩餘差涵蓋內。r2 沒有經驗證之下游 IC／ML 容差，SPEC 沒有把 grok「足夠」或 composer 與原始價格 std 比較之說法升格為驗收結論。 |
| 「rank 同值差為 float32 輸入量化、不列缺陷」 | codex r2 同 float32 輸入 rank 對 Polars／registry 均 0；原 float64 輸入 diff rank 最大 0.001984119415283203。此為已量測個案的來源分類，不證明任意市場／dtype 的 rank 差異都無下游影響，詳 (2a)/(2b)。 |
| 「現行分派 registry 不可達、Polars 為預設臂」 | r2 三家所列 feature_factory pre-IC／L7 raw 關閉三項、post-IC 無帶選欄 caller；IC 頁與 run_ic_first 使用 transform_selected。限定現行 repo 生產分派，不涵蓋外部直接調用 registry。生產碼自 40f863d4 無已提交差異，命令見 sentinel。 |
| 「研究啟動已觸發，排序諮詢定序與登記處」 | §N 明示已觸發、研究項①②與 ROADMAP 本票 pointer；ROADMAP RM-ICPOSTLEAK 實有 SPEC §N 指標，manifest `batch_card.not_executable` 第一條 reason=needs-research、owner=claude、expiry=2026-12-31。沒有把已觸發事項銷帳為已處理。 |

### 必答 (2a)：assumed 與「我沒查」是否成立？

assumed 成立於本輪要求的「可達差異有列出或由待研究項涵蓋」：Polars 0.0975 與同 float32 1.5e-5 均有上表明確落點；registry 成本與下游影響各自列入研究。§N 沒有逐格枚舉所有 42 對，但沒有任何 r2 生產可達差異被排除於研究涵蓋。

「我沒查」仍屬未驗證：未來台股、美股、期貨的非 float32 落盤與下游影響沒有本輪資料支持。可成立的是量化機制及 r2 同 float32 個案；不能成立的是「所有未來市場也一定無問題」的外推。§N 不列缺陷的分類沒有清除 Polars 組合差與下游研究義務，故此未查面不構成本輪新的實質 finding。

### 必答 (2b)：依據

讀碼 `api/services/ic_analysis_service.py:3001-3005`：明示 HDF5／Parquet 直接讀入，沒有 dtype 限制。`momentum/FeatureEngineering/polars_adapter.py:95-122`：`pandas_to_polars(use_float64=False)` 預設轉 float32。這與 codex r2 真實資料 H5 loader 保留 float64 的觀測相符，支持精度邊界可在轉換入口發生，而非所有檔案早已 float32。r2 的同 float32 控制比較是個案證據；本輪未對其他市場做新數值或 IC 排序探針。若非 float32 輸入之差異影響下游，仍落在已觸發的 Polars 臂研究項內，不能援引 rank 分類當成已證安全。

### 必答 (3a)：可否收第 1 批並收 ICPOSTLEAK 票？

可以，依本輪文件變更範圍與 r2 已完成的產品審查結論。第一條殘留是數值核心一致性研究，reason=needs-research、觸發已成立、研究項具名且列入排序諮詢；第二條是 ICFIRSTALIGN 乙部分（不可變 run context／L7 raw 時間軸），reason=user-ruling、觸發為該諮詢定案、登記處為 ROADMAP RM-ICFIRSTALIGN，manifest 亦具名列示。收案不表示上述研究或乙部分已完成，也不表示未來 dtype／市場資料正確性已簽核。本輪允許停止的依據是文字與碼證逐項一致、既定修補不變、兩條殘留處置可追溯。

### 必答 (3b)：擋收之 P0／P1

none。本輪沒有可重現的新未來洩漏或意外漂移反例；沒有以增加機制、測試或容差作為收案條件。

### 收尾與實跑界線

ASSUMPTIONS_VERIFIED: git show 4733b743 -- docs/ICPOSTLEAK_SPEC.md（rc=0）僅版本頭與 §N 第一條；git diff --name-only 40f863d4 HEAD -- momentum api frontend tests（rc=0、空輸出）無已提交產品差異；jq 對兩份 JSON 的 summary／Polars／registry 對應列讀取（rc=0）數字如上。r2 微探針與 baseline 成果為引用，非本輪重跑。
TESTS_RUN: 未跑產品 pytest／數值探針（brief 明示本輪僅文件一條）；指定 completeness 與末次狀態比對之實跑結果在下方補記。
FAILURES_SEEN: none。
SCOPE_CHANGES: none；只新增指定交件，未改碼、SPEC、manifest、templates、根 HANDOFF 或 git。
NUMERIC_OR_SCHEMA_IMPACT: none；沒有核可輸出大小、公式、dtype、schema 或容差變更。
HANDOFF_NOT_UPDATED: 本輪 brief 唯讀，依 AGENTS 7 不另寫狀態交接檔；指定交件為審查產出例外。
產出: handoffs/20261001-icpostleak-b1-review-r3-codex.md

交件檢查：依使用者指定在主樹執行 `bash scripts/completeness_check.sh --single handoffs/20261001-icpostleak-b1-review-r3-codex.md --family codex --round-id ca201aa1-4738-47b1-8759-b765da4044b5` → rc=0，`COMPLETENESS PASS(single)`、1 個 canonical ID；此命令為使用者明示之交件檢查例外，未跑產品探針。
範圍檢查：`git status --short -- momentum api frontend tests templates config` 前後存於 `/tmp/review-ca201a/status-before`、`status-final`；`cmp /tmp/review-ca201a/status-before /tmp/review-ca201a/status-final` → rc=0、無輸出；既有 cache／golden dirty 狀態未改。
清理：`rm -r /tmp/review-ca201a` → rc=0；`test ! -e /tmp/review-ca201a && test -d /tmp/claude-501` → rc=0。本次 workdir 已刪除，claude-501 保留；其他工作目錄未動。

VERDICT: proceed
BLOCKED-BY:
CLOSED:
