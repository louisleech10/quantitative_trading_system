# FF-STAT TODO 審查 r24：SPEC v44 之 TODO 同步（Task 2.3 改寫、Task 2.4 新增）

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R24

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R24-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r23 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面；多個 ID 以半形逗號分隔）。零 finding 用 `## <FAMILY>-R24-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run、不跑 §G⑦ 雙起點全設定測試；探針用真實 K 線小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git show b0cf1d8d --stat` 與其 diff：`docs/manifests/FFSTAT.json`（test_files、script_acceptance、contract_jsons、stub_modules、run_receipts、batch_card 之 touches／callers_now／gate_cmd／forbidden／not_executable／coverage_risk／risk_mitigation）、`momentum/FeatureEngineering/preprocessing/stable_mask.py`（新空殼）、`tests/feature_engineering/test_ffstat_stable_start.py`、`test_ffstat_warmup_table.py`、`test_ffstat_golden.py`（§G②／⑦ 新增）、`ffstat_helpers.py`（`dual_start_report`）、`tests/_golden/ffstat/contract.json`、`retired_tests.json`、`nan_propagation_classes.json`、`handoffs/run_receipts/ffstat_probes/{warmup_table_coverage,stable_start_receipts,freeze_baseline_nostart}.py`、`handoffs/run_receipts/20260927-ffstat-longhist-download.json`。
- SPEC：`docs/FFSTAT_SPEC.md` v44（v44 為寫 TODO 時之事實更正：`effective_output_start` 保留且只於 `output_start_source == "user"` 時寫入——請判此更正是否成立）；§P「TODO 同步必含清單」。
- r23 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r23/synth.md`（codex 請確認 CODEX-R23-P2-01 已閉合：§G⑦ 長歷史 `validate_continuity=False` 與缺口收據）。
- **使用者裁定（不重議）**：R1–R9（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）；使用者 2026-09-27 同意 v43 定案並進入 TODO 同步。
- 生成指引：`templates/TODO_GENERATION_PROMPT.md`（五類落點、每條邊界恰一具名測試、每檔至少一 `test_mutation_*`、實作前應紅、不得 skip／xfail）。

## 本 brief 前提
fact-verified: 三個測試檔 `venv/bin/python scripts/mutation_probe_static.py <檔>` 皆 rc=0；`bash scripts/template_check.sh todofmt docs/manifests/FFSTAT.json` → TODOFMT PASS；`pytest --collect-only` 三檔＋既有 ffstat／b6 共 236 支可收集。
fact-verified: 純函式子集實跑為紅且原因為 NotImplementedError、倍數表無 period_keys、預熱開關未刪、舊測試未退役（主委實跑 2026-09-27）。
assumed: SPEC v44 之每條驗證項與邊界（Task 2.3 ①–⑫、邊界①–④；Task 2.4 驗證與邊界①①′②③、CDL 映射；§G②⑦；§V v32–v42 mutant）皆恰有對應之具名測試或 not_executable 項。
→ 否證觀測：某 SPEC 驗證項或邊界無對應測試、或兩項對到同一測試而使其一不可證偽。／我跑了：只以 coverage_risk 之對照自查。
assumed: 各 mutation 測試於實作完成後（主測試轉綠）會真實翻轉，不是恆過；特別是實作前即綠之三支（`test_mutation_calibration_rows_not_masked_is_caught`、`test_mutation_dead_filter_full_denominator_is_caught`、`test_mutation_config_hash_without_policy_is_caught`）。
→ 否證觀測：某 mutant 在正確實作下仍不使主測試紅（mutant 替換之對象不在主測試之呼叫路徑上）。／我跑了：無（實作前無法驗）。

## 攻擊面
- **已排除**：SPEC v43 以前已收斂之條文內容（本輪審 TODO 對 SPEC 之追溯與可執行性，非重議 SPEC）；使用者裁定。
- **我沒查**：①`_ast_step_functions` 之前綴規則（compute／_apply_／apply／align）是否漏列 L2–L6.5 之實際計算入口（如 rolling_aggregator 內私有方法、tf_aligner 之 merge_asof 路徑）；②`dual_start_report` 以 `generate_features(start_date=None)` 跑預設全設定於 8 GB 下之可行性與耗時；③`freeze_baseline_nostart.py` 於 `02350721^` worktree 之 API 相容性（`create_feature_factory`、`fast_payload` 當時是否存在）；④測試引用之 metadata 鍵（`stable_start`、`warmup_doubling`、`column_set_reasons`、`start_dependent_columns`）是否皆已落於契約；⑤`test_every_l1_output_column_passes_output_point_contract` 以 `_layer0_data_ingestion`／`_layer1_atomic_indicators` 之簽名是否正確。

## 必答（成對）
1. **(1a)** 本家 r23 條目是否閉合？**(1b)** 逐條核對結果。
2. **(2a)** TODO 對 SPEC v44 之追溯是否完整（每條驗證項與邊界恰一具名測試）？**(2b)** 缺漏或重複之清單與 SPEC 出處。
3. **(3a)** 兩條 assumed 各判成立或不成立？**(3b)** 碼證或實跑。
4. **(4a)** 「我沒查」①–⑤ 各有無命中？**(4b)** 碼證。
5. **(5a)** v44 事實更正是否成立？**(5b)** 碼證。
6. **(6a)** 本版 TODO 可否放行實作（`VERDICT: proceed`）？**(6b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 使用者定死「任何每次都會跑的檢查，單次必須秒級」；驗收測試不在此限，但須於 coverage_risk 記實測時長。
2. 威脅模型＝**意外漂移**；每條 P0／P1 須附可重現之輸入或操作序列。
3. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由。
4. 研究設計不得寫死 24h／UTC／加密貨幣特有假設。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api scripts tests docs templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
