# HANDOFF

## 當前：GAP-3 事件型 UAT 缺口修補 SPEC（目標＝FROZEN）

- 標的 `docs/GAP3_EVENT_UX_SPEC.md`：**3,511 行／42 Task（三十輪未增未減）**，版本行 `R30-landing`，**狀態未 FROZEN**。
- 內容最後落地＝R29 八條（commit `f15e9cea`）。`ed411291`＝**僅檔頭收據＋`ERRATA-R30-01`**，零內容。
- **進行中**：R31 三家對抗審已派出，ledger round `e0bdac3b-d5f5-4b02-9d36-a3bf9797f16b`（OPEN）。
  產物 `handoffs/20260824-gap3ux-x-review-r31-{codex,composer,grok}.md`。

## R30 輪的處置（已結案，勿重查）

R30（round `03422383`）codex 交件格式不合規（來源摘要寫成 `path#sha256:<hex>`，
`completeness_check.sh:352` 要求 `#` 緊接 12 位 hex）。`cx_run` 說「可同輪重派」，
但**同輪重派需 dispatch token，而 `gate.sh` 於 OPEN 債時一律拒發** ⇒ 主委路徑上死鎖。
依設計逃生口 `debt_clear --abandon --kind collection-failed` 銷帳，**該輪零落地**，
議題原封不動改編為 R31 重派三家。此死鎖與「ABANDONED 輪被 header 閘要求寫 `-landing`」
兩件，是本輪新發現的工具自傷，**應列入 R31 議題請委員裁**。

## 最高位階條款（`docs/GAP3_EVENT_UX_ROLE_CARD.md` 為準，本檔不重述細節）

R20 主委不得新建驗收機制／R21 條件②′／R22 主委不得自我歸類＋(a)-(e) 五類／
R23 主委不再自擬殘留查核清單／R25 anchor 只錨 AFTER 仍存在之字面／
R28 `must_exist`＝AFTER 每一非空行、跨包衝突停手不擇一。

## 工作方法（不得違反）

委員出【補丁包】、主委整包**逐字**套用（`scripts/gap3ux_apply_patch.py`），不得自寫第二處複述；
觸及 SPEC 之 commit 須有補丁包或 ERRATA id；派審前 `gap3ux_pre_review.sh` 須 rc=0；
補丁包互相矛盾時在具體提案間裁決並把理由寫進 SPEC，不另創第四種；文件一律不寫閘數。

## 未答否決點（自 R21 起十輪）

凍結條件②之替換（改為四指標），使用者可推翻。

## 下一步

R31 落地 → 續派 R32 → **FROZEN 後停下來等使用者**，不要自己往 TODO 或實作走。
