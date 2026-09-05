# HANDOFF — 當前任務狀態

**更新：2026-09-05｜狀態：G-7FIX **已轉向並收斂**——第 4 步 ✅ DONE，狀態機整套作廢。下一件＝回 `G3-D2` 主線之 B-D4。**

## 🔴 G-7FIX 轉向紀錄（使用者 2026-09-05 質疑「你能收斂嗎還是又發散了」）

**我確實發散了。** 證據：五輪收完（perf R1/R2、consult R1/R2、SPEC review R1），
**64 條 finding、11 個 P0、產品碼改動零行**；P0 數三輪平盤（4→4→3），
且每輪 P0 都長在我當輪剛寫的東西裡（consult R2 群集 β、SPEC review R1 群集 1）＝finding 產生器。

**產生器＝`epic_state` 狀態機**（我把「GOVB1 沒在做時別套 G-7」做成帶守衛轉態謂詞的狀態機，
每加一層就長出新攻擊面）。**已整套作廢**：`docs/G7FIX_SPEC.md` 不再是有效計畫，
SPEC review R2（`20260905-g7fix-x-review-r2`）之產出**不採用**，僅跑完清債。

**關鍵事實（使用者問「1/2/3 到底防什麼」後查明）**：G-7 保護的 GOVB1 是 `DRAFT`、
從未實作、2026-08-14 遭裁定擱置；且會驗 trailer 的檢查自 2026-08-14 起沒在 push 上跑過
（`gov_check.sh:266-267` `--fast` 早退，G-7 在 `:343-350`）⇒ **trailer 一直被收，沒有東西在讀**。
⇒ 1/2/3 不是防護，是清掉沒人讀的手續。第 4 步才是唯一純未來收益。

## ✅ 已完成：第 4 步（TODO「路徑」欄）

`templates/TODO_GENERATION_PROMPT.md` 加 `- 路徑：` 欄（加欄不換欄、前向適用、**禁被任何 gate 當 scope 來源**、
無格式閘並具名殘留 `needs-research`）。驗收：範本含該欄規則；`GAP3_EVENT_UX_TODO.D-006` 與
`GOVB1_INPUT_QUALITY_TODO` 之 `template_check` 皆 rc=0（證明前向適用、不回溯變紅）。

## 待使用者決定（不阻塞主線）

第 1+2 步合併之 20 行清理（`g7_trailer_precheck.sh`：scope 逐路徑判 → 硬保護集；trailer 值改向 gate 取），
可把 trailer 稅由 **76%（564/743）降到 1.7%（13/746）** 且閘不再說謊。第 3 步砍到只改兩處假敘述。
使用者尚未表態要不要做；**不做也不擋主線**。

## 🔴 下一件＝回 G3-D2 主線 B-D4

`B-D0／B-D1／B-D3` 皆 ✅ DONE。唯一入口＝`docs/GAP3D2_IMPL_HANDOFF.md`（§2 七步不得跳步、§5 收據、§3 地雷、§4 裁定總表）。
B-D4＝D4.2 全矩陣 13 對 ＋ D4.3 k 參數化與掃描網格；🔴 D4.3 之 benchmark 子步須**先於**凍結 cap。
新 TODO 起適用上述「路徑」欄。
