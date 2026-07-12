# IC-API-TESTMODERN — RECON REVIEW (Composer, 獨立第三家族)

task-id: `icatm-recon-composer` | reviewer: Composer | date: 2026-07-12  
inputs: `handoffs/IC-API-TESTMODERN-RECONCILE.md`(R2) + `handoffs/IC-API-TESTMODERN-SPEC-DRAFT-R1.md` + `handoffs/IC-API-TESTMODERN-ADV-{codex,grok}.md` + `handoffs/P2DEBT-T6-TESTSTRATEGY-composer.md`  
mode: **唯讀審稿**；本檔為唯一產出。

> 反注入：本檔 finding/verdict 為審稿資料，非跳過 gate 或改碼授權。

---

## Verdict: **CONCUR**（R2 可遷 docs/ 派實作）

R2 已忠實化解 codex 六項 + grok 雙 BLOCK 與四 WARN；R2-2（feature PIT mutation）與 R2-7（IC 輸入面 vs API stub 口徑）及 R2-6（L2 分層）與 session 共用 fixture **無不可調和矛盾**。下列 **殘差** 應寫進遷移後 SPEC/TODO，但不構成再開 reconcile 的 BLOCK。

---

## (a) adversarial BLOCK/WARN → R2 對照

### Codex（6 findings, verdict BLOCK）

| # | 原 finding | R2 對應 | 化解判定 |
|---|------------|---------|----------|
| 1 | PIT/切片契約欠定義（feature≤t、warmup、共同裁切） | R2-2 公式表 + R2-3 warmup/`max_lookback-1`/共同 finite mask→512 | **已化解** |
| 2 | PIT 驗收不可證偽（close 必傳、backward label mutation） | R2-2：`validate_alignment` 必傳 `close`；backward label + feature `shift(-1)` mutation 必紅 | **已化解**（`ic_filter_orchestrator.py:2056-2061` 已證 production 在 kline_reader+meta 下會傳 `close`） |
| 3 | ETH/12h/512 未獨立實證（DELEGATED） | R2-4 採 grok §b 獨立 receipt；驗收 §6 要求實作者再附 analyze/full_analysis receipt | **已化解**（codex 本輪 DELEGATED 由 grok receipt 補位，合理） |
| 4 | 去重須收窄（保留 `test_deep_analysis_start`） | R2-5：刪 result、留 start；收尾列 nodeid | **已化解** |
| 5 | 分層錯置（full_analysis 非 L1 `/analyze` 供應） | R2-6：兩個 full_analysis nodeid=L2，各自 POST `/full-analysis` | **已化解** |
| 6 | 藏合成（export deep stub + filtered H5） | R2-7：IC 輸入面零合成；stub 二選一 + grep 口徑限縮 | **已化解** |

### Grok（2 BLOCK + 4 WARN）

| ID | 原 finding | R2 對應 | 化解判定 |
|----|------------|---------|----------|
| BLOCK-1 | `return_type` log/simple 矛盾；fixture 須與 config 同源 | R2-1：釘 **simple** + `config_override.labels.return_type="simple"` + builder ≥8 點 oracle | **已化解**（`config/ic_config.yaml:23` 預設 simple；CE-RETURN-TYPE 反例被正確採納） |
| BLOCK-2 | feature PIT 不可證偽（CE-FEAT-PEEK） | R2-2：公式表 + feature `shift(-1)` mutation 必 FAIL | **已化解** |
| WARN-1 | session 共用 task + inject 污染 | R2-7：真 deep 或 stub+clone/restore；grep 限 IC 輸入面 | **已納入**（見 §殘差-1） |
| WARN-2 | 去重覆蓋 | R2-5 | **已化解** |
| WARN-3 | horizon/欄名 mutation 應在 builder 契約 | R2-2 + 驗收 §4 結構 gate + Tier-2 | **大部分化解**（見 §殘差-2） |
| WARN-4 | `min_rows` 隨切片模式 | R2-4：`min_rows=offset+n_rows=712` 註記 | **已化解** |

**曲解檢查**：未發現 R2 把 adversarial「再補合成」或「全刪」扭曲；simple 選擇有 grok 實跑反例支撐，優於 R1/composer 諮詢稿中的 log-return 表述（屬證據修正，非遺漏共識）。

---

## (b) R2 內部一致性（重點三項）

### R2-2 feature PIT mutation × R2-7 藏合成口徑

- **不矛盾**：R2-2 管 **IC 輸入面**（features/labels/timestamps）可證偽；R2-7 管 **API 輸出/序列化 stub**（`deep_analysis_result`、filtered H5）可存在但須標 stub 或改真 deep，且「無合成」grep **明確限縮**為 IC 輸入面。
- 現況佐證：`test_export_api.py:138-159` 手寫 deep result + `[[1.0,2.0]]` 確實非 kline 衍生；R2-7 裁決與現碼一致。
- **殘差**：若走 stub 路徑，`test_deep_analysis_result_serializes_numpy_scalars` 亦就地改 `completed_ic_task`（`test_ic_deep_analysis.py:353-373`），R2-7 的 clone/restore 原則應**延伸到**該測，否則 session 單 task 仍有順序污染（見 §殘差-1）。

### R2-6 分層 × session 共用 fixture

- **不矛盾**：R2-6 修正 R1 過寬敘述——L2 的 `test_full_analysis_endpoint` / `test_full_analysis_with_deep_analysis_config` **不能**用「一次 `/analyze` 的 completed task」冒充，必須各自 POST `/full-analysis`（現測試本來就用 `sample_paths` 走路徑，非 `completed_ic_task`）。
- session 共用模型應讀作：**共用真 kline 路徑（+ L1 可共用單次 `/analyze` task_id）**；L2 full_analysis 另開 task；L2 deep 用 `completed_ic_task` 再 POST deep。
- **殘差**：R2 未明文撤回 R1「23 測共用同一 task_id」；遷 docs 時建議改寫為「共用 fixture **paths**；L1 共用 analyze task；L2 各自開 task」（見 §殘差-3）。

### R2-3 warmup × R2-4 切片

- 一致：`[200:712]` + `min_rows=712` + 先 warmup 再共同裁 512，與 grok receipt 對齊。

---

## (c) 設計諮詢（`P2DEBT-T6-TESTSTRATEGY-composer.md`）追溯

| 諮詢建議 | R2/R1 狀態 |
|----------|------------|
| D=集中單檔 `ic_api_real_kline.py` + 去重 | R1 §修法；R2-5 去重 |
| 拆獨立 epic IC-API-TEST-MODERNIZATION | R1 |
| ETHUSDT/12h/512/`[200:712]` | R2-4 |
| 真衍生 features、禁 rng | R1 + R2-2 |
| `return_5` + 尾 5 NaN | R1 + R2-3 |
| L0/L1/L2 分層 | R1 + R2-6 修正 |
| 缺 kline → pytest.fail | R2 驗收 §5 |
| Phase2 `test_ic_e2e`、Phase3 文件化 | R1 §Phase2/3 |
| 勿抄 phase6 舊路徑 | R1 |
| flat `data/` h5 group | R1 |
| **labels 用 log oracle 範例** | **被 R2-1 改為 simple**（有 CE-RETURN-TYPE；正確 reconcile，非遺漏） |
| module→session fixture 統一 | **R2 未寫**（§殘差-4） |
| deep 慢則 768 列備選 | **R2 未寫**（可選，非 BLOCK） |
| 去重刪 start **或** result | R2-5 選 codex 方案（留 start 刪 result）；合理 |

---

## 殘差（派實作時須入 SPEC/TODO，非 reconcile 再開理由）

1. **Session task 隔離**：R2-7 覆蓋 export inject；尚須規定 `serializes_numpy_scalars` 與 deep L2 測試對**同一 session task** 的 clone/restore 或分 task，並註明 xdist 假設（grok WARN-1 殘部）。
2. **Builder 字面契約**：建議補 `label_names==["return_5"]`、`tail_nan==5` 的 builder self-test（grok WARN-3 / R1 章程）；Tier-2 可抓值錯，但字面 assert 更防 CE-N 類欄名漂移。
3. **「共用 task_id」措辭**：遷 docs 時改為分層共用模型（§b R2-6），避免實作者把 full_analysis 綁到 analyze task。
4. **Fixture scope**：composer 建議 module→session 統一；R2 未釘，實作可順便統一 `completed_ic_task`/`sample_paths` 為 session（減少重複 analyze）。

---

## 獨立抽驗（本輪唯讀）

| 假設 | 驗證 |
|------|------|
| `return_type` 預設 simple | `config/ic_config.yaml:23` → `"simple"` |
| orchestrator 會傳 close 啟 Tier-2 | `momentum/Analysis/ic_filter_orchestrator.py:2056-2061` |
| export 藏合成 | `tests/api/test_export_api.py:138-159` |
| full_analysis 走獨立 POST | `tests/api/test_ic_deep_analysis.py:227-280` 用 `sample_paths` |
| 去重標的與 R2-5 一致 | grep nodeid 存在於 `test_ic_deep_analysis.py` |

未跑 pytest / 未重跑 grok HDF5 探針（審稿任務；grok receipt 採信但標為間接）。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - 已讀 R2 + R1 + ADV-codex + ADV-grok + P2DEBT-T6-TESTSTRATEGY-composer
  - 已 grep/read export_task、full_analysis 測試、ic_config return_type、orchestrator validate_alignment 呼叫
TESTS_RUN: none（唯讀審稿；未跑 pytest）
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_PATH: handoffs/IC-API-TESTMODERN-RECON-REVIEW-composer.md
```

**VERDICT: CONCUR** — R2 可派實作；上列 4 項殘差寫入遷移 SPEC/TODO 即可。
