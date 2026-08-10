# fixture — 只有 code fence 內寫 brief-kind（`CODEX-R1-P2-02` 反例）

本檔**沒有**真實的行首 `brief-kind:` 宣告；下面那行在 fence 內，是「示範怎麼寫」的說明文字。

```
brief-kind: impl
```

期望：kind 解析須判為「缺宣告」而 fail-closed，不得採信 fence 內容。
