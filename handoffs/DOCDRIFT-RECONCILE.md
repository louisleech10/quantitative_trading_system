# 四源 doc 漂移 reconcile — 主委定案草案(待使用者確認再改)
Task-id: docdrift | Date: 2026-07-12 | Chair: Claude(Opus 4.8)
> 三家研究 handoffs/DOCDRIFT-STUDY-{grok,codex,composer}.md,強烈收斂。本檔=定案草案,**確認前不改任何治理文件**。

## 研究揭露(比預期嚴重——不只規則 5/6 不同)
1. **canonical 7 條=CLAUDE.md 版**(Rule 5=Config single source、Rule 6=Tests without run_api)——三家一致,證據:CLAUDE.md 是宣告權威、ARCHITECTURE.md 自己後段(§349)也用這版、`check_decoupling_phase4.sh` R6 實作為 `pytest tests/momentum/Strategy/`(135 passed)。
2. **ARCHITECTURE.md 單檔內三套 Rule 5/6 語意**(§150 singleton/callback、§349 Config/Test、§489 config-driven/pipeline)——自相矛盾。
3. **ARCHITECTURE 的「已修復/全部已驗證」是假的**:singleton/callback 程式裡still在(三家實測:chart_signal_service.py:57、signal_analysis_service.py:47、data_source_registry.py:69、task_manager.py callback…)。
4. **DEV_GUIDE 規範過時且與現況衝突**:§237「絕對禁任何硬編碼數值/random 測試資料」與實際測試策略衝突(repo 大量 seeded np.random 單元/性質測試合法);且自相矛盾(§308 又允許標註示例值、§327 要所有測試打真 API=非決定性);§54「人工驗證+Claude 實作」工作流已被多 agent/三方簽核取代。
5. **ARCHITECTURE factory map 過時**:momentum/factories.py 有 79 個 create_,ARCH §216 清單缺一堆(feature_preprocessor/reader/library、IC artifact/split/report、MCP、LSTM…);狀態漂移(§60 仍「2026 Q1」、FF UI §1499 說已做 §1804 又說待開發)。
6. 兩個 check_decoupling 腳本**同編號指不同東西**(scanner 語義漂移)。

## 主委定案(採三家共識,交使用者確認)
### D1 規則單一真相源
- **canonical 7 條解耦規則採 CLAUDE.md 版**(Config single source / Tests without run_api);ARCHITECTURE.md §150 的 singleton/callback 表**改正**。
- **singleton/callback 不廢**,但降為**獨立具名 invariant(Rule 8/9 或 named checks)**,不冒名頂替 canonical R5/R6;兩 scanner 編號 deconflict(codex/composer 建議)。
- **CLAUDE.md = 規範唯一權威**(短、規則 ID);ARCHITECTURE/DEV_GUIDE **移除重述規則、改 pointer**,保留各自 domain 內容(架構圖/factory 機制/how-to/範例)。
  - codex caveat:CLAUDE.md 別塞爆(128 行自動注入,過長稀釋);細節 enforcement mapping 可放版本化 governance registry 或 ARCH 非權威 reference table;pointer 要穩定可 CI 檢查。

### D2 修正假宣稱/過時(不只搬文字,是改錯)
- ARCHITECTURE:改掉 singleton/callback「已修復」假綠(據實記「仍存在,列 Rule 8/9 追蹤」)、更新 factory map、修狀態漂移(2026 Q1、FF UI 矛盾)。
- DEV_GUIDE:改「絕對禁 random/硬編碼數值」為**分層**(production truth 用真資料 / regression byte-faithful / synthetic unit/property 測合法)——對齊剛入版的 docs/IC_API_TEST_LAYERING.md;刪自相矛盾;更新 §54 工作流為現行多 agent。

### D3 驗收(定案後實作階段)
規則單一版本 + scanner 語義對齊 + 假宣稱修正 + pointer CI 可檢;不改程式邏輯(純文件治理);改後 check_decoupling 仍綠。

## ⚠️ 需使用者定案的兩點(judgment)
- **A. 修正範圍**:全面清(D1+D2 都做,含改 4400 行的假宣稱/factory map/過時)? 還是先只做 D1(解衝突+單一真相源),D2 的假宣稱/過時另立一票?
- **B. 規則放哪**:規則續留 CLAUDE.md(維持自動注入權威),還是照 codex 建議另立 governance registry 放細節、CLAUDE 只留 ID?
