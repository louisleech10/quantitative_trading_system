# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC 撰寫中（R3 已收斂，**尚未 FROZEN**）。
使用者裁定：**SPEC 寫完 FROZEN 後停下來**，不進 TODO／實作。

---

## 🔴 開工前必讀：三條最高位階規則

1. **量化主線 100% 正確，只能更嚴不能放水**（使用者 2026-08-22 定死）。
   「95% 解法就收、殘留具名記錄不當阻塞」**只適用治理 epic 之散文問題**，量化路徑一律不受理。
   已寫入 `docs/GAP3_EVENT_UX_SPEC.md` §C0（最高位階，四條具體禁止＋主委違規紀錄）
   ＋機械閘 `scripts/quant_standard_check.sh`。
2. **改 §D 裁定必須同步 §P Task**——`feedback_cross_reference_sync` 載此類錯已犯 **7 次**。
   已做成閘：`scripts/spec_ruling_task_sync.sh`（掛 narrow_check_router，寫 SPEC 時自動跑）。
3. **全棧三欄稽核**（後端 code／前端 UI／wiring）——`feedback_fullstack_wiring_audit` 已犯 2 次。
   B5 蓋章後仍漏接六個維度，就是沒執行這條。

---

## 立即待辦（下一 session 第一件事）

**T-1｜補完 26 條「覆蓋風險：無」**（唯一未完成的機械缺口）
- 現況：`grep -c "覆蓋風險：無" docs/GAP3_EVENT_UX_SPEC.md` → **26**（共 38 個 Task）
- 出處：COMPOSER-R1-P1-03（consult 輪）「四欄機檢在 GAP3 **流於形式**，語義密度低於 GAP2」
- 做法：逐 Task 改為實質理由——說明「**為何後續 Phase 不會改寫此產出**」或
  「**會被哪個 Phase 覆蓋、須同步什麼**」。禁止只寫「無」。
- 🔴 **必須用 Edit 工具逐條改**，不得用 Bash heredoc 跑 python 改檔（本 session 因此被拒兩次）
- 參考已改好的範例：Task 1.1／1.3／1.8／1.11／1.12／7.1／7.4 之覆蓋風險欄

**T-2｜派 SPEC R4**（T-1 完成後）
- session：`20260822-gap3ux-x-review-r4`，task-id 大寫
- 派工命令模板見 scratchpad 之 `spec_r3.sh`（改 r3→r4）；找不到就照 T-3 之派工規約重建
- **R4 brief 必須改掉「請攻 X」的寫法**——三家 consult 量化證明其錨定效應：
  三份 brief 共 **10 處**「請攻」，而 R3 的 18 條 findings **幾乎全落在點名的軸上**
  ⇒ 改為「請獨立盤點，主委不指定方向」（第 4 個機械缺口，尚未做成範本層檢查）

**T-3｜R4 通過後 FROZEN，然後停**（使用者明示）

---

## SPEC 現況

`docs/GAP3_EVENT_UX_SPEC.md`（782 行，`doc_format_precheck` rc=0）
- §C0 收斂標準（最高位階）｜§RISK a,b｜§A 假設＋**FACT-RECEIPT 14 條**
- §D 七條裁定（D-1..D-7）｜§C 約束｜§G 拆 G-1／G-2｜§P **7 Phase／38 Task**｜§V 16 條｜§R｜§N
- 檔頭有 **3 條 `SYNC-FORBID`** 宣告（供閘 2 讀）

**收斂履歷**：R1 24 條（6 P0）→ R2 7 條（2 P0）→ R3 18 條（5 P0）
R3 反彈之歸因（grok 拆分，**推翻主委單一歸因**）：同步失敗 45%／使用者注入新 scope 40%／
G-2「留實作」判斷債 15%。

### R3 十八條處置
| 群集 | 內容 | 狀態 |
|---|---|---|
| A | SPEC 自我矛盾（Task 4.1b 寫死 scenario 專屬文案） | ✅ 已修（grep 零命中） |
| B | D-7 之 L1/L2/L3 只有敘述未落 Task | ✅ 已修（Task 1.10/1.11/1.12） |
| C | **future72 單位寫錯**（72 是小時非根數） | ✅ 已修 |
| D | Task 7.2 機械閘可被 disabled 控制項湊過；`control_kind` enum(4) vs accepted(3) 矛盾 | ⬜ **R4** |
| E | Phase 7 未涵蓋 IC 分析頁與 Feature Library `time_range` 對證 | ⬜ **R4** |
| F | G-2 canonical serialization 仍未定義（主委「留實作階段」之判斷被三家推翻） | ⬜ **R4** |
| G | A/B 之機械式深度定義；選 A/B 時 label 來源不變之語意漂移 | ⬜ **R4** |

---

## 使用者提出的 10 條 UAT 問題之歸屬

| # | 內容 | 歸屬 |
|---|---|---|
| 0 | 自篩 CSV 匯入＋匯出前篩選（使用者選 (c) 兩者都做） | Phase 1／2 |
| 1 | 答案窗單選不夠 | Phase 4（裁定採 (a)：多選只影響附帶欄，label 語意不變） |
| 2 | 缺答案窗欄之確認框 | Task 5.3 |
| 3 | `.source.json` 誤傳訊息 | Task 5.1 |
| 4 | 事件批次不能刪 | Phase 3 |
| 5 | 匯入只認 CSV | Phase 1 |
| 6 | 兩表 tooltip＋正反例混算 | Task 5.0／5.2／7.5 |
| 7 | B8/B8b 數據來源 | 已答（見 SPEC §A FACT-RECEIPT 第 10、11 條） |
| 8/10 | Feature Library 涵蓋關係 | 具名殘留＋R3 群集 E |
| 9 | IC 分析 Failed to fetch | **9a 止血閘＝Phase 6**；**9b 規模防護＝排 GAP-6** |

---

## 🔴 #9 根因（實測；receipt 見下）

BTCUSDT/12h run 有 **218,369 特徵**。IC 分析對特徵數**無任何上限**：
- `sample <pid>` 顯示 **Physical footprint 7.1GB**（`ps rss` 只顯示 96–400MB——macOS 壓縮頁面）
- 進度卡在 `progress=0.12 / preprocessing` **15 分鐘不動**
- 使用者那次後端被系統 kill（`grep -c bdeea1ef logs/case_search_api_20260822.log` → `1`，
  其後 18 分鐘零輸出、**無 traceback**）

VERIFY-EXEMPT:session-probe:20260822-ic-oom（本 session 實跑探針；後端已關閉，
重現法＝啟動 `python run_api.py` 後對該 run 呼叫 `/api/v1/ic/analyze` 並以 `sample <pid>` 取樣）

⇒ Phase 6 為**過渡止血閘**（fail-closed 擋下），規模防護本體排 GAP-6（registry #6）。
**代價**：止血閘上線後，218k 那個 run 在 GAP-6 前 IC 分析不可用（使用者已同意）。

---

## 使用者的實際研究形態（釐清後，勿再誤解）

- **正反例由 t0 條件決定**（如「漲幅 > 5%」），案例搜尋**不看後面 30 個欄位**
- 使用者**可能**另加 future 欄當**品質過濾**（排除漲完就崩），**那才是 lookahead 來源**
- 「預測未來幾根會漲跌」是**另一種 scenario**（契約之 A/B 預測型）——
  🔴 **系統不得寫死任一 scenario**（使用者當場打斷主委的 Edit 並糾正）
- 使用者既有批次 `20260822T011331Z-eb210a16`：780 筆／label 0:520,1:260／
  `control_kind=user_labeled_same_trigger`／`scenario=C`／`horizon_bars=3`／**未做任何篩選**
  ⇒ lookahead **＝ 0**，D-7 洩漏情境不適用（主委原判「可能偏樂觀」**已撤回**）
  （receipt：SPEC §A FACT-RECEIPT 第 14 條，可重跑）
- PIT 無洩漏之依據：SPEC §A FACT-RECEIPT 第 9 條
  （`ic_feed.py:75-77` 之 `decision_time_rule` 與 `feature_cutoff_rule`，特徵最晚取至 t0−1 收盤）

---

## 本 session 新增之機械閘（已上線，commit `ad43151c`）

| 腳本 | 擋什麼 | 鑑別力 |
|---|---|---|
| `quant_standard_check.sh` | 量化主線放水語（15 種同義語） | 造假語料 2/2；統計用語／禁令條文／引用行零誤報 |
| `spec_ruling_task_sync.sh` | ①裁定未落 Task ②SYNC-FORBID 禁用語殘留 | 以 R3 兩個實際 bug 反測皆抓到 |

掛在 `narrow_check_router.sh`（逐檔精確路徑）；`test_narrow_check_router.py` 14 passed。

**第 4 個缺口未做**：brief 去錨定之範本層檢查（見 T-2）。

---

## 分工現況（技術可行性已查）

- ORCH §1／`governance_roles.json`：`implementer=claude`（主委自任）、`reviewers=codex,composer,grok`
- `governance_families.json` 之 `executor_clis` ＝ `codex/cursor-agent/grok/agy`——**無 claude**
  ⇒ 無「派工給另一 Claude session」之 CLI 配方
- **但 Claude Code 有 Agent 工具可派 sub-agent 並指定模型**（主委先前答「不行」是錯的，已更正）
  - 陷阱一：sub-agent **不在治理審計鏈**（債帳／戳記／completeness 都不認）
  - 陷阱二：**prompt 是主委寫的** ⇒ 錨定效應照舊；真正的獨立性來自「寫的人≠審的人」
- 使用者目前用 Opus 是因為 **Fable5 沒額度**，分工暫時改不了

---

## 坑（本 session 新增）

- **commit 之 `Governance-Scope` trailer 必須是單行**——換行寫 git 不認，會被 G-7 擋
- **改檔一律用 Edit 工具**——Bash 跑 python heredoc 改檔會被權限拒（本 session 被拒 2 次）
- **`cmd | head` 讀到的是 head 的 rc**——本 session 又踩一次，rc 一律直接取
- consult 輪 brief 須 `brief-kind: consult` **＋引用委員範本全文**（寫 `n/a:` 會被擋）
- review 輪派工用 `--risk low` ＋ `--template "n/a:"`；`--spec` **只能用於 impl 派工**
- session 命名 `<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，batch 段須為 `b<數字>` 或 `x`
- SPEC 機檢：`RISK-HIT:` 宣告行／每 Task 四欄／§A「已確認…」或「待使用者確認：無」／
  §A FACT-RECEIPT 須緊接章節不得夾引言／驗證 bullet 須含具體 token（數字/pytest/==/.py…）
- HANDOFF 之「已驗」類宣稱須附 `VERIFY:` 或 `VERIFY-EXEMPT:`，否則 PreToolUse 擋下

---

## 已知既有紅（非本批造成）

- `tests/api` 10 failed + 3 errors（R2 已 byte-identical 基準對證）
- `gen_fact_key_blocks.sh --check` 對 `白話說明/Archived/GAP-2施工進度.md` 誤報 6 條
  （識別碼撞名：治理批次表用 B1–B5、GAP-2 看板也用 B1–B5）

---

## 其他線的狀態

- **`/search` 三 bug 修復**：🏁 已收案（三家 RECONCILE-STAMP rc=0，commit `bf0fd48a`）
- **GAP-3 B1–B5**：全部蓋章，**只差使用者 UAT B 段 13 項簽字**
- **純事件研究模組**：使用者裁定另立模組（「這可以未來另做一個模組研究就好」）
- **標籤方法論討論**：使用者裁定排在整個系統完成之後
