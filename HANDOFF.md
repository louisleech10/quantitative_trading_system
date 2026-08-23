# HANDOFF

**當前任務**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）審到 **完整 FROZEN**。
**工作方法**：先讀 `docs/GAP3_EVENT_UX_ROLE_CARD.md`（委員出補丁包、主委整包套用；主委不得自寫第二處複述）。

## 狀態（R18 已全數落地並收尾）

- SPEC **3,071 行／42 Task**（十九輪未增未減）；版本行 = `R18-landing`，狀態 **未 FROZEN，待 R19**。
- R18：8 findings（codex 5／composer 1／grok 2）→ 5 群集，**全數落地**；三家 Verdict 一致「需修訂後定版」。
  **P0＝0（連四輪）**。
- 🔴 **兩家明確判「未陷入不收斂」並給停止判準**。codex 之五條**本輪已全部落地** ⇒ **R19 即為驗證輪**：
  ①purge 自由變數逐項入 hash＋symbol／timeframe swap 反例 ②⑨(f) 單一 oracle
  ③兩 route dual-field 400-before-analyzer ④digest registry 可在 ESM Vitest 執行 ⑤no-row skip 有 marker。
- 🔴 **本輪結構性修正**：「purge 自由變數已全綁進 hash」**連三輪被反例打破**（R16 漏 `symbol`、R17 漏觸發
  `timeframe`）⇒ 病根是**以列舉代替導出**。§D-3′-a（ii）新增**導出程序**；§G G-3 ⑥ 新增
  **(d) 集合相等斷言**（`V == H`）與 **(e) timeframe swap mutation**。**列舉會漏，集合相等不會。**
- 🔴 **主委兩處臆測被碼證撤回**：`ICFullAnalysisRequest` 為**繼承**（`ic_models.py:173`），無第二條 analyzer
  路徑；Task 7.0b ⑯ 原驗收「400 且 spy 收到值」自相矛盾 ⇒ 已拆為三條。
- header 閘之 no-row 分支改 fail-closed，**以 codex 原反例實跑得 rc=2（原為靜默 0）**。
- 輪數估計：三家皆「至少再一輪驗證」。

## FROZEN 四條件現況

①⬜ P0=0／**P1=8**　②⬜ 自傷 5 群集　③✅　④當輪補丁包 locus 待清（規則已裁 (甲)）

## 下一步（依序）

1. **派 R19**：由 r18 三份改號生成 brief/facts/locus。
   🔴 **改號時必查 `locus.sh` 之 PATCHES glob 有沒有跟著換**（R17 踩過：只換 base 造成整批假紅）。
   🔴 **R19 brief 必含**：①逐條驗收 codex 五條停止判準（本輪已落地，R19 是驗證輪）
   ②再構造一次 purge 反例——集合相等斷言是否真的擋得住 ③覆核導出程序之「常數排除清單」是否封閉
   ④各家重寫自家 R18 SYNC-LOCI（條件④＝(甲)，當輪須 rc=0）。
   `--task-id` **須為 session 之大寫形式**（`20260824-GAP3UX-X-REVIEW-R19`）。
2. R19 落地 → 若四條件齊備 ⇒ **FROZEN，然後停下來等使用者**（不得自行往 TODO 或實作走）。

## 查法（不寫聲稱，只寫命令）

- 常駐閘：`bash scripts/gap3ux_pre_review.sh`；失敗全量輸出落 `.claude/gate/gap3ux_pre_review.last.log`
- locus：`python3 scripts/patch_locus_check.py handoffs/patches/*r18*.md`
- 債務：`bash scripts/debt_ledger.sh --has-open`　治理票：`bash scripts/gen_fact_key_blocks.sh --check`
- 白話看板同步：`bash scripts/plain_docs_sync_check.sh`（git-commit 基準，未 commit 前會紅）

## 定案，不要重新討論

輪次上限**已解除**／42 Task 一個不砍／條件 IC 答案窗屬 IC 分析層／A-6 取代裁定＝使用者原話（條件③已滿足）／
凍前**不拆 SPEC**／條件④＝(甲)（R17 委員裁定）。

## 流程紀律（累積）

- 批次套補丁之腳本**任一條沒命中須非零退出**；落地後**當場跑補丁包 VERIFY grep**（R16）。
- **不要用 `git stash` 驗「檔案乾淨時的行為」**——會連待測程式一起藏起來（R17）。
  工作區另有他人留下的 `stash@{0}: review-temp`（只動 HANDOFF.md），**勿誤刪**。
- **「已全部涵蓋」之宣稱被打破第二次 ⇒ 不補第三次，改成從定義導出＋機械對證**（R18）。
- **規格內凡「A 呼叫 B」「有第二條路徑」之結構斷言須附行號碼證**；凡「請這樣跑」之驗收
  須先確認在本專案測試環境（ESM／jsdom）真的跑得起來（R18）。
