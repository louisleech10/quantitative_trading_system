<!--
委員 finding 四欄範本（Convergence Method Task 2.1 / B2）
每 finding 必須用 canonical heading ID + 四欄，供 scripts/completeness_check.sh 機械抽取。
-->

# 委員 Finding 四欄範本

## 規則（機械可檢）

1. **Heading ID**（全局唯一）：`## <FAMILY>-<ROUND>-<SEVERITY>-<NN>`
   - 正則：`^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$`
   - FAMILY allowlist：`CODEX` | `COMPOSER` | `GROK` | `CLAUDE` | `AGY`
   - 例：`## GROK-R1-P0-01`、`## CODEX-R2-P1-03`
   - **禁止**：`## GROK-01`（缺 ROUND/SEVERITY）、`## UNION-01`、任意自創前綴
2. **四欄**（每個 `## ID` 後至下一個 heading 之間必備）：
   - `**斷言**`：一句可證偽的主張
   - `**碼證**`：檔案路徑 / 行號 / 命令 / 觀測輸出摘要
   - `**來源摘要**`：`<src_path>#sha256[:12]`（機器欄，非語意）
   - 正文：說明 / 修法 / 影響（可選但建議）
3. **P0/P1** 缺 `**來源摘要**`（或 harness 注入 `source_digest: <hex≥12>`）→ completeness **FAIL**
4. **DEGRADE 第二命名空間**（合法缺席事件，**不進** union 分母）：
   - `## DEGRADE-<FAMILY>-<NN>`（例：`## DEGRADE-GROK-01`）
   - 僅供 degrade 狀態機；不得寫成 finding ID

## 單條 finding 範本

```markdown
## GROK-R1-P0-01

**斷言**: <一句可證偽主張；無證據不得列 BLOCKING>

**碼證**: <path:line 或 `cmd` + stdout 摘要>

**來源摘要**: path/to/source.md#a1b2c3d4e5f6

正文：背景、失敗模式、建議修法、影響範圍。
```

## 多條 + 合法 DEGRADE 範例

```markdown
## CODEX-R1-P0-01

**斷言**: ...

**碼證**: ...

**來源摘要**: handoffs/foo-codex.md#0123456789ab

...

## CODEX-R1-P2-02

**斷言**: ...

**碼證**: ...

**來源摘要**: handoffs/foo-codex.md#fedcba987654

...

## DEGRADE-GROK-01

缺席家族：GROK；原因：timeout；approver：…；expiry：…；remediation_owner：…
（此 heading 不進 completeness union 分母）
```

## harness 注入（測試 / 工具鏈）

若無法寫 `**來源摘要**` 欄，允許在 finding body 注入：

```text
source_digest: a1b2c3d4e5f6
```

`completeness_check.sh` 認 hex≥12 為 digest 在場（TC14）。

## 與派工的銜接

- 對抗審查輸出格式見 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`（canonical 四欄段）
- 派工說明見 `docs/MULTI_AGENT_ORCHESTRATION.md` 派工段
