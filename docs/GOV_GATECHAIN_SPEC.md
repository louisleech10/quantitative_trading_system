# 閘門鏈成本治理：段序前移 ＋ ASSERT 執行封閉化 — SPEC

> 來源診斷：本 session 實測 ＋ `handoffs/reconcile/20260812-govassert-x-consult-r1/synth.md`
> | 日期：2026-08-12 | 對應 TODO：`docs/GOV_GATECHAIN_TODO.md`

## §RISK 風險分級

- **大小**：**大**。
- **命中高風險原則**：**(b) 跨模組／共用路徑**——`gov_check.sh` 與 `template_check.sh`
  同屬 pre-push 控制流，所有推送皆經之。不命中 (a)／(c)／(d)。

RISK-HIT: b

## §A 假設與待使用者確認

- FACT-RECEIPT: `python3 -m pytest tests/governance -q --durations=30` → 最慢 26 項合計約 276s／全套 678s
  （主委 實跑 2026-08-12）
- FACT-RECEIPT: 三條便宜閘計時 → `g7=7s factkey=0s plaindocs=1s 合計=8s`（主委 實跑 2026-08-12）
- FACT-RECEIPT: `grep -n _GC_SEG_IDS scripts/gov_check.sh` → `'1 1b 2 3 4 5'`；
  段 2＝pytest 全套（678s），段 4＝白話同步（1s），段 5＝fact-key（0s）（主委 實跑 2026-08-12）
- FACT-RECEIPT: 本 session 兩次 push 被拒，皆由段 4／段 5 判定 ⇒ 各付 678s 才得知（主委 實跑 2026-08-12）
- FACT-RECEIPT: T0 止血後實測 → 寫檔路徑 1s；gate 路徑 timeout=5s 時 12s 抓到 2 條逾時
  （主委 實跑 2026-08-12；commit `53966e90`）
- **待確認：無**。
  🔴 卡頓歸因修正（`.claude/settings.json` 之 PostToolUse 順序：`ts_stamp.sh OUT` 於 `:184`
  早於 `doc_format_precheck` 之 `:197` ⇒ hook 執行時間被記為「Claude 生成慢」）
  **刻意排除於本 SPEC 之外**——該檔屬使用者設定，需其明示同意，
  留在此處會使本 SPEC 卡在未解事實。改列**具名殘留**，另案處理。

## §C 約束

- 🔴 **不得刪除、跳過或放寬任何既有檢查**；本案只改**順序**、**執行邊界**與**輸出位置**。
- 🔴 **新文法（`ASSERT-TEST:`）之判定路徑不得執行文件內容之任何命令**。
  r1–r3 曾試圖以「封閉可執行集合＋rlimit＋supervisor＋ledger」使執行變安全，
  r3 三家證明該目標在 POSIX 上不可達 ⇒ 新路徑改為**零執行**。
  🔴 **舊文法之既有執行路徑本 SPEC 不動**（危害已由 T0 止血涵蓋）；
  其移除屬另票 `GOV-ASSERT-LEGACY-MIGRATION`。
- 🔴 **保護真空守衛**（`COMPOSER-R1-P1-01`）：`gov_check` 段 1b 對改動 `docs/*.md`
  之硬檢**必須保留**——Phase B 移除的是「執行」，不是「檢查」。
- 段號登記表 `_GC_SEG_IDS` 為唯一宣告處，分母**現算**，禁寫死。
- `pre-push` 委派字面 `gov_check.sh --no-probe` 不得更動。
- 🔴 **本 SPEC 及其 TODO 內禁出現呼叫治理閘門腳本之 ASSERT 行**（本輪出生事故）。
- 解耦 7 條：N/A（見 §N）。

## §G Golden / Baseline

**N/A** — 見 §N。

## §P Phase 與依賴

### Phase A — 段序前移（依賴：無）

**Task A.1 — 便宜閘移到 pytest 之前**
- 目標：1 秒可判定之失敗不必等 678 秒。
- 檔案：`scripts/gov_check.sh`（`_GC_SEG_IDS`；段 2／4／5 區塊位置）
- 既有 caller：`scripts/git_hooks/pre-push`、`--fast` 路徑、
  `tests/governance/test_govb1_factkey_hook.py`、`tests/governance/test_gov_check_dep_failclosed.py`、
  🔴 **新增依賴** `scripts/govb1_final_gate.sh`（G-7 預檢段所呼叫）。
  🔴 **缺檔契約＝FAIL，非略過**〔`CODEX-R2-P0-01`：原文同時寫「不得 fail-open」與「rc 不變」，
  兩者互斥——前序全綠時「rc 不變」等於放行〕：依賴腳本缺檔 ⇒ **該段判 FAIL 且 rc=1**，
  比照 `gov_check` 既有之依賴檢查（`:168` 對三支腳本之存在性檢查同型）。
- 改法：新序＝語法 → 文件格式 → 白話同步 → fact-key → **G-7 預檢（新段）** → pytest → 探針健檢。
  🔴 **G-7 預檢之呼叫式逐字釘死**：`bash scripts/govb1_final_gate.sh --only g7`
  〔r8 兩家：若省略 `--only g7`，該腳本**預設跑全表含 `_g0_tests`＝全套 pytest**
  ⇒ 在 pytest 之前再跑一次全套，製造昂貴遞迴，與本 SPEC 目的完全相反〕。
  驗收須斷言該呼叫**逐字含 `--only g7`**。
  便宜段**彼此不中止**（全跑完再判），僅在進入 pytest 前判一次。
  🔴 **`--fast` 語義同批重新定義**〔`GROK-R1` 抓出〕：現行 `--fast` 於段 1b 之後即 `exit`，
  **永遠跑不到**白話同步與 fact-key ⇒ 若不重定義，本 Task 的驗收會假綠或永紅。
  新定義：**`--fast` ＝ 執行 pytest 之前的所有便宜段**（語法、文件格式、白話、fact-key、G-7），
  於進入 pytest 前 `exit`。此為**擴大**受檢範圍，非放寬。
  🔴 **段號重編為必然**：`_GC_SEG_IDS` 由 `'1 1b 2 3 4 5'` 改為新序之登記表；分母仍現算。
- **驗證（可證偽）**：新增 `tests/governance/test_gov_check_order.py`，於 tmp repo 內跑真腳本：
  ① 注入 fact-key 漂移 ⇒ `--fast` 之 `returncode == 1`
  ② 未注入 ⇒ `returncode == 0`
  ③ 便宜段紅時，stdout **不含**字串 `passed in`（證明 pytest 未執行）
  ④ 兩個便宜段同時紅 ⇒ 失敗摘要行數 `== 2`
  ⑤ **G-7 專屬**：注入未宣告路徑 ⇒ `--fast` 之 `returncode == 1` 且輸出含 `G-7`；
    未注入 ⇒ `returncode == 0`
  ⑥ **`--fast` 新語義**：`--fast` 之 stdout 須**逐段**含全部便宜段之段標題
    （語法／文件格式／白話同步／fact-key／G-7 共 5 段，缺一即紅）且**不含** `passed in`
    〔r8 `GROK`：原文只驗「含 fact-key 段標題」，漏跑其餘段仍會綠〕
  ⑦ **G-7 呼叫式**：`gov_check.sh` 原始碼須逐字含 `--only g7`（缺即紅）
  ⑧ **缺檔契約**：把 `scripts/govb1_final_gate.sh` 暫時移走 ⇒ `--fast` 之 `returncode == 1`
    〔r8 兩家：改法／caller 已訂「缺檔 ⇒ FAIL」，驗證欄原本只在邊界提及，無可證偽格〕
- **邊界（≥2）**：①便宜段全綠而 pytest 紅 ⇒ rc==1 且摘要指向 pytest 段
  ②`govb1_final_gate.sh` 缺檔 ⇒ **該段 FAIL 且 rc==1**
  〔`CODEX-R2-P0-01`／`COMPOSER-R3`／`GROK-R3` 三家指出原「具名略過、rc 不變」
  與正文之「不得 fail-open」互斥——前序全綠時等於放行〕
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得刪任何段；不得改 `--no-probe` 委派字面。

**Task A.2 — 失敗摘要印於輸出最末**
- 目標：`tail` 即可見失敗項，消除「重跑套件去重新發現已有資訊」（本 session 白花 22 分鐘）。
- 檔案：`scripts/gov_check.sh` 收尾區塊
- 改法：累積失敗段名，收尾以固定前綴 `GOV-CHECK-FAILED:` 逐行印出；全綠不印。
- **驗證（可證偽）**：`tests/governance/test_gov_check_order.py`——
  ①單段失敗 ⇒ 末 5 行內該前綴出現次數 `== 1`；兩段 ⇒ `== 2`；全綠 ⇒ `== 0`
  ②🔴 **內容正確性**〔r8 `CODEX`：只計次數，捏造名稱或重複同一段名亦會通過〕：
    每行之段名須**屬於實際失敗之段集合**，且**無重複**；
    以「令白話段與 fact-key 段同時紅」為例，摘要兩行之段名集合須逐一等於該兩段名
  ③🔴 **落尾**：摘要須出現在**所有段輸出之後**（以摘要行號 > 最後一個段標題行號 判定）
- **邊界（≥2）**：①多段失敗各一行 ②全綠無雜訊
  ③🔴 **並行呼叫**〔r6 `CODEX`：兩個 hook／push 同時觸發 `gov_check` 時，
  便宜段會被重複跑、失敗摘要會交錯〕：以 **single-flight 鎖**使同一時刻僅一份 `gov_check` 執行。
  🔴 **一律用 `mkdir` 原子鎖，禁 `flock`**〔r8 `GROK`：本 repo 既有憲法多處標明
  「禁 `flock`（macOS 無此指令）」，原文寫「兩者擇一」會誘導實作出在本平台跑不起來的版本〕；
  取不到鎖者**等待而非略過**（略過＝保護真空），並設等待上限；逾上限 ⇒ FAIL。
  **驗收格**〔`COMPOSER-R7-P1-03`：原僅列為 MUST 而無可證偽格〕：
  `tests/governance/test_gov_check_order.py` 兩格——
  ①同時啟兩份 `gov_check --fast`，第二份之 stdout 須含等待字樣且**最終 rc 與第一份一致**
  ②把鎖機制移除後，該格須由綠轉紅（證明鎖承重）
  ③🔴 **逾等待上限之可證偽格**〔r8 兩家：改法訂「逾上限 ⇒ FAIL」卻無對應格〕：
    以持鎖者故意不釋放（持鎖時間 > 上限）⇒ 第二份之 `returncode == 1`
    且 stdout 含逾時字樣。
    **上限秒數具名**：`GOV_CHECK_LOCK_WAIT_SEC`，預設 **120s**
    （依據＝本 repo 實測便宜段合計 8s，取 15 倍餘裕；非拍腦袋，且 env 可覆寫）
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：不得只印第一個失敗。

### Phase B — ASSERT 由「執行」改為「宣告」（依賴：**無**）

> 🔴 **依賴由「Phase A」改為「無」**〔r8 `GROK`：Task B.1 只改 `template_check.sh` 與
> `templates/`，與 Phase A 之 `gov_check.sh` **無執行期輸入輸出依賴**；
> 原標依賴會誤導實作者串行等待，且使兩者無法並行 commit〕。
> 兩者可各自獨立 commit 與 revert。

> 🔴 **本 Phase 於 r3 後整段重寫。** r1–r3 共 29 條 finding，其中約七成源於同一個錯誤前提：
> 主委一直在設法「**安全地執行文件內的任意命令**」。r3 三家證明該目標**在 POSIX 上不可達**——
> 子程序可 `setpgid(0,0)` 自行脫離 process group；aggregate CPU 在 macOS 無可移植 oracle
> （已 reap 之子程序漏計）；ledger 可被 child 刪檔／換 symlink／清環境。
> 要真正圍住任意子程序之後代，需 cgroups／jail，本 repo 不具備。
>
> ⇒ **改變題目**：`ASSERT` 的原始用意是「驗收條件必須可證偽、不得是散文」。
> 達成該目的**不需要 `template_check` 去執行它**。改為**宣告式**：
> ASSERT 行宣告一個**真實的 pytest node id**，`template_check` 只做**靜態檢查**，
> **完全不執行任何命令**；真正的執行由既有 `pytest tests/governance` 承擔
> （它本來每次 pre-push 就會跑）。
>
> **驗收強度不降反升**：原設計只在 gate 那一刻跑一次；改為 node 宣告後，
> 該測試**每次 pre-push 都會跑**，且與其餘測試共用同一套 mutation／防假綠機制。

**Task B.1 — `ASSERT` 語法改為 pytest node 宣告**
- 目標：消除「文件可使檢查鏈執行任意命令」這一整類問題（含自鎖、fork 爆炸、TOCTOU）。
- 檔案：`scripts/template_check.sh`（`_run_assert_lines` 整段）、`templates/SPEC_TEMPLATE.md`
- 既有 caller：`scripts/gate.sh:800,805`、`scripts/doc_format_precheck.sh:197`、
  `scripts/spec_fourway_check.sh:43`
- 改法：新文法 `ASSERT-TEST: <path>::<test_name>`（一行一條）。
  判定**純靜態**：①`<path>` 之 **canonical realpath** 須位於 `tests/` 下，
  且**拒 `..`、拒 symlink**〔r5：naive 前綴檢查會把 `tests/../scripts/…` 當成合法〕
  　②該檔含 `def <test_name>(`
  ③`<test_name>` 於該檔**模組層唯一**（比照 `_b49_selector_is_substantive` 之既有作法）。
  🔴 **不執行、不 import、不 collect**——零命令執行。
  ④🔴 **實質性**〔r4 三家：靜態「有 `def`」不保證有斷言，`def test_x(): pass` 會過〕：
  該 node 之函式本體須含 ≥1 個 `assert` 或 `pytest.raises`。
  🔴 **不得寫「直接複用 `_b49_selector_is_substantive`」**〔r8 `CODEX`／`COMPOSER`：
  該函式是 **Python 測試模組內的函式**，而 `template_check.sh` 是 **shell**；
  跨語言「複用」在此不可能，且與本 Task「不 import」之要求互斥〕。
  ⇒ 改為**共用判準文字 ＋ 共用反例語料**：
  判準（模組層同名定義唯一、只計自身可達 body、靜態可證不執行者不計）
  於本 SPEC 定義一次；shell 端自行實作，
  但**必須通過與 `_b49_selector_is_substantive` 相同的反例語料**
  （巢狀死碼／同名重複定義／`if False:`／`while False:`／`for _ in []:`／
  巢狀類別方法／判不出真假須計入），語料置於
  `tests/governance/fixtures/substantive_corpus/`，兩實作共用。
  ⇒ 漂移由「同一語料兩邊都跑」機械擋住，而非靠「複用同一份程式碼」。

  🔴 **本 Task 只做「接受新文法」，舊文法行為逐字不變**
  〔r4：若「舊文法一律 FAIL」先於遷移落地，既有 9 檔 89 行會立即轉紅，逼出刪行或假遷移〕。
  「拒絕舊文法」與「遷移既有 89 行」屬**另票** `GOV-ASSERT-LEGACY-MIGRATION`（見下方範圍說明）。
- **驗證（可證偽）**：新增 `tests/governance/test_assert_declarative.py`——
  ①宣告存在之 node ⇒ rc==0
  ②宣告不存在之檔 ⇒ rc==1
  ③檔存在但無該 `def` ⇒ rc==1
  ④同名 `def` 出現兩次 ⇒ rc==1（fail-closed，比照既有唯一性判準）
  ⑤`<path>` 不在 `tests/` 下（例如 `scripts/x.sh`）⇒ rc==1
  ⑥文件含**舊文法** ⇒ **本 Task 仍 rc==0**（行為不變）；
    「舊文法 ⇒ rc==1」屬**另票** `GOV-ASSERT-LEGACY-MIGRATION`，不在本 SPEC 範圍
    〔r5 三家：原文把 B.4 之驗收留在 B.1a，與「舊文法暫時仍接受」互斥〕
  ⑦🔴 **零執行證明**：以「一執行就建立標記檔」之 fixture 作為 node 名／路徑，
    跑完 `template_check` 後該標記檔**不存在**
  ⑧🔴 **realpath／symlink／`..` 承重**〔r6 兩家：改法有要求、驗證欄無對應格〕：
    `tests/../scripts/x.sh::test_a` ⇒ rc==1；`tests/` 下之 symlink 指向樹外 ⇒ rc==1
  ⑨🔴 **collect 可能性**：`<path>` 須同時滿足位於 `tests/` 下、副檔名 `.py`、
    basename 匹配 `test_*.py` ⇒ 否則 rc==1
    〔r6：原規則只要求「在 `tests/` 下且有唯一 `def`」，非 `.py`／非 `test_*.py` 會被誤收〕
  ⑩🔴 **實質性承重**：node 之函式體無 `assert`／`pytest.raises` ⇒ rc==1
  ⑪🔴 **共用語料**：`tests/governance/fixtures/substantive_corpus/` 之每一格，
    shell 端判定與 `_b49_selector_is_substantive` 之判定**逐格相同**（不同即紅）
  ⑫🔴 **symlink 指向 `tests/` 內合法檔**〔r8 `CODEX`：原 ⑧ 只測指向樹外〕
    ⇒ 仍 rc==1（判準是「非 symlink」，不是「指向哪裡」）
  ⑬🔴 **範本同步**〔r8 `CODEX`：`templates/SPEC_TEMPLATE.md` 列為必改卻無驗收〕：
    該範本須含 `ASSERT-TEST:` 之說明與範例，且**不得**再教作者寫舊 command／rc 文法
    ——以 `grep -c 'ASSERT-TEST:' templates/SPEC_TEMPLATE.md` >= 1 且
    範本內舊文法教學段已改寫為「舊文法（將由另票淘汰）」之標註
- **邊界（≥2）**：①`tests/` 下之檔含 BOM／CRLF ⇒ 仍正確判定
  ②node 名為既有 `def` 之子字串（如 `test_foo` vs `test_foobar`）⇒ 不得誤判為存在
- **存活至**：永久
- **覆蓋風險**：無
- 不可做：🔴 **本 Task 之「新文法路徑」不得有任何執行**；
  舊文法之既有執行路徑**維持現狀**（其危害已由 T0 止血涵蓋：寫檔零執行 ＋ 逐行 timeout），
  移除屬另票 `GOV-ASSERT-LEGACY-MIGRATION`。
  ⇒ 「完全零執行」是**該票完成後**之終態，非本 SPEC 之交付
  〔r5 三家指出原文把終態寫成當下要求，與「舊文法行為不變」互斥〕；
  不得以 `pytest --collect-only` 實作（那仍會 import 測試模組＝執行程式碼）。

> 🔴 **本 SPEC 之範圍到此為止（r7 後裁定）。**
>
> 原 Task B.2（89 行舊語法遷移）／B.4（拒絕舊文法）／B.3（移除 T0 設施）**全數移出**，
> 理由為實測之收斂失敗：finding 數 13→16→17→10→10→12→**16**，**七輪未收斂**。
> 根因不是那三個 Task 本身難，而是它們為了處理跨 **9 檔 89 行**（含**兩個凍結檔 45 行**）
> 的歷史語法，長出 grandfather／ledger／baseline／對照檔／證據 schema 等五套機制，
> **每套都新增一組「改法↔驗證」配對**，而主委每輪手工維持都會漏——
> r6 補了四格、r7 又被抓到漏五格，屬 `票 B-25`「原則修了、實例沒修」之同型。
>
> 🔴 **移出不等於留殘留**：ASSERT 自鎖之危害**已由 T0 止血擋住並 push**
> （commit `53966e90`：寫檔路徑零執行 ＋ 逐行 timeout ＋ `proc_guard.sh`）。
> 移出的是「把歷史語法遷乾淨」，該工作牽涉凍結檔，**需要自己的授權與批次**，
> 硬塞進一份「改執行順序」的修法內，正是本輪七輪未收斂的成因。
>
> **另立票**：`GOV-ASSERT-LEGACY-MIGRATION`（見 `handoffs/20260801-GOV-AMEND-BACKLOG.md`），
> 前置＝凍結檔之修改授權；其危害面已由 T0 涵蓋，故**不阻塞任何推送**。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：本案之三條實質宣稱各附 mutation（移除該判定後對應斷言須由綠轉紅）：
  ①「便宜段紅時不跑 pytest」②「`ASSERT-TEST` 之 node 不存在／不唯一 ⇒ 拒」
  ③「**新文法判定路徑**零執行」——以標記檔不存在證明（Task B.1 驗收 ⑦）。
  🔴 不得宣稱「`template_check` 整體零執行」——舊文法路徑仍在，屬另票。
- 測試層級：整合——於 tmp repo 內跑真腳本，比照 `tests/governance/test_govb1_factkey_hook.py` 既有作法。
- **防假綠**：🔴 原文寫「不得放寬或刪除既有斷言」與本案**必然要改**的斷言**互相矛盾**
  〔`CODEX-R1-P0-02`／`GROK-R1`：段號重編必動 `_GC_SEG_IDS`，
  而 `test_govb1_factkey_hook.py` 硬釘 fact-key 段號與該字面表；
  改 `_TC_ASSERT_CMD_ALLOW` 則使 `test_govb1_template_check_ext.py` 轉紅〕。
  ⇒ 改為**逐項列舉「預期同步變更」之斷言**，其餘一律不得動：
  ① `tests/governance/test_govb1_factkey_hook.py` — `_GC_SEG_IDS` 字面表、fact-key 之段號、
     分母期望值：**同批更新**（分母仍須現算，不得寫死）
  ② `tests/governance/test_gov_check_dep_failclosed.py` — `--fast` 之受檢範圍期望：**同批更新**；
     🔴 併同其 `_iso_repo` 之**複製清單**〔r4 兩家指出原清單只想到 `.sh`〕：
     新 `--fast` 含 fact-key 與 G-7 兩段 ⇒ 隔離副本須另含
     `scripts/fact_keys.json`、`scripts/govb1_scope.manifest`、`scripts/govb1_frozen_hashes.txt`
     及 fact-key 之宿主檔；**缺任一項 ⇒ 該段在隔離副本內必假紅**。
     施工時以「新 `--fast` 實際讀取之檔案」現算，**不寫死清單**。
  ②b 🔴 `tests/governance/test_govb1_factkey_hook.py::test_fast_mode_contract_is_unchanged`
     — 該測試以舊 `--fast` 契約為 oracle，新語義下**必轉紅**〔`COMPOSER-R2` 指出原清單漏列〕：
     **同批更新**，並改為釘住新契約（`--fast` ⊇ 便宜段全部、且不含 pytest）
  ③ `tests/governance/test_govb1_template_check_ext.py` — **只准新增**宣告式文法之斷言。
     🔴 **原「執行並比對 rc」之斷言逐字保留、不得移除**
     〔r8 `GROK`：原文寫「整組移除，因已消除執行路徑」，但 Task B.1 明文
     「舊文法之既有執行路徑維持現狀」⇒ 兩者互斥〕。
     其移除屬另票 `GOV-ASSERT-LEGACY-MIGRATION`。
  🔴 **判準**：上述三項只准**同步事實**，不准**放寬強度**。
  🔴 **證據 schema**〔r6 兩家：原文只寫「擋住同一反例」，無 baseline／oracle／receipt 規格，
  實作者可用新加的同一條弱測試自證〕——每項須附：
  ① **baseline**：改動前該斷言之原始碼片段（以 pre-change commit SHA 取得，非憑記憶）
  ② **反例集合**：原斷言能擋住的**全部**輸入，逐一列舉（非只一個）
  ③ **receipt**：新斷言對該集合**逐一**仍為紅之實跑輸出（`run_with_receipt.py` 產）
  ④ **獨立性**：反例集合須取自 baseline，**不得**由新斷言反推
  🔴 **對應之機械格**〔r8 兩家：schema 是硬性要求，但三個 Task 之驗證欄皆無對應格〕：
  於 `tests/governance/test_gov_check_order.py` 新增 `test_sync_evidence_schema_present`——
  斷言每一項同步變更皆有：①baseline 片段檔存在於
  `handoffs/run_receipts/sync_evidence/<斷言名>.baseline.txt`
  ②反例集合檔存在且列數 >= 1　③對應 receipt 之 `VERIFY:` id 存在於
  `handoffs/run_receipts/`　④四者缺一即紅
  其餘既有斷言（含 `test_doc_format_precheck.py`）一律不得動。
- **邊界目錄**：量化類（空DF/全NaN/Inf/std=0/重複timestamp/OOM/浮點）皆 N/A（見 §N）；
  適用者＝依賴腳本缺檔、多段同時失敗、並行呼叫、逾等待上限、tmp repo 無 git 歷史
  〔r8 `GROK`：原列「資料檔缺檔、budget 為 0」係已移出機制之殘句，已清〕。

## §R 回退

- Phase A／B 各自獨立 commit，可單獨 `git revert`（**無 Phase C**——已於 §A 抽出為具名殘留）。
- 不引入 feature flag：順序與邊界無「預設關閉」的中間態，加 flag 會使執行期行為不確定。
- 回退後行為＝現況（T0 止血仍在），無資料面副作用。

## §N N/A 登記

- **§G Golden**：N/A — 不碰數值／ML／特徵路徑。
  🔴 **行為不變之證明分兩類，不得混談**〔r6 `GROK`：原文與 §V「逐項列舉預期同步變更」互斥，
  實作者可能拒改 §V 清單、或反向拒收合法的同步更新〕：
  ① §V 具名清單內之三項 —— **預期會變**，判準＝「只准同步事實、不准放寬強度」
  ② 其餘所有既有斷言 —— **逐字不動且全綠**
  ⇒ 兩者互補；清單以外的任何改動即為違規。
- **解耦 7 條**：N/A — 只動 `scripts/`，不跨 `momentum/`↔`api/`。
- **§V 量化邊界目錄**：N/A — 無數值輸入輸出。
- **`npm run build`**：N/A — 無前端改動。
