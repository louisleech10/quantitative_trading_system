# HANDOFF

## 當前：GAP-3 事件型 UAT 缺口修補 SPEC（目標＝FROZEN）

- 標的 `docs/GAP3_EVENT_UX_SPEC.md`：**3,547 行／42 Task（三十四輪未增未減）**，版本行 `R34-landing`，**未 FROZEN**。
- R34 已落地（3 件），債已銷。**下一步＝建 R35 派工包並派三家。**
- 🔴 **本 session 動過 `scripts/`**（`gap3ux_apply_patch.py`、`gap3ux_header_round_check.sh`）
  ⇒ **收 epic 前須跑 `bash scripts/gov_check.sh --no-probe`（丟背景）**；本輪尚未跑完。
  ⚠️ 跑它時**主控端不得動檔**（治理測試比對工作區 dirty 數）。

## R35 必辦（理由皆為實跑，勿重推測）

1. **E-1 同輪重派死鎖**：GROK 字面讀 `GATE_CHECK_CMD`——`grep -c` → **0**；真正變數是 `cmd`
   （`gate_check.sh:164` 由 `jq -r '.tool_input.command'` 取得）⇒ parser 恆空、helper 永不被呼叫；
   且該 parser **不檢查 intent 字面**，重開 CODEX-R34-P1-01 之洞。請 GROK 修、CODEX 覆核（勿再交散文）。
2. **E-3 補丁包碰撞收集端閘**：CODEX 散文／COMPOSER 引用**不存在**之 `scripts/gap3ux_patch_family_audit.sh`／
   GROK 用 `declare -A`（bash 4）而**本機為 bash 3.2.57**（`declare -A` → `invalid option`）。
   三家一致：**產出端在本架構無可攔截點** ⇒ 須 registry 具名豁免＋收集端 fail-closed。
3. **編排草圖自 R34 起不再 `compile()` 通過**（含 illustrative 佔位 `<Task 7.7 picker 所選 run_id>`）。
   三家皆標 illustrative，**但無人明講可放棄該 receipt** ⇒ 請裁。
4. **主委兩處具名修正待覆核**：`gap3ux_header_round_check.sh` 之 `sed -E` 可攜性修正
   （BSD sed 不支援 BRE `\|`，實測誤紅）。
5. **第三類 VERIFY 撰寫缺陷**：包側 VERIFY 與自身 AFTER 自相矛盾。
   原則已定（`CODEX-R34-P2-02`）：**由 package author 修 scope，不放寬 extractor 或判準**。

## 最高位階條款（`docs/GAP3_EVENT_UX_ROLE_CARD.md` 為準）

R20 不得新建驗收機制／R21 條件②′／R22 不得自我歸類／R23 不自擬殘留查核清單／
R25 anchor 只錨會被寫入之字面／**R32 擇一權＋機器判準（角色卡首節）**。

🔴 **R32 判準**：得擇一，**僅當被排除之 AFTER 不可執行或自相矛盾**
（`compile()` 失敗／引用名在包內與標的皆無定義／宣稱效果在其所改範圍不可能達成／
觸發條件永不成立／**依賴不存在之變數或檔案**／**用了本機 shell 不支援的語法**）。
「語意較佳」「兩家同向」皆不算 ⇒ 停手。
🔴 **副則**：ERRATA 不重貼被否決之字面（已咬三次）。

## 未答否決點（自 R21 起十四輪）

凍結條件②之替換（改為四指標），使用者可推翻。

## 下一步

R35 → **FROZEN 後停下來等使用者**，不要自己往 TODO 或實作走。
