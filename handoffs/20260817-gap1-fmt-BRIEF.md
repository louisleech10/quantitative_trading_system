# GAP-1 R1 格式修補：codex recon 6 條 findings 補「來源摘要」機器欄

brief-kind: impl

EXPECTED-DELTA: 只改 `handoffs/20260817-gap1-recon-codex.md` 一檔；為其 6 條 canonical findings
（CODEX-R1-P0-01/-P0-02/-P0-03/-P1-04/-P1-05/-P1-06）各補一行 `**來源摘要**:` 欄。
不得改任何 finding 的斷言、碼證或正文語意；不得新增或刪除 finding；不得動其他檔。

## 任務
你上一輪（task-id `20260817-GAP1-X-CONSULT-R1`）產出的 `handoffs/20260817-gap1-recon-codex.md`
在四方 reconcile 收集時被 `scripts/completeness_check.sh` 判 FAIL：
6 條 P0/P1 findings **全部缺** `**來源摘要**` 機器欄（其餘三家 codex/composer/grok/claude 中的
composer、grok、claude 皆有，故只你這份擋住收斂）。

實際錯誤訊息：
```
COMPLETENESS FAIL: P0/P1 missing source digest (**來源摘要** or source_digest:): CODEX-R1-P0-01
（-P0-02 / -P0-03 / -P1-04 / -P1-05 / -P1-06 同）
```

## 怎麼補（格式規則見 `templates/COMMITTEE_FINDING_TEMPLATE.md` §規則 2-3）
每條 finding 的四欄之一加：

```
**來源摘要**: <該 finding 的主要證據檔路徑>#<該檔 sha256 前 12 碼>
```

- 路徑＝**你該條 finding 引用的主要證據檔**（例：`api/services/optimization_task_service.py`、
  `momentum/Strategy/performance_metrics.py`、`api/routes/ml_pipeline.py`），不是你自己的報告檔。
- digest **必須實跑取得**，禁手編：`shasum -a 256 <path> | cut -c1-12`。
- 每條各自對應自己的證據檔；六條可以有重複路徑，但 digest 必須與該路徑實際內容相符。

## 硬性要求
1. **禁改語意**：斷言／碼證／正文一字不動，只新增 `**來源摘要**` 行。
2. 補完自驗並貼 rc：`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-recon-codex.md --family codex`
   必須 `rc=0`。
3. 不 commit、不 push。
4. 不得改 `handoffs/reconcile/` 下任何檔（那是收集端的鎖，主委處理）。

## 產出
改動摘要（哪六行加在哪）＋每條所用證據檔與其 shasum 實跑輸出＋completeness rc。
收尾清 /tmp workdir（保留 claude-501）。
