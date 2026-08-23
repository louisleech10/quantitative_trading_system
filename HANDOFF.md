# HANDOFF

**當前任務**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）審到 **完整 FROZEN**。
**工作方法**：先讀 `docs/GAP3_EVENT_UX_ROLE_CARD.md`（委員出補丁包、主委整包套用；主委不得自寫第二處複述）。

## 狀態（R15 已全數落地並收尾）

- SPEC **2,787 行／42 Task**（十六輪未增未減）；版本行 = `R15-landing`，狀態 **未 FROZEN，待 R16**。
- R15：10 findings（codex 4／composer 2／grok 4）→ 6 群集，**全數落地**；三家 Verdict 一致「需修訂後定版」。
- 三類歸因 **(N)0／(A)8／(R)2** ⇒ (N) 三家全員為 0。**主委自傷絕對數 6**（上輪 10，首次明顯下降）。
- 三家獨立比對 `git diff 776a0faa^..776a0faa`，一致確認主委 R14 落地**符合**「只刪殘、不加新」。
- 輪數估計：composer **1**（自 2 下修）／grok 1／codex 約 3。
- reconcile synth 已填並過機檢（cluster attribution／completeness 皆 rc=0）；債務已銷（`debt_ledger --has-open` rc=0）。

## FROZEN 四條件現況

①⬜ OPEN **P0=0／P1=2**（皆 (R) 字面殘留）　②⬜ 自傷 6（需 0）　③✅ 已滿足（使用者 8/23 原話）　④⬜ locus 歷史債

## 下一步（依序）

1. **派 R16**：`handoffs/20260824-gap3ux-x-review-r16-{brief,facts.sh,locus.sh}.md|sh`（由 r15 三份改號生成，見
   `scratchpad/build_r15.py` 之作法）；派前必跑 `bash scripts/gap3ux_pre_review.sh`（rc=0）。三家＝codex＋composer＋grok。
2. R16 落地 → 若四條件齊備 ⇒ **FROZEN，然後停下來等使用者**（不得自行往 TODO 或實作走）。

## 查法（不寫聲稱，只寫命令）

- 常駐閘：`bash scripts/gap3ux_pre_review.sh`；失敗全量輸出落 `.claude/gate/gap3ux_pre_review.last.log`
- 債務：`bash scripts/debt_ledger.sh --has-open`　治理票：`bash scripts/gen_fact_key_blocks.sh --check`
- 補丁包：`ls -1 handoffs/patches/`（R8 起 7 份，在磁碟未入版控，**勿清**）
- 白話看板同步：`bash scripts/plain_docs_sync_check.sh`（git-commit 基準，未 commit 前會紅）

## 定案，不要重新討論

輪次上限**已解除**（做到 FROZEN，不用問要不要續派）／42 Task 一個不砍／條件 IC 答案窗屬 IC 分析層（三家碼證，已入 §D-3）／
A-6 取代裁定＝使用者原話（條件③已滿足）／凍前**不拆 SPEC**。
