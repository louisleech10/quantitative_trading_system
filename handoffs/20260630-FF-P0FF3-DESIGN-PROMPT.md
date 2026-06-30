# 委員會:完整 P0-FF-3 多 TF 全鏈截斷 MR 設計(委員獨立腿)

使用者選完整 P0-FF-3。讀 Claude 腿 `handoffs/20260630-FF-P0FF3-CLAUDE.md`(範圍+已有護網+提案)。**讀碼推理為主,勿跑慢全鏈**(generate 多TF更慢)。

## 你的設計判斷
1. **多 TF config 實際組合**:讀碼定 production multi-TF 怎麼設(primary + training TFs;`feature_factory.py` config.timeframes.training)。用哪個組合測(如 1h+[1h,4h,12h])?
2. **對齊 look-ahead mutation 注入**:monkeypatch `TimeframeAligner.build_asof_index_map`/`align_to_primary` 成 forward/未來粗 bar（look-ahead）→ 截斷 MR 必紅。確認對齊洩漏在前綴**怎麼現形**(粗 TF 對齊衍生欄值變?還是 NaN?)→ 決定 oracle(值 vs NaN mask vs c2_2 擾動)。V-6 的 `test_before_baseline_shows_lookahead` 是否可複用注入機制?
3. **window 估算**:多 TF 暖機(粗 TF W233 換算細 TF 列數);用足夠長窗。
4. **複用 B2**:新檔 `test_ff_multitf_truncation_mr.py` 共用 B2 helper(批次讀/抽樣/收斂gate/mutation),還是擴 B2 檔?mutation 層覆蓋守衛加「對齊層」。
5. 結論:`P0-FF-3 設計定案`。

輸出 `handoffs/20260630-FF-P0FF3-<你>.md`。只寫你的檔。完成 STATUS: DONE。
