# 任務：產出「分析類型地圖 — 階段一」你的獨立完整版（Round 1）

READ-ONLY。產出**你自己**的階段一完整地圖（不要等別人、不要互看，這是獨立版）。直接把內容寫在輸出，我會存檔。

## 範疇已定（四家收斂的 SCOPE-FINAL）
組織法=「訊號研究生命週期 5 階段」。**本輪只做階段二「品質、動態與細節」(撐多久?線性?挑對環境?穩定?)**（這訊號真能預測未來嗎）。

### 階段二要涵蓋的 4 種分析
1. 分位/單調性分析
2. IC衰減/半衰期
3. 分組/狀態(regime)條件 IC
4. 穩定性/一致性(Win Rate, ICIR)

### 每種分析寫 9 欄 schema
1. 🔍 核心問題（白話）
2. 📐 業界標準做法
3. 🗂 資料形狀與輸入（Panel/Pooled/事件清單+標籤/單標的時序）
4. 📊 平台現況+實際怎麼實作（**讀碼查證**：逐symbol還pool、event吃不吃顯式事件清單、有沒有切train/test）
5. 🧩 **全棧實作狀態**（逐項查：後端code有/空殼/無 · 前端UI有/無 · 連結wiring通不通 → 判定 ✅全棧連通 / 🔌後端有前端缺 / 🎨前端有後端空殼 / ⛓️‍💥兩端有沒連結(靜默失效) / ⚠️有但壞掉 / ❌完全缺）
6. 🛡️ PIT與洩漏防禦（該分析最易踩的未來函數地雷）
7. ⚡ 430K×20K×百symbol 尺度對策
8. 🔧 做對沒/漏洞
9. 🏷️ 優先級

## 使用者處境（背景）
泛用平台、無量化背景、主戰場=事件 case-control 正反 pre-pattern、尺度 430K×20K×百symbol。已知:無 pooled IC、主路徑無 train/test 切分(洩漏)、grouped/decay 會崩潰、幽靈 feature_filter(前端送後端忽略)。

## 重要：誠實邊界
- **第 4、5 欄(平台現況/全棧狀態)需實際讀 repo 程式碼**（momentum/Analysis/ic_engine.py、ic_filter_orchestrator.py、event_filter.py、api/services/ic_analysis_service.py、frontend/src/app/ic-analysis/、frontend/src/components/ic-analysis/）。
- **若你無法讀 repo 檔案,把第 4、5 欄標「needs-code-verification:＜你的假設/該查什麼＞」,不要瞎猜現況**。其餘欄位(業界標準/資料形狀/洩漏/尺度/優先級)照你的專業填。
- 全棧狀態要特別揪「⛓️‍💥兩端有但沒連結」型(如 feature_filter)。

輸出格式：標題「階段一 — ＜你的家族＞獨立版」,逐 6 種分析填 9 欄。具體、可被另三家詰問。本輪後會互審 + 我做總結(我的總結也會交你們檢查)。
