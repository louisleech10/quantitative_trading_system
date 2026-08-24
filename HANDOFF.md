# HANDOFF

## GAP-3 事件型 UAT — SPEC 與 TODO **皆已 FROZEN**（2026-08-24）

| 文件 | 狀態 | 依據 |
|---|---|---|
| `docs/GAP3_EVENT_UX_SPEC.md` | 🔒 **FROZEN**（3,547 行／42 Task） | 使用者 2026-08-24 直接裁定；commit `4ce3d6d9` |
| `docs/GAP3_EVENT_UX_TODO.md` | 🔒 **FROZEN v1.0**（1,618 行／42 Task） | 三輪對抗審＋戳記輪；三家全數 APPROVED |

**TODO 已可據以派工。** 後續修訂走延伸檔 `docs/GAP3_EVENT_UX_TODO_AMENDMENTS.md`，不就地改。

## 🔴 下一手：停在這裡，等使用者指示

**使用者尚未裁定是否進實作。** 不要自己開 B1。

## TODO 之對抗審履歷（三輪，輪次上限）

- **R1**（12 findings）：主委 brief 鎖版失效 ⇒ codex／grok 正確停手、內容審缺席；
  composer 10 條全數落地。主委自查另發現「以行號注入致三處錯置」（無委員提出）。
- **R2**（19 findings）：抓出主委 R1 修法留下之**假綠**（同步斷言只驗子字串存在）、
  mutation 覆蓋率宣稱有誤（腳本比對範圍過寬致假跳過）、**§B 缺跨批單點依賴**
  （`depth_by_timeframe` 與 `canonical_serialize.py` 建立批次晚於消費批次）。CLOSED 16／PARTIAL 3。
- **R3**（3 findings）：composer 與 grok 皆判**可定版**；codex 程序性 BLOCKED
  ——R1／R2 之 reconcile **缺委員戳記**（主委漏做收案程序），該缺失成立、已補。
- **戳記輪**：`reconcile_stamps_check.sh` 對 R1／R2／R3 **皆 PASS**，三家全數 APPROVED。

## 定版時之機械對證（皆經 composer 與 grok 獨立複跑）

Task 42/42（追溯缺 0 多 0）；§V 20/20、§G 3/3 有落點；五必填欄各 42/42；
驗證欄 mutation 42/42、可執行前綴 42/42；§B 經 Kahn 檢查**無環**；
7.0b 簽章 SPEC≡TODO；`doc_format_precheck.sh` rc=0。

## 具名殘留（SPEC 4 條 ＋ TODO 4 條，皆非量化正確性）

- **SPEC**（末節 F-1..F-4）：同輪重派死鎖／補丁包檔名碰撞／草圖 illustrative 佔位不通過
  `compile()`／`gap3ux_apply_patch.py` 包側 VERIFY 缺陷。**不排工、不另立治理票。**
- **TODO**（R3 reconcile）：前端 directory-only 路徑 10 處／Task 5.0 驗證 defer SPEC／
  五 Task 之 mutation 全文 defer SPEC（composer 已交 exact mutant 補丁包）／B1 須並讀 SPEC。

## 🔴 不要再碰治理（使用者 2026-08-24 定死）

逐字：「當初就是發現你做治理是無解才不做」「你這樣岔題去問委員，永遠沒完沒了」。
遇治理工具壞掉 ⇒ **繞過並具名記錄，不修、不開票**。要動須使用者明示。
⚠️ 本 session 之教訓：落地出錯就**抄仔細**，不要做工具量自己——
那正是 GAP-3 SPEC 燒掉六輪的原因。

## 本 session 之主委自傷（供下一手避開）

「比對範圍過寬」犯**四次**：Phase Gate 標籤與 Task 欄位同字面／以**行號**注入落到錯的
Task（行號取自修補前之掃描，中間已位移）／mutation 跳過判準掃整個區塊／
同步斷言只驗子字串存在（假綠）。**一律用字面錨點，且檢查要用「已知會紅的輸入」試一次。**
