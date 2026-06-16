# batch_alias 前端修復 — Composer 2.5

**時間**: 2026-06-17 | **範圍**: 僅前端（後端勿動）

## 失敗根因

### 失敗 1 — disambiguation 短碼不足
- `shortBatchId` 固定 `slice(0, 8)` → `batch-alpha-001` 顯示 `batch-al…`，無法匹配測試 `/batch-alp/`、`/batch-bet/`。
- 同名 `batch_alias`（wave-a）跨兩個 `batch_id` 時，需在目視短碼中保留差異片段（alpha vs beta）。

### 失敗 2 — 單列 run 誤出現「批次：」
- **impl 分組邏輯正確**（無 `batch_id` → `singles`，不渲染 group header）。
- 根因是 **測試缺 RTL `cleanup`**：test 1 渲染的 `批次：wave-a` group header 留在 `document`，test 2 的 `screen.queryByText(/批次：/)` 命中殘留 DOM（與 `FeatureExplorer.test.tsx` 等既有測試慣例一致，應加 `afterEach(cleanup)`）。
- 額外防禦：rename / batch-rename `Dialog` 改為僅在開啟時掛載，避免關閉態 portal 殘留。

## 修改檔案

| 檔案 | 變更類型 | 說明 |
|------|----------|------|
| `frontend/src/components/feature-factory/RunManagerPanel.tsx` | **impl** | 新增 `disambiguateBatchIds`（LCP + 最少 3 字分歧前綴）；`batchIdPreviewById` useMemo；group header 括號內短碼改為可辨識預覽；Dialog 條件掛載 |
| `frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchAlias.test.tsx` | **test** | `afterEach(cleanup)` |

## 實作要點

- 同名 `batch_alias` 的 groups 共用 `peerIds`，`disambiguateBatchIds(peerIds, 3)` → `batch-alp…` / `batch-bet…`（可見文字，非僅 `title`）。
- 無碰撞時維持 `shortBatchId` 預設 12 字元預覽。
- 未放寬任何既有斷言；未改後端。

## 驗證（協調者代跑）

```bash
cd frontend
npx vitest run src/components/feature-factory/__tests__/RunManagerPanel.batchAlias.test.tsx
npm run build
```

**執行端 shell 不可用**，未能在此環境實跑；邏輯審查預期兩測試皆綠。

---

ASSUMPTIONS_VERIFIED: `shortBatchId(8)` 無法產出 batch-alp/batch-bet；`groupRunsByBatch` 無 batch_id 時僅入 singles；「批次：」僅出現在 group header 行；同檔其他測試已用 afterEach(cleanup)
TESTS_RUN: 未能執行（shell rejected）
FAILURES_SEEN: none（未跑）
SCOPE_CHANGES: none（僅允許之前端 RunManagerPanel + 對應測試）
NUMERIC_OR_SCHEMA_IMPACT: none

HANDOFF_NOT_UPDATED: 依 .cursorrules 執行端不覆寫根 HANDOFF.md

STATUS: DONE
