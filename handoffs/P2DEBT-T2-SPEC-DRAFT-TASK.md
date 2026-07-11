# 起草任務:P2 債票 2 SPEC 初稿(legacy 測試寫 data_cache → tmp redirect)
Task-id: p2debt-t2 | Date: 2026-07-11 | 起草人: Composer(四調行)

## 背景(自己驗證,不可只信本檔)
HANDOFF 票 2+出處 handoffs/IC1EB-B3-REVIEW-R3-codex.md 歸屬裁定:1a cut1 等舊測試走真 service 路徑,會**覆寫 data_cache 衍生檔**(污染使用者真實資料)。修法方向已定=測試輸出 tmp redirect,參考 1e+1b capture 的 persist patch 模式(scripts/ic1eb_b5_replay.py 內 `patch_persist_outputs`)。

## 你要做的
1. 偵察(全部附實跑 receipt):
   - 找出**所有**會寫 data_cache 的測試:grep tests/ 中 service 真路徑呼叫(analyze/persist/材料化),對照 data_cache 寫入點(momentum/api 內 persist 函式清單);列完整測試→寫入路徑對照表。
   - 讀 scripts/ic1eb_b5_replay.py 的 patch_persist_outputs 模式,評估可否泛化成 conftest fixture(monkeypatch persist 目標到 tmp_path)。
   - 確認與票 5(1a cut1 golden provenance)的交界:1a cut1 golden 測試重放是否在本票 redirect 範圍內;若 redirect 會改變 golden 測試讀寫行為,明列為 RISK-HIT 升級訊號。
2. 起草 SPEC 初稿寫入 `handoffs/P2DEBT-T2-SPEC-DRAFT-R1.md`,依 templates/SPEC_TEMPLATE.md;§RISK 誠實評估(涉 data_cache=原則(a) 資料品質邊界,寫明 RISK-HIT 判定與理由);§A canonical fact-scope+FACT-RECEIPT(票 1 剛教的);§V 含可證偽設計:redirect 後「測試跑完 data_cache 零變化」須是可機驗斷言(檔案系統快照比對),且證明「拿掉 redirect 會 FAIL」。
3. 硬邊界:不改生產 code 的 persist 語意(只動測試層);data_cache 現有檔案唯讀;禁 conftest 大改造成其他 suite 行為漂移(列影響面)。

## 禁止事項
禁改 repo 任何檔(除 R1 草稿);偵察只 read-only;禁跑會寫 data_cache 的測試(先 grep 靜態確認,要跑就 --collect-only);禁 git checkout/restore。
