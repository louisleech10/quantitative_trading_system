# HANDOFF

**當前任務**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）審到 **完整 FROZEN**。
**工作方法**：先讀 `docs/GAP3_EVENT_UX_ROLE_CARD.md`（委員出補丁包、主委整包套用；主委不得自寫第二處複述）。

## 狀態（R19 已全數落地並收尾）

- SPEC **3,140 行／42 Task**（二十輪未增未減）；版本行 = `R19-landing`，狀態 **未 FROZEN，待 R20**。
- R19：8 findings（codex 5／composer 1／grok 2）→ 5 群集，**全數落地**；三家 Verdict 一致「需修訂後定版」。
  **P0＝0（連五輪）**；歸因 **(N)=0**，八條**全部**指向 R18 落地批。
- 🔴 **R19 是 R18 五條停止判準之驗證輪，結果：五條中三條之機制本身壞掉**——
  ①`TIMEFRAME_SECONDS` 被主委當常數排除，碼證 `momentum/core/constants.py:6` 為可變 dict
  ④digest 述詞判準三家實跑打穿（`webcrypto` 被 function 守衛擋掉／誤中 `getHashes`、`Hmac`）⇒ **驗收恆紅**
  ⑤header 閘 state 值域三值而只特判 `CLOSED` ⇒ **同一支閘連三輪 fail-open**
- 🔴 **主委病根（連續第二輪同型）**：把「解析自然語言文件」與「用述詞分類語意」當成機械檢查。
  **機械閘只能做三件事：比對位元組、比對集合成員、比對物件參考。**
- **本輪改法**：①單一來源搬進碼（`PURGE_FREE_VARIABLES`，且 `purge_lower_bound_ms()` 讀它取值
  ⇒ 漏變數則 purge 算不出來）②digest 不分類，改 golden 快照＋變更即人工複審
  ③「常數」須附 immutable 碼證，導出程序禁「（常數，不計）」列 ④accessor 補齊
  （`keys.py::event_scope_key()`／`event_trigger_timeframe()`）⑤header 閘 state 逐值窮舉。

## FROZEN 四條件現況

①⬜ P0=0／**P1=8**　②⬜ 自傷 5 群集　③✅　④當輪補丁包 locus 待清（規則已裁 (甲)）

## 下一步（依序）

1. **派 R20**：由 r19 三份改號生成 brief/facts/locus。
   🔴 **改號時必查 `locus.sh` 之 PATCHES glob 有沒有跟著換**（R17 踩過）。
   🔴 **R20 brief 必含**：①攻擊「ABANDONED＋clean tree」——主委之 mutation 以 dirty=1 跑，
   **未隔離該組合**（見 synth 之自承）②`PURGE_FREE_VARIABLES` 方案是否真的讓「漏變數」導致
   purge 算不出來，還是又一個宣稱 ③golden 快照方案之誠實邊界是否足夠 ④各家重寫自家 R19 SYNC-LOCI。
   `--task-id` **須為 session 之大寫形式**（`20260824-GAP3UX-X-REVIEW-R20`）。
2. R20 落地 → 若四條件齊備 ⇒ **FROZEN，然後停下來等使用者**（不得自行往 TODO 或實作走）。

## 查法（不寫聲稱，只寫命令）

- 常駐閘：`bash scripts/gap3ux_pre_review.sh`；失敗全量輸出落 `.claude/gate/gap3ux_pre_review.last.log`
- locus：`python3 scripts/patch_locus_check.py handoffs/patches/*r19*.md`
- 債務：`bash scripts/debt_ledger.sh --has-open`　治理票：`bash scripts/gen_fact_key_blocks.sh --check`
- 白話看板同步：`bash scripts/plain_docs_sync_check.sh`（git-commit 基準，未 commit 前會紅）

## 定案，不要重新討論

輪次上限**已解除**／42 Task 一個不砍／條件 IC 答案窗屬 IC 分析層／A-6 取代裁定＝使用者原話（條件③已滿足）／
凍前**不拆 SPEC**／條件④＝(甲)（R17 委員裁定）。

## 流程紀律（累積）

- 批次套補丁之腳本**任一條沒命中須非零退出**；落地後**當場跑補丁包 VERIFY grep**（R16）。
- **不要用 `git stash` 驗「檔案乾淨時的行為」**（R17）。工作區另有他人之 `stash@{0}: review-temp`，**勿誤刪**。
- **「已全部涵蓋」之宣稱被打破第二次 ⇒ 改成從定義導出＋機械對證**（R18）。
- **結構斷言須附行號碼證**；**「請這樣跑」之驗收須先確認在本專案環境跑得起來**（R18）。
- 🔴 **機械閘只能比對位元組／集合成員／物件參考**；需要「解析文字」或「判斷分類」者不是機械閘（R19）。
- 🔴 **「這是常數」是需要碼證的宣稱**，不是可順手寫下的分類（R19）。
- 🔴 **rc=0 不等於沒問題**——工具警告區要讀完（R19：群集歸因 rc=0 但六行「掉項？」）。
