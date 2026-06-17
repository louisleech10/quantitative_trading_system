# L65 Hardening SPEC/TODO — Adversarial Review (Composer 2.5)
**範圍**：子項1 移 legacy + 子項3 釘死 causal（子項2 已否決）| **Reviewer**：Composer 2.5 獨立 | 2026-06-17

## Verdict：需修補後派工
核心方向可施作，但 §G golden 無落地 Task、batch OOM 護欄會因移除 `ic_first_pipeline` 靜默失效、causal=False 既有測試與 G-3 口徑衝突——Agent 照現稿實作高機率假綠或多 symbol OOM。

## Findings（挑戰前提優先）

**[BLOCKING|High] §G「動工前 baseline」無對應 Task/腳本** — §G:44-46「動工**前**…baseline 存 `tests/golden/l65_hardening/`」；repo 無此目錄、TODO 無 freeze/compare 命令。B1/B2 Gate 要求 G-1/G-3 byte 一致卻無可執行產生/比對步驟 → 驗收不可證偽。

**[BLOCKING|High] batch IC-First OOM 護欄移除後必失效** — `batch_service:635-640` 靠 `_config_enables_ic_first`（讀 `ic_first_pipeline`）；Task 2.2 刪欄位後恆 False，IC-First 成唯一路徑卻不再 `concurrent_symbols=1`。§P 未列 `:635-660` 改法 → 多 symbol batch OOM（命中 §3 多 symbol 原則）。

**[BLOCKING|High] causal 釘死 vs 既有測試語義衝突（假綠）** — `test_ff_causal_golden.py:41` 顯式 `causal_preprocessing:False` 並斷言與 True 不同；`test_l65_v2_transforms.py:32,44` 同。Phase1 強制 True 後這些測試仍可能綠但語義變成「測 causal=True」；§V「不得只刪斷言」未列改寫清單與新 golden 策略。

**[MAJOR|High] §A 前端事實錯誤** — §A:27「ic-analysis/page.tsx 引用 ic_first」；`frontend/src/app/ic-analysis` grep 0 匹配。實際僅 PreprocessingPanel+types（2 檔）。影響面盤點失真。

**[MAJOR|High] Task 3.2 / §V 簽核空殼** — Task3.2「§V 全套不變量」；§V 僅泛述「值守恆/隔離」，無可執行不變量表、命令、輸出 schema。三方簽核無機械 gate → 流於口頭 PASS。

**[MAJOR|Medium] Task2.1 metadata 策略未定** — §P:75「`ic_first_pipeline` 保留 True 常數**或**委員會定」；與 Task2.2「刪欄位」矛盾。Agent 會二選一亂猜，下游 metadata 契約漂移。

**[MAJOR|Medium] B2 grep 漏 env** — Task2.2 驗證含 `FFACT_IC_FIRST` 但漏 `FFACT_MULTI_SYMBOL_IC_FIRST`（`config.py:67`）；刪 helper 後 env 殘留無偵測。

**[MAJOR|Medium] `get_multi_symbol_ic_first_enabled` 為孤兒碼** — 僅 `config.py:66` 定義、無 caller；§A 當活躍路徑陳述。刪除無功能影響，但「env 覆蓋」敘述誇大。

**[MINOR|High] §C:40 walk-forward cache 約束過時** — 「fingerprint 必須隨 walk-forward 參數變動」；子項2 已否決。易誤導實作者改 cache。

**[MINOR|Medium] 測試面低估** — HANDOFF「~10 測試」；實測 ≥13 檔含 `test_multi_symbol_ic_first`(27處)、`test_ic_first_pipeline`(8處) 等，無逐檔改寫矩陣。

**§1 十類摘要**：1 矛盾(metadata)有；2 漏項(batch/golden/測試矩陣)有；3 不可測(G freeze)有；4 quant(假綠測試)有；5-6 過度工程/OOM(batch)有；7 cache(過時§C)輕；8 API( batch 契約)有；9 測試品質有；10 Agent 可執行性(golden 腳本缺)有。

## 被當成事實的未驗證假設
1. **§G baseline 已可跑** — 目錄/腳本不存在；僅規格文字。（assumption）
2. **ic-analysis/page.tsx 引用 ic_first** — grep 反證。（§A 錯陳述）
3. **`get_multi_symbol_ic_first_enabled` 為活躍路徑** — 無 caller，孤兒。（§A 誇大）
4. **G-3「預設 byte 不變」足以守 causal** — Phase1 只改 `__init__`；`causal=False` 執行路徑差異靠 Phase3.1 才清死碼，中間期假綠窗口未封堵。（assumption）
5. **移除 `ic_first_pipeline` 後 batch 行為仍安全** — OOM 護欄依賴該欄位，未驗證替代。（assumption→已用程式碼反證風險）

STATUS: DONE
