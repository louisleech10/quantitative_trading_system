# 委員會:B2 mutation 2 修定案(委員獨立腿)

讀 Claude 腿 `handoffs/20260630-FF-B2-MUTFIX-CLAUDE.md`(含 2 問題+假設+提案)。**讀碼推理為主,勿跑慢全鏈**;問題1根因可做小 targeted 驗(小 generate 看 L4 fill_rate / mutation 是否生效)。

## 問題1:l4 shift(-1) 探針沒紅
- 驗/反駁 Claude 根因 A(mutation加NaN降fill_rate)/B(L4本低fill)/C(monkeypatch沒生效,registry快取如C1-2)。
- 定 shift(-1) robust 偵測:提案1(改用 c2_2 擾動邏輯,比值)/ 提案2(c2_1 對應高fill欄的 trunc-NaN 視為look-ahead fail)/ 其他。哪個既抓 shift(-1) 又不誤殺列數依賴良性 NaN?

## 問題2:fracdiff 探針靜態誤判
- 定:放寬 `mutation_probe_static.py` 啟發(資料擾動+呼叫被測 generate 也算碰系統)vs 改探針顯式引用被測符號。**不可削弱靜態對真空心/偽raises的攔截**。

## 輸出
`handoffs/20260630-FF-B2-MUTFIX-<你>.md`:問題1根因+修法、問題2修法、`B2-MUTFIX 定案`。只寫你的檔。完成 STATUS: DONE。
