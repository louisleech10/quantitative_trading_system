# GAP-1 B1 RECONCILE-STAMP — composer

**task-id**: `20260818-GAP1-B1-STAMP-R11`  
**family**: composer  
**stamp-target**: `handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md`  
**判定**: **APPROVED**

## body_sha256（實跑）

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md
→ 7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4
```

與 BRIEF 宣告值一致。

## 判準 1–7（各一句）

1. **0 掉項**：`completeness_check.sh --synth … --lock …` → `COMPLETENESS PASS(dropped-ID+schema+lock+body-hash 層)`，codex 5／composer 1／grok 4 全在 synth。
2. **K1**：`_SwallowEngine`（**kwargs 吞 timeframe、無 annualization）與 `_WrongSourceEngine`（`source="default_730"`）皆 `pytest.raises(ValueError)`；`test_objective_legacy_path_keeps_730_without_timeframe` 仍回 730 且不 raise（3 passed rc=0）。
3. **K2**：暫改 `test_frequency.py` 使 baseline 紅 → `gap1_b1_mutation_probe.sh` **probe_rc=1**，印「baseline 非綠…中止」，**未**印「全部 mutation 皆轉紅」；已還原。
4. **K3**：探針七條全轉紅且 post-restore 全綠：**§V-8** rc=1 FAILED=8、**§V-15** rc=1 FAILED=5、**§V-5** rc=1 FAILED=7、**§V-10** rc=1 FAILED=1、**§V-13** rc=1 FAILED=1、**§V-9a** rc=1 FAILED=1、**§V-9b** rc=1 FAILED=1；baseline/post-restore 皆 rc=0；腳本 rc=0。
5. **K4**：① `_real_backtest` 缺 kline 為 `pytest.fail`（非 skip）② `test_reexport_is_identical_object_to_core_implementation` 三名稱 `is` core ③ registry **G1-R10** 已登記 ④ `rg 'A1-1\.\.A1-(15|18)'` 於 `docs/`、`momentum/` 零命中（TODO 已統一 A1-1..A1-20）。
6. **未破壞既有**：`pytest tests/momentum/Analysis/strategy_validation/ tests/momentum/Strategy/ tests/momentum/Optimization/ -q` → **253 passed, 2 failed**（`test_model_hyperparam_enhanced` 兩條既有紅）。
7. **Verdict／A1-19 處置**：synth Verdict「需修補後進 B2」與 K1–K4 處置一致；延伸檔 **A1-20** 明文作廢 A1-19 末段「不靜默 730」宣稱並記錄兩家反例，誠實且足夠。

## 戳記（已 append 至 synth `## 戳記`）

```
RECONCILE-STAMP: composer APPROVED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R11
```
