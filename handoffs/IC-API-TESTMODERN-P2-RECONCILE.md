# IC-API-TEST-MODERNIZATION Phase2 scope reconcile
Task-id: ic-api-testmodern | Date: 2026-07-12 | Chair: Claude(Opus 4.8)

## 裁決:Phase 2 鐵律遷移標的 = 空集
三方 scope 分類(handoffs/IC-API-TESTMODERN-P2SCOPE-{grok,composer}.md):
- grok:5 檔全 LEGIT-SYNTHETIC。
- composer:test_ic_e2e MIGRATE、其餘 4 LEGIT。
- **分歧點=test_ic_e2e**;主委實測裁決(receipt):該檔**無注 kline_reader**(不觸 Tier-2 值 oracle)、
  斷言全結構性(report key/summary_table/event tier,非 IC 數值)、perf 測需 800×10k 大矩陣(真 kline 不可行)
  → **LEGIT-SYNTHETIC**(採 grok);composer 的 MIGRATE 因無 oracle/perf 需求被 overrule。
- 其餘 4 檔兩家一致 LEGIT(mutation/FDR/OOS/filter 受控探針;遷真 kline 會毀可證偽性)。

## 意涵
真正的鐵律違憲僅 Phase 1 那 23 個(注 kline_reader+Tier-2 卻餵合成冒充可跑契約),已修(56a9566)。
本 5 momentum 檔合成皆合法。**epic 實質於 Phase 1 完成**;Phase 2 無實作;Phase 3=判準文件化 docs/IC_API_TEST_LAYERING.md。

## 收尾
epic 三 Phase 全閉合:Phase1 實作(56a9566)+Phase2 scope 裁決(空集)+Phase3 文件(docs/IC_API_TEST_LAYERING.md)。
