# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-12 | **Branch**: main

## ✅ 本 session:doc 漂移 D1+D2 施工 + 委員 review 修訂(純文件治理,未改程式邏輯;未 commit)
**D1**:CLAUDE.md §The 7 Decoupling Rules 定 canonical 唯一權威 + named invariant Rule 8(singleton,誠實記殘留)/Rule 9(callback);ARCH §162 錯表→canonical、§1402 假✅修正;AGENTS/.cursorrules/DEV_GUIDE 頂加 pointer;兩 scanner 加註解頭編號對照(grep 零改)。
**D2**:factory map 補漏+標「權威=factories.py 78 個」;§60 日期;FF UI「部分已建」;DEV_GUIDE §237 blanket-ban→分層(對齊 IC_API_TEST_LAYERING)、§327、§54 多agent。

## 🔴 委員 review(codex+composer 雙 BLOCK)揪出更廣真相——已全數修訂
- **R2/R3/R4 全紅,非只 R4**:`check_decoupling.sh` 實跑 R2=5、R3=12、R4=1;phase4 只窄查特定檔故長期誤報綠(**我首輪 tail 截斷只看到 R4,驗收失誤,composer 抓到**)。R2/R3=momentum/Analysis 與 api/* 直接 import `momentum/FeatureEngineering` 共用工具(warmup_lookup/consumer_gate/run_paths…)。ARCH 主表/IC 小節/PRODUCT_VISION 已全改據實⚠️。
- **兩個競爭權威 doc(我首輪漏)**:PRODUCT_VISION.md 自列 7 規則+R2/R3/R4「已達成」假綠→改 pointer+據實;全系統解耦Prompt.md 宣稱「唯一且不可變」+舊 R4/R5/R6→加 HISTORICAL banner+舊→canonical 對照+inline 標失效。
- scanner over-claim 收斂(ROADMAP 不再稱「查全 R1-7」;canonical R6 標明 phase4 僅跑 Strategy/ 子集);DEV_GUIDE 補 L1 缺口(走 ingest 即使只斷 schema 仍須真 kline);§541 R6 語意釐清。
- 閉合自驗:grep C1/C2/C3 無殘留假綠/競爭權威✅;phase4 135 passed✅。review 檔=handoffs/DOCDRIFT-D1D2-REVIEW-{codex,composer}.md。
- **codex 閉合重驗**(handoffs/DOCDRIFT-D1D2-REVIEW-codex-closure.md):競爭權威+R2/R3 主表已 CLOSED;再揪 ARCH:1546「Rule 1-7 全部通過」殘留→**已修**(改為「不宜宣稱全部通過」+指債票);最終 grep 全庫無殘留假綠✅。**所有 BLOCKING 已閉合**。

## 🔴 待你決策/待辦
- **解耦 R2/R3/R4 既存違規**(共 18 筆)已立 ROADMAP P2 債票:R2/R3 是真違規還是 FeatureEngineering 該豁免為共用基礎設施=架構 triage(非 doc 能定);code 本 session 不動(你 2026-07-12 裁定立票)。
- **commit**:doc diff 待你點頭(排除 .claude/settings.json 既有改動、.claude/gate/audit.log)。
- 派 codex 閉合重驗中(確認 findings 真關閉)。
- 之後:文檔簡化研究(委員會,接 D1/D2)。

## 其他剩餘(doc 後)
1c Net IC 量綱(大,net_ic_analyzer.py:34)→1d/1f→實測→AI Agent。
