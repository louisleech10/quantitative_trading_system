# GAP-1 B1 stamp v2 — composer（R12 複驗）

**task-id**: `20260818-GAP1-B1-STAMP-R12`  
**family**: composer  
**stamp-target**: `handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md`  
**判定**: **APPROVED**

## body sha256（實跑）

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md
→ 7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4
```

與 brief 宣告一致。

## 判準 1–6（各一句）

1. **0 掉項**：`completeness_check.sh --synth … --lock …` → COMPLETENESS PASS（codex 5/5、composer 1/1、grok 4/4；dropped-ID+schema+lock+body-hash 全綠）。
2. **K1**：`660e4f91` 已加 `_resolve_metrics_periods` fail-loud；`_SwallowEngine`／`_WrongSourceEngine` 參數化測試 2 passed（`ValueError`）；`test_objective_legacy_path_keeps_730_without_timeframe` 未宣告 timeframe 仍回 730 且不 raise。
3. **K2／K3**：`bash scripts/gap1_b1_mutation_probe.sh` → probe_rc=0；baseline rc=0（99 passed）；8 條 §V-5／7／8／9a／9b／10／13／15 皆 rc=1；post-restore rc=0；`bash -n` rc=0。fail-closed 實測：暫加 `test_composer_failclosed_probe_r12` 弄紅 baseline → probe rc=1、印「baseline 非綠…中止」、**無**「全部 mutation」成功訊息；`git checkout -- test_frequency.py` 還原後無殘留。
4. **K4**：`test_returns_contract.py` 缺 kline 改 `pytest.fail`；`test_frequency.py` 有 re-export identity 斷言；registry 具名 **G1-R10**；`rg 'A1-1\.\.A1-(15|18)'` → 0 命中。
5. **未破壞既有**：`pytest tests/momentum/Analysis/strategy_validation/ tests/momentum/Strategy/ tests/momentum/Optimization/ -q` → **297 passed, 2 failed**（`test_model_hyperparam_enhanced` 兩條既有紅，與本 epic 無關）。
6. **Verdict 一致**：收斂檔 Verdict「需修補後進 B2」與 K1–K4 處置對齊；A1-19 錯誤宣稱於 synth K1 與延伸檔 **A1-20** 明文作廢並改寫 K1 fail-loud 規則，誠實且足夠。

## 戳記（已 append 至 synth `## 戳記`）

```
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R12
```

## /tmp 收尾

嘗試刪除本輪 receipt／probe log（`gap1-*`、`b2commit*`、`v7_patch.py` 等）遭 sandbox 阻擋；`claude-501/` 未動。請本機手動：`rm -f /tmp/gap1-* /tmp/b2commit* /tmp/v7_patch.py`
