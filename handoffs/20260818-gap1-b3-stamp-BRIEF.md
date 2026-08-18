# GAP-1 B3 收斂檔 RECONCILE-STAMP（三家；探針**只由 codex 跑**）

VERIFY-EXEMPT:doc-example:gap1-b3-stamp-criteria

> 本檔為給委員的核可判準清單（實測項目），非主委之 operational 結論。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap1-b3-review-r16/synth.md

## 背景
- 你們三家 R16 對 B3（commit `cbd9ec69`）之 code review 共 12 條（codex 4／composer 2／grok 6），已收斂為六群集 **M1–M6**
  （stamp-target「群集／處置」段；0 掉項、債 `5f795d52…` 已銷）。三家 Verdict 一致「需修補後進 B4」；分歧取較嚴、**全部本輪修、不登記殘留**。
- 修補 commit：**`e20776ca`**（`git show e20776ca --stat`）；延伸檔新增 **A1-22**（`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`；
  route 例外分類覆寫 A1-16 第 2 點字面、契約 `n_source_values` 使頂層鍵 16→17）。
- 🔴 **工作區狀態**：主委已 commit＋push；本輪主委**不動任何檔、不跑探針**。`scripts/governance_families.json` 有既有 no-op dirty，請忽略。
- 🔴 自建探針**一律加 timeout**；產出檔尾最後一行寫 `STATUS: DONE`（cx_run 看門狗以此判完成）。

## 任務
對 `stamp-target` append `RECONCILE-STAMP`（`## 戳記` 區段）。
body sha256 ＝ `b367b5722c772db7902138f4cf38bfe090e6f5b95ed9498e8210bc8d2d4c4774`
（`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap1-b3-review-r16/synth.md`；請自行重跑確認）。

## 核可判準（逐條實測；每條貼 rc／計數）
1. **0 掉項**：`bash scripts/completeness_check.sh --synth handoffs/reconcile/20260818-gap1-b3-review-r16/synth.md --lock handoffs/reconcile/20260818-gap1-b3-review-r16/sources.lock` ⇒ rc=0；
   肉眼確認你自己的每條 canonical ID 都被某群集 `**引用**` 且處置**對得上你的斷言**。
2. **你自己的反例是否真關閉**（章程 §B8：由原提出方重跑同一反例）：
   - codex：`_kurt3_returns` 之 `sps.skew==0`／`kurtosis(fisher=False)==3`（現應成立）；`_ledger` fixture 不變式（現應成立）；IVA 5xx 後儲存目錄無 json（`test_wiring_error_negative_t_years_is_5xx_not_reporter_failed`）；`factories.py:564` 之多餘 import（現應不存在，`grep -n "strategy_validation.reporter import" momentum/factories.py` 應恰 2 處：TYPE_CHECKING＋專用 factory）。
   - composer：裸 `ValueError` ⇒ 現應 **500**（`test_bare_value_error_from_reporter_is_5xx_not_400`；你的 `_composer_b3_ve_probe.py` 若還在可重跑）；IVA detail 現應恰為 `strategy_validation reporter argument error`（不再 `Internal error:` 前綴）。
   - grok：裸 `ValueError`→500；orphan 檔（IVA 5xx 後 `tmp.glob('*.json')` 應為空）；`n_source_values` 三值在契約且 `validate_against_contract` 拒 `made_up`（`test_n_source_values_are_contract_enum_and_validated`）；kurt=3 序列。
3. **測試**：`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` ⇒ 期望 **224 passed** rc=0；
   `venv/bin/python -m pytest tests/test_phase6_end_to_end.py tests/test_frontend_integration.py -q` ⇒ 9 passed。
4. **mutation 探針（🔴 只由 codex 跑；composer／grok 讀 receipt，禁並行）**：`bash scripts/gap1_b1_mutation_probe.sh` ⇒ rc=0、**17 條**皆 `rc=1 且 FAILED>=1`、baseline／post-restore 221 passed。
   主委 receipt：`handoffs/run_receipts/20260818T093000Z-gap1-b3-fix-mutation.log`。探針印 `exit 3` ＝別家在跑，讀 receipt 即可。
5. **A1-22 與碼一致**：M1–M6 每條之「回歸鎖」測試名**真的存在**；契約頂層鍵恰 17（`contract_top_level_keys()`）；`_EXPECTED_TOP_LEVEL_KEYS` 含 `n_source_values`；
   route 之 `except HTTPException: raise` 位於 `except ValueError` **之前**；reporter 呼叫位於 `pipeline_file` 寫入**之前**。
6. **decoupling**：`python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` ⇒ BASELINE OK；`grep -r "from api\." momentum/` ⇒ 0。
7. Verdict 與內文一致；「取較嚴版全部修、不留殘留」是否有任何一條其實沒修到（請找）；A1-22 對 A1-16 第 2 點之覆寫是否誠實。

## 戳記格式（逐字，單行；FAMILY ∈ codex／composer／grok）
```
RECONCILE-STAMP: <FAMILY> APPROVED 2026-08-18 sha256:<你實跑取得的完整 sha256> task:20260818-GAP1-B3-STAMP-R17
```
不核可就寫 `BLOCKED` 並具名理由——**若根因在主委側，請直說**。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改群集／處置／Verdict／附錄。
2. 任何 mutate／stash 實測**必須還原**。
3. 不得改 SPEC／TODO／延伸檔／產品碼；不得 commit、不得 push。
4. 自建探針一律加 timeout；產出檔尾 `STATUS: DONE`。

## 產出
判定＋實跑 body_sha256＋判準 2／3／4／6 之實際 rc 與計數＋一句 Verdict 理由。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
