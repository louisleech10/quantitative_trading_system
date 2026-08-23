# HANDOFF

## 當前：GAP-3 事件型 UAT 缺口修補 SPEC（目標＝FROZEN）

- 標的 `docs/GAP3_EVENT_UX_SPEC.md`：**3,538 行／42 Task（三十二輪未增未減）**，版本行 `R32-landing`，**狀態未 FROZEN**。
- 最後落地＝**R32 十五條處置**（commit `61404144`）。
- **下一步**：建 R33 派工包並派三家。

## R33 必辦（已定，勿重議）

1. **E-1 同輪重派死鎖**：方向三家已定「必修、不得以 ERRATA 代替」。三版中只有 CODEX 完整
   （須讓 `gate.sh` 與 `gate_check.sh:125` 之獨立重查用同一 predicate），**但未附 bash literal**、
   其 VERIFY 指名之 `tests/governance/test_result_state_format_failed.py` 不存在
   ⇒ **請 codex 附完整 literal ＋ 反測 receipt**。主委不自寫核心閘控制流。
2. **E-2 ABANDONED 假收據**：composer 版呼叫無定義 helper 已排除；CODEX（檔頭＝前一輪）與
   GROK（後綴允許 `-abandoned`）**皆可執行、語義互斥、無機器判別** ⇒ **停手，請兩家合議**。
3. **`ERRATA-R32-COLLISION`**：composer 與 grok 本輪輸出同一檔名 `r32-spy-gate-call.md`，
   一家補丁包被靜默覆蓋（15 findings 對 14 檔）⇒ 兩家改名重交，並裁檔名碰撞是否須機械擋。
4. **群集 C 疑義**：Task 7.0b ① 該塊標題寫「簽章如下」而所採 AFTER 為呼叫形式（`名=值`）。
5. **harness 殘留**：`verify_greps` 抽出之字面含跳脫反引號時 `unescape` 未處理，仍有一條假紅。

## 最高位階條款（`docs/GAP3_EVENT_UX_ROLE_CARD.md` 為準，本檔不重述細節）

R20 停止新建驗收機制／R21 條件②′／R22 不得自我歸類／R23 不自擬殘留查核清單／
R25 anchor 只錨會被寫入之字面／**R32 擇一權＋機器可導出判準（新，見角色卡首節）**。

🔴 **R32 判準摘要**：主委**得**擇一，但**僅當被排除之 AFTER 本身不可執行或自相矛盾**
（`compile()` 失敗／引用之名在包內與標的皆無定義／宣稱效果在其所改範圍不可能達成／
觸發條件永不成立）。**「語意較佳」「兩家同向」「觸及 R20 疑慮」皆不算證據 ⇒ 停手。**
🔴 **副則**：**ERRATA 一律不重貼被否決之字面**（引用反例會被對證工具算成落地；已咬兩次）。

## 未答否決點（自 R21 起十二輪）

凍結條件②之替換（改為四指標），使用者可推翻。

## 下一步

R33 → **FROZEN 後停下來等使用者**，不要自己往 TODO 或實作走。
