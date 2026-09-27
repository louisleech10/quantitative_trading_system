# FF-STAT SPEC v32 審查 r13 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R13  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R13-BRIEF.md`  
標的：`git diff 2b45c1d8 9c37a345 -- docs/FFSTAT_SPEC.md`；裁定 `handoffs/20260927-ffstat-b4-redesign-rulings.md`；倍數表收據 `handoffs/run_receipts/20260927-warmup-table-coverage.txt`。唯讀；探針 `venv/bin/python /tmp/ffstat-r13-wd/probe_invariance.py`（真實 `kline_cache.h5` BTCUSDT 1h 前 800 根）。

fact-verified: v32 版註與 R1–R7 映射見 §C／Task 2.3／2.4／§N；`venv/bin/python handoffs/run_receipts/20260927-warmup-table-coverage.py` → 76 指標中 39 缺表（與 §A FACT 一致）；`warmup_window.py:364-371` 現碼仍 `FFACT_WARMUP_TRIM`＋僅有 `start_date` 時預熱（規格要求刪除，屬實作批）；winsor `min_periods<window` 不傳 NaN（§A FACT，v32 以 +251 遮罩處理）。

## COMPOSER-R13-P1-01

**斷言**: v32「未填起始日、平穩化開啟」之路徑下，§G ③ 與 Task 2.1 仍要求每欄 `max(校準時間) < 輸出起始日`，與 §C 同欄校準值取公開域 `stable_start` 後最早 N 個有效值且校準列留於全史 index 內之設計不可同時滿足（校準時間必 ≥ 該欄首個有效值時間，而全史模式無使用者 `start_date` 時「輸出起始日」若指資料首列則恒不成立）。

**碼證**: `git show 9c37a345:docs/FFSTAT_SPEC.md` → §C「未填起始日」校準列定義；同檔 §G 通過條件③「`max(校準時間) < 輸出起始日`」；Task 2.1 驗證首句同句。對照 §C「校準資料無洩漏」已 split 無起始日例外，但 §G／Task 2.1 未 split。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:79
MUTATION: 以無 `start_date`、平穩化開啟之真實 1h run 產出收據，任取一欄令 `max(校準時間)` 為第 N 個有效值時間、`輸出起始日` 取 manifest 資料首列時間 ⇒ 斷言 `max < start` 失敗而 §G ③ 紅。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0

**修法**: §G ③ 與 Task 2.1 校驗句分支——僅「有 `start_date`＋校準域／封包路徑」保留 `max(校準時間) < 輸出起始日`；`output_start_source=per_column` 時改為 `max(校準時間) < 該欄公開輸出起點`（=第 N 個有效值下一列）且 Task 2.3 ④ 之 spy 為準。可行性：純 SPEC／manifest 文案與既有測試名分支，無新長跑檢查。

---

## COMPOSER-R13-P1-02

**斷言**: §C「公開值之不變量」與 §G ②「`stable_start` 之後四 hash 與改前（無遮罩基準）逐欄全等」對遞迴／受前史輸入影響之欄不成立——L1 前段改 NaN 後同索引之重算值可與改前未遮罩值大幅偏離，與 brief assumed「stable_start 後逐位元組相同」矛盾。

**碼證**: `venv/bin/python /tmp/ffstat-r13-wd/probe_invariance.py` → BTCUSDT 1h 前 800 根：`close.ewm(span=20)` 全史 vs 前 200 根置 NaN，索引 250 處 `46252.99` vs `46254.85`，`max_abs_diff_after_mask_end=250.49`（非零）。§A 已有 codex EWM 600 列改變之前例；v32 宣稱與 §G ② 未限定僅 window_only。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:61
MUTATION: 對任一 recursive L1 欄（如 EMA_233），無起始日 run 在 `stable_start` 列取改後值，與 worktree 重冻之改前 baseline 同 timestamp 比對 ⇒ 超出 float 相等，§G ② 紅。

**類別**: code-contract

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0

**修法**: 刪除或收窄 §C 不變量／§G ②——改前基準改為「同遮罩語意下重冻」或僅對 window_only／已證 L2+ min_periods=window 鏈路聲明 hash 全等；recursive 與 L3+ 改以 §G ⑦ 收斂容差為唯一公開正確性判準。可行性：§G ⑦ 與 Task 2.3 ⑥ 已規劃全設定探針，調整 ② 文案不新增生成期分鐘級 gate。

---

## COMPOSER-R13-P2-01

**斷言**: §A FACT-RECEIPT 仍標「L5、L6 未查」，但 v32 §C 要求 L2–L6.5 與多週期對齊完整 NaN 傳遞盤點收據，設計前提與已驗證事實清單不一致，實作前無法確認「只遮 L1＋縮尾」是否充分。

**碼證**: `git show 9c37a345:docs/FFSTAT_SPEC.md` §A 末條 FACT「L5、L6 未查」；§C「盤點範圍：… L5 … L6 … 多週期對齊」。Task 2.3 ② 要求盤點收據與 AST 步驟集合全等。靜態：`tf_aligner.py:225-249` 對 `idx_map=-1` 寫 NaN（傳遞）；`state_counters.py:128-133` `cross_count` 窗未滿前為 NaN 但语义 0 计数——须入盘点。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:34
MUTATION: 若盤點收據缺 L5 reference 對齊或 L6 state_counters 任一步 ⇒ Task 2.3 ②「少一即紅」在 impl 前即無法簽 off。

**類別**: doc-sync

**來源摘要**: docs/FFSTAT_SPEC.md#96038395d4f2

[P2] 不單獨挡 VERDICT；须于 Task 2.3 动工前补 FACT 或收拢盘点范围措辞。

---

## 必答

1. **(1a)** R1–R7 在 v32 正文均可逐条对上（预热带开、逐栏 stable、表 fail-closed、缩尾 +251、IC-First 登记见 §N）。**(1b)** R3/R4 使用者未另明示「同意」已在版注与 `20260927-ffstat-b4-redesign-rulings.md` 披露；NaN 传递取代血缘为主委提案，版注已标待白话审阅。

2. **(2a)** 有——§G ③ 与无起始日逐栏校准冲突（P1-01）；§G ②／§C 不变量与遮罩重算冲突（P1-02）。**(2b)** P1-02：`venv/bin/python /tmp/ffstat-r13-wd/probe_invariance.py`（见上）；P1-01：无 start_date 收據时间序与 §G ③ 字面反例（操作：全史 run + 收據 `max(cal_time)` vs 首列 timestamp）。

3. **(3a)** brief 两条 assumed：**第一条（L2–L6 皆传 NaN）——有条件不成立**：winsor 已知不传递且 v32 已列 +251；L5/L6/对齐/ state_counters 未查完，不可默認成立。**第二条（无起始日 stable 后逐位元组不变）——不成立**（P1-02 探针）。**(3b)** `feature_preprocessor.py` winsor 路径；`probe_invariance.py`；§A FACT L5/L6 未查。

4. **(4a)** ① **部分命中**——L5 对齐 NaN 传递有码证，但 L6/state_counters/ADF 差分链未全读；② **未查** CGSA 遮罩接点；③ v32 已写死栏 NaN 率排除遮罩列，与 `rolling_aggregator.py:803-821` 现状需 impl；④ **未跑** §G ⑦ 全设定 8GB（brief 排除）；⑤ D 加倍最坏成本 SPEC 已记 Task 4.1；⑥ replace/衍生栏 SPEC Task 2.3 ④ 已列；⑦ v32 Task 2.3 改 `resolve_output_window` 恒预热与 v29 `run_ic_first` 带 start_date 可并存，但须 impl 统一；⑧ Task 2.4 边界① 已挡 MAMA 等 period=1 之 5 根陷阱。 **(4b)** 见各 CODE-ANCHOR 与 `tf_aligner.py:225-249`。

5. **(5a)** **L1 遮罩 + 盘点 NaN 传递**较逐栏血缘更可维护（R4 量一次、无 lineage 字段）。**(5b)** 反例：若无盘点，L6.5 winsor 已在 §A 证明不传递；仅 L1 遮罩会使缩尾窗内出有限值早于真稳定点——v32 以 +251 遮罩补救，依赖完整盘点（P2-01）。

6. **(6a)** §G ⑦ 三 mutant 必红设计可证伪；M=2×max K 合理。**(6b)** 本家未跑全设定 BTC 1h/4h/12h 双起点（brief ④ 8GB 风险）；判准 0.5% scale-normalized 与表一致。未跑数字不构成挡 SPEC 之新 P1，但 impl 前须 Task 4.1/2.3 ⑥ 实跑。

7. **(7a)** **否**，`VERDICT: blocked`。**(7b)** `COMPOSER-R13-P1-01`、`COMPOSER-R13-P1-02`。

---

ASSUMPTIONS_VERIFIED: `git diff 2b45c1d8 9c37a345 -- docs/FFSTAT_SPEC.md`；`git show 9c37a345:docs/FFSTAT_SPEC.md` 节选；warmup coverage 脚本；EMA 探针；`warmup_window.py`/`tf_aligner`/`state_counters` 静态。  
TESTS_RUN: `git diff 2b45c1d8 9c37a345 -- docs/FFSTAT_SPEC.md`（164 行 diff）；`venv/bin/python handoffs/run_receipts/20260927-warmup-table-coverage.py | head -3`（76/39 missing）；`venv/bin/python /tmp/ffstat-r13-wd/probe_invariance.py`（max_abs_diff=250.49）；开跑 `git status --short -- momentum api scripts tests docs templates config` 与 brief 前提一致（14 行量级）。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（审 v32 SPEC 文案；v32 动产出 schema 已为用户裁定，本 finding 要求修验收字面与不变量，非弱化 gate）  
產出: `handoffs/20260926-ffstatauto-x-review-r13-composer.md`

VERDICT: blocked
BLOCKED-BY: COMPOSER-R13-P1-01, COMPOSER-R13-P1-02
CLOSED: COMPOSER-R12-P3-00

STATUS: DONE
