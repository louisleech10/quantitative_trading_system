# GAP-3 事件型 UAT 缺口修補 — **實作交接**（更新於 2026-08-25）

> **給下一個 session 的完整交接。** `HANDOFF.md` 只放指標，細節全在本檔。
> 讀完本檔即可開工，不必回頭問。

---

## §0 一句話狀態

**SPEC 🔒 凍結、TODO 🔒 凍結 v1.0；B1 ✅ 已收斂並蓋章；下一步＝B2＝Task 1.2／1.3／1.4／1.8。**

| 文件 | 路徑 | 狀態 | commit |
|---|---|---|---|
| SPEC（語意權威） | `docs/GAP3_EVENT_UX_SPEC.md` | 🔒 FROZEN，3,547 行／42 Task | `4ce3d6d9` |
| TODO（操作依據） | `docs/GAP3_EVENT_UX_TODO.md` | 🔒 FROZEN v1.0，1,618 行／42 Task | `afa70967` |
| TODO 延伸檔 D-001（**須並讀**） | `docs/GAP3_EVENT_UX_TODO.D-001.md` | ✅ 三家 APPROVED | `81cbe7ab` |
| TODO 延伸檔 D-002（**須並讀**，A-002..A-015 共 14 條） | `docs/GAP3_EVENT_UX_TODO.D-002.md` | ✅ 三家 APPROVED | `51f1a65e` |
| 施工看板（給使用者看） | `白話說明/GAP-3施工看板.md` | 3 ✅／1 🔧／38 ⬜ | 每批收尾更新；版本看 `git log -1 --` 該檔 |

🔴 **層級**：**操作依據＝TODO；語意權威＝SPEC（衝突以 SPEC 為準並回報）；
讀 TODO 必須並讀 D-001 與 D-002**（凍結後修訂只走延伸檔，不就地改 TODO）。
🔴 **驗收字面之唯一來源＝SPEC 各 Task 之「驗證」欄**；TODO 只給可執行命令＋條目下限＋SPEC 行號。
**不得把 SPEC 斷言字面抄成第二份副本**——本 epic 三十四輪之自傷絕大多數出自副本漂移。

### B1 已交付什麼（B2 可以直接用）

| Task | 產出 | 可直接 import 的東西 |
|---|---|---|
| 1.1 | `event_import_contract.json` typed namespace-aware `receipt_schema` | `import_contract.py`：`flatten_receipt_schema()`／`receipt_type_ok()`／`validate_receipt_namespace()` |
| 1.10 | `contracts/future_column_lookahead.json`（37 個 future 欄） | `event_samples/lookahead_registry.py`：`load_lookahead_registry()`／`normalize_future_column()`／`hours_to_bars()`／`resolve_lookahead_bars()`／`lookahead_resolution()`／`unregistered_future_columns()` |
| 2.1b | 唯一 exported 深度函式 | `event_samples/lookahead_depth.py::depth_by_timeframe(referenced_columns, declared_window_bars, timeframes, registry=None)`；前端 `frontend/src/lib/lookaheadDepthLock.ts::withHorizonLowerBoundGuard()` |
| 4.2（僅 §G S-9） | canonical bytes 參考實作 | `event_samples/canonical_serialize.py`：`normalize_for_canonical()` `:43`／`canonical_event_table_bytes()` `:71`／`canonical_event_table_sha256()` `:76` |

🔴 **B2 之 Task 1.3 依賴 `canonical_serialize.py`——已存在，B2 不會停批。**

---

## §1 開工前稽核（逐條跑，全部要對；不對先修再開工）

```bash
git log --oneline -3
bash scripts/debt_ledger.sh --has-open          # 期望 rc=0（無未清委員會債）
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.md        # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-001.md  # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-002.md  # 期望 rc=0
grep -c '^### Task ' docs/GAP3_EVENT_UX_TODO.md # 期望 42
for r in r1 r2 r3; do bash scripts/reconcile_stamps_check.sh \
  handoffs/reconcile/20260824-gap3uxtodo-x-review-$r/synth.md codex,composer,grok; done   # 三份皆 PASS
python3 scripts/gap3_freeze_golden.py --check   # 期望 rc=0（canonical_sha 全程不變）
pytest tests/momentum/event_samples/ -q         # 期望 270 passed
```

B1 之四個 Task 已 ✅，其 mutation receipt 為 `handoffs/run_receipts/gap3ux-b1-all-mutations.receipt.json`
（32 條，`closure: CLOSED`）。**不需要重跑**，除非你改了 B1 的產出。

---

## §2 B2 是什麼（四個 Task）

**B2 ＝ CSV 匯入主線 ＝ Task 1.2、1.3、1.4、1.8。** 依 §B 拓撲，B2 之前置只有 B1（已完成）。

### 2.1 🔴 偵察結論（2026-08-25 主委實跑，下個 session **不必重查**）

> **Task 1.2 不是「加 CSV 支援」——CSV 已經能匯入了。**
> `api/services/case_import_service.py::parse_upload()` `:654` 對**非 `.json` 檔名**直接走
> `pd.read_csv(..., dtype=str, keep_default_na=False, chunksize=5000)` ⇒ `/case/import-events` 現在就吃 CSV。
> **1.2 的真正 delta ＝ `column_mapping` ＋ `batch_defaults`**：讓使用者用**自己的欄名**匯入，
> 不必先把標頭改成契約欄名。TODO 沒點破這件事，但它決定實作形狀——
> **不要再寫一條 CSV 解析路徑**，要做的是「對映層 → 既有 `import_records()`」。

| 事實 | 位置 | 對 B2 的意義 |
|---|---|---|
| `/case/import-events`（multipart）／`/case/import-events/json` | `api/routes/case.py:139`／`:180` | 1.2 之新端點緊鄰這兩個；1.3 之「服務端入口」也在這條鏈上（**不新增 route**） |
| 全部 route 行號 | `api/routes/case.py` 之 `@router`：`46,139,180,201,206,214,229,251,274,320,348` | TODO Task 1.3 要求開工時 `grep -n '@router'` 定位並**記入 commit message**——即本行 |
| `EventImportService.parse_upload()` | `:654` | 分塊 CSV 解析已在此；1.2 只加對映，不改它 |
| `EventImportService._csv_rows_to_records()` | `:677` | 已支援 dotted 欄（`label_definition.rule_id`）與 JSON 儲存格；對映層輸出應餵給它或其後 |
| `EventImportService.import_records()` | `:709` | **1.2 要共用的就是這個函式物件**（V-3 之 AST oracle 會驗同一物件） |
| 契約已有的 reason 字面 | `event_import_contract.json:116-117` | `column_mapping_missing`／`column_not_found_in_file`／`heterogeneous_rows_in_batch`／`label_column_not_binary` **都已在封閉集合內，不需新增** |
| `ms_magnitude_min: 1000000000000` | `event_import_contract.json:4` | 1.4 之門檻唯一來源，**不得寫死第二份** |
| 現行 t0 單位判定 | `import_contract.py:184`（讀門檻）／`:226`（`fail(..., "invalid_timestamp_unit")`） | TODO 定案：1.4 **新增** `detect_t0_unit_ms()`，**不從此處抽出**（抽出會動既有行為） |
| 前端自算 digest | `frontend/src/lib/eventExport.ts`：`sha256Hex()` `:20`（WebCrypto `subtle`）／`canonicalSourceText()` `:28`／`sourceDigest` `:66`／`event_id` 模板 `:88`／`source_file_digest` `:105`,`:116` | 1.3 要把這段改成**呼叫後端取得**；前端不得再自算 |

### 2.2 四個 Task 之關鍵座標（詳細內容一律回讀 TODO 該 Task 全文）

| Task | TODO 行 | 主要落點 | 驗收命令（條目下限） |
|---|---|---|---|
| **1.2** 新端點 `POST /api/v1/case/import-events/csv` | `191` | `api/routes/case.py` 新增 `import_events_csv`；`EventImportService` 抽出共用檢核方法（若尚未共用） | `pytest tests/api -q -k gap3_csv_import` **≥8 條** ＋ V-3 兩重 oracle（AST 靜態＋行為 mutation） |
| **1.3** `event_id` 沿用既有 canonical（D-2） | `218` | `frontend/src/lib/eventExport.ts`（改呼叫後端）；`api/routes/case.py` 既有 case 鏈**加兩個回應欄位**；`import_contract.py` 新增 `verify_source_digest()` | `npx vitest run canonicalSourceCoverage` **≥3 條** ＋ ④(a) 執行期 stub 枚舉 ＋ ④(b) AST 靜態 ＋ mutation 三條 |
| **1.4** t0 單位偵測 | `273` | `import_contract.py` 新增 `detect_t0_unit_ms()`；`EventImportService` 呼叫 | `pytest tests/api -q -k gap3_t0_unit_detect` **≥3 條**；秒級輸入輸出精確 `== 1704067200000` |
| **1.8** 異質列顯式拒收（A-5′） | `359` | `import_contract.py::validate_event_import()` 加異質列檢查 | `pytest tests/api -q -k gap3_heterogeneous_rows` **≥2 條**；訊息列出前 3 個衝突列號（斷言列號數 `== 3`） |

### 2.3 B2 之四個陷阱（TODO 已明列，逐條抄在這裡免得漏）

1. **1.2**：**不得**為 CSV 路徑另寫一份 schema 檢核邏輯。V-3 之行為 mutation 判準是
   「另寫一份 ⇒ **只有一條路徑轉紅**」——**若兩條同時紅代表仍共用、該 mutation 無效**。
2. **1.3**：**不得**發明新的 `event_id` 演算法（R1 兩家獨立判 BLOCKING）；前端**不得**自算
   `source_file_digest`；**不得**新增第二個 transport／route；
   🔴 `rule_digest`（綁 `search_rule_summary`）與 `source_file_digest`（綁完整 `CaseData` 列）
   **是兩件事，同一 helper 不得共用序列化路徑**。
   🔴 S-9 之參考實作**只准 import，禁在 TS 重寫**（S-9 第 7 條）。
   ⚠️ 具名殘留（**不得宣稱已解決**）：純 JS 手刻 sha256（不經 WebCrypto／`node:crypto` 入口）
   本閘看不見；三值理由 `needs-research`。
3. **1.4**：判不出單位時**不得猜預設值**。偵測函式須為 **exported 單一函式**，CSV 與 JSON 共用。
4. **1.8**：**不自動分批**、**不靜默取第一列之值套用全批**。

### 2.4 D-002 中與 B2 相關的一條

- **A-004 前端下界值來源**：`blocked-by` Task 2.1（篩選面板，B5）與 **Task 1.3（B2）**所建之傳輸點。
  ⇒ **B2 落地 1.3 時只需把傳輸點建好**；接線留到 B5 收尾一併做（D-002:71,76）。

### 2.5 之後的批次（不在本批，僅供排序）

| 批 | Task | 依賴 |
|---|---|---|
| B3 深度三層防線 | 1.11、1.12、1.9 | B1、B2、Task 2.1b |
| B4 匯入前端 | 1.5、1.6、1.7 | B2 |
| B5 匯出前篩選 | Phase 2 全部（扣除已於 B1 完成之 2.1b） | B1 |
| B6 刪除 | Phase 3 全部 | 無 |

---

## §3 派工管線（**大任務**，不得跳步）

命中高風險 (a) 數值/資料品質 ＋ (b) 跨模組 ⇒ **大任務**。SPEC／TODO 皆已凍結、已過 adversarial
⇒ **實作階段之管線為**：

1. **實作＝Claude 主委自任**（`docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行，2026-08-17 使用者五調逐字：
   「SPEC/TODO 初稿＝Claude 主委一律起草；**中/大實作＝Claude(Fable 5/Opus)主委自任**；
   討論/code review/adversarial＝**Codex＋Grok＋Composer 三家全員**；簽核 quorum＝三家」）。
   🔴 **派工前必先重讀該行**——選層是動態的，以使用者當下指示為準。
2. **每批收尾必派 code review**：三家全員，**實作者不自審**；機器強制
   `scripts/review_quorum_check.sh`（接在 `gate.sh` 派下一批前驗前批 quorum，不足即拒發 token）。
3. **開門**：`bash scripts/gate.sh dispatch --task-id … --risk high --intent … --facts-asked … --review-role … --template …`
   （委派與創建治理文件都需 fresh token；900 秒）。
4. **前後**：`bash scripts/agent_preflight.sh` → 派工 → `bash scripts/agent_postflight.sh`，PASS 才驗收。
5. **委員派工一律走** `scripts/cx_run.sh`（brief 放 repo 內、用絕對路徑、**禁 `&`**）。
6. **兩輪斷路器**：任何問題自己弄 ≤2 輪仍失敗 ⇒ 立即開委員會，禁 solo 硬幹。

**B1 之實績供校準**：code review 五輪，findings **3 → 2 → 10 → 7 → 0**；最嚴重等級全程 0；
第五輪由**當初提出問題的那一家**各自重跑自己的反例確認閉合（章程 §B8）。

---

## §4 「完成」的判準（不得放寬）

一個 Task 標 ✅ 的條件：
1. 該 Task「驗證」欄之命令**全部 rc=0**，且條目數 ≥ TODO 所列下限；
2. **該 Task 之 mutation 已實跑**——故意改壞 ⇒ 對應斷言**轉紅**；還原 ⇒ 轉綠；
3. **receipt 路徑寫進 commit message**。

🔴 **只有測試綠、沒有 mutation receipt ⇒ 仍是 🔧，不是 ✅。**
理由：測試綠只證明「現在沒壞」，mutation 才證明「壞了測得出來」。

🔴 **mutation 判準＝轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。
該判準在 B1 救過兩次：一次抓出主委寫的**無效 mutation**（副本委派回本尊 ⇒ 空紅集合），
一次讓委員之併發假失敗可被辨識。**不要放寬成「有紅就算過」。**

**批次間 Gate**：上一批全部 mutation 轉紅並還原轉綠、receipt 入 commit，才可開下一批。

**每批收尾固定動作**：更新 `白話說明/GAP-3施工看板.md`（每完成一個 Task 改一列、更新「一眼看完」三個數字）
＋ 更新 `docs/ROADMAP.md` ＋ 更新 `HANDOFF.md` ＋ commit ＋ **背景 push**（使用者在外看進度）。

### 4.1 怎麼寫 mutation runner（2026-08-25 起已隔離，可平行）

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from mutation_worktree import IsolatedWorktree, venv_python   # noqa: E402

with IsolatedWorktree(prefix="b2mut_") as wt:
    ...   # 所有改檔與 pytest 都在 wt 底下；主 repo 一個位元組都不動
```

- 現成範本：`handoffs/gap3ux_b1_mutations.py`（32 條）、`handoffs/survivor_nsamples_mutations.py`（7 條）。
- 官方單條 CLI：`bash scripts/verify_mutation.sh <檔> <原字串> <變異字串> <pytest目標>`（已同樣隔離）。
- 🔴 `<檔>` 須為 **repo 相對路徑且不含 `..`**，否則 rc=2 拒收
  （`Path(wt) / "/abs/x"` 在 pathlib 等於 `/abs/x`，會靜默打回主 repo）。
- ⚠️ `handoffs/*.py` 由 **`.git/info/exclude:21`（本機檔，非 `.gitignore`）** 排除 ⇒
  **runner 本身不入版控，換機器就沒有**；入版控的只有 `scripts/mutation_worktree.py` 與官方 CLI。

---

## §5 未辦事項（開工前／收 epic 前要處理）

| # | 事項 | 何時 | 狀態 |
|---|---|---|---|
| 1 | D-001／D-002 委員戳記 | 開 B2 前 | ✅ **已完成**（D-001 `81cbe7ab`、D-002 `51f1a65e`，三家 APPROVED） |
| 2 | 動過 `scripts/` ⇒ 收 epic 前跑 `gov_check.sh --no-probe` | 收 epic 前 | ✅ **2026-08-25 已跑**；結果見 §6.4。**若 B2 又動 `scripts/` 需重跑** |
| 3 | **GAP-3 B5 之 UAT B 段簽字**仍在使用者手上（`docs/GAP3_UAT_CHECKLIST.md`），與實作無依賴 | 使用者 | ⬜ **未簽字不收案** |

---

## §6 地雷（本 epic 專屬，逐條是實際踩過的）

### 6.1 🔴 「比對範圍過寬」——主委在本 epic 犯了**五次**，形狀完全相同

| # | 形態 | 後果 |
|---|---|---|
| 1 | Phase Gate 之測試層標籤與 Task 欄位**同字面** | 機械閘分不出來 |
| 2 | 以**行號**注入修補，行號取自修補**前**之掃描輸出（中間檔案已位移） | 三處落到**錯的 Task**（1.3／1.10／7.0b 被塞了別人的 selector） |
| 3 | 判斷 Task 有無 mutation 時掃**整個區塊** | 被區塊尾端別人的字樣騙過（1.2／2.3 假跳過） |
| 4 | 同步斷言只驗**子字串存在**，散文卻宣稱「參數名序列逐字相等」 | **假綠**，改參數名照樣過 |
| 5 | 驗 gitignore 時問**目錄**（`git check-ignore tests/golden` 得空輸出） | `.gitignore` 之 `*.h5` 沒被看見 ⇒ 隔離副本缺 e2e fixture、全紅 |

**共同形狀＝拿比目標更大的範圍去比對，然後把命中當成目標命中。**
🔴 **對策（照做）**：①錨點落在**真正要判斷的那個東西**上——不是它的段落、不是行號、不是附近的字
②**一律字面錨點，禁行號** ③檢查寫完要用**已知會紅的輸入**試一次，只看綠不算驗過。

🔴 **B1 R3 之另一條教訓（更重要）**：不要用**原始碼形狀**（或任何代理物）去證明**執行期性質**——
形狀有無限多種等價寫法，逐一補斷言是黑名單，永遠列不完。正確的問法是
「這個性質為什麼需要用猜的」，答案通常是**改設計讓它變成結構保證**
（B1 的解法＝把整段匯出包進 `withHorizonLowerBoundGuard(…, {proceed})`，
使「阻擋早於網路動作」由需檢查之性質變成結構保證）。**B2 之 1.3 ④(b) AST oracle 同一風險面。**

### 6.2 產出端閘會擋你，而且多半擋對了

- `doc_format_precheck.sh`：驗證欄須**逐行**含可證偽 token（`pytest`／`==`／數字／`.py`…）；
  含「驗證」二字的 bullet **該行自身**要有 token（多行寫法會被判空殼）。
- commit message：operational claim 需 backing；`VERIFY:<path>`**冒號後不能有空格**，
  且該檔須含 `CLOSED`／`APPROVED`／`RECONCILE-STAMP` 等閉合判詞
  （🔴 由 runner 直接寫 `closure` 欄，**不要事後手補**）。
- 🔴 **`Governance-Scope: out-of-epic <理由>` trailer**：staged 含 epic scope 外路徑時**必加**，
  且**必須在 commit 訊息之最後一段**（git 只解析最末段；與 `Co-Authored-By` 同段即可）。
  漏加只能重寫歷史，補後續 commit 解不掉。
- 計數字面稽核：說明文字裡的「一支」「一筆」也會被當計數字面 ⇒ 改措辭。
- 白話狀態檔（`README.md`／`接下來要做什麼.md`）**禁純檔尾追加**，須改寫現況段。
- 延伸檔命名須 `<BASE>.D-00N.md`（`*_AMENDMENTS.md` 會被誤判為 todo 型別）；
  且 dext 必含 `BASE:`／`PREDECESSOR:`／`## 觸及面宣告`／`## 內容`／`## 戳記`。
- `plain_docs_sync_check.sh`：改過 `scripts/`／`docs/GOV*`／`tests/governance/` 就會讓
  `治理進度日誌.md`／`流程摩擦記錄.md`／`接下來要做什麼.md`／`README.md` 判定過期
  ⇒ **同一批就寫進去**，別留到 push 前才發現（`--fast` 不查它，但收 epic 之手動關卡會查）。

### 6.3 工具與環境

- **本機 bash 3.2.57** ⇒ **無 `declare -A`**；`sed` 為 BSD ⇒ **BRE 不支援 `\|`**，一律用 `sed -E`。
  跨平台差異多半**不報錯，只是安靜地做錯**（曾使字尾沒切掉、到數字比較才炸）。
- **絕不寫 `cd <專案路徑>` 前綴**；瑣事別用 `python3 -c`；改檔用 Edit／Write 工具。
- `pytest tests/governance` 與 `govb1_final_gate.sh` 全跑皆**十分鐘級** ⇒ **一律丟背景**。
- 委員會清 `/tmp` ⇒ 自己導到 `/tmp/x.log` 的檔可能被刪；重要輸出看 harness task output 檔。
- `handoffs/` **未入版控**（勿清）。
- 跑完測試須 `bash scripts/restore_golden_inventory.sh` 還原 golden inventory 副作用。

### 6.4 🔴 治理現況（2026-08-25 實測，**兩條都是既有債，不要以為是自己弄的**）

| 檢查 | 結果 | 歸屬證據 |
|---|---|---|
| `gov_check.sh --no-probe` 段 4 **G-7 scope 淨差** | FAIL，**383 條**「未宣告即修改」（base `62787fe4` 在 **567 個 commit** 之前） | 於 `HEAD~2` 隔離 worktree 跑同一條閘**亦 FAIL 且路徑集合逐一相同**（`comm` 兩向皆空） |
| `pytest tests/governance -q` | **1743 passed / 6 failed**（45m40s） | 於 `HEAD~3` 隔離 worktree 實跑同這 6 條，**同樣 6 failed**（24m27s） |

- 6 條之組成：4 條 `test_govb1_contract_matrix` 皆 **G-7 相關**（同源）；
  2 條 `test_govb1_factkey_hook` 斷言「fact-key 漂移時 pre-push 須拒絕」，
  而 pre-push 已於 **2026-08-14 使用者裁定改跑 `--fast`（刻意不含第 2–4 段）** ⇒ **測試比裁定舊**。
- 🔴 **連帶效果（重要）**：段 4 FAIL 後 `gov_check` **不再往下跑第 5／6 段**
  ⇒ 全套 pytest **從未經由 gov_check 執行**。需要時直接跑 `pytest tests/governance -q`（丟背景）。
- 兩條皆已登記為 `HANDOFF.md` 之殘留 `R-GOV7-1`／`R-GOV7-2`，三值理由 `user-ruling`，**不排工**。

---

## §7 🔴 不要碰的東西

### 7.1 治理（使用者 2026-08-24 定死）

逐字：「當初就是發現你做治理是無解才不做」「你這樣岔題去問委員，永遠沒完沒了」。
⇒ **遇治理工具壞掉：繞過並具名記錄，不修、不開票。要動須使用者明示。**
⇒ **落地出錯就抄仔細**，不要「做一支工具來量自己」——那正是 SPEC 階段燒掉六輪的原因
（R28 新建對證工具 → 六輪修那支工具 → 把工具問題寫進派工單 → 委員回更多治理 findings → 自我餵養）。
⇒ **治理／工具問題不得寫進派工單**，那是迴圈的燃料。

🔴 **唯一已獲明示授權之例外（2026-08-25，已完成，不必再動）**：mutation 併發隔離
`scripts/mutation_worktree.py` ＋ `scripts/verify_mutation.sh` 改薄殼委派。用法見 §4.1。

### 7.2 已具名封存之殘留（**不排工、不另立票**）

- **SPEC 末節 F-1..F-4**：同輪重派死鎖／補丁包檔名碰撞／編排草圖含 illustrative 佔位不通過
  `compile()`／`gap3ux_apply_patch.py` 包側 VERIFY 缺陷。
- **TODO（R3 reconcile）四條**：前端 directory-only 路徑 10 處／Task 5.0 驗證 defer SPEC／
  五 Task（1.10／3.3／4.3／7.3／7.5）之 mutation 全文 defer SPEC（**composer 已交 exact mutant 補丁包**
  `handoffs/patches/20260824-gap3ux-todo-r2-composer-mutation-five.md`）／B1 須並讀 FROZEN SPEC。
### 7.3 B1 期間新增之具名殘留（**本節為全文；`HANDOFF.md` 只指回這裡**）

- **R-GOV7-1 G-7 scope 淨差長期紅（383 條）**：詳見 §6.4。判準要求 trailer 落在**該 commit 自身**
  ⇒ 前向修不掉。三值理由 `user-ruling`。owner 主委。
- **R-GOV7-2 治理 pytest 6 條長期紅**：詳見 §6.4。其中 2 條之斷言比 2026-08-14 之使用者裁定舊。
  三值理由 `user-ruling`。owner 主委。
- **R-B1-1 全量跑之測試順序污染**：`pytest tests/momentum tests/api` 全量跑時有若干紅，
  單獨跑較少。歸因**未實跑證明**（需以 stashed 樹全量跑一次，約 64 分鐘）。
  三值理由 `needs-research`。owner 主委。
- **R-A005-1 producer-backed 表為人工稽核非執跑探針**：`lookahead_registry` 之
  `_PRODUCER_SEMANTICS` 表若與 producer 漂移，本閘看不見。
  三值理由 `needs-research`（需把 `CaseSearchEngine` 之未來欄計算段抽成純函式，屬搜尋引擎重構）。
  owner 主委；**觸發＝下次動到該段時一併做**。
- **D-002 A-004 前端下界值來源**：三值理由 `blocked-by` Task 2.1（B5，篩選面板）
  與 Task 1.3（B2，傳輸點）。B2 只建傳輸點，接線留 B5。
- **D-001／D-002 provenance 不可登記**：`gate.sh register-output` 只收 `handoffs/` 或
  `stampable_artifacts.txt` 明列者 ⇒ 對 `docs/*.D-00N.md` 跑 `reconcile_stamps_check.sh` 會報
  provenance pending（**非戳記造假**）。provenance 完備之機械標的為對應
  `handoffs/reconcile/.../synth.md`。三值理由 `user-ruling`。

---

## §8 檔案地圖（實作會碰到的）

| 用途 | 路徑 |
|---|---|
| 事件樣本模組（新邏輯放這） | `momentum/Analysis/event_samples/`（`alignment.py`／`event_split.py`／`ic_feed.py`／`pipeline.py`／`tables.py`／`dedupe.py`／`import_contract.py`／`types.py`／**`lookahead_registry.py`**／**`lookahead_depth.py`**／**`canonical_serialize.py`**） |
| 契約（欄位／枚舉／reason 之 SoT） | `momentum/Analysis/contracts/event_import_contract.json`、**`future_column_lookahead.json`**、`ic_report_contract.json` |
| case 匯入端點 | `api/routes/case.py`（`import_events_file` `:139`／`import_events_json` `:180`／`_rejected` `:132`；全部 `@router` 行號見 §2.1） |
| 匯入服務 | `api/services/case_import_service.py::EventImportService`（`parse_upload` `:654`／`_csv_rows_to_records` `:677`／`import_records` `:709`） |
| IC 分析端點／服務 | `api/routes/ic_analysis.py`（`@router.post("/analyze")` `:34`）；`api/services/ic_analysis_service.py::_run_analysis` |
| 前端匯出 | `frontend/src/lib/eventExport.ts`（`sha256Hex` `:20`／`canonicalSourceText` `:28`／`event_id` 模板 `:88`／`source_file_digest` `:105`,`:116`）；呼叫端 `frontend/src/app/search/page.tsx` |
| 前端深度鎖定（B1 產出） | `frontend/src/lib/lookaheadDepthLock.ts`＋`lookaheadDepthLock.test.ts`＋`lookaheadDepthLock.page.test.ts` |
| 搜尋引擎（future 欄之來源） | `momentum/DataExtraction/case_search_engine.py`（`periods_{H}h` `:1385-1387`；⚠️ `periods_72h` 亦用於**過去 3 天 lookback** `:1028-1046`，同名不同義） |
| B1 之 mutation receipt | `handoffs/run_receipts/gap3ux-b1-all-mutations.receipt.json`（32 條 CLOSED） |
| 三輪 TODO 審查之 reconcile | `handoffs/reconcile/20260824-gap3uxtodo-x-review-r{1,2,3}/synth.md`（三份皆三家 APPROVED） |
| 過程與教訓（給使用者） | `白話說明/GAP-3施工看板.md`（進度）、`白話說明/GAP-3施工進度.md`（歷史）、`白話說明/治理進度日誌.md`、`白話說明/流程摩擦記錄.md` |
