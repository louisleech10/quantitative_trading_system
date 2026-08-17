# GAP-1 B1 RECONCILE-STAMP — grok

**task-id**: `20260818-GAP1-B1-STAMP-R11`  
**family**: grok  
**stamp-target**: `handoffs/reconcile/20260817-gap1-b1-review-r10/synth.md`  
**判定**: **APPROVED**  
**body_sha256（實跑）**: `7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4`  
（與 brief 宣稱一致；`bash scripts/reconcile_body_hash.sh …` 重跑得同值）

## 判準 1–7

1. **0 掉項**：`completeness_check.sh --synth … --lock …` → **COMPLETENESS PASS**，`completeness_rc=0`（codex 5/5、composer 1/1、grok 4/4）。
2. **K1 反例封死（自跑）**：`_SwallowEngine`（`**kwargs` 吞 timeframe、無 annualization）→ `ValueError`「未回填…拒絕靜默以 730」；`_WrongSourceEngine`（`source="default_730"`）→ `ValueError`「source='default_730' != 'resolved'」；`timeframe=None` legacy → **不 raise**、`_resolve_metrics_periods(None)==730`。回歸鎖 `test_objective_fails_loud_when_engine_swallows_timeframe` 存在於 `660e4f91`。
3. **K2 探針 fail-closed（實測）**：baseline／post-restore 均有 `rc≠0 ⇒ exit 1`。暫時於 `test_frequency.py` 注入必紅斷言後跑探針 → **`k2_probe_rc=1`**，印「baseline 非綠…中止」，**未**印「全部 mutation 皆使測試轉紅」；測完已還原。
4. **K3 §V-9 進探針（實跑）**：`bash scripts/gap1_b1_mutation_probe.sh` → **`probe_rc=0`**  
   - baseline rc=0（83 passed）  
   - §V-8 rc=1 FAILED=8；§V-15 rc=1 FAILED=5；§V-5 rc=1 FAILED=7；§V-10 rc=1 FAILED=1；§V-13 rc=1 FAILED=1；**§V-9a** rc=1 FAILED=1；**§V-9b** rc=1 FAILED=1  
   - post-restore rc=0（83 passed）  
   （中途曾與 K2 並行污染，已 `git checkout` 還原目標檔後單獨重跑得上列乾淨結果。）
5. **K4**：① `test_returns_contract.py` 缺 kline → `pytest.fail`（非 skip）；② `test_reexport_is_identical_object_to_core_implementation` 三名稱 identity；③ registry 有 **G1-R10**；④ `grep -nE 'A1-1\.\.A1-(15|18)'` 於 TODO／延伸檔／registry／package docstring → **0 命中**（rc=1）。
6. **未破壞既有**：`pytest tests/momentum/Analysis/strategy_validation/ tests/momentum/Strategy/ tests/momentum/Optimization/ -q` → **`2 failed, 253 passed`**（既有紅：`test_overfitting_detection_pruned`、`test_trial_user_attrs_recorded`；與本批無關）。
7. **Verdict／A1-20**：內文 K1–K4 與「需修補後進 B2」一致；A1-20 明文作廢 A1-19「不靜默 730」之錯誤宣稱，處置誠實足夠。

## 戳記（已 append 至 stamp-target `## 戳記`）

```
RECONCILE-STAMP: grok APPROVED 2026-08-18 sha256:7c01a8e7af8d9ef9d580505651827c6cc677277b76dbe7fcf79db717ff64e8e4 task:20260818-GAP1-B1-STAMP-R11
```

## 範圍

- 只 append 戳記；未改群集／處置／Verdict／附錄；未改 SPEC／TODO／延伸檔／程式碼（K2 實測已還原）；未 commit／push。
