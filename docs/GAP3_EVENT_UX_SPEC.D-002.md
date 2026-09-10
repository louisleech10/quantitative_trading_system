# GAP3_EVENT_UX_SPEC — D 延伸 002（`SPLITUNIFY`：切分權威改由 K 線 holdout 決定，事件切分降為投影）

BASE: docs/GAP3_EVENT_UX_SPEC.md @ e0f3cb52
PREDECESSOR: docs/GAP3_EVENT_UX_SPEC.D-001.md

改什麼: 事件切分**不再自行決定邊界**——`split_authority == "kline_holdout"`，`EventSplitPlan` 降為投影容器；拿不到 post-trim feature universe 的匯入流程只能明示 `event-study-only`，不得按事件數另切並宣稱 OOS。

為什麼: 票 `SPLITUNIFY`（使用者 2026-09-10 裁定「切法由你跟委員討論共識」）；consult 收斂 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`（D1–D8，body-hash `120b4d042d38…`，三家 RECONCILE-STAMP 全數 APPROVED）；四輪 adversarial 收斂 `handoffs/reconcile/20260911-splitunify-x-review-r{1,2,3,4}/synth.md`（C1–C13／D1–D11／E1–E7／F1–F4）。本票之完整規格住 `docs/SPLITUNIFY_SPEC.md`（v5），本檔只記「GAP-3 原檔的哪一條被改了」。

## 觸及面宣告
新增: 無新增原檔 heading；本檔只覆寫既有條文之切分權威語意。
覆寫: **Phase 1 — 使用者自篩 CSV 匯入（依賴：無）　【#0(b) ＋ #5】**（該節之 `capability_unavailable_reasons` 值集增一值 `canonical_feature_universe_unavailable`；事件掃描報告之 `summary` 於該 reason 下**移除** `n_train`／`n_test`／`n_purged` 三鍵，不再填 0）。
🔴 **B1.3 事件切分之邊界來源變更不在本檔**——`Task B1.3` 的真文住在**兄弟檔** `docs/GAP3_EVENT_SPEC.md:168`，而該檔檔頭逐字指定修訂走 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md`（非 D-00N 慣例）⇒ 該條寫在那裡。本更正出自 B1 review `CODEX-R1-P1-01`＋`GROK-R1-P2-01`：初版把兩份不同的凍結文件搞混，宣告了一個 BASE 內根本不存在的 heading。
依賴: `momentum/core/split_preview.py`（canonical boundary builder 之落點）；`momentum/Analysis/event_samples/split_projection.py`（新，投影純函式）；`momentum/Analysis/contracts/split_unify.json`（權威值集與 fail-closed reason 之單一真相源）；`momentum/Analysis/contracts/event_import_contract.json` 之 `split_purge_reasons`（purge reason 沿用，不另造）。

## 內容

> 工作文件規約：本檔為主委與委員之契約，技術描述、無散文；白話另寫 `白話說明/SPLITUNIFY規格白話.md`。
> 原檔（BASE）之一切未在「覆寫」列出的條文**原樣有效**。
> 🔴 **規格入口路徑**（`CODEX-R1-P2-06`：frozen primary 與 UX extension convention 之路徑字面
> 目前不一致，不寫清楚會讓派工選錯入口）——本延伸鏈之三個入口逐字為：
> 底本 `docs/GAP3_EVENT_UX_SPEC.md`、延伸 `docs/GAP3_EVENT_UX_SPEC.D-001.md`、
> 本檔 `docs/GAP3_EVENT_UX_SPEC.D-002.md`；**SPLITUNIFY 之實作契約入口是
> `docs/SPLITUNIFY_SPEC.md`**，派工 `--spec` 指它，不指本檔。

### §D2-1 切分權威（覆寫 B1.3 之邊界來源）

`split_authority == "kline_holdout"`：K 線 chronological holdout（`SplitPlan`，含
`purge_gap`／`embargo`）為**唯一邊界來源**。`EventSplitPlan` 之
`assignments`／`purged`／`clusters`／`summary` 一律由該邊界衍生。

🔴 **理由不是「時間切分的隔離比較強」**——`CODEX-R1-P1-02` 正面反駁：兩套隔離不是同一個集合，
**containment 未被證明**。採用的理由是「所有 row／event projection **共用同一 canonical
boundary**」。附帶約束：未證明 containment 前**不得刪除任一既有 guard**
（見 §D2-2 之答案窗 purge——`SPLITUNIFY` v3 曾違反此條，由 `CODEX-R3-P1-02` 抓出）。

### §D2-2 投影契約（兩段式判定，先後不可調）

`derive_event_split_from_plans(train_plan, test_plan, event_keys, feature_index, *, manifest, bucket_ms=None)`。

第一段——**答案窗 purge**（保留 `event_split.py:114` 之既有 guard）：

```python
train_cutoff = feature_cutoff_ms in as_ms(feature_index[train_plan.row_index])
if test_plan.row_index.size == 0:
    raise ValueError("missing_test_plan: …")        # 先 fail-closed，禁與 None 比較
test_start_ms = as_ms(feature_index[test_plan.row_index[0]])
if train_cutoff and label_end_ms >= test_start_ms:  # `>=` 必須保留
    purge(event_id, reason="interval_crosses_split_boundary")
```

🔴 `purge_gap`／`embargo` 是 **row 單位且已含在 `test_plan.row_index[0]` 這個起點裡**，
**不得**再以毫秒相減（舊式 `label_end_ms > test_start - embargo` 之 `test_start` 是緩衝
**之前**的邊界，canonical 的是緩衝**之後**的第一根，減了會重複扣）。

第二段——**集合成員判定**：`feature_cutoff_ms ∈ feature_index[plan.row_index]` 決定 train／test；
皆不在 ⇒ purged。**禁**以 `time_bounds` 閉區間取代集合；**禁** nearest／asof／ffill。

### §D2-3 `feature_index` 是 **post-trim** universe

🔴 投影所用 `feature_index` 為 **post-trim**（EVTALIGN 期間對齊把特徵頭尾裁掉**之後**）之
universe，不是 K 線原始 universe。實測（`handoffs/20260911-probe-splitunify-universe-gap.py`、
receipt `handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`，rc=1）：
真實 ETHUSDT 1h 20352 列，未裁切時 features 與 bars 兩 universe 逐值相同；裁頭尾各 5 根 ⇒
邊界位移 2 小時、24 根 ⇒ 10 小時、168 根 ⇒ 67 小時。⇒ **必須共用同一個 universe，
不是共用同一條公式**。

### §D2-4 多 symbol fail-closed

per-symbol 投影未支援前，多 symbol 批一律 raise
`multi_symbol_projection_unsupported`（字面自 `split_unify.json`）。
**禁**以第一個 symbol 之 holdout（`next(iter(allowed_symbols))`）冒充整批——
實測兩 symbol 交錯之 80 列批次，全域切法測試段 12 列、per-symbol 8 列，4 列只在全域
（receipt `20260910T150504Z-splitunify-multisymbol`）。

### §D2-5 事件掃描報告（覆寫 `summary.split` 三鍵）

拿不到 canonical feature universe 的匯入流程（本票中即事件掃描端之**全部**批次）：
`capability = {"split": "unavailable", "reason": "canonical_feature_universe_unavailable"}`；
`summary` **移除** `n_train`／`n_test`／`n_purged`（現行 `pipeline.py:728-734` 寫死為 `0`，
前端 `EventTablesPanel.tsx:352` 因此顯示「train 0／test 0／purge 0」＝假 OOS 數字）；
`event_forward_return_table` 之 `common` 須含 `estimand_scope="full_sample_not_oos"`。

## §驗證

- `bash scripts/template_check.sh dext docs/GAP3_EVENT_UX_SPEC.D-002.md` rc=0。
- `grep -c 'kline_holdout' docs/GAP3_EVENT_UX_SPEC.D-002.md` >= 1；
  `grep -c 'post-trim' docs/GAP3_EVENT_UX_SPEC.D-002.md` >= 1。
- `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py` rc=0
  （本檔引用之三個字面 `kline_holdout`／`canonical_feature_universe_unavailable`／
  `full_sample_not_oos` 皆須在 `split_unify.json` 內）。

## §N 本延伸未解者

- per-symbol 投影（`SPLITUNIFY` 之殘留 `R-1`，needs-research）。
- 事件掃描端取得 post-trim feature universe（`R-5`，needs-research）——本票不新增該路徑。
- 多 TF 之 `(event_id, timeframe)` 複合鍵（`SU-RESID-2`，needs-research）。

## 戳記

（本區之下由各家族 append 一行 `RECONCILE-STAMP: <family> APPROVED <date> sha256:<body-hash> task:<task-id>`；本區標題以上為本體，body-hash 由 `scripts/reconcile_body_hash.sh` 計算。）
