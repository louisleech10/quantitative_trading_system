# FF-STAT SPEC v37 審查 r18 — CODEX

task-id: 20260926-FFSTATAUTO-X-REVIEW-R18  
family: codex  
brief-kind: review  
標的：`git diff 3130de9b 5551dc5b -- docs/FFSTAT_SPEC.md`；r17 reconcile `handoffs/reconcile/20260926-ffstatauto-x-review-r17/synth.md`。本輪唯讀；未修改 code、SPEC、manifest、templates、CLAUDE.md、git 或 `data_cache/`。

## CODEX-R18-P1-01

**斷言**: v37 已寫明「各自訂指標輸出點」與「沒有參數字典即 fail-closed」，但尚未把這項要求化成所有 L1 路徑都能機械驗證的 output-to-params contract。TA-Lib 路徑在 `compute` 內確實持有一次呼叫的 params；非 TA-Lib 路徑則可由一次方法呼叫產生多個不同 window 的欄，回傳後只剩 plain `DataFrame`，沒有每欄的 provenance／closed `period_keys` mapping。若實作者以欄名猜 period，會直接違反 v37；若不猜，現行介面沒有指定如何列出缺鍵並在 concat 前阻擋。這使「每個 L1 output column 都能取得生成該欄之參數字典」對 advanced/custom 全體不成立，構成 v37 新增契約的 P1 缺口。

**碼證**: 下列 source anchors 顯示多 window／arbitrary DataFrame 在 plain frame 邊界失去 output-to-period mapping。
CODE-ANCHOR: momentum/FeatureEngineering/atomic/microstructure_indicators.py:164
CODE-ANCHOR: momentum/FeatureEngineering/atomic/custom_indicators.py:25
CODE-ANCHOR: momentum/FeatureEngineering/feature_factory.py:1066
MUTATION: 在隔離複本註冊一個 `params={}` 的 custom function，回傳 `short=close.rolling(5)` 與 `long=close.rolling(233)` 兩欄，並以真實 BTCUSDT/12h 資料執行；若仍可把兩欄交給單一 K 計算而沒有 per-output period_keys receipt 或明確 blocked reason，即重現 output-to-params 缺口。

**來源摘要**: docs/FFSTAT_SPEC.md#91ef7ea7ae63；momentum/FeatureEngineering/atomic/microstructure_indicators.py#e497947a3f2e；momentum/FeatureEngineering/atomic/custom_indicators.py#c8d69c237696；momentum/FeatureEngineering/feature_factory.py#47f362f67de2；momentum/FeatureEngineering/feature_config.py#d7e5a9fb2df2

修法：定義一個唯一的 L1 output-point contract；每個 TA-Lib、advanced、custom 輸出點在交給 L2 或跨 engine concat 前，必須同時提供輸出欄、該次呼叫 params、封閉的 `period_keys`／K provenance。advanced engine 的多 window 迴圈要逐欄建立 mapping；custom definition 若不能聲明每個輸出的 period keys，則在輸出前 fail-closed，不能退回欄名解析。blocked receipt 至少列 engine、output columns、缺少的 keys；AST 檢查應驗證這個 contract 的每個輸出點，而非只數到一個 `DataFrame` return。

可行性證據：`TALibWrapper.compute` 已在呼叫 TA-Lib 前複製 params，`_to_dataframe` 對同一次 tuple output 共用該 params；`compute_batch` 也對每個 params 呼叫 `compute`。`MicrostructureIndicatorEngine.get_feature_metadata` 已按 window 列出欄級 params，表示可以把既有 metadata 收斂成輸出 contract；本修法未改數值計算，但若選擇 split output 或改變遮罩欄數，須另行核准 schema／數值影響。

**類別**: code-contract

## CODEX-R18-P2-02

**斷言**: v37 刪除 12h 子集選擇器後，§G⑦ 對 12h 只要求 default full config 的 qualification blocked receipt，並以 Task 2.3 的 12h 單項驗收覆蓋遮罩；但文字沒有明定該 12h 單項驗收要量測每一個啟用的 advanced/custom L1 output point。Task 2.3 列出的 EMA_233、SMA_200、ADX_14、STOCH 與 AST enumeration 可以驗證代表性欄與靜態接線，不能單獨證明動態 12h 路徑的每個輸出都取得正確 K。default config 的 primary/training 是 12h，而既有真實 HDF5 收據記錄 12h 全長 1,696 根；因此雙起點資格路徑會持續被 blocked，這個 runtime coverage gap 不應隨 selector 刪除而隱含消失。

**碼證**: 下列 SPEC 與 default config anchors 顯示 12h qualification blocked 與 single acceptance 的覆蓋邊界。
CODE-ANCHOR: docs/FFSTAT_SPEC.md:86
CODE-ANCHOR: docs/FFSTAT_SPEC.md:122
CODE-ANCHOR: momentum/FeatureEngineering/feature_config.py:57
MUTATION: 在隔離複本只讓一個未列於 12h 範例的 dynamic advanced/custom output 跳過遮罩或取錯 period_key，保留 EMA/SMA/ADX/STOCH 驗收與 AST 可見的其他遮罩呼叫，再以真實 BTCUSDT/12h 1,696 根資料走 qualification blocked path；若現有條文仍可產生 blocked receipt 且所有列明驗收皆通過，即重現 12h output-complete coverage 不足。

**來源摘要**: docs/FFSTAT_SPEC.md#91ef7ea7ae63；momentum/FeatureEngineering/feature_config.py#d7e5a9fb2df2；handoffs/run_receipts/20260927-warmup-table-coverage.txt（本輪讀取：76 enabled、37 in table、39 missing）；handoffs/20260926-ffstatauto-x-review-r17-codex.md（先前真實 HDF5 12h rows=1696 探針紀錄）

修法：保留「12h 雙起點不足只出 blocked receipt」的裁定，但把 Task 2.3 的 12h single acceptance 明定為對 `ConfigManager` 啟用集合之每個 L1 output point、每個 resolved period-key 組合逐一驗證；blocked 只豁免雙起點收斂，不豁免 12h 遮罩與缺鍵 fail-closed。收據列出已執行與未執行的 output points，未執行者不能靜默進入通過。

可行性證據：Task 2.4 已要求 coverage script 列舉基本六類、進階 atomic、CDL 與多輸出元件；現有 12h 真實資料長度足以做單項首個有效值／K 驗收，即使不足以做 §G⑦ 的 500-row dual-start overlap。此補強不恢復 v34–v36 selector，也不要求 full FF run。

**類別**: doc-sync

**必答**

1. **(1a)** `CODEX-R17-P1-01` 已閉合於其原始範圍：v37 的 §G⑦ 不再使用 selector，§N 明確把 `_estimate_indicator_params` mismatch 標為既有且不依賴；`CODEX-R17-P2-01` 也已閉合於其原始 TA-Lib mapping 文字：§C／Task 2.4 現在明列封閉 `period_keys`、STOCH 三鍵與缺鍵 fail-closed。R18-P1-01 是更廣的 advanced/custom output provenance contract，不把 r17 finding 重複計算。
2. **(1b)** 本輪以文字與 source-anchor 核對原 r17 counterexample，沒有重跑原始 full probe：selector 的舊等式在 v37 已被刪除，估算器 mismatch 改列 §N；STOCH／period_keys／fail-closed 已出現在 v37。現行 worktree 的既有 coverage receipt 仍是 76 enabled、37 in table、39 missing，故不能把未實作的表補齊誤報為已通過。
3. **(2a)** 新 v37 defect 是 `CODEX-R18-P1-01`，另有非阻擋 coverage finding `CODEX-R18-P2-02`。前者由 v37 把遮罩範圍擴至 custom／advanced output points 而暴露；後者由刪除 12h selector 後的替代驗收邊界暴露。沒有新增 P0。
4. **(2b)** P1 counterexample 是 `params={}` 的 custom function 內部產生 rolling(5)／rolling(233) 兩欄，及 microstructure 一次 dict comprehension 產生多 window 欄；現行 return 邊界沒有 output-to-period mapping。P2 counterexample 是保留 Task 2.3 列明樣本與 AST 接線、只讓另一個 dynamic 12h output 取錯 K，仍走真實 1,696-row qualification blocked path。上述 mutation 未寫入 repository，也未宣稱已執行。
5. **(3a)** 兩項假設分開判定：① `compute_batch` 會把多個 parameter groups 合併計算後才拆欄——對現行 TA-Lib code 為假，`compute_batch` 逐 params 呼叫 `compute`；②每個 L1 output column 都能在產出點取得生成它的 params dict——TA-Lib 子集為真，但對 microstructure 等多 window advanced output 與任意 custom multi-column output 未被現行介面保證，整體判定為假／未封閉。
6. **(3b)** 證據是 `talib_wrapper.py:332-344,357-369,469-498` 的 params snapshot／逐 params 呼叫／tuple 欄名生成；`microstructure_indicators.py:93-115,153-166` 的獨立 metadata 與多 window DataFrame；`custom_indicators.py:12-33` 的 arbitrary function result concat；`feature_factory.py:991-999,1042-1066` 的 plain frame concat。數字證據為既有真實收據 12h=1,696、coverage=76/37/39；本輪未以探針聲稱取得其他數值。
7. **(4a)** brief 所列未檢查項①未命中：現行 `compute_batch` 沒有 batch 內多組再拆分的反例。項②命中 R18-P1-01：custom、Keltner／Force Index 類 custom-derived 與 microstructure／entropy／tail-risk 的 output provenance 沒有統一可驗證 contract。項③命中 R18-P2-02：12h selector 刪除後，條文沒有明定 12h 全 output-point runtime coverage。
8. **(4b)** 項①由 `talib_wrapper.py:357-369` 證明；項②由上述 custom／advanced／factory anchors 證明；項③由 `docs/FFSTAT_SPEC.md:86,122`、default `primary="12h"` 及既有 1,696-row HDF5 receipt 證明。既有 warmup coverage receipt 的 39 missing 也說明 implementation coverage 尚未可當作通過證據。
9. **(5a)** 不能核准 `VERDICT: proceed`；R18-P1-01 使 v37 的逐呼叫 K／全 L1 output-point fail-closed contract 尚不可驗收。
10. **(5b)** 唯一阻擋裁決的 P0/P1 是 `CODEX-R18-P1-01`；`CODEX-R18-P2-02` 是需在收批前補明的非阻擋 acceptance coverage。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、r18 brief、r17 reconcile、R1–R7 rulings、target diff、template 與 governance verdict values；已核對 TA-Lib params 保留、custom／advanced plain-DataFrame 邊界、12h 條文與 default primary；只把既有真實 HDF5 receipt 的 1,696-row／76-37-39 數字作為已存在證據，未宣稱本輪新 probe 已執行。
TESTS_RUN: `git diff --no-ext-diff --unified=20 3130de9b 5551dc5b -- docs/FFSTAT_SPEC.md` → target diff read-only；`nl -ba`／`rg -n` on `docs/FFSTAT_SPEC.md`, `talib_wrapper.py`, `custom_indicators.py`, `microstructure_indicators.py`, `feature_factory.py`, `feature_config.py` → anchors above；`sed -n '1,240p' handoffs/run_receipts/20260927-warmup-table-coverage.txt` → existing receipt `total_indicators=76 in_table=37 missing=39`；`shasum -a 256` → source digests in findings；`test -d /tmp/claude-501` → `PRESERVED /tmp/claude-501`；`git status --short -- momentum api scripts tests docs templates config` → review前 baseline unchanged；本輪沒有跑 full FF、minute/hour generation check 或新的 real-kline probe。
FAILURES_SEEN: 隔離探針命令在建立前被 PreToolUse／環境安全鉤拒絕，原因是同一命令含 `rm -rf -- "$workdir"`；工具回報 `rm -f style commands are not permitted. Use a safer approach`。依 brief 未改寫清理形式繞過，因此 probe 未啟動、未建立本輪 temp workdir；`/tmp/claude-501` 未觸碰。
SCOPE_CHANGES: none；只新增本輪 committee artifact 與狀態交接檔，未改任何受保護 source／SPEC／manifest／template／git／data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none implemented；本輪只提出 output provenance 與 12h acceptance contract 缺口，未改變數值、欄位 schema、檔案大小或測試門檻。
TMP_CLEANUP: 本輪隔離命令在建立前被拒，故沒有新 workdir 可清理；未執行或改寫任何刪除命令；`/tmp/claude-501` 已確認存在並保留。既有其他輪次暫存不在本輪 scope。
OUTPUT_PATH: handoffs/20260926-ffstatauto-x-review-r18-codex.md
HANDOFF_OUTPUT: handoffs/20260927-20260926-FFSTATAUTO-X-REVIEW-R18.md

VERDICT: blocked
BLOCKED-BY: CODEX-R18-P1-01
CLOSED: CODEX-R17-P1-01, CODEX-R17-P2-01
STATUS: DONE
