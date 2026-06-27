# 任務:adversarial 審 FF 深稽 Claude 獨立腿(不同模型,作者不自審)

讀 `handoffs/20260627-FF-DEEPAUDIT-CLAUDE-LEG.md`(被審物)+ `handoffs/20260627-FF-AUDIT-RECONCILE.md`(scoping 背景,已雙家戳記)。

你是 **adversary**,不是確認者。目標:獵出這份「深稽腿 + 測試設計」自身的漏洞。**禁止確認式放水**(把真漏洞降級 MINOR)。每個 finding 必附**可證偽的具體反例或真實程式路徑**,不接受「看起來合理」。

## 必答(逐項給 BLOCK/RISK/OK + 理由 + 反例)
1. **§A 事實準不準**:實際 grep/讀碼驗 A1–A5。有沒有把「其實有值驗證的測試」誤判成 smoke?或漏掉某個已存在的 differential/causal 測試?(真去 `tests/` 跑 grep)
2. **§B 可疑點真假**:B1(input_type 預設 single 陷阱)、B2(BETA/CORREL 餵 close_volume)、B3(手刻 Klinger/ForceIndex/EOM 非 canonical)、B4。哪些是真 bug、哪些是 Claude 誤讀?**真 run 一個最小反例驗證**(如造一個漏登錄的指標看是否靜默走 close;或對 BETA 比對 talib 預期 input)。
3. **§C 測試設計會不會假綠**:
   - C2-1 全鏈截斷 MR 的 **warmup 對齊**是不是會掩蓋真實差異(§E1)?比對區間怎麼界定才不假綠?
   - C1-3 手刻指標的 canonical oracle 由誰定義才可證偽(不准拿實作自身當 oracle)?
   - C1-1 differential 「vs 直呼 talib」是否只驗了 wrapper 沒驗 talib——夠不夠抓 B1/B2 類錯配?
   - mutation 門檻(C1/C2/C4-mutation)真的會 FAIL 嗎?有沒有改壞但測試仍綠的漏網?
4. **§D 邊界**:「不全重測」對不對?有沒有 P0 該補卻被本批排除?
5. **§E 四個前提**你怎麼答。

## 輸出格式
寫到 `handoffs/20260627-FF-DEEPAUDIT-ADV-<你的名字codex或composer>.md`:
- 結論一行:腿可進 SPEC / 須修後再審
- BLOCK 清單(每條:問題+反例+建議修法)
- RISK / OK 清單
- 對 §C 測試設計的具體補強(讓 mutation 真的擋得住)

**不准改 repo 其他檔**,只寫你的 review 檔。兩輪內有疑直接寫進 review,別 solo 硬幹。
