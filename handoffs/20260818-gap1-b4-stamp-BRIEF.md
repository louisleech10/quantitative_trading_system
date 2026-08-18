# GAP-1 B4 收斂檔 RECONCILE-STAMP（三家；探針**只由 codex 跑**）——本輪 PASS 即 GAP-1 全票收工

VERIFY-EXEMPT:doc-example:gap1-b4-stamp-criteria

> 本檔為給委員的核可判準清單（實測項目），非主委之 operational 結論。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap1-b4-review-r18/synth.md

## 背景
- 你們三家 R18 對 B4（commit `763b9d56`）之 code review 共 13 條（codex 6／composer 2／grok 5），已收斂為六群集 **N1–N6**（stamp-target「群集／處置」段；0 掉項、債 `4fa301c3…` 已銷）。
  三家 Verdict 一致「需修補後收工」；N2 之修法分歧（codex 全 N 母體 vs grok 保留縮小母體）**取守 Frozen 字面**（見 N2 裁決）；全部本輪修、不登記殘留（G1-R11 為 B1 既有語意之具名殘留，非本批漏修）。
- 修補 commit：**`00965160`**（`git show 00965160 --stat`）；延伸檔 **A1-24**（覆寫 A1-23 #1／#2／#6）；registry 新增 **G1-R11**。
- 🔴 **工作區狀態**：主委已 commit＋push；本輪主委**不動任何檔、不跑探針**。`scripts/governance_families.json` 有既有 no-op dirty，請忽略。
- 🔴 自建探針**一律加 timeout**；產出檔尾最後一行 `STATUS: DONE`。

## 任務
對 `stamp-target` append `RECONCILE-STAMP`（`## 戳記` 區段）。
body sha256 ＝ `c69a22c07dfb1c07929ee36b2781474e505dc460c5b8395844f175d91a43debc`
（`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap1-b4-review-r18/synth.md`；請自行重跑確認）。

## 核可判準（逐條實測；每條貼 rc／計數）
1. **0 掉項**：`bash scripts/completeness_check.sh --synth handoffs/reconcile/20260818-gap1-b4-review-r18/synth.md --lock handoffs/reconcile/20260818-gap1-b4-review-r18/sources.lock` ⇒ rc=0；
   肉眼確認你自己的每條 canonical ID 都被某群集 `**引用**` 且處置**對得上你的斷言**。
2. **你自己的反例是否真關閉**（章程 §B8：原提出方重跑同一反例）：
   - codex：`reason=obj.payload`／`reason=obj["dynamic_key"]`／區域 f-string 遮蔽 ⇒ 現應 rc=1（`test_wiring_check.py::test_mutation_n1_non_whitelisted_passthrough_is_unresolved` 五組）；
     `UNUSED="new_reason"`／docstring 死枚舉 ⇒ 現應 rc=1（`test_mutation_n1_dead_enum_via_unused_constant_or_docstring_is_red`）；
     PBO 分母＝`len(path_valid)+1`、任一 OOS 非有限即 skip（`test_non_champion_oos_degenerate_skips_path_keeps_denominator`／`test_denominator_is_path_valid_count_plus_one`）；
     exclusions 每候選每 path 至多 +1（④d 現斷言 ==2）；雙冠手算（`test_double_champion_takes_smallest_index_hand_computed`）；近常數欄逐位相等（`test_vectorized_sharpe_matches_compute_sharpe` 之 `0.01` 欄 `==`）。
   - composer：雙冠手算 ω=ln(2/3)／ln(7/3)；`0.01` 近常數欄 vec==ref（逐位）。
   - grok：`reason=data["x"]`／`reason=o.reason`（現：`o.reason` 為白名單 `.reason` 形態 ⇒ 仍放行——請判定這是否為可接受之語意；`data["x"]` ⇒ rc=1）；exclusions 雙計已除；分母守字面；golden 三檔皆經 `_golden.py` 驗 sha。
3. **測試**：`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` ⇒ 期望 **280 passed** rc=0。
4. **mutation 探針（🔴 只由 codex 跑）**：`bash scripts/gap1_b1_mutation_probe.sh` ⇒ rc=0、**20 條**皆 `rc=1 且 FAILED>=1`、baseline／post-restore 277 passed。
   主委 receipt：`handoffs/run_receipts/20260818T110000Z-gap1-b4-fix-mutation.log`。探針約 5 分鐘（含 wiring 測試）；印 `exit 3` ＝別家在跑，讀 receipt 即可。
5. **wiring 閘**：`bash scripts/strategy_wiring_check.sh` ⇒ rc=0 `✓ W1..W4`；`bash -n scripts/strategy_wiring_check.sh` rc=0。
6. **decoupling／治理連動**：`python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` ⇒ BASELINE OK；`grep -r "from api\." momentum/` ⇒ 0；`bash scripts/gov_check.sh --fast` ⇒ ✅。
7. **A1-24 與碼一致**：N1–N6 每條之「回歸鎖」測試名**真的存在**；`pbo.py` 之 `GuardResult`／`guard.reason`；`_sharpe_pp_1d`；registry G1-R11 三值形式（needs-research）與觸發條件具名。
8. **收工複核（TODO B4 Gate）**：registry「GAP-1 待補完」G1-R1..R7／R9／R10／R11 逐項觸發條件**未成立**（請逐條看一眼）；Verdict 與內文一致；「取較嚴版全部修、不留殘留」是否有任何一條其實沒修到。

## 戳記格式（逐字，單行；FAMILY ∈ codex／composer／grok）
```
RECONCILE-STAMP: <FAMILY> APPROVED 2026-08-18 sha256:<你實跑取得的完整 sha256> task:20260818-GAP1-B4-STAMP-R19
```
不核可就寫 `BLOCKED` 並具名理由——**若根因在主委側，請直說**。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改群集／處置／Verdict／附錄。
2. 任何 mutate／stash 實測**必須還原**。
3. 不得改 SPEC／TODO／延伸檔／產品碼；不得 commit、不得 push。
4. 自建探針一律加 timeout；產出檔尾 `STATUS: DONE`。

## 產出
判定＋實跑 body_sha256＋判準 2／3／4／5／6 之實際 rc 與計數＋一句 Verdict 理由。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
