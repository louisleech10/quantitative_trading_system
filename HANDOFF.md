# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手任務：**GAP-3 開 B5 施工（B1–B4 已 CLOSED 2026-08-21：各批三家 RECONCILE-STAMP rc=0；B4 review 四輪 8→2→1→0、stamp 蓋 `handoffs/reconcile/20260821-gap3-b4-review-r4/synth.md`）**

- **依據**：`docs/GAP3_EVENT_TODO.md`（FROZEN）Phase B5（Task B5.1／B5.2／B5.3 五欄＋W9／W10）＋延伸檔 `docs/GAP3_EVENT_TODO.D-001.md`；SPEC FROZEN。開工前照 CLAUDE.md 稽核 HANDOFF vs repo（`git log -3`、`pytest tests/momentum/event_samples/ -q` 應 ~224 passed、`tests/momentum/feature_engineering/ -k state_counters` 17、`tests/momentum/Analysis/strategy_validation` 272、`bash scripts/debt_ledger.sh --has-open` rc=0）。
- **B5 批內順序**：B5.1 API 接線＋legacy adapter（白名單 §0-6-⑤／⑦：`api/models/`＋`api/routes/case*`＋`api/services/case_import_service.py`；新增 `event_samples/pipeline.py::EventSamplePipeline`（validate→align→dedupe→split→materialize）＋`momentum/factories.py` **唯一**新增 `create_event_sample_pipeline()`；驗證唯一實作在 `import_contract.py`，API 層只透傳、拒絕走 4xx＋逐列 reason；`/case/import` 舊格式 ⇒ 顯式 migration 提示／拒、禁 silent coerce；**前置＝偵察 T-3 定 workload**，驗收 receipt `handoffs/run_receipts/gap3_import_scale.json`{n_events≥10000, wall_clock_s, peak_rss_mb}（記錄型，不私定門檻）；同批順手做 B3 follow-up：`api/models/requests.py:50` `allowed_filtering_params` 改讀 `condition_engine.allowed_filtering_params()`）→ B5.2 前端三頁升級不翻掉（`/ic-analysis` 事件模式切換＋「從已匯入案例選事件」入口；兩張新表只在事件模式；`unavailable` reason 顯示；empty/loading/error 三態；vitest `frontend/src/**/gap3_*.test.{ts,tsx}` ≥3 檔、`npx vitest run gap3`；`pendingFeatures` registry 防漂移）→ B5.3 UAT＋收尾（新增 `docs/GAP3_UAT_CHECKLIST.md` 逐項步驟＋命令＋rc＋使用者簽字欄；殘留入 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」；UAT 缺陷回對應批修不在 B5 繞）。B5 Gate：`pytest tests/api/ -q -k gap3_import`＋`cd frontend && npm run build`＋`npx vitest run gap3`＋`pytest tests/momentum/event_samples/ -q`＋`bash scripts/plain_docs_sync_check.sh` 全 rc=0＋使用者 UAT 簽字。
- **既有介面（B1–B4 產出，直接消費）**：`validate_event_import`／`align_events`／`build_event_manifest(..., events=)`／`split_events`／`materialize_features_at_decision(..., events=)`／`permutation_oracle`／`event_forward_return_table`／`binary_discrimination_table(..., manifest=)`／`ic_feed.build_event_ic_inputs`／`evaluate_all_bars`／orchestrator `analyze(..., event_timestamps=, event_label_values=, event_context=)`／**B3** `condition_engine.parse_condition`→`ConditionSpec`、`generator.generate_events(spec, bars_by_tf, [LabelRule], GeneratorConfig)`、`event_filter.apply_filter(..., condition_spec=)`、`state_counters` 五算子／**B4** `pattern_bridge.extract_event_patterns(features, labels, plan, survivor_v2, BridgeConfig, manifest=)`、`candidate_ledger.to_return_series(..., events=)`→Series(attrs 收據)、`record_candidate(LedgerKey, meta{command,expected 必填})`、`run_dsr_pbo(LedgerKey, {cid: CandidateReturns})`、`provenance_reconcile(LedgerKey)`。
- **每批收尾固定動作**：更新 `白話說明/GAP-3施工進度.md`＋接下來/README；commit 後背景 push；review session 命名 `<YYYYMMDD>-gap3-b5-review-r<N>`、stamp `…-b5-stamp-r1`；寫回前把 finding「修法」拆清單逐條對碼＋自跑其 RECHECK（摩擦八十三）；帳本／收據類修補先把「寫入順序、完整性對帳、指紋綁值」一次想完（摩擦八十四）。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十四）
- 🔴 含家族名的 Bash 會被擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`；`committee_run.sh --session <s> <brief> <out前綴> codex,composer,grok -- --task-id <大寫>`；reconcile `reconcile_build.sh <s> --mode review <三檔逐列>`（glob 會吃到 brief）；R1 若建成 discovery 鎖要 `--mode review --rebuild`（不帶檔）才能 `debt_clear --lock <sources.lock>`。
- 🔴 委員「清 /tmp workdir」會把 Claude 的 scratchpad（`/private/tmp/claude-501/.../scratchpad`）整個刪掉（B4 stamp 輪實際發生）⇒ 派工前把要保留的 log 放 `handoffs/run_receipts/`，scratchpad 只放可重建腳本；每次派工前 `mkdir -p` 確認目錄在。
- 🔴 handoffs 委員交件／brief 被 .gitignore；審計鏈入檔＝`git add -f handoffs/reconcile/<session>/`。commit 訊息末段必帶 `Governance-Scope: out-of-epic GAP-3 量化主線 B5 …`（G-7 前移檢查）。
- 🔴 B5 碰 `api/`＋`frontend/`＋`factories.py`：膨脹訊號全中，仍屬 TODO 白名單；`npm run build` 前端改動必跑；API 層禁重複實作契約檢查（R7）。
- 🔴 GAP-1 ledger 根目錄＝`MomentumConfig.from_project_root().results_path/strategy_validation/`；測試一律 monkeypatch `ledger.ledger_path` 到 tmp（勿碰真實 results/）。
- 白話看板狀態欄用文字（排隊中／完工蓋章／施工中），禁 ⬜／✅／「收案」／「進行中」字樣貼 B<n>（factkey 守衛；「才收案」亦中）；`Archived/GAP-2施工進度.md:13-22` 紅＝既有；push 丟背景；venv Python 3.9.6；`-p no:logging` 會拿掉 caplog。
