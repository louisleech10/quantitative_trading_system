# HANDOFF

**當前任務**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）審到 **完整 FROZEN**。
**工作方法**：先讀 `docs/GAP3_EVENT_UX_ROLE_CARD.md`（委員出補丁包、主委整包套用；主委不得自寫第二處複述）。

## 狀態（R16 已全數落地並收尾）

- SPEC **2,898 行／42 Task**（十七輪未增未減）；版本行 = `R16-landing`，狀態 **未 FROZEN，待 R17**。
- R16：9 findings（codex 5／composer 1／grok 3）→ 5 群集，**全數落地**；三家 Verdict 一致「需修訂後定版」。
- 三類歸因（逐家自報）codex (N)0/(A)2/(R)3；composer (N)0/(A)0/(R)1；grok (N)0/(A)2/(R)1 ⇒ **(N) 全員 0，連兩輪**。
- 🔴 **R15 收斂檔宣稱「群集 E 已閉」不實**——補丁包 AFTER 明文要求改之 ⑭(f) 本體未被套用（三家全員抓到，主委漏套）。
- 🔴 **兩處委員互斥，主委已裁決並把理由寫進 SPEC 供 R17 覆核**：①receipt hash 只納入 `lookahead_bars_declared`、
  不納入導出之 purge rows ②治理三條紀律逐條拆——檔頭 receipt 封口為機械閘，另兩條維持具名殘留。
- 🔴 **新閘 `scripts/gap3ux_header_round_check.sh`**（掛入 `gap3ux_pre_review.sh`）上線首跑即抓到檔頭停在 R15。
- 條件④ locus 歷史債 **25 → 13**（主委只補「被刪字面」12 條）；餘 13 條列 (甲)(乙) 兩選項請 R17 裁，**主委是受益方故不自裁**。
- 輪數估計：composer 1／grok 1／codex ≥2。

## FROZEN 四條件現況

①⬜ P0=0／**P1=7**　②⬜ 自傷去重 5 群集（需 0）　③✅　④⬜ 13 條 anchor 待 R17 裁定

## 下一步（依序）

1. **派 R17**：由 r16 三份改號生成 brief/facts/locus；派前必跑 `bash scripts/gap3ux_pre_review.sh`（rc=0）。
   🔴 **R17 brief 必含**：①覆核主委兩處裁決 ②裁定條件④之 (甲)/(乙) ③覆核新閘之可證偽性（檔頭改回舊輪次須紅）。
   `--task-id` **須為 session 之大寫形式**（`20260824-GAP3UX-X-REVIEW-R17`），否則 `committee_run.sh` fail-closed。
2. R17 落地 → 若四條件齊備 ⇒ **FROZEN，然後停下來等使用者**（不得自行往 TODO 或實作走）。

## 查法（不寫聲稱，只寫命令）

- 常駐閘：`bash scripts/gap3ux_pre_review.sh`；失敗全量輸出落 `.claude/gate/gap3ux_pre_review.last.log`
- 債務：`bash scripts/debt_ledger.sh --has-open`　治理票：`bash scripts/gen_fact_key_blocks.sh --check`
- locus 歷史債：`bash handoffs/20260824-gap3ux-x-review-r16-locus.sh`
- 補丁包：`ls -1 handoffs/patches/`（在磁碟未入版控，**勿清**）
- 白話看板同步：`bash scripts/plain_docs_sync_check.sh`（git-commit 基準，未 commit 前會紅）

## 定案，不要重新討論

輪次上限**已解除**（做到 FROZEN，不用問要不要續派）／42 Task 一個不砍／條件 IC 答案窗屬 IC 分析層（三家碼證，已入 §D-3）／
A-6 取代裁定＝使用者原話（條件③已滿足）／凍前**不拆 SPEC**。

## 本輪學到、已改的流程

批次套補丁之腳本**任何一條沒命中須非零退出**（不得只印 NOT FOUND 續跑）；落地後**當場跑補丁包 VERIFY grep**，
不等下一輪委員來跑。出處＝R16 群集 A（本 epic 第二條 (R) 回歸）。
