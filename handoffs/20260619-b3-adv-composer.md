# B3 Adversarial Review — Composer 2.5 (2026-06-19)

SPEC=`docs/B3_BATCH_RETENTION_SPEC.md` TODO=`docs/B3_BATCH_RETENTION_TODO.md` STRICTNESS=MAXIMUM

## Verdict：需修補後派工

## 被當成事實的未驗證假設
1. **§A「staging 只改 :606 register」** — `feature_factory.py:3216-3227` 生成結束即 `FeatureRegistry.add`；RunManager/`list_runs` 不依 browse register。**assumption，未處理**。
2. **§A checkpoint「:178-209」** — 實為 `resume_batch` 邏輯；schema 在 `:889-916`。**行號錯，誤導實作**。
3. **§G/TODO BYTE「golden 證 register 時機」** — `build_l65_golden_baseline.py --check` 只驗特徵 byte，**無法證延遲 register**。
4. **Task1.3「沿用 T-C `_resolve_*_reserve_bytes`」** — batch_service 無此符號；T-C 在 CGSA `column_group_registry`。**名稱/落點未驗證**。

## Findings
**[BLOCKING|High] ① 多下游一致性** — 延遲僅 `_browse_registrar.register(:606)`；`FeatureRegistry.add`、磁碟 artifact 仍即時。不變量②③「discard 不 register/不見」與 RunManager 語意衝突；`FeatureFactoryQualityAdapter.compute(:34)` 會 side-effect register，品質 API 可繞過 staging。
**[BLOCKING|High] ② 背壓+T-C** — discard「B3 不刪檔」但背壓要求「decide 釋放 bytes」；若只扣帳不刪檔，真實 disk 仍漲→T-C 事故重演。缺 wakeup 機制、無人 decide 永久 pause、無預設閾值/公式。
**[BLOCKING|High] ③ resume 守恆** — `resume_batch(:178-193)` 僅 manifest 缺失才 requeue；`generated` 待決有 manifest 不會重算（好），但**未規範** crash 於 retain 中途、batch `status=completed` 與待決並存、REST 列 pending items。
**[MAJOR|High] ④ flag 關舊行為** — 缺 env 名/預設；byte gate 不足以覆蓋 register 時機；需明確回歸（browse_task_ids 出現時機、WS payload）。
**[BLOCKING|High] ⑤ 前端 completionQueue** — 單 symbol `RunRetentionDialog` 用 `deleteRun`/`updateRunAlias`（已 registry）；batch 需 retain/discard endpoint。共用 queue 無 `source: batch|single` 會誤路由；`page.tsx:510` 常駐 modal 與 batch 面板互斥未定。
**[MAJOR|High] ⑥ 五不變量可證偽** — ②③缺 RunManager/quality 斷言；④無並發 wave 測試規格；⑤ resume 無逐步劇本；`retention_error` 無觸發定義；測試 `-k retention_*` 尚不存在可接受但需 fixture 契約。
**[MAJOR|High] ⑦ 並發/冪等/404** — 邊界僅列字樣；缺 item key 契約、HTTP 碼(重複 decide)、鎖策略；Phase1 無 WS/`map_batch_progress_ws_data` 擴充任務，Task2.1「WS 推 staging」缺 REST list pending fallback API。
**[MINOR|Med] §1 漏項** — flag 名、decide path、types.ts 欄位、vitest 檔名未定。
**[MINOR|Med] §5** — 可接受；狀態機+背壓已夠，勿再加 framework。

## §1–§3 掃描
矛盾:無(內部一致但與 codebase 事實衝突)。漏項:見上。不可測:BYTE/register/背壓閾值。quant:不碰數值(OK)。過度工程:無。OOM:背壓需 tier 預設。Cache:N/A。API:缺 contract。測試:核心缺路徑。Agent:Task1.2 缺 endpoint 偽碼。

HANDOFF_NOT_UPDATED: read-only adversarial review
STATUS: DONE
