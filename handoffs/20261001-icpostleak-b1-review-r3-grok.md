# ICPOSTLEAK B1 審碼 r3 — GROK

task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R3
brief: handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R3-BRIEF.md
family: GROK
brief-kind: review
findings-round: R3

本輪唯讀。標的＝r2 收斂檔與 commit `4733b743`（SPEC v5 版本頭＋§N 殘留第一條）。全面審。未改碼、未改文檔、未 git 寫入。本輪標的為文件一條，未重跑數值探針；數字只讀收據 JSON 與 r2 三家交件。指令列與暫存路徑不含委員家族名稱。

## 必答（成對）

**(1a) GROK-R2-P2-01 是否閉合？**

閉合。原斷言是：以「registry zscore 改用 `_rolling_zscore_2d`」把 §N 殘留第一條標成已處理不成立，因為現行觸發由 |legacy| 近零放大與 Polars／rank 同值差共同點燃，該改動清不掉觸發。

`4733b743` 後之 SPEC v5：殘留維持；版本頭寫「registry 改核心不足以清除觸發」；理由附量級數字；待研究兩項具名。r2 收斂對本條為部分採納：主委原立場撤回、理由改寫；「為何現在不做」維持 `needs-research`。原斷言之缺陷（標已處理）已消除。建議改 `blocked-by` 屬修法偏好，r2 收斂已記錄不採理由（Task 1.1 不改公式為本票範圍界定；待決者為成本與下游影響＝研究問題）。本輪不重開該處置。

**(1b) 逐句對照（引收據欄位）**

§N 殘留第一條現行字面 vs 收據／r2 碼證：

1. 「觸發已成立（…最大相對差 58.8 位於 legacy 近零之 z 值格〔絕對差約 2e-6〕）」  
   `handoffs/run_receipts/20261002-icpostleak-branch-diff.json` `summary.max_rel_diff_overall=58.82005852248459`、`max_rel_diff_at=registry_parallel_split|rank+zscore`、`residual_trigger_rel_gt_1e-3=true`。近零格絕對差約 2e-6 取自本家 r2 對 after.npz 重算（row=2843 col=3，legacy=3.456e-8，abs=2.033e-6，rel=58.82）。主委事實 1 允許取 r2 交件數字。相符。

2. 「最大絕對差 0.0975」  
   同檔 `summary.max_abs_diff_overall=0.09747552871704102`。locate 同值落在 `polars` × `rank+zscore`（EMA_21 第 1053 列）。相符。assumed 所指 float64 輸入之 Polars rank+zscore 0.0975 即此欄。

3. 「registry 單步 zscore 最大 0.038、p99 0.009，與改前逐格相同」  
   locate `registry_parallel_split` × `zscore`：`abs_diff=0.03847217559814453`、`abs_diff_p99=0.009199649095535254`。branch-diff 同組合 `max_abs_diff=0.03847217559814453`。r2 本家碼證：與改前 `d31c170e` 逐格相同。本輪生產碼自 `40f863d4` 起 0 筆 momentum／api／frontend／tests commit，該「與改前相同」仍可引用。相符。

4. 「Polars 單步 zscore 最大 4.7e-5，同 float32 輸入下仍非零」  
   locate `polars` × `zscore`：`abs_diff=4.738569259643555e-05`。branch-diff 同組合 `max_rel_diff=0.00761911304103904`。float32 仍非零取自 r2 交件：codex 表 Polars zscore 3.63e-5、rank+zscore 1.52587890625e-5。相符。

5. 「待研究① registry 改 float64 累積或同 legacy 核心（候選已實證七組合全等）於大群組之記憶體與耗時（float64 pandas 核心單次微探針約 9–10 倍時間、3 倍配置）」  
   七組合全等＝codex r2 `probe_candidate.py`。成本＝codex 約 10.4×／3.0×、本家 r2 8.8×／3.3×；主委事實 1 並列兩者。§N「約 9–10 倍、3 倍」為兩次微探針之約數。相符。

6. 「待研究② Polars 臂之剩餘差是否影響下游 IC／ML 排序」  
   涵蓋 Polars 單步 4.7e-5 與 float32 rank+zscore 剩餘 1.5e-5（codex r2 表）。1.5e-5 未另引數字，類別落在此項。涵蓋成立。

7. 「rank 同值差屬 float32 輸入量化（同 float32 輸入時為 0），不列缺陷」  
   codex r2 表：同 float32 輸入時 rank 於 Polars／registry 最大絕對差 0。與 r2 本家「測試輸入 float64 unique 2980 vs float32 2977」一致。相符於現行落盤路徑。

8. 「生產可達性：registry 帶 rank／zscore／gaussian 經現行分派不可達…Polars 臂為 IC 頁與 `run_ic_first` 預設臂」  
   r2 三家交件一致。本輪未重掃 caller（生產碼未改）。相符。

9. 「觸發（研究啟動）：已觸發 ⇒ 列入使用者 2026-10-01 裁定之全票細項排序諮詢定序；登記處：`docs/ROADMAP.md` 本票列之 pointer 與本 SPEC」  
   ROADMAP 第 331 列 RM-ICPOSTLEAK：「殘留二條（各分支 zscore 數值核心統一＝needs-research；ICFIRSTALIGN 乙部分＝user-ruling 交全票細項排序諮詢）見 SPEC §N」。manifest `batch_card.not_executable` 兩條 reason＝`needs-research`／`user-ruling`。相符。

**(2a) assumed 與「我沒查」是否成立？**

assumed 成立。r2 三家碼證所示生產可達差異均出現在 §N 該條或其待研究項：Polars rank+zscore 0.0975（float64）為 `max_abs_diff_overall`；同 float32 之 1.5e-5 由待研究②「Polars 臂之剩餘差」涵蓋；registry 單步 0.038／p99 0.009、近零相對差 58.8、成本約數、生產分派均入句。否證觀測（可達差異未入條文或待研究項）未出現。

「我沒查」成立為誠實缺口，不推翻 assumed、不擋收批。§N「rank 同值差…不列缺陷」之適用範圍是現行落盤（r2：parquet float16／h5 float32；float16 unique 在 float32 與 float64 皆 547）。台股／美股／期貨之非 float32 落盤路徑本票不存在、本輪無收據。若未來以 float64 落盤，rank 同值差會再現，歸已登記之「各分支數值核心不一致」殘留，觸發仍是全票細項排序諮詢。

**(2b) 依據**

- assumed：上列 (1b) 1–7 與 `jq -c '.summary'`／locate `zscore`／`rank+zscore` 列；codex r2 float32 表 rank+zscore Polars `1.52587890625e-5`。
- 「我沒查」：brief 攻擊面原文；r2 本家 `ASSUMPTIONS_VERIFIED` 之落盤 dtype；SPEC §C「不得侷限加密貨幣」為窗口單位（根），未另定未來市場 persist dtype。本輪未重跑探針。

**(3a) 可否收第 1 批並收 ICPOSTLEAK 票？**

可以。第 1 批：r1 兩條已由提出方於 r2 CLOSED；生產碼自 `40f863d4` 起未再改；本輪無新 P0／P1。收票：殘留兩條皆具名、皆有允許之「為何現在不做」值、皆有觸發與登記處——① 各分支 zscore 核心不一致＝`needs-research`，觸發已成立並列入全票細項排序諮詢，登記 SPEC §N＋ROADMAP RM-ICPOSTLEAK＋manifest `not_executable[0]`；② ICFIRSTALIGN 乙部分＝`user-ruling`，觸發＝該諮詢定案，登記 SPEC §N＋ROADMAP RM-ICFIRSTALIGN＋manifest `not_executable[1]`。

**(3b) 擋之 P0／P1：** 無。

---

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding。GROK-R2-P2-01 已由 SPEC v5 §N 改寫閉合；assumed 之可達差異均入該條或待研究項；殘留兩條具名且有觸發與登記處，可收第 1 批並收票。

**碼證**: `git rev-parse --short HEAD` → `4733b743`。`git log --oneline 40f863d4..HEAD -- momentum api frontend tests` → 0 行。`git show 4733b743 --stat -- docs/ICPOSTLEAK_SPEC.md` → 4 行改動（版本頭＋§N 殘留第一條）。`jq -c '.summary' handoffs/run_receipts/20261002-icpostleak-branch-diff.json` → `max_rel_diff_overall=58.82005852248459`、`max_rel_diff_at=registry_parallel_split|rank+zscore`、`max_abs_diff_overall=0.09747552871704102`、`residual_trigger_rel_gt_1e-3=true`。locate `polars`×`zscore` abs=4.738569259643555e-05；`registry_parallel_split`×`zscore` abs=0.03847217559814453 p99=0.009199649095535254；`polars`×`rank+zscore` abs=0.09747552871704102。`jq -c '.batch_card.not_executable' docs/manifests/ICPOSTLEAK.json` → 兩條 reason=`needs-research`／`user-ruling`。ROADMAP 第 331 列 pointer 殘留二條見 SPEC §N。`git status --short -- momentum api frontend tests templates config` 與開跑快照相同。

**類別**: other

**來源摘要**: docs/ICPOSTLEAK_SPEC.md#ee2da5b1c527;handoffs/reconcile/20261001-icpostleak-b1-review-r2/synth.md#ae5b75d61c80;handoffs/run_receipts/20261002-icpostleak-branch-diff.json#8fcb13eb146f;handoffs/run_receipts/20261002-icpostleak-branch-diff-locate.json#6c037695529b;handoffs/20261001-icpostleak-b1-review-r2-grok.md#5035afcac094;handoffs/20261002-ICPOSTLEAK-B1-REVIEW-R3-BRIEF.md#92e61914ef36;docs/ROADMAP.md#7cf98e5016b2;docs/manifests/ICPOSTLEAK.json#c19914e3f92e

正文：核對依據＝r2 收斂對 GROK-R2-P2-01 之部分採納（殘留維持、數字入句、主委原立場撤回）與 `4733b743` 實際 diff；收據 summary／locate 欄位與 §N 逐句對讀；float32 rank+zscore 1.5e-5 由待研究②涵蓋；兩條殘留之 reason／觸發／ROADMAP／manifest 三處登記。未重跑 49 例探針、未改產品碼。停輪依據是上述對讀，sentinel 只作零 finding 契約形態。

---

ASSUMPTIONS_VERIFIED: GROK-R2-P2-01 閉合；§N 數字與 receipt summary／locate 及 r2 交件一致；assumed 可達差異有涵蓋；「我沒查」為未來非 float32 落盤之誠實缺口、不擋收票；生產碼自 40f863d4 起未改。
TESTS_RUN: 本輪未跑 pytest／數值探針（brief：不需重跑數值探針）。機讀：`jq` summary／locate／manifest；`git show 4733b743`；`git log 40f863d4..HEAD` 0 行；`git status --short -- momentum api frontend tests templates config` 與開跑快照相同。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀）
NUMERIC_OR_SCHEMA_IMPACT: none
產出: handoffs/20261001-icpostleak-b1-review-r3-grok.md
HANDOFF_NOT_UPDATED: 本輪 brief 唯讀，依 AGENTS 7 不另寫狀態交接；根 HANDOFF 未改。
WORKTREE_CHECK: `git status --short -- momentum api frontend tests templates config` 與開跑快照相同（既有 numba cache／golden l65 dirty 列未增減）。

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R2-P2-01
STATUS: DONE
