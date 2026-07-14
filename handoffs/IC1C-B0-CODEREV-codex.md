# IC1C-B0 Code Review — Codex

範圍：依 `docs/IC1C_NETIC_TODO.md:38-46` 審 `scripts/ic1c_{freeze,validate}_baseline.py`、`g_old.{json,sha256}` 與 `IC1C-B0-RESULT.md`；RECONCILE 三家戳記均 APPROVED。

## 驗收結論
- 偽碼符合：fixture 真 kline 入口 `freeze:105-124`；排序 Spearman/現行 turnover `:143-160`；真特徵 skipped 注入 `:163-177`；直呼 analyzer `:191-205`；lineage/strict JSON `:217-243`。
- validator 獨立：`validate:16-23,46` 僅 stdlib 與 fixture `FEATURE_NAMES`，未 import producer 或 `NetICAnalyzer`；內容檢查在 `:64-175`。
- 決定性：feature 排序 `freeze:152-159`、JSON keys 排序 `:234`；掃描無 random/sample/shuffle；目前 HEAD、fixture hash、artifact hash 與 JSON/sha 檔一致。
- G-OLD 抽驗：`g_old.json:1` 有 7 features；`oc_return=turnover_missing`、`hl_range=gross_ic_missing`；其餘 5 feature 與 sensitivity rows 均故意保留 `net_ic`；無 NaN/Infinity 字面。
- Scope：`git diff --name-only -- momentum api frontend tests/fixtures/ic_api_real_kline.py data_cache` 為空；B0 僅新增指定腳本、baseline 與必要交接/RESULT。

## Findings
- [MINOR][confidence 10/10] `scripts/ic1c_freeze_baseline.py:180-188` — `_default_net_ic_config` 複製 canonical YAML/schema 現值；目前逐值一致，但日後漂移時名稱「現行 default」可能失真。非 blocking：G-OLD 是舊態快照，Task 0.1 未要求動態載入 config。
- [MINOR][confidence 10/10] `scripts/ic1c_validate_baseline.py:92-98` — validator 只要求 `len(features) >= FEATURE_NAMES-2`，不要求 7 名全覆蓋；符合 TODO 明文下限，實際 artifact 已完整 7/7。
- [INFO][confidence 9/10] `scripts/ic1c_freeze_baseline.py:217-220` — lineage hash 涵蓋 fixture Python 檔但不涵蓋 `kline_cache.h5` bytes；TODO 僅指定 `fixture_sha256`，本批不阻塞。

ASSUMPTIONS_VERIFIED: Frozen Task 0.1、三家 APPROVED stamp、fixture 7 名、現行 config 值、analyzer 舊 schema、無隱藏隨機入口。
TESTS_RUN: `shasum -a 256 -c .../g_old.sha256` PASS；jq 7 features/2 skips/net_ic/nonfinite/lineage assertions PASS；strict literal scan PASS；import-independence scan PASS；runtime/fixture/data scope diff PASS。
FAILURES_SEEN: 隔離至 `/tmp` 的 freeze replay 兩次在 fixture bootstrap 超時，依 debug 上限停止；未改工作區，故未把 RESULT 的 freeze stdout 冒充本次重跑。
SCOPE_CHANGES: none；本審查唯一寫入為本檔。
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀審查）。
STATUS: DONE
CODE-REVIEW: APPROVE (0 BLOCKING)
