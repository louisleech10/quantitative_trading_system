# GAP-1 B1 code review 收斂檔之 RECONCILE-STAMP 核可（**重派**；工作區已凍結）

VERIFY-EXEMPT:doc-example:gap1-b1-stamp-v2-criteria

> 本檔為給委員的核可判準清單（提問／實測項目），非主委之 operational 結論。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md

## 🔴 為何重派（前輪 codex 判 BLOCKED，且判得對）
前輪（`20260818-GAP1-B1-STAMP-R11`）codex 具名 `CONCURRENT_WORKTREE`：**主委在你們驗收期間持續改工作區**
（寫 B2 檔案、patch mutation 探針、改 HANDOFF）⇒ 你驗的是移動中的標的。
其記錄之 `probe rc=2 at line 110`、`297 passed` 皆為**該瞬時狀態**，非穩定事實。
主委承認為流程違規（CLAUDE.md「執行端跑驗收時主控端不得動檔」應擴充為「亦不得跑會讀寫工作區的驗證腳本」）。

**現已凍結**：B1 修補（`660e4f91`）與 B2（`7f0decc8`）皆已 commit；本輪期間主委**不會**再動任何檔案。
composer／grok 前輪已 APPROVED 且 body hash 未變（`7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4`），
其戳記仍有效；**本輪只需 codex 之判定**（另兩家若願複驗亦可，重複 APPROVED 不影響檢查器）。

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`（放入 `## 戳記` 區段）。
body sha256 ＝ `7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md` 確認。

## 核可判準（逐項；任一不成立即 BLOCKED）
1. **0 掉項**：`bash scripts/completeness_check.sh --synth handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md --lock handoffs/reconcile/20260817-gap1-b1-review-r10/sources.lock`
2. **K1（你上一輪的反例是否真被封死）**：`git show 660e4f91 -- momentum/Optimization/objectives/strategy_backtest.py`；
   用你自己的 SwallowEngine 反例重跑（吞 kwargs 不回填 ⇒ 應 `ValueError`；回 `source="default_730"` ⇒ 亦應 raise）；
   `timeframe=None` legacy 路徑仍回 730 且不 raise。
3. **K2／K3（探針是否 fail-closed 且含 §V-9）**：`bash scripts/gap1_b1_mutation_probe.sh`
   （現為 **8 條**：§V-5／7／8／9a／9b／10／13／15；主委實跑 rc=0、八條皆 rc=1，
   receipt `handoffs/run_receipts/20260818T020000Z-gap1-b1b2-mutation-clean.log`）。
   前輪你看到的 `rc=2 at line 110` 請重測——現行 `bash -n` rc=0。
   另請實測 fail-closed：暫時弄紅某測試 ⇒ 探針應非零退出且**不**印成功訊息；**測完務必還原**
   （前輪有一個 `test_k2_baseline_intentional_break` 殘留在 `test_frequency.py`，後來已被還原；請確認你這輪不留殘留）。
4. **K4**：① 缺 kline 由 skip 改 fail ② `test_frequency.py` 有 re-export identity 斷言
   ③ registry 有 **G1-R10** ④ `rg -n 'A1-1\.\.A1-(15|18)'` 應為 0（前輪你指出 HANDOFF.md:13 殘留，已修）。
5. **未破壞既有（新基準）**：`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/momentum/Strategy/ tests/momentum/Optimization/ -q`
   ⇒ 應為 **297 passed, 2 failed**（B2 已併入；那 2 條為既有紅 `test_model_hyperparam_enhanced`，與本 epic 無關）。
   🔴 前輪 brief 寫 253 是 B2 尚未 commit 時之數，本輪更新為 297——這正是前輪標的移動之證據。
6. Verdict 與內文一致；主委對 A1-19 錯誤宣稱之處置（A1-20 明文作廢）是否誠實且足夠。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-18 sha256:<你實跑取得的完整 sha256> task:20260818-GAP1-B1-STAMP-R12
```
不核可時把 `APPROVED` 改 `BLOCKED`，理由寫你自己的產出檔。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改群集／處置／Verdict／附錄。
2. 判準 3 之 fail-closed 實測**必須還原**（可用 `git checkout -- <tracked file>`；工作區現為乾淨狀態）。
3. 不得改 SPEC／TODO／延伸檔／產品碼；不得 commit、不得 push。

## 產出
判定＋實跑 body_sha256＋判準 1–6 各一句（含 K1 反例與探針之實際 rc）。收尾清 /tmp workdir（保留 claude-501）。
