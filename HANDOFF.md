# HANDOFF

**當前任務**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）審到 **完整 FROZEN**。
**工作方法**：先讀 `docs/GAP3_EVENT_UX_ROLE_CARD.md`（委員出補丁包、主委整包套用；主委不得自寫第二處複述）。

## 狀態（R17 已全數落地並收尾）

- SPEC **2,983 行／42 Task**（十八輪未增未減）；版本行 = `R17-landing`，狀態 **未 FROZEN，待 R18**。
- R17：12 findings（codex 8／composer 2／grok 2）→ 9 群集，**全數落地**；三家 Verdict 一致「需修訂後定版」。
  **P0＝0（連三輪）**。條數回升係委員照要求「以反例重跑」而挖深，非品質變差。
- 🔴 **條件④已由委員裁定＝(甲)**（composer＋grok；主委為受益方未參與）：量測範圍＝**當輪**補丁包，
  歷史輪 anchor 債具名結案；並確認主委「不宣稱未發生之改動」界線正確。
- 🔴 **主委 R16 裁決 D 之理由二被 CODEX-R17-P1-01 反例打破**（`event_level` 無 `symbol`
  ⇒ 交換 symbol 分派可得「不同 purge、相同 hash」）⇒ 不改裁定方向，**補齊缺的輸入**（增 `symbol`）。
- 🔴 **新閘 `gap3ux_header_round_check.sh` 兩個 skip 分支確為 fail-open**（clean tree 不查 ⇒ 已提交之
  stale header 擋不到）⇒ **已改以債務帳本輪次狀態判定**，實跑 mutation（stale rc=2／duplicate rc=2／還原 rc=0）。
- 🔴 **locus 22 個「非字面」為工具假紅、非委員寫錯**：根因＝brief 格式行之方括號被三家照字面寫成
  `#錨點[@spec]`，而 `_STAGE_SUFFIX` 只吃 `\s*@stage$`。已修切分（不改判準）＋補回歸測試（18 條全過）。
- 輪數估計：composer 1／grok 1／codex ≥2。

## FROZEN 四條件現況

①⬜ P0=0／**P1=9**　②⬜ 自傷 9 群集　③✅　④**規則已裁定 (甲)**；當輪補丁包仍須 locus rc=0（尚有 anchor 待原家族重寫）

## 下一步（依序）

1. **派 R18**：由 r17 三份改號生成 brief/facts/locus。
   🔴 **改號時必查 `locus.sh` 之 PATCHES glob 有沒有跟著換**（R17 踩過：只換 base 造成整批假紅）。
   🔴 **R18 brief 必含**：①要求各家依 grok R17 #10 之三條規則**重寫自家 R17 SYNC-LOCI**
   （敘述型→可 grep 之已寫入字面／未入 hunk→改錨到實際落地句或刪／檔未改→移除使補丁包與採納範圍一致）
   ②覆核 `event_level` 增 `symbol` 後「遞移綁定」是否真成立（再構造反例）
   ③覆核重寫後之 header 閘（含 CLOSED＋clean tree 分支）④Task 7.0b ⑯ 之 400 互斥是否夠。
   `--task-id` **須為 session 之大寫形式**（`20260824-GAP3UX-X-REVIEW-R18`）。
2. R18 落地 → 若四條件齊備 ⇒ **FROZEN，然後停下來等使用者**（不得自行往 TODO 或實作走）。

## 查法（不寫聲稱，只寫命令）

- 常駐閘：`bash scripts/gap3ux_pre_review.sh`；失敗全量輸出落 `.claude/gate/gap3ux_pre_review.last.log`
- locus：`python3 scripts/patch_locus_check.py handoffs/patches/*r17*.md`
- 債務：`bash scripts/debt_ledger.sh --has-open`　治理票：`bash scripts/gen_fact_key_blocks.sh --check`
- 白話看板同步：`bash scripts/plain_docs_sync_check.sh`（git-commit 基準，未 commit 前會紅）

## 定案，不要重新討論

輪次上限**已解除**／42 Task 一個不砍／條件 IC 答案窗屬 IC 分析層／A-6 取代裁定＝使用者原話（條件③已滿足）／
凍前**不拆 SPEC**／條件④＝(甲)（R17 委員裁定）。

## 流程紀律（累積）

- 批次套補丁之腳本**任一條沒命中須非零退出**；落地後**當場跑補丁包 VERIFY grep**（R16 群集 A）。
- **不要用 `git stash` 驗「檔案乾淨時的行為」**——會連待測程式一起藏起來（R17 實際踩到）。
  工作區另有一個他人留下的 `stash@{0}: review-temp`（只動 HANDOFF.md），**勿誤刪**。
