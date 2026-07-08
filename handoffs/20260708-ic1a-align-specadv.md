# 20260708 ic1a-align-specadv handoff

- 正在做: 已完成 `docs/IC_PHASE1_1A_ALIGN_SPEC.md` + TODO adversarial review。
- 產出: `handoffs/IC1A-ALIGN-SPECADV-codex.md`。
- Verdict: REJECT；ADV-CODEX-1~7 為 BLOCKING，ADV-CODEX-8~9 為 NON-BLOCKING。
- 待辦: Claude/作者需修 consumer-map、gap/freq/bar-ordinal 語義、legacy HDF5/RangeIndex、Golden 寫 data_cache 風險、M5 mutation、外部 label horizon metadata。
- 阻塞: SPEC line 3 引用 `handoffs/IC1A-CUTS-ORDER-claude.md` 不存在；實際讀到 `handoffs/IC1A-REMAINING-CUTS-ORDER-claude.md`。
- 本次決策: Phase 3 cut2 oracle 收斂建議 deferred，避免 MultiIndex/per-symbol gate API 返工。
- 踩坑提醒: `data_cache/features/registry.json` 有 V2 manifests；但 API materialize path 會寫 `data_cache/reports/ic_ingest_cache`，驗證設計需避開。
- VERIFY: `rg`/`nl -ba` 靜態讀 consumer/caller；read-only Python 讀 kline HDF5 timestamp，確認 `data_cache/kline_cache.h5` ETHUSDT/1h 有 gap 且 `pd.infer_freq=None`。
- 測試: 未跑 pytest；任務為 read-only adversarial review。
