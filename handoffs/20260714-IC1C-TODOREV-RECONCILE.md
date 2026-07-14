# IC1C TODO 審查 RECONCILE(r1)— Claude 主編

task-id: IC1C-TODOREV | 2026-07-14 | 輸入: handoffs/20260714-IC1C-TODOREV-{codex,composer,grok}.md
verdicts: codex REJECT(8B) / composer REJECT(4B+6 MAJOR) / grok REJECT(3B+6 MAJOR) → TODO 退回改寫 r2

## 合併裁決(全 ACCEPT,無 REJECT/降級)

| 主題 | 來源 | r2 落點 |
|------|------|---------|
| T-F1 reporter/export 消費點零 Task | CODEX-2+COMPOSER-4/6+GROK-1 | 新 Task 1.4(B1):ic_reporter :150/:209/:631-634/:773 改 `cost_drag_return`+§U union、刪 net_ic alias;export_formats fixture(:73-74)改 §U profile+斷言 CSV 無 net_ic 欄;各附 red-on-break |
| T-F2 gate 命令不可執行 | COMPOSER-2+GROK-2 | 全部 Gate 命令帶明確參數:`mutation_probe_check.sh <測試檔...>`;B1/B2 分列 |
| T-F3 Task 1.2 驗收跨批依賴 | COMPOSER-3+CODEX-4+GROK-4 | Task 1.2 驗證改 momentum 層直測 `_run_net_ic`(T1b,B1);T2 e2e 歸 Task 2.1/B2 |
| T-F4 M10 批次錯置 | COMPOSER-1 | §B:M10-B1=僅 T1 層;M10 三層完整=B2 Gate |
| T-F5 G-NEW2 空洞+freeze 腳本未定義+producer 自證 | COMPOSER-5/8+CODEX-7/8+GROK-3 | freeze 腳本 `--baseline old\|new\|new2` 三模式+固定輸出路徑;canonical 重算**禁 import analyzer**(內嵌獨立 numpy);G-NEW2=API 入參 7bps vs config 直開 7bps 的 feature dict sha256 等值+具體命令+exit oracle;G-OLD 附獨立內容 validator(行數/鍵數/必含路徑/fixture hash lineage) |
| T-F6 SCHEMA 常數路徑漂移 | CODEX-3+GROK-10 | 依 Frozen SPEC:專檔 `tests/momentum/Analysis/test_net_ic_schema_profiles.py::SCHEMA_*`,他檔 import 單一來源 |
| T-F7 cost_bps 域驗證漏 disabled 分支 | CODEX-6 | 三層 validator:cost_bps 非 None 一律驗域(與 enabled 無關);enabled 另驗非 None;M10 各層覆蓋 true/false |
| T-F8 grep 0.1 誤殺 | CODEX-5+GROK-12 | 靜態檢查改鎖舊 fallback 表達式(`turnover ?? 0.1`/`|| 0.1`);行為由 RTL 測試「缺 turnover 顯示無資料」守 |
| T-F9 capacity NaN vs JSON 禁 NaN 互斥 | GROK-6 | batch 組 dict 邊界:非有限 capacity 欄→null(計算函式不動);`json.dumps(allow_nan=False)` 全 dump 強制;T1 斷言 capacity 子樹 strict-JSON 可序列化 |
| T-F10 Task 0.1 冷啟動不足 | COMPOSER-9+GROK-5+CODEX-8 | 給準入口偽碼(fixture→features/labels→IC summary+turnover_data 構造或 `run_deep_analysis(force_modules=...)` 前置)+確定性(排序/seed)+skipped 注入具名步驟+lineage 標記 |
| T-F11 Task 1.3 漏第二個 proxy 測試 | GROK-7 | 改寫表補 `test_net_ic_proxy_nan_turnover`(:92-96);完成定義=`rg compute_net_ic_proxy tests/`==0 |
| T-F12 config_override 雙入口 | GROK-8 | Task 2.1 明列 `DeepAnalysisRequest.config_override`+`ICAnalyzeRequest.config_override` 兩路徑皆 422;merge 順序禁 override 蓋 typed 欄;測試矩陣兩 path |
| T-F13 §0 解耦 7 條不全 | GROK-9 | §0 補 7 條 checklist 一行表+本票適用/N/A |
| T-F14 diff manifest 機器可讀 | COMPOSER-10 | G-NEW 產 `handoffs/ic1c_baseline/diff_manifest.json`,Gate 讀取比對 |
| T-F15 request JSON 示例 | GROK-11 | Task 2.1 附完整 deep-analysis body fenced JSON |
| T-F16 service 序列化破壞 union | COMPOSER-7 | Task 2.1 增 `_serialize` 保 union 三鍵禁扁平化+T2 斷言 |

## 下一步
TODO r2 → 三家閉合重驗 → 戳記 → Frozen → B0 開工(Grok 實作)。

(r2 輪補記 2026-07-14:composer 4/4 B CLOSED+2 新 B;codex 4/8 CLOSED+4 STILL-OPEN+3 新 B;grok 3/3 CLOSED+1 新 B。合併裁決 T-F17 真 fixture 特徵名(oc_return/hl_range);T-F18 validator 統一偽碼「非 None 一律驗域」三層同步;T-F19 負 turnover→SKIPPED 去 clamp(SPEC v1.1 補裁;grok 抓到本檔 r1 漏列 codex ADV-CODEX-1,已認);T-F20 G-NEW2 async 入口(POST task_id→輪詢 GET);T-F21 npm --prefix frontend;T-F22 reporter cost_drag_return=裸 number 非 union;T-F23 UI 三態具名 oracle;T-F24 phase26 入 B3 Gate;T-F25 docs 唯一路徑;T-F26 B0 Gate 補 shasum -c+雙跑決定性。全 ACCEPT 落 TODO r3。)

(r3/r4/r5 輪補記 2026-07-14:r3=grok APPROVE+戳記;composer REJECT(1B:Task1.3 clamp 殘字)+MAJOR(G-NEW2 bootstrap/Phase3 Gate/npm prefix)→r4 全落;codex REJECT(5B:§0 漏負值+負 turnover 無具名測試/G-NEW2 注入不對稱/雙跑非字面命令/capacity 鍵集合無斷言/collect-only 未入 Gate 行)→r5 全落:test_negative_turnover_skipped+probe m11/G-NEW 三注入含 zscore_20=-0.2/G-NEW2 比對集排除三注入特徵/h1-h2 字面比較/capacity 恰等+calibration 恒 uncalibrated/--collect-only 入 §B B2。全 ACCEPT。)

(r5/r6 定稿記錄 2026-07-14:composer r5 APPROVE(0B;2 MINOR=G-NEW2 編號漂移/nan turnover 擇一→r6 釘死);codex r5 REJECT(2B:G-NEW 注入 vs byte 等值矛盾/擇一字樣)→r6 修=不變欄比對排除三注入特徵(oc_return/hl_range/zscore_20,常數與 G-NEW2 共用,注入特徵改驗 SKIPPED 形狀)+nan/負 turnover 唯一 raise→codex r6 **APPROVE**。TODO 定稿=r6;grok r3 APPROVE/composer r5 APPROVE/codex r6 APPROVE,三家齊。)

## 戳記
RECONCILE-STAMP: grok APPROVED 2026-07-14 sha256:6c2a230df7f952069af7d1779d235f47e3a17bcdcc88e44fda53d2e95d4affe0 task:IC1C-TODOREV
RECONCILE-STAMP: composer APPROVED 2026-07-14 sha256:936daabcb2eadcf526e481725da471f68d97804ff868039bfca739d71efe33d9 task:IC1C-TODOREV
RECONCILE-STAMP: codex APPROVED 2026-07-14 sha256:936daabcb2eadcf526e481725da471f68d97804ff868039bfca739d71efe33d9 task:IC1C-TODOREV

RECONCILE-STAMP: grok APPROVED 2026-07-14 sha256:936daabcb2eadcf526e481725da471f68d97804ff868039bfca739d71efe33d9 task:IC1C-TODOREV
