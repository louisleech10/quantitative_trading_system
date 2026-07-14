# IC1C-B0 Code Review（Composer）

**task-id**: IC1C-B0  
**reviewer**: Composer  
**date**: 2026-07-14  
**對象**: Grok B0 實作 — `scripts/ic1c_freeze_baseline.py`、`scripts/ic1c_validate_baseline.py`、`handoffs/ic1c_baseline/g_old.{json,sha256}`  
**對照**: `docs/IC1C_NETIC_TODO.md` Task 0.1 / §B B0→B1 Gate、`handoffs/IC1C-B0-RESULT.md`  
**範圍**: read-only（除本檔）

---

## 審查摘要

Task 0.1 入口偽碼五項核心（fixture 衍生 → spearman summary + quantile turnover → 真名 skipped 注入 → `NetICAnalyzer.batch_analyze` → strict JSON + lineage）均已落地；producer 未自證；`momentum/` `api/` `frontend/` git diff 為空。本審查獨立重跑 Gate 與決定性雙跑均 PASS。

**VERDICT: APPROVE（0 BLOCKING）**

---

## ① 偽碼符合度（fixture 衍生 / skipped 注入 / lineage / allow_nan=False）

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| 真 kline fixture 衍生 features/labels | ✅ | `ic1c_freeze_baseline.py:105-124` 讀 `ic_api_real_kline.FEATURE_NAMES` + `build_real_kline_frames(kline)`；cache 路徑與 fixture `L148-157` 一致 |
| summary `ic_mean=spearman`、feature 名排序 | ✅ | `L127-160` `_spearman_ic_mean` + `ordered = sorted(feature_names)` |
| turnover `compute_quantile_turnover` | ✅ | `L149-159` `TurnoverAnalyzer.compute_quantile_turnover`（對應 TODO「quantile_turnover」現行 API 名） |
| skipped 注入真 fixture 名 | ✅ | `L37-38` 常數 `oc_return`/`hl_range`；`L163-177` `turnover_data.pop("oc_return")` + `summary["hl_range"]["ic_mean"]=nan`；fixture `FEATURE_NAMES` 7 欄含二者（`ic_api_real_kline.py:27-35`） |
| 直呼 analyzer、不跑 deep pipeline | ✅ | `L191-205` 僅 `NetICAnalyzer(...).batch_analyze(summary, turnover_data)`，無 orchestrator/API |
| `allow_nan=False` + 非有限→null + 清單 | ✅ | `L66-103` sanitize；`L234` `json.dumps(..., allow_nan=False)`；`L221` `non_finite_fields` |
| lineage 頂層 | ✅ | `L217-220` `fixture_sha256` / `git_head` / `generated_by`；g_old 抽驗三者皆非空字串 |
| G-OLD 保留現行 `net_ic` 鍵 | ✅ | g_old 非 skipped 5 欄皆含 `net_ic`；`cost_sensitivity[].net_ic` 亦保留（故意對照） |

**Findings**

| ID | 嚴重度 | 說明 | 證據 |
|----|--------|------|------|
| CR-B0-1 | MINOR | `_default_net_ic_config()` 硬編碼 YAML 現值，未從 `config/ic_config.yaml` 載入；當前數值與 yaml 一致（`default_cost_bps:5` 等），但日後 yaml 漂移時 G-OLD 可能靜默偏離「現行 default config」 | `ic1c_freeze_baseline.py:180-188` vs `config/ic_config.yaml:181-186` |
| CR-B0-2 | INFO | 頂層除 lineage 三鍵外另增 `feature_names_input` / `injected_skips` / `non_finite_fields`，利於審計；TODO 未禁止 | `ic1c_freeze_baseline.py:217-227` |

---

## ② Validator 真獨立（不自證）

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| producer 不呼叫 validator | ✅ | `rg ic1c_validate scripts/ic1c_freeze_baseline.py` → 0；僅 kline `validate_continuity`（`L119`） |
| validator 不 import producer | ✅ | `ic1c_validate_baseline.py` 僅 stdlib + `tests.fixtures.ic_api_real_kline.FEATURE_NAMES`（`L46`） |
| 注入名常數獨立複製（非共用模組） | ✅ | freeze `L37-38` / validate `L29-30` 同值但無交叉 import |
| 驗 skipped 路徑 + reason | ✅ | validate `L100-121` |
| 驗 fixture_sha256 與現檔 | ✅ | validate `L77-82` |
| 驗 non-skipped 含 `net_ic`（G-OLD 契約） | ✅ | validate `L123-141` |
| 驗 JSON 無非有限字面 | ✅ | validate `L51-61` + `L162` 全樹掃描 |

**Findings**

| ID | 嚴重度 | 說明 | 證據 |
|----|--------|------|------|
| CR-B0-3 | MINOR | validator 僅斷言 `len(features) >= n_fixture-2`（≥5），未斷言 7 個 `FEATURE_NAMES` 全覆蓋；符合 TODO 字面下限，但理論上 5 欄子集（含兩注入名）可過關 | `ic1c_validate_baseline.py:92-98` |
| CR-B0-4 | INFO | `non_finite_fields` 僅驗 `list[str]` 型別，未交叉比對 null 欄位一致性 | `ic1c_validate_baseline.py:156-160` |

---

## ③ 確定性真來源

| 機制 | 結果 | 證據 |
|------|------|------|
| feature 名排序 | ✅ | build `L153`；payload `feature_names_input` sorted |
| JSON `sort_keys=True` | ✅ | `L234` |
| 尾端換行固定 | ✅ | `L235-237` |
| `non_finite_fields` 排序 | ✅ | `L221` |
| 無隨機種子路徑 | ✅ | spearman/turnover 為確定性數值函式 |
| §B 字面雙跑 hash | ✅ | 本審查重跑：`h1=h2=6e23ff632cb9153b6f2b803bfc607a033151efa3b57a0fa22ac5ec91bdc36179` |

**Findings**

| ID | 嚴重度 | 說明 | 證據 |
|----|--------|------|------|
| CR-B0-5 | INFO | `git_head` 寫入 baseline 使跨 commit 的檔案 hash 必然變動；同 commit 內重跑決定性仍成立（TODO lineage 要求） | `ic1c_freeze_baseline.py:219`；雙跑 PASS |

---

## ④ g_old.json 內容抽驗

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| features=7，全 fixture 名覆蓋 | ✅ | 抽驗 `missing_features=∅` `extra_features=∅` |
| `oc_return` skipped `turnover_missing` | ✅ | g_old `result.features.oc_return` |
| `hl_range` skipped `gross_ic_missing` | ✅ | g_old `result.features.hl_range` |
| 非 skipped 5 欄含 `net_ic` | ✅ | `non_skipped_net_ic=True` |
| 無 NaN/Inf JSON 字面 | ✅ | raw text `nan_literals_in_text=[]` |
| `non_finite_fields`=5（capacity NaN→null） | ✅ | g_old 頂層清單 5 條 `*.capacity.estimated_capacity_usd` |
| sha256 與 `.sha256` 檔一致 | ✅ | `6e23ff632cb9153b6f2b803bfc607a033151efa3b57a0fa22ac5ec91bdc36179` |

---

## ⑤ 零 scope 外變更

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| `git diff momentum/ api/ frontend/` | ✅ 空 | 本審查 `git diff … \| wc -l` → 0 |
| 僅新增 scripts×2 + handoffs/ic1c_baseline | ✅ | `git status` → `?? scripts/ic1c_*.py` `?? handoffs/ic1c_baseline/` |
| 未改 fixture | ✅ | fixture 無 diff；`fixture_sha256` 與現檔一致 |

---

## 獨立驗收重跑（VERIFY）

```bash
# CMD A — Task 0.1 Gate
python scripts/ic1c_freeze_baseline.py --baseline old \
  && python scripts/ic1c_validate_baseline.py handoffs/ic1c_baseline/g_old.json \
  && shasum -a 256 -c handoffs/ic1c_baseline/g_old.sha256
# → VALIDATE OK + g_old.json: OK + exit 0

# CMD B — 決定性雙跑
h1=$(python scripts/ic1c_freeze_baseline.py --baseline old >/dev/null 2>&1 \
  && shasum -a 256 handoffs/ic1c_baseline/g_old.json | cut -d' ' -f1)
h2=$(python scripts/ic1c_freeze_baseline.py --baseline old >/dev/null 2>&1 \
  && shasum -a 256 handoffs/ic1c_baseline/g_old.json | cut -d' ' -f1)
[ "$h1" = "$h2" ]  # → determinism=OK
```

---

## Finding 彙總

| ID | 嚴重度 | 標題 | 阻 B0? |
|----|--------|------|--------|
| CR-B0-1 | MINOR | default config 硬編碼 vs yaml 單源漂移風險 | 否 |
| CR-B0-2 | INFO | 頂層額外審計鍵（允許） | 否 |
| CR-B0-3 | MINOR | validator 特徵數下限弱於全覆蓋（符合 TODO 字面） | 否 |
| CR-B0-4 | INFO | non_finite_fields 未交叉驗 null | 否 |
| CR-B0-5 | INFO | git_head 使跨 commit hash 變（設計如此） | 否 |

---

```
ASSUMPTIONS_VERIFIED: FEATURE_NAMES 7 欄含 oc_return/hl_range；ic_config.yaml net_ic_analysis 現值與 _default_net_ic_config 一致；g_old 全 fixture 名覆蓋
TESTS_RUN: CMD A Gate exit 0；CMD B h1==h2；git diff momentum/api/frontend 空；g_old 抽驗腳本（7 features/2 skipped/無 NaN 字面）
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改產物）
```

CODE-REVIEW: APPROVE(0 BLOCKING)
