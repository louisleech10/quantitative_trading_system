brief-kind: consult

# fixture — 真實宣告為 consult，另在 fence 內出現 impl（`CODEX-R1-P2-02` 反例之二）

templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做
fact-verified: fixture → 供 kind 解析之 fence 排除測試使用
assumed: fence 內宣告不應影響解析結果

下面這段是說明「impl brief 長什麼樣」，**不是**本檔自己的宣告：

```
brief-kind: impl

EXPECTED-DELTA:
- 範例
```

期望：kind 解析結果為 `consult`（單一宣告，不觸發多宣告歧義），`--only impl-kind` 須拒。
