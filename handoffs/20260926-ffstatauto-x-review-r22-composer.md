# FF-STAT SPEC v41 審查 r22 — COMPOSER

task-id: 20260926-FFSTATAUTO-X-REVIEW-R22  
family: composer | brief-kind: review  
brief: `handoffs/20260926-FFSTATAUTO-X-REVIEW-R22-BRIEF.md`  
標的：`git diff 38ca2137 834f41af -- docs/FFSTAT_SPEC.md`；r21 收斂 `handoffs/reconcile/20260926-ffstatauto-x-review-r21/synth.md`；裁定 R1–R9 `handoffs/20260927-ffstat-b4-redesign-rulings.md`。唯讀；探針 `/tmp/ffstat-r22-work`（真實 longhist kline，禁合成 fixture）。

## COMPOSER-R22-P3-00

**斷言**: 本輪逐項核對 v41 差分（§G⑦ `M_tf＝K_max_tf`、§A 交易所缺口、Task 4.1 12h N 一致率、§N 刪 12h 1,696 殘留）與 r21 採納修法對位後，未發現可重現之新 P0／P1 SPEC 缺陷；r21 之 `CODEX-R21-P1-01`／`CODEX-R21-P2-02` 在 v41 條文層已閉合。

**碼證**: `git diff --stat 38ca2137 834f41af -- docs/FFSTAT_SPEC.md` → 4 insertions／4 deletions；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → TEMPLATE PASS rc=0；`nl -ba docs/FFSTAT_SPEC.md | sed -n '91p'` → `M_tf＝K_max_tf` 且資格仍為 `M_tf＋F_max_tf＋500`（v40 之 `K＋2F＋500=7,155` 互斥已解除）；`nl -ba docs/FFSTAT_SPEC.md | sed -n '180p'` → 無 1,696 blocked 殘留（§N 末行為範圍外 winsor 說明）；`env PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat-r22-work/eligibility_r22_probe.py` → `btc_12h_rows=6656`、`estimate_max_warmup_bars_12h=2051`、`required_rows_M_plus_F_plus_500=4853 pass=True`、`overlap_worst_case_tail=4354 pass_500=True`、`row_margin=1803`；`handoffs/reconcile/20260926-ffstatauto-x-review-r21/synth.md` 處置與 v41 版本註記一致；brief fact `dead_feature_filter.py:77-82`（`notna().sum`／`nunique`）、`talib_wrapper.py:316,347` 逐字成立。

**類別**: other

**來源摘要**: docs/FFSTAT_SPEC.md#976f6c4f47d7; handoffs/reconcile/20260926-ffstatauto-x-review-r21/synth.md#r21; handoffs/20260927-ffstat-b4-redesign-rulings.md#8804fc628db0; handoffs/run_receipts/20260927-ffstat-longhist-download.log#download6656

---

## 必答

1. **(1a)** r21 三條：**CODEX-R21-P1-01**、**CODEX-R21-P2-02** 於 v41 已按 synth 採納修法閉合；**COMPOSER-R21-P3-00** 所覆 v40 範圍未被 v41 差分推翻，本家可閉合。**(1b)** P1-01：逐字核對 `docs/FFSTAT_SPEC.md:91`，`M_tf` 僅 `K_max_tf`，B 起點與 r21 反例算式 `K_max=2051 F_lower=2302 required=7155` 不再同時成立；資格改為 `2051+2302+500=4853≤6656`（probe 實跑）。P2-02：`git diff 38ca2137 834f41af` 刪除原 §N 末行 1,696 blocked 文案，與 §G⑦ 長歷史路徑一致。本家 r21 sentinel 仍為「v40 無 P0/P1」，v41 為其後修補而非否定。

2. **(2a)** v41 差分內**無**新 P0／P1。**(2b)** 否證：模板檢 PASS；longhist BTC 12h 6656 根與 §A 收據一致；未重跑預設全設定 FF（brief 禁止全設定 run）；§A:35 之「kline_cache 12h 皆 1696 根」為 2026-09-24 校準探針歷史事實，與 v41 刪 §N 限制不構成新互斥。

3. **(3a)** brief **assumed (i)**「`M_tf＝K_max_tf` 下預設全設定 BTC 12h 6,656 根資格可滿足」→ **成立**（下界 `F_max≥K_max+251` 時仍 `4853≤6656`，重疊 tail≥4354≥500）。**(ii)**「四類遮罩 mutant 仍必紅」→ **條文層成立**：v41 明示 B 比較自各欄首個有限值起且 `M_tf=K_max_tf` 時 A 於該列已有 ≥K_max 前史；刪 L1 遮罩／縮尾不遮／第④類不遮／recursive 係數 1.0 皆使 B 開頭未收斂而與已收斂之 A 相異（≥0.005 判準），未跑 1h 全 mutant FF（brief 禁分鐘級 run）。**(3b)** probe 輸出見 sentinel **碼證**；mutant 論證見 `docs/FFSTAT_SPEC.md:91` v41 括號內收斂對證敘述與 §G mutant 清單。

4. **(4a)** brief「我沒查」：**①** `cache_dir` 注入——**未命中** v41 新缺陷（`momentum/factories.py:236-251` 已支援；`scripts/verify_l1_warmup_requirements.py:49-50` 仍固定 `kline_cache.h5` 屬 Task 2.4 impl 接線，§G 已寫測試以儲存層指向）。**②** 5m×105,260 量測腳本記憶體／耗時——**未命中**本輪 SPEC 字面（v41 未改 eval cap）。**③** ADA 12h 較晚起點——**未命中**（§A 已列 ADA 6,171 根；跨標的取 max 仍為 BTC/ETH 6,656）。**(4b)** 同上檔案行號與 `handoffs/run_receipts/20260927-ffstat-longhist-download.log` 列數收據。

5. **(5a)** **是**，v41 可 **`VERDICT: proceed`**（r21 blocking 已修、本輪無新 P0/P1）。**(5b)** 無。

---

ASSUMPTIONS_VERIFIED: 已讀 brief、template、governance 類別集、v41 diff、r21 synth、R8/R9；longhist 列數與 eligibility probe；fact L7/TA-Lib 行號  
TESTS_RUN: `git diff --stat 38ca2137 834f41af -- docs/FFSTAT_SPEC.md`；`bash scripts/template_check.sh spec docs/FFSTAT_SPEC.md` → PASS rc=0；`env PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat-r22-work/eligibility_r22_probe.py` → rc=0；開跑／收尾 `git status --short -- momentum api scripts tests docs templates config` 無本輪新增 source 變更  
FAILURES_SEEN: probe 初回 `ConfigManager` import 路徑錯誤（`momentum.core`），改為 `momentum.FeatureEngineering.config_manager` 後 rc=0  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）  
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r22-composer.md  
TMP_CLEANUP: `rm -rf /tmp/ffstat-r22-work` 被環境安全閘拒絕（目錄可能仍在）；`/tmp/claude-501` 保留確認

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R21-P3-00

STATUS: DONE
