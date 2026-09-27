# FF-STAT SPEC v42 審查 r23 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R23  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R23-BRIEF.md`  
標的：`git diff 834f41af c6f7e6db -- docs/FFSTAT_SPEC.md`；r22 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r22/synth.md`；裁定 R1–R7 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針 `/tmp/ffstat-r23-probe`（真實 longhist kline，禁合成 fixture）。

## COMPOSER-R23-P3-00

**斷言**: 本輪逐項核對 v42 差分（§G⑦ 12h 實測 F_max 收據＋不合資格交使用者三擇一、係數 mutant 固定 ADXR 233 並記 EMA5 判準界線）與 r22 synth 採納修法對位後，未發現可重現之新 P0／P1 SPEC 缺陷；r22 之 `CODEX-R22-P1-01`／`CODEX-R22-P1-02` 在 v42 條文層已閉合，本家 `COMPOSER-R22-P3-00` 所覆 v41 範圍未被 v42 推翻。

**碼證**: `git diff --stat 834f41af c6f7e6db -- docs/FFSTAT_SPEC.md` → 1 file, 2 insertions／1 deletion（版本註記＋§G⑦ 單段）；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`rg -n "F_max_12h|不得由主委|倍數表 ADXR" docs/FFSTAT_SPEC.md` → 皆命中 `:92` 同段；逐字對位 r22 修法：`收據必記實測之 F_max_12h、各欄首個有限值、6,656−(M_tf＋F_max_tf＋500)`、`不得由主委或委員自行以 blocked 收案`、三擇一裁定、`倍數表 ADXR 係數改為 1.0`＋`period_keys＝timeperiod` period 233、ADXR 0.1053 紅／EMA5 0.0011 不紅；`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. venv/bin/python /tmp/ffstat-r23-probe/rows.py` → `BTCUSDT/ETHUSDT 12h rows=6656`、`ADAUSDT 12h rows=6171`（與 §A／下載收據一致）；brief fact `dead_feature_filter.py:77-82`（`notna().sum`／`nunique(dropna=True)`，不計 NaN 率）、`talib_wrapper.py:316,347` 逐字成立；`momentum/factories.py:237-246` 已支援 `cache_dir` 注入 longhist。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#4f10344303eb; handoffs/reconcile/20260926-ffstatauto-x-review-r22/synth.md#r22; handoffs/20260926-FFSTATAUTO-X-REVIEW-R23-BRIEF.md#1a88446b1f75; handoffs/run_receipts/20260927-ffstat-longhist-download.log#6656

---

## 必答

1. **(1a)** r22 三條：**CODEX-R22-P1-01**、**CODEX-R22-P1-02** 於 v42 已按 synth 採納修法閉合；**COMPOSER-R22-P3-00** 仍成立（v42 僅補 §G⑦／版本註記，未改 v41 已閉合之 M_tf＝K_max_tf、§N 1,696 刪除等）。**(1b)** P1-01：v41「12h 不得以 blocked 收場」與一般資格 `M+F+500` 之字面互斥，v42 改為「照一般資格＋收據必記實測 F_max_12h／逐欄首有限值／餘量」且仍不合資格時**不得主委 blocked 收案**、交使用者三擇一——與 R8 意旨及 r22 codex 反例（F_max 臨界 4,105、窗長 proxy 非收據）對位；F_max 實測數字留 Task 2.4 收據，brief 明示不得以「未實跑」列 finding。P1-02：mutant 字面由「某 recursive」改為「倍數表 ADXR 係數 1.0」並封閉 period 233、`period_keys`＝timeperiod，收據欄位與 r22 真實 1h 數字嵌入條文。本家 r22 sentinel 未被否定。

2. **(2a)** v42 差分內**無**新 P0／P1。**(2b)** 否證：模板檢 PASS；longhist 列數與 §G⑦／§A 一致；v42 未改 manifest／程式契約；未重跑預設全設定 FF（brief 禁止）。

3. **(3a)** brief **assumed**（三遮罩 mutant 於 BTC 1h 預設全設定下至少一欄 B 開頭偏差 ≥0.005；係數 mutant 固定 ADXR233 且 r22 已紅）→ **條文層成立**：v41–v42 §G⑦ 仍要求刪 L1 遮罩／縮尾不遮／第④類不遮各跑 1h 皆紅，且 B 比較自各欄首有限值、M_tf＝K_max_tf 時 A 於該列已有 ≥K_max 前史；係數路徑以 ADXR233 為唯一目標並引用 r22 實跑 0.1053（紅），EMA5 0.0011 明示為判準界線而非漏檢。本輪未跑 1h 全 mutant FF（brief 禁分鐘級 run）。**(3b)** 見 sentinel **碼證**與 `docs/FFSTAT_SPEC.md:92` v42 括號內 ADXR／EMA 對照。

4. **(4a)** brief「我沒查」：**①** `cache_dir` 注入——**未命中** v42 新缺陷（factory 已支援；`scripts/verify_l1_warmup_requirements.py` 仍固定一般快取屬 impl 接線，§G 已寫測試以儲存層指向，與 r22 codex 同判）。**②** 5m×105,260 量測記憶體／耗時——**未命中**（v42 未改 eval cap）。**③** ADA 12h 6,171 較晚起點——**未命中**（probe 實跑；跨標的取 max 仍 BTC/ETH 6,656，§A 已列）。**(4b)** `momentum/factories.py:237-246`；probe 輸出；`handoffs/run_receipts/20260927-ffstat-longhist-download.log`。

5. **(5a)** **是**，v42 可 **`VERDICT: proceed`**（r22 blocking 已修、本輪無新 P0/P1）。**(5b)** 無。

---

ASSUMPTIONS_VERIFIED: 已讀 brief、template、類別封閉集、v42 diff、r22 synth、R8 裁定摘要；longhist 列數 probe；fact L7／TA-Lib 行號；未改 source  
TESTS_RUN: `git diff --stat 834f41af c6f7e6db -- docs/FFSTAT_SPEC.md`；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → PASS rc=0；`env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. venv/bin/python /tmp/ffstat-r23-probe/rows.py` → rc=0（BTC/ETH 6656、ADA 6171）；`bash scripts/completeness_check.sh --single handoffs/20260926-ffstatauto-x-review-r23-composer.md --family composer --round-id 1dfd2f08-4351-44b8-a250-ff249bc8e559`（收尾驗收）  
FAILURES_SEEN: `/tmp/ffstat-r23-probe/rows.py` 初回誤用 `load_klines`（應為 `read_klines`），改正後 rc=0；收尾 `rm -rf /tmp/ffstat-r23-probe` 被環境安全閘拒絕，未改寫命令形式；未改 source  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r23-composer.md  
TMP_CLEANUP: `rm -rf /tmp/ffstat-r23-probe` 被 PreToolUse 安全閘拒絕（目錄可能仍在）；`/tmp/claude-501` 保留確認

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R22-P3-00

STATUS: DONE
