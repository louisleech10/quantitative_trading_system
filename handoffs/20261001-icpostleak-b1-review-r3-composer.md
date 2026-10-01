# ICPOSTLEAK B1 審碼 r3 — COMPOSER（§N v5 閉合確認；唯讀）

task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R3  
family: composer  
findings-round: R3  
brief-kind: review  
brief: handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R3-BRIEF.md  
note: 唯讀。標的＝commit `4733b743`（`docs/ICPOSTLEAK_SPEC.md` v5 §N 殘留第一條）＋r2 收斂 `handoffs/reconcile/20261001-icpostleak-b1-review-r2/synth.md`。未重跑 branchdiff／候選探針；數字只讀 `handoffs/run_receipts/20261002-icpostleak-branch-diff.json` 與 `handoffs/run_receipts/20261002-icpostleak-branch-diff-locate.json`。

---

## 必答（成對）

### (1a) GROK-R2-P2-01 是否閉合？§N 改寫是否忠實反映 r2 碼證？

**GROK-R2-P2-01：閉合。** r2 主張為「僅改 registry zscore 核心並把殘留標已處理」不成立（觸發含 legacy 近零相對差放大與 Polars／rank 同值差）。`4733b743` 之 §N 已改為 `needs-research`、明文 `觸發已成立`、附收據量級，並具名待研究①registry 大群組改核心之成本②Polars 剩餘差之下游影響；不再宣稱 registry 單步修法可清除觸發。與 r2 synth 對 GROK-R2-P2-01「部分採納」一致。

**§N 對 r2 碼證：忠實（生產可達差異層級）。** 三家 r2 收據與交件中之關鍵數字均可從交付 JSON 重讀，且與 §N 該條逐項對齊（見 (1b)）。未發現 r2 所列**生產可達**臂（Polars；IC 頁／`run_ic_first` 預設）之最大量級被 §N 否認或改寫為「未觸發」。

### (1b) 逐句對照（引收據欄位）

| §N 字面（`docs/ICPOSTLEAK_SPEC.md:99` 殘留第一條內） | 收據／r2 碼證欄位 | 判定 |
|---|---|---|
| 最大相對差 58.8、位於 legacy 近零之 z 值格〔絕對差約 2e-6〕 | `summary.max_rel_diff_overall=58.82005852248459`，`max_rel_diff_at=registry_parallel_split\|rank+zscore`；grok r2 近零格 abs≈2.033e-6 | 一致（四捨五入） |
| 最大絕對差 0.0975 | `summary.max_abs_diff_overall=0.09747552871704102`；`rows` 中 `polars`+`rank+zscore` 同值 | 一致 |
| registry 單步 zscore 最大 0.038、p99 0.009，與改前逐格相同 | `registry`+`zscore`：`max_abs_diff=0.03847217559814453`；locate `registry`+`zscore` `abs_diff_p99=0.009199649095535254` | 一致 |
| Polars 單步 zscore 最大 4.7e-5，同 float32 輸入下仍非零 | `polars`+`zscore`：`max_abs_diff=4.738569259643555e-05`；locate row903 `abs_diff` 同 | 一致 |
| 待研究①微探針約 9–10 倍時間、3 倍配置 | codex r2：≈10.4×／3.0×；grok r2：8.8×／3.3× | 一致（區間敘述） |
| rank 同值差…同 float32 輸入時為 0 | codex r2 表：rank 步 Polars／registry `max_abs_diff=0`（共用 float32 輸入） | 一致 |
| 生產可達性：registry 三項關閉、Polars 為 IC 預設臂 | r2 三家 `feature_factory.py:2971-2982` 掃描＋無 `selected_features` 生產 caller | 一致（讀碼複核，未重跑 FF） |

**邊界（不升格 P0/P1）：** §N 未逐字寫出 codex r2 在同 float32 輸入下 Polars `rank+zscore` 之 `max_abs_diff=1.52587890625e-05`（`branch-diff.json` `polars`+`rank+zscore` 在 float32 對照實驗中）；§N 僅將 rank **同值**差歸 float32 量化。該格仍遠小於 §N 已載之整體 `max_abs` 0.0975（float64 探針路徑）與 Polars 單步 4.7e-5，且待研究②已涵蓋 Polars 剩餘差之下游影響，**不構成** brief 假設之否證（遺漏生產可達主量級）。

### (2a) brief `assumed` 與「我沒查」是否成立？

**assumed（§N 未遺漏 r2 可達差異）：成立。** 上表＋整體 `max_abs`／`max_rel` 與 Polars／registry 分步欄位對讀；否證觀測未出現。

**brief「我沒查」**（§N rank／float32 敘事對未來非 float32 落盤市場資料是否仍成立）：**仍成立為未查、本輪不推翻。** `feature_storage.py` 標準邊界仍為 float32；§N 之 rank 量化說明明確限定「同 float32 輸入」。台股／美股／期貨或其他 dtype 路徑本輪未實跑，與 brief 攻擊面自陳一致。

**r2「我沒查」1–4（延續判斷）：** 生產碼自 `40f863d4` 起 `time_order.py`／`feature_factory.py`／`ic_analysis_service.py` 無新 commit（`git log 40f863d4..HEAD --` 上述路徑為空）⇒ r2 ①② 與 caller 掃描結論仍有效；②③④ 仍為成本／統計邊界未全量驗，**不阻擋** r3 文件閉合。

### (2b) 依據

機讀：`jq '.summary' handoffs/run_receipts/20261002-icpostleak-branch-diff.json`；`jq` 篩選 `rows[]` 之 `polars`／`registry`+`zscore`／`rank+zscore`；locate `registry`+`zscore` 之 `abs_diff`／`abs_diff_p99`。讀碼：`docs/ICPOSTLEAK_SPEC.md:99`；`git show 4733b743 -- docs/ICPOSTLEAK_SPEC.md`；r2 三家交件與 `handoffs/reconcile/20261001-icpostleak-b1-review-r2/synth.md`。

### (3a) 可否收第 1 批並收 ICPOSTLEAK 票？

**可以。** 洩漏修補批（`40f863d4` 及前序）與 r2 三家一致；§N 殘留**兩條**均具名、有觸發與登記處：

1. 各分支 zscore 核心不一致——`needs-research`、觸發已觸發並列入全票細項排序諮詢；登記處 ROADMAP pointer＋本 SPEC（§N:99）。
2. ICFIRSTALIGN 乙部分——`user-ruling:2026-10-01`；觸發＝諮詢定案；登記處 `docs/ROADMAP.md` RM-ICFIRSTALIGN（§N:100）。

本家 r2「明確 follow-up」已由 §N 具名待研究項＋觸發已觸發滿足（r2 synth 部分採納 composer 該點）。

### (3b) 擋收之 P0／P1

none。

---

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對 `4733b743` §N 與 r2 收據／三家碼證後，無意外漂移或未閉合之 P0／P1；GROK-R2-P2-01 之文件論點已由 v5 改寫閉合，可收第 1 批。

**碼證**: `jq '.summary' handoffs/run_receipts/20261002-icpostleak-branch-diff.json` → `residual_trigger_rel_gt_1e-3: true`、`max_rel_diff_overall: 58.82005852248459`、`max_abs_diff_overall: 0.09747552871704102`；`git show 4733b743:docs/ICPOSTLEAK_SPEC.md` 版本頭 v5＋§N 殘留第一條含上述量級與 `needs-research` 兩項待研究；`git log 40f863d4..HEAD -- momentum/FeatureEngineering/preprocessing/time_order.py momentum/FeatureEngineering/feature_factory.py api/services/ic_analysis_service.py` → 無輸出；`cmp` 開跑／收尾 `git status --short -- momentum api frontend tests templates config` → rc=0。

**類別**: other

**來源摘要**: docs/ICPOSTLEAK_SPEC.md#4733b743;handoffs/run_receipts/20261002-icpostleak-branch-diff.json#8fcb13eb146f;handoffs/run_receipts/20261002-icpostleak-branch-diff-locate.json#6c037695529b;handoffs/reconcile/20261001-icpostleak-b1-review-r2/synth.md;handoffs/20261001-icpostleak-b1-review-r2-grok.md;handoffs/20261001-icpostleak-b1-review-r2-codex.md

正文：威脅模型＝意外漂移與未來洩漏；本輪僅審 SPEC §N 改寫閉合，不重跑數值探針。ROADMAP 表列仍寫「SPEC v4」與「審碼中」（`docs/ROADMAP.md:59`）與 v5 字面略舊，屬路線表同步 lag，不在本 brief 修補標的內，亦不構成本家 P0/P1（§N 內登記處 pointer 仍有效）。

---

ASSUMPTIONS_VERIFIED: 主委事實 1–2（收據數字來源、生產碼自 40f863d4 未改）；§N 與 branch-diff／locate summary 對齊；GROK-R2-P2-01 論點已被 v5 吸收。  
TESTS_RUN: 未跑 pytest／branchdiff（brief 明示不需重跑數值探針）；`jq` 收據摘要；`git show`／`git log` 唯讀。  
FAILURES_SEEN: none。  
SCOPE_CHANGES: none（唯讀；僅新增本交件）。  
NUMERIC_OR_SCHEMA_IMPACT: none。  
OUTPUT_PATH: handoffs/20261001-icpostleak-b1-review-r3-composer.md  
HANDOFF_NOT_UPDATED: 執行端不改根 HANDOFF.md；brief-kind=review。  
WORKTREE: `git status --short -- momentum api frontend tests templates config` 與開跑快照相同（rc=0）。

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:

STATUS: DONE
