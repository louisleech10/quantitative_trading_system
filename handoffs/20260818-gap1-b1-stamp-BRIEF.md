# GAP-1 B1 code review 收斂檔之 RECONCILE-STAMP 核可（含 K1–K4 修補落地之機械核可）

VERIFY-EXEMPT:doc-example:gap1-b1-stamp-brief-criteria

> 本檔為**給委員的核可判準清單**：各判準是「請你實測的項目」，不是主委的 operational 結論；
> 實測結果在各家戳記產出檔與收斂檔戳記區。
> 🔴 本輪 codex 判 **BLOCKED**（`CONCURRENT_WORKTREE`）——主委在戳記期間持續改工作區，
> 使其驗的是移動中的標的；已 commit 凍結後重派（見 `20260818-gap1-b1-stamp-v2-BRIEF.md`）。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md` 重跑確認。

## 背景
本檔為 **B1 實作 code review**（`20260817-GAP1-B1-REVIEW-R10`）之收斂：三家 10 findings，
Verdict 一致「需修補後進 B2」，收斂為四群集 K1–K4。修補已落在 commit `660e4f91`。
本輪戳記**兼任修補驗收**：通過即進 B2（Task 2.1–2.3）。

## 核可判準（逐項查；任一不成立即 BLOCKED）
1. **0 掉項**：`bash scripts/completeness_check.sh --synth handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md --lock handoffs/reconcile/20260817-gap1-b1-review-r10/sources.lock`
2. **K1（你們的反例是否真被封死）**：`git show 660e4f91 -- momentum/Optimization/objectives/strategy_backtest.py`
   看 `_resolve_metrics_periods`；**請用你自己上一輪的反例 engine 重跑**
   （`**kwargs` 吞 timeframe＋不回填 annualization ⇒ 應 `ValueError`；回 `source="default_730"` ⇒ 亦應 raise）。
   另確認 `timeframe=None` 之 legacy 路徑仍回 730 且不 raise（不得為修這條而弄壞既有行為）。
3. **K2（探針是否真 fail-closed）**：`scripts/gap1_b1_mutation_probe.sh` 之 baseline 與 post-restore
   是否都有 `rc≠0 ⇒ exit 1`？**請實測**：暫時把某測試改壞使 baseline 紅，跑探針，確認它以非零退出且**不**印
   「全部 mutation 皆轉紅」；測完還原。
4. **K3（§V-9 是否真進探針且可證偽）**：探針是否含 §V-9a／9b？請直接跑
   `bash scripts/gap1_b1_mutation_probe.sh`（約 1 分鐘，自我還原），回報七條之 rc 與 FAILED 數。
5. **K4**：① `test_returns_contract.py` 缺 kline 是否已由 `skip` 改 `fail`（可 `mv` 走 kline 實測後還原，
   或讀碼確認）② `test_frequency.py` 是否有 identity 斷言 ③ registry 是否有 **G1-R10**（Protocol 漂移殘留）
   ④ `rg -n 'A1-1\.\.A1-(15|18)'` 是否已清零。
6. **未破壞既有**：`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/momentum/Strategy/ tests/momentum/Optimization/ -q`
   應為 **253 passed, 2 failed**（那 2 條為既有紅：`test_model_hyperparam_enhanced`，與本批無關）。
7. Verdict 與內文一致；主委對 A1-19 錯誤宣稱之處置（A1-20 明文作廢該句）是否誠實且足夠。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-18 sha256:<你實跑取得的完整 sha256> task:20260818-GAP1-B1-STAMP-R11
```
不核可時把 `APPROVED` 改 `BLOCKED`，理由寫你自己的產出檔。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改群集／處置／Verdict／附錄。
2. 不得改 SPEC／TODO／延伸檔／程式碼（第 3、5 點之實測請**還原**）；不得 commit、不得 push。

## 產出
判定＋實跑之 body_sha256＋判準 1–7 各一句結論（含你重跑 K1 反例與探針之實際 rc）。
收尾清 /tmp workdir（保留 claude-501）。
