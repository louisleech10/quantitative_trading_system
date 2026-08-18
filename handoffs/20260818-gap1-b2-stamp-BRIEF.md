# GAP-1 B2 收斂檔 RECONCILE-STAMP（三家；探針**只由 codex 跑**）

VERIFY-EXEMPT:doc-example:gap1-b2-stamp-criteria

> 本檔為給委員的核可判準清單（實測項目），非主委之 operational 結論。

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap1-b2-review-r14/synth.md

## 背景
- 你們三家 R14 對 B2（commit `7f0decc8`）之 code review 共 21 條（codex 6／composer 5／grok 10），
  已收斂為十群集 **L1–L10**（stamp-target 之「群集／處置」段；0 掉項、債 `d38851a5…` 已銷）。
- 三家 Verdict 一致「需修補後進 B3」；嚴重度分歧一律**取較嚴版**、**全部本輪修、不登記殘留**。
- 修補 commit：**`0ab25f54`**（`git show 0ab25f54 --stat`）；延伸檔新增 **A1-21**
  （`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`；作廢 TODO ⑥b／母 SPEC:252、:319 之「annualized 計入 `n_rows_rejected`／記 `ledger_row_invalid`」字面）。
- 🔴 **工作區狀態**：主委已 commit＋push；本輪主委**不動任何檔、不跑探針**（前兩次戳記輪被 codex 正確 BLOCKED 之根因）。
  `scripts/governance_families.json` 有一處與本 epic 無關之既有 dirty（`active_stampers` 鍵，值＝`review_families`，行為 no-op），非本輪造成、請忽略。
- 🔴 **上一個 review 輪 composer 之自建多行程探針曾卡死 7 小時**（cursor-agent 不退出，害債銷不掉）——
  本輪若你自建探針，**一律加 timeout**（`subprocess.run(..., timeout=60)`／`thread.join(timeout=)`），不要用無界 barrier。

## 任務
對 `stamp-target` append `RECONCILE-STAMP`（`## 戳記` 區段）。
body sha256 ＝ `d5e6b1a88562fee7701aa69f6e14a241d0afab580779bdea1c8e9f751c92f113`
（`bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap1-b2-review-r14/synth.md`；請自行重跑確認）。

## 核可判準（逐條實測；每條貼 rc／計數）
1. **0 掉項**：`bash scripts/completeness_check.sh --synth handoffs/reconcile/20260818-gap1-b2-review-r14/synth.md --lock handoffs/reconcile/20260818-gap1-b2-review-r14/sources.lock` ⇒ rc=0；
   並肉眼確認你自己的每條 canonical ID 都被某群集 `**引用**` 且處置**對得上你的斷言**（不是只被點名）。
2. **你自己的反例是否真關閉**（章程 §B8：由原提出方重跑同一反例）——每家至少重跑自己 R14 貼過的反例：
   - codex：`CROSS_CONTEXT`（現應 `ContractViolation`）、`NONFINITE`（現應 rejected／raise）、`INVALID_ONLY`（現應 `reason=ledger_row_invalid`、`status=unavailable`）、
     `SNAPSHOT_COLLISION`（現應 False）、`UNKNOWN_TOP_LEVEL`／`ENUM invalid`（現應 raise）、`CACHE_MUTATION`（現應 False）。
   - composer：`snapshot_hash` 碰撞對（現應不同）、`Enum(str)` metric_unit（現應拒）、`ledger_path` 真實推導（`test_ledger_path.py` 走真 `MomentumConfig`）、annualized 單列（`n_rows_rejected=0` 且測試已顯式斷言）。
   - grok：TOCTOU（`test_duplicate_evaluation_id_race_writes_exactly_one_row`；並請確認拿掉 `fcntl.flock` 那行該測試會紅——可讀探針 receipt §V-7e，或自行 mutate 後**務必還原**）、
     NaN 進 `valid_sharpe_values`（現應 rejected）、`np.float64`／`np.int64` 對稱（現皆拒）、PIPE_BUF（多行程 4×8KB 測試）、全非法 reason。
3. **測試**：`venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ -q` ⇒ 期望 **135 passed** rc=0。
4. **mutation 探針（🔴 只由 codex 跑；composer／grok 讀 receipt，禁並行）**：
   `bash scripts/gap1_b1_mutation_probe.sh` ⇒ 期望 rc=0、**12 條**（§V-5／7／7b／7c／7d／7e／8／9a／9b／10／13／15）皆 `rc=1 且 FAILED>=1`、
   baseline 與 post-restore 皆 141 passed。主委 receipt：`handoffs/run_receipts/20260818T080000Z-gap1-b2-fix-mutation.log`。
   若探針印「已有另一個執行實例 exit 3」⇒ 是別家在跑，**不要**視為失敗，讀 receipt 即可。
5. **A1-21 與碼一致**：延伸檔 L1–L10 每條之「回歸鎖」測試名稱**真的存在**（`grep -n "def test_<name>"`）；
   `_EXPECTED_TOP_LEVEL_KEYS` 只列鍵名、不複列 `capability_status` 六值（`grep -c` 應為 0）。
6. **未破壞既有**：`venv/bin/python -m pytest tests/momentum/Strategy/ tests/momentum/Optimization/ -q` ⇒ 期望 **207 passed, 2 failed**
   （2 條為既有紅 `test_model_hyperparam_enhanced`，與本 epic 無關）。
7. Verdict 與內文一致；主委對「自己 brief 描述錯、Frozen 字面錯」之處置（A1-21 明文作廢＋顯式斷言鎖）是否誠實且足夠；
   「取較嚴版全部修、不留殘留」是否有任何一條其實沒修到（請找）。

## 戳記格式（逐字，單行；FAMILY ∈ codex／composer／grok）
```
RECONCILE-STAMP: <FAMILY> APPROVED 2026-08-18 sha256:<你實跑取得的完整 sha256> task:20260818-GAP1-B2-STAMP-R15
```
不核可就寫 `BLOCKED` 並具名理由——**若根因在主委側，請直說**。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改群集／處置／Verdict／附錄。
2. 任何 mutate／stash 實測**必須還原**（工作區除上述 governance_families.json 外應乾淨）。
3. 不得改 SPEC／TODO／延伸檔／產品碼；不得 commit、不得 push。
4. 自建探針一律加 timeout。

## 產出
判定＋實跑 body_sha256＋判準 2／3／4／6 之實際 rc 與計數＋一句 Verdict 理由。收尾清 /tmp workdir（保留 claude-501）。
