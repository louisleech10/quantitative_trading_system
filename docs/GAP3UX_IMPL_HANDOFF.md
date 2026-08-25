# GAP-3 事件型 UAT 缺口修補 — **實作交接**（更新於 2026-08-25，B3 開工態）

> **給下一個 session 的完整交接。** `HANDOFF.md` 只放指標，細節全在本檔。
> 讀完本檔即可開工，不必回頭問。

---

## §0 一句話狀態

**SPEC 🔒 凍結、TODO 🔒 凍結 v1.0；B1／B2 皆已收斂並蓋章；下一步＝B3＝Task 1.11／1.12／1.9。**

| 文件 | 路徑 | 狀態 | commit |
|---|---|---|---|
| SPEC（語意權威） | `docs/GAP3_EVENT_UX_SPEC.md` | 🔒 FROZEN，3,547 行／42 Task | `4ce3d6d9` |
| TODO（操作依據） | `docs/GAP3_EVENT_UX_TODO.md` | 🔒 FROZEN v1.0，1,618 行／42 Task | `afa70967` |
| TODO 延伸檔 D-001（**須並讀**） | `docs/GAP3_EVENT_UX_TODO.D-001.md` | ✅ 三家 APPROVED | `81cbe7ab` |
| TODO 延伸檔 D-002（**須並讀**，A-002..A-015 共 14 條） | `docs/GAP3_EVENT_UX_TODO.D-002.md` | ✅ 三家 APPROVED | `51f1a65e` |
| 施工看板（給使用者看） | `白話說明/GAP-3施工看板.md` | 7 ✅／1 🔧／34 ⬜ | 每批收尾更新 |

🔴 **層級**：**操作依據＝TODO；語意權威＝SPEC（衝突以 SPEC 為準並回報）；
讀 TODO 必須並讀 D-001 與 D-002**（凍結後修訂只走延伸檔，不就地改 TODO）。
🔴 **驗收字面之唯一來源＝SPEC 各 Task 之「驗證」欄**；TODO 只給可執行命令＋條目下限＋SPEC 行號。
**不得把 SPEC 斷言字面抄成第二份副本**——本 epic 三十四輪之自傷絕大多數出自副本漂移。

### B1／B2 已交付什麼（B3 可以直接用）

| Task | 產出 | 可直接 import 的東西 |
|---|---|---|
| 1.1 | `event_import_contract.json` typed namespace-aware `receipt_schema` | `import_contract.py`：`flatten_receipt_schema()`／`receipt_type_ok()`／`validate_receipt_namespace()` |
| 1.10 | `contracts/future_column_lookahead.json`（37 個 future 欄） | `event_samples/lookahead_registry.py`：`load_lookahead_registry()` `:31`／`lookahead_columns()` `:44`／`normalize_future_column()` `:50`／`hours_to_bars()` `:64`／`resolve_lookahead_bars()` `:73`／`lookahead_resolution()` `:99`／`unregistered_future_columns()` `:132` |
| 2.1b | **唯一** exported 深度函式 | `event_samples/lookahead_depth.py::depth_by_timeframe(referenced_columns, declared_window_bars, timeframes, registry=None) -> Dict[str,int]` `:42`；前端 `frontend/src/lib/lookaheadDepthLock.ts::withHorizonLowerBoundGuard()` |
| 4.2（僅 §G S-9） | canonical bytes 參考實作 | `event_samples/canonical_serialize.py`：`normalize_for_canonical()`／`canonical_event_table_bytes()`／`canonical_event_table_sha256()`／**B2 新增** `canonical_source_bytes()`／`canonical_source_digest()` |
| **1.2**（B2） | CSV 欄名對映端點 | `api/routes/case.py::import_events_csv`；`EventImportService.csv_records_from_mapping()` |
| **1.3**（B2） | `event_id` 之 D-2 唯一定義來源 | `import_contract.py`：`event_id_template()`／`canonical_event_id(symbol, timeframe, t0)`／`verify_source_digest()`；前端 `frontend/src/lib/eventId.ts::canonicalEventId()`／`EVENT_ID_TEMPLATE` |
| **1.4**（B2） | t0 單位偵測 | `import_contract.py`：`detect_t0_unit_ms()`／`normalize_t0_units()`／`T0UnitUndetectedError` |
| **1.8**（B2） | 異質列拒收 | `validate_event_import(..., enforce_batch_homogeneity=True)` |

🔴 **B3 之 Task 1.9 依賴 `depth_by_timeframe()`——已存在（B1 交付），B3 不會停批。**

### `EventSamplePipeline` 之 R3 出口清單（api 層只能經這些取用 momentum）

`import_contract()`／`canonical_event_id()`／`event_id_template()`／`mapping_failure_reasons()`／
`normalize_t0_units()`／`canonical_source_payload()`／`condition_engine_contract()`／
`bars_from_kline_cache()`／`validate()`／`run()`／`run_with_params()`／`analyze_tables()`
（見 `momentum/Analysis/event_samples/pipeline.py` 之 `@staticmethod` 區）。
🔴 **B3 若要讓 api 層用到 `requires_declaration()`／`run_event_study_only()`，必須在此加出口**
——直接 `from momentum...import` 會被 `scripts/check_decoupling_imports.py`（R3）在 PostToolUse 當場擋掉。
B2 開工第一次就踩到這個，改走 pipeline 出口即過。

---

## §1 開工前稽核（逐條跑，全部要對；不對先修再開工）

```bash
git log --oneline -3                            # 期望最新為 ade67f3f（B2 收斂）
bash scripts/debt_ledger.sh --has-open          # 期望 rc=0（無未清委員會債）
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.md        # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-001.md  # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-002.md  # 期望 rc=0
grep -c '^### Task ' docs/GAP3_EVENT_UX_TODO.md # 期望 42
python3 scripts/gap3_freeze_golden.py --check   # 期望 rc=0（canonical_sha 全程不變）
venv/bin/python -m pytest tests/momentum/event_samples/ -q            # 期望 270 passed
venv/bin/python -m pytest tests/api -q -k "gap3_csv_import or gap3_source_digest or gap3_t0_unit_detect or gap3_heterogeneous_rows"   # 期望 44 passed
```

B1／B2 之 mutation receipt 為 `handoffs/run_receipts/gap3ux-b1-all-mutations.receipt.json`（32 條）
與 `handoffs/run_receipts/gap3ux-b2-all-mutations.receipt.json`（**14 條**），皆 `closure: CLOSED`。
**不需要重跑**，除非你改了 B1／B2 的產出。

---

## §2 B3 是什麼（三個 Task）

**B3 ＝ 深度三層防線 ＝ Task 1.11（L2 強制宣告）、1.12（L3 禁進切分）、1.9（宣告 UI 與 purge 下界）。**
依 §B 拓撲，B3 之前置為 **B1、B2、Task 2.1b**——**全部已完成**。

> **一句話**：B1 的 registry（L1）只能回答「這個欄看多遠」。若欄位**解析不出深度**，
> L2（1.11）**強制使用者宣告**、L3（1.12）**在宣告缺失時禁止進切分與條件 IC 但仍可產事件研究表**，
> 1.9 則是 L2 的**使用者介面**（逐 tf 收集宣告值並投影到 purge 下界）。

### 2.1 🔴 偵察結論（2026-08-25 主委實跑，下個 session **不必重查**）

| 事實 | 位置 | 對 B3 的意義 |
|---|---|---|
| `run()` **無條件**呼叫 `split_events` | `pipeline.py:258`（`plan = split_events(manifest, config.split)`） | 這正是 SPEC 群集 E 所指的矛盾：照現有呼叫鏈只能在「違反 L3」與「產不出表」之間二選一 ⇒ **1.12 必須新增 `run_event_study_only()`** |
| API 走的是 `run_with_params()` → `run()` | `pipeline.py:129`；`case_import_service.py::analyze` `:894`（`:904` 呼叫 `run_with_params`、`:908` 呼叫 `analyze_tables`） | 1.12 之 event-study-only 路徑要在**這條鏈**上分派；`analyze` 是唯一 API 消費者 |
| `event_forward_return_table` 之 `event_split_plan` **目前為必填** | `tables.py:88`（def）／`:92`（參數）／`:117`（`event_split_plan.clusters.set_index(...)` 直接取用） | 1.12 ② 要把它改 `Optional`；`:143` 對不在 `cl.index` 者已回 `-1`，與 SPEC 所述一致 |
| `_common_constraint_block` **已 fail-closed** | `tables.py:61`（def）／`:67-69`（`allowed`）／`:80`（`reason=no_event_split_plan`） | 1.12 ③ 之 `ci` unavailable 分支要與**這裡既有的行為一致**，不是新造一套 |
| `ci` 之計算點 | `tables.py:157`（`_cluster_bootstrap_ci(...)`，定義在 `:24`） | `event_split_plan is None` 時**不得走到這一行**（全塞 `-1` 會產出看似有效的錯誤 CI） |
| `analyze_tables` 直接把 `result.split_plan` 傳進去 | `pipeline.py:150-151` | event-study-only 時這裡要傳 `None`，不是傳假 plan |
| `split_events` 入口 | `event_split.py:38` | 1.12 ① 之拒絕分支落點 |
| `ic_feed` 入口 | `ic_feed.py::build_event_ic_inputs` `:24` | 1.12 ① 之另一個拒絕分支落點 |
| `unregistered_future_columns()` 已存在 | `lookahead_registry.py:132` | **1.11 之 `requires_declaration()` 應建在它之上**，不要另寫一套欄位偵測 |
| `depth_by_timeframe()` 之 `Raises` | `lookahead_depth.py:42-60`：缺 tf 鍵 ⇒ `KeyError`；深度不可導出 ⇒ `UnresolvableLookaheadDepth` | 1.11／1.9 之 fail-closed 語意**已由這兩個例外承載**，不需新造 |
| B3 三個 selector **目前皆 0 條** | `lookahead_declaration`／`split_blocked`／`gap3_horizon_declaration` 實跑 `--collect-only` 皆 `no tests collected` | 三個測試檔都要新建 |
| purge 下界之**唯一**權威式 | SPEC §D-3′-a（ii），約 L228–246 | 1.9 ⑤「只呼叫、不重述」指的就是這一式；`timeframe_seconds` 是**注入之 map**（R22），**不是** module-level `TIMEFRAME_SECONDS` |
| `lookahead_bars_declared` 為 **map 非 scalar** | SPEC §D-3′-a（i），約 L200–215 | 1.9 ② 之 derived 欄型別；契約 `derived_fields.names` 已登記（B1 交付） |
| 對齊失敗列**不進** purge／split | SPEC §D-3′-a（ii）之 R26／R27 段，約 L248–262 | purge scope ＝ `prepared0.windows`（**不是**全部 records）；但其 `timeframe` 仍保留在鍵集內 |

### 2.2 三個 Task 之關鍵座標（詳細內容一律回讀 TODO 該 Task 全文）

| Task | TODO 行 | SPEC 行 | 主要落點 | 驗收命令（條目下限） |
|---|---|---|---|---|
| **1.11** L2 強制宣告 | `452` | `1687–1703` | `lookahead_registry.py` 新增 `requires_declaration(columns, timeframe) -> bool`；`frontend/src/app/`（宣告輸入＋勾選 UI） | `pytest tests/api -q -k lookahead_declaration` **≥2 條**；mutation 1 條 |
| **1.12** L3 禁進切分 | `476` | `1704–1750` | `pipeline.py` 新增 `run_event_study_only()`；`tables.py` `event_split_plan` 改 Optional ＋ `ci` unavailable 分支；`event_split.py`／`ic_feed.py` 拒絕分支 | `pytest tests/momentum/event_samples/ -q -k split_blocked` **≥6 條**（①②③③b③c④）；mutation **4 條** |
| **1.9** 宣告 UI 與 purge 下界 | `520` | `1751–1792` | `frontend/src/app/`（**逐 tf** 宣告區塊）；`case_import_service.py` 寫入 derived 欄；呼叫 `resolve_lookahead_bars()` | `pytest tests/api -q -k gap3_horizon_declaration` **≥5 條**（①②③④⑤⑥）；mutation **2 條** |

### 2.3 B3 之陷阱（TODO／SPEC 已明列，逐條抄在這裡免得漏）

1. **1.11**：🔴 **不得**因為「其他欄都能解析」就取它們的 **max** 當全批深度。只處理「解析不出深度」的情形。
   未填宣告即送出 ⇒ fail-closed，**落檔數 `== 0`**。
2. **1.12**：
   - 🔴 **不得**以空的假 `split_plan`（`clusters` 為空 DataFrame）冒充「未執行切分」——這是 codex 具名之**假綠形態**，
     且 SPEC ③c 明訂該輸入須 **raise**，不得靜默當 `None` 走過去。
   - 🔴 `event_split_plan is None` 時 **`ci` 一律標 `unavailable`，不得計算**。
   - 🔴 驗收①是「斷言 `split_events` **未被呼叫**」，**不是**只回警告字串。
   - 🔴 reason 字面**不得硬寫進程式**：驗收④含
     `grep -rc 'split_blocked_unverifiable_lookahead' api/ frontend/src/ momentum/ --include=*.py --include=*.ts` 之**硬編碼字面數 `== 0`**。
     字面唯一住 `event_import_contract.json` 之 `capability_unavailable_reasons`（B1 已登記）。
   - 🔴 **不得**與 Phase 6 止血閘合併為同一回應（合併後使用者無法分辨「洩漏不可證」與「特徵數過大」）。
   - 🔴 本 Task **不再自寫該清單之計數**（R8 已移除）——增量由 Task 1.1 驗收④之差集統一驗證。
3. **1.9**：
   - 🔴 預設取**檔內最大可用 horizon**（有 `future_1..12` ⇒ 預設 **12**）；**不得**給小於檔內最大 horizon 的預設值。
   - 🔴 **逐列**取該列自己的 `timeframe`（批內可有多 TF，「該批所屬 tf」無唯一值）。
   - 🔴 **UI 逐 tf 收集**：多 TF 時逐 tf 各一個輸入框；以單一輸入框套用全部 tf ⇒ **fail-closed**。
   - 🔴 **不得**以「檔內有哪些 `future_N` 欄」**推斷**實際用到第幾根（D-7：偵測不可能）。
   - 🔴 CSV 路徑「可調低但須勾選聲明」 vs 系統內篩選路徑「鎖定不可調低」是**兩條路徑之不同規則**
     ⇒ 實作須**以批次來源分派**；統一為寬鬆版即 fail-open，統一為嚴格版則 CSV 無法上傳。
   - 🔴 驗收⑤是**深度公式一致性**：兩條路徑須呼叫**同一 exported 函式** `depth_by_timeframe()`，非各自實作。
   - 欄位接受**任意正整數**（不限 1..12）；宣告 20 須被接受。

### 2.4 D-002 中與 B3 相關的一條

- **A-004 前端下界值來源**：`lookaheadLowerBound` 現恆為 `null`。`blocked-by` Task 2.1（B5）與 Task 1.3（B2）。
  **B2 已建好傳輸點**（`/search/task/{id}/result` 之兩鍵），但**接線仍留到 B5**（D-002:71,76）。
  ⇒ **B3 不處理這條**；1.9 走的是 CSV 匯入路徑之宣告，與前端下界鎖定是兩件事。

### 2.5 之後的批次（不在本批，僅供排序）

| 批 | Task | 依賴 |
|---|---|---|
| B4 匯入前端 | 1.5、1.6、1.7 | B2 |
| B5 匯出前篩選 | Phase 2 全部（扣除已於 B1 完成之 2.1b） | B1 |
| B6 刪除 | Phase 3 全部 | 無 |
| B7 匯出端報酬欄 | Phase 4 全部（4.2 之 S-9 已於 B1 完成） | B1、Task 2.1b |
| B8 訊息與表頭 | Phase 5 全部 | Task 5.0 |
| B9 IC 止血閘 | Phase 6 全部 | Task 6.0 |
| B10 全棧接線 | Phase 7 全部 | B1–B9 |

---

## §3 派工管線（**大任務**，不得跳步）

命中高風險 (a) 數值/資料品質 ＋ (b) 跨模組 ⇒ **大任務**。SPEC／TODO 皆已凍結、已過 adversarial
⇒ **實作階段之管線為**：

1. **實作＝Claude 主委自任**（`docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行；
   機器版 SoT＝`scripts/governance_roles.json`：`implementer=claude`、`reviewers=[codex,composer,grok]`）。
   🔴 **派工前必先重讀該行＋該 JSON**——選層是動態的，以使用者當下指示為準。
2. **每批收尾必派 code review**：三家全員，**實作者不自審**。
3. **開門**：`bash scripts/gate.sh dispatch --task-id … --risk … --intent … --facts-asked … --review-role … --template …`
   🔴 **`--task-id` 必須是 session 名之全大寫形式**（B2 第一次派工就被這條擋下：
   session `20260825-gap3ux-b3-review-r1` ⇒ task-id `20260825-GAP3UX-B3-REVIEW-R1`）。
4. **派工指令**（B2 實測可用，逐字照抄改 session 名即可）：
   ```bash
   bash scripts/committee_run.sh --session <session> <brief> <out-prefix> codex,composer,grok \
     -- --intent "…" --risk low --facts-asked "…" --review-role "reviewer（…）" \
     --template "n/a: 用 brief" --task-id "<SESSION 大寫>"
   ```
   丟背景跑；三家平行，B2 之 R1 約 30 分鐘、R2 約 10 分鐘。
5. **收集**：`bash scripts/reconcile_build.sh <session> --mode review <三個 -family.md>`
   → 手填 `synth.md` 之「群集／處置」→
   `bash scripts/reconcile_cluster_attribution_check.sh <synth.md>`（rc=0）→
   🔴 `bash scripts/completeness_check.sh --lock <session>/sources.lock`
   （**只給 lock 路徑，不得再帶 synth.md**——多一個參數就 fail）。
6. **清債**：`bash scripts/debt_clear.sh --round-id <id> --session <name> --lock <sources.lock>`。
   🔴 **債未清會擋掉下一輪派工**（B2 R2 派工時就被擋，正確）。
7. **前後**：`bash scripts/agent_preflight.sh` → 派工 → `bash scripts/agent_postflight.sh`，PASS 才驗收。
8. **兩輪斷路器**：任何問題自己弄 ≤2 輪仍失敗 ⇒ 立即開委員會，禁 solo 硬幹。

**B1／B2 之實績供校準**：
- B1：code review 五輪，findings **3 → 2 → 10 → 7 → 0**；最嚴重等級全程 0。
- B2：code review **兩輪**，findings **2 → 1**（皆 codex 提出，composer／grok 兩輪皆 0）；**P0／P1 全程 0**。
  R2 由**原提出方 codex** 逐字重跑 R1 兩個反例確認閉合（章程 §B8），三家一致判可進 B3，故**未派 R3**。

---

## §4 「完成」的判準（不得放寬）

一個 Task 標 ✅ 的條件：
1. 該 Task「驗證」欄之命令**全部 rc=0**，且條目數 ≥ TODO 所列下限；
2. **該 Task 之 mutation 已實跑**——故意改壞 ⇒ 對應斷言**轉紅**；還原 ⇒ 轉綠；
3. **receipt 路徑寫進 commit message**（`VERIFY:<path>`，冒號後不得有空格）。

🔴 **只有測試綠、沒有 mutation receipt ⇒ 仍是 🔧，不是 ✅。**
🔴 **mutation 判準＝轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。

**批次間 Gate**：上一批全部 mutation 轉紅並還原轉綠、receipt 入 commit，才可開下一批。

**每批收尾固定動作**：更新 `白話說明/GAP-3施工看板.md`（每完成一個 Task 改一列、更新「一眼看完」三個數字）
＋ `白話說明/GAP-3施工進度.md`（歷史敘事）＋ `docs/ROADMAP.md` ＋ `HANDOFF.md`
＋ commit ＋ **背景 push**（使用者在外看進度）。

### 4.1 怎麼寫 mutation runner（已隔離，可平行）

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from mutation_worktree import IsolatedWorktree, venv_python   # noqa: E402

with IsolatedWorktree(prefix="b3mut_") as wt:
    ...   # 所有改檔與 pytest 都在 wt 底下；主 repo 一個位元組都不動
```

- **現成範本（強烈建議直接複製改）**：`handoffs/gap3ux_b2_mutations.py`（14 條，含 pytest 與 vitest 兩種 selector、
  `--record` 模式、預期集合外置於 `handoffs/gap3ux_b2_expected.json`）。
  另有 `handoffs/gap3ux_b1_mutations.py`（32 條）。
- **工作流**：先 `--record` 跑一次取得實際紅集合 → **逐條人工對證語意**（不是抄輸出了事）→
  寫進 `<epic>_expected.json`（含 `_<id>_why` 說明）→ 不帶 `--record` 跑正式 receipt。
- 官方單條 CLI：`bash scripts/verify_mutation.sh <檔> <原字串> <變異字串> <pytest目標>`。
- 🔴 `<檔>` 須為 **repo 相對路徑且不含 `..`**，否則 rc=2 拒收。
- ⚠️ `handoffs/*.py` 與 `handoffs/*.json` 由 **`.git/info/exclude:21`（本機檔，非 `.gitignore`）** 排除
  ⇒ **runner 本身不入版控，換機器就沒有**；入版控的只有 `scripts/mutation_worktree.py`、
  官方 CLI、與 `handoffs/run_receipts/*.json`。

### 4.2 🔴 mutation 抓假綠之三個實例（B2 實際發生，B3 照著防）

1. **比對對象錯層**：Task 1.8 用**原始列**比對，把「`label_return_mode` 預設值未寫出」誤判成異質
   ⇒ 改比對**正規化後**的列。
2. **golden 生成順序**：斷言寫在寫檔**前** ⇒ 後端序列化被改壞時 golden 不重生、前端**假綠**。
   `1.3-M1b` 錄到**空紅集合**才抓出來 ⇒ 改成**先寫檔再斷言**。
3. **測到 fixture 而非生產接線**：新的執行期斷言直接呼叫工廠，但該檔 autouse fixture 已
   `monkeypatch` 掉單例 ⇒ 驗到的是 fixture 注入物件。`1.2-M4` 錄到**空紅集合**才抓出來
   ⇒ 測試內先把單例清成 `None`，逼工廠真的走建構路徑。

**共同形狀＝「錄到空紅集合」就是假綠的信號**。`--record` 出現 `紅=[]` 一律當作
「這條測試沒有在測它宣稱在測的東西」，先查根因再往下走。

---

## §5 未辦事項（開工前／收 epic 前要處理）

| # | 事項 | 何時 | 狀態 |
|---|---|---|---|
| 1 | D-001／D-002 委員戳記 | — | ✅ 已完成（`81cbe7ab`／`51f1a65e`，三家 APPROVED） |
| 2 | 動過 `scripts/` ⇒ 收 epic 前跑 `gov_check.sh --no-probe`（丟背景） | 收 epic 前 | ✅ 2026-08-25 已跑；**B2 未動 `scripts/`**。**若 B3 動了 `scripts/` 需重跑** |
| 3 | **延伸檔 D-003**：更正 TODO Task 1.3「修改檔案」行之 `api/routes/case.py` 字面（三家判 doc drift） | 收 epic 前 | ⬜ **不擋 B3** |
| 4 | **GAP-3 B5 之 UAT B 段簽字**仍在使用者手上（`docs/GAP3_UAT_CHECKLIST.md`） | 使用者 | ⬜ **未簽字不收案** |

---

## §6 地雷（本 epic 專屬，逐條是實際踩過的）

### 6.1 🔴 「比對範圍過寬」——主委在本 epic 犯了**六次**，形狀完全相同

| # | 形態 | 後果 |
|---|---|---|
| 1 | Phase Gate 之測試層標籤與 Task 欄位**同字面** | 機械閘分不出來 |
| 2 | 以**行號**注入修補，行號取自修補**前**之掃描輸出 | 三處落到**錯的 Task** |
| 3 | 判斷 Task 有無 mutation 時掃**整個區塊** | 被區塊尾端別人的字樣騙過（假跳過） |
| 4 | 同步斷言只驗**子字串存在**，散文卻宣稱「參數名序列逐字相等」 | **假綠**，改參數名照樣過 |
| 5 | 驗 gitignore 時問**目錄** | `.gitignore` 之 `*.h5` 沒被看見 ⇒ 隔離副本缺 fixture、全紅 |
| 6 | **（B2 新增）** 驗「兩件事不共用序列化路徑」時掃**整段原始碼文字** | 自己 docstring 裡的 `rule_digest` 三字讓斷言誤紅 ⇒ 改用 AST 只看**實際呼叫了什麼** |

**共同形狀＝拿比目標更大的範圍去比對，然後把命中當成目標命中。**
🔴 **對策（照做）**：①錨點落在**真正要判斷的那個東西**上——不是它的段落、不是行號、不是附近的字
②**一律字面錨點，禁行號** ③檢查寫完要用**已知會紅的輸入**試一次，只看綠不算驗過。

### 6.2 🔴 **不要用原始碼形狀證明執行期性質**（B1 R3 → B2 R1 → B2 R2，同一病三度復發）

- **B1 R3**：用原始碼形狀證明「阻擋早於網路動作」⇒ 修法是**改設計讓它變成結構保證**
  （整段匯出包進 `withHorizonLowerBoundGuard(…, {proceed})`）。
- **B2 R1**（`CODEX-R1-P2-02`）：V-3 之 AST oracle **只比對 attribute 名稱** ⇒ 升級為「`def import_records` 恰一個」。
- **B2 R2**（`CODEX-R2-P2-01`）：上一條**仍可繞**——保留原 `def`，另以
  `import_records = copied_fn` 綁到 subclass 並讓工廠回傳它。
  🔴 **此時主委沒有再補第三條形狀斷言**，改採**執行期**錨點：
  斷言 `get_event_import_service()` 回來那個物件之 `import_records`
  **就是** `EventImportService.import_records` 那一個 function object
  ⇒ assignment／`setattr`／subclass／factory-return 四類繞法一次全關，且不必枚舉。

**B3 之高風險面**：1.12 驗收①「斷言 `split_events` **未被呼叫**」——
這正是同一類問題。**請直接用執行期探針**（monkeypatch／spy 計數 `== 0`），
**不要**用「掃 `run_event_study_only()` 的原始碼裡沒有 `split_events` 字樣」那種形狀斷言。

### 6.3 產出端閘會擋你，而且多半擋對了

- `doc_format_precheck.sh`：驗證欄須**逐行**含可證偽 token（`pytest`／`==`／數字／`.py`…）。
- commit message：`VERIFY:<path>` **冒號後不能有空格**，且該檔須含 `CLOSED`／`APPROVED` 等閉合判詞
  （🔴 由 runner 直接寫 `closure` 欄，**不要事後手補**）。
- 🔴 **`Governance-Scope: out-of-epic <理由>` trailer**：staged 含 epic scope 外路徑時**必加**，
  且**必須在 commit 訊息之最後一段**（git 只解析最末段；與 `Co-Authored-By` 同段即可）。
  B1／B2 三個 commit 都加了，可直接複製措辭。
- 計數字面稽核：說明文字裡的「一支」「一筆」也會被當計數字面 ⇒ 改措辭。
- 白話狀態檔（`README.md`／`接下來要做什麼.md`）**禁純檔尾追加**，須改寫現況段。
- `plain_docs_sync_check.sh`：改過 `scripts/`／`docs/GOV*`／`tests/governance/` 才會要求同步治理白話檔；
  **B2 未動這些，故未觸發**。
- 🔴 **R3 解耦閘掛在 `PostToolUse`**：api 層直接 `from momentum.Analysis...import` 會**當場被擋**。
  改走 `EventSamplePipeline` 之 `@staticmethod` 出口（見 §0 出口清單）。

### 6.4 工具與環境

- **本機 bash 3.2.57** ⇒ **無 `declare -A`**；`sed` 為 BSD ⇒ 一律用 `sed -E`。
- 🔴 **絕不寫 `cd <專案路徑>` 前綴**——會讓每個指令走權限分類器（2.3s 起跳，~7% 機率變 600s）。
  B2 session 因 `cd frontend && npx …` 觸發多次 10–19 秒卡頓。
  **前端指令改用** `npm --prefix frontend test` ／ `npm --prefix frontend run build`。
- 瑣事別用 `python3 -c`；改檔一律用 Edit／Write 工具。
- `pytest tests/api tests/momentum/event_samples` 全量約 **6.5 分鐘** ⇒ 丟背景。
- `pytest tests/governance` 與 `govb1_final_gate.sh` 全跑皆**十分鐘級** ⇒ 一律丟背景。
- 委員會清 `/tmp` ⇒ 自己導到 `/tmp/x.log` 的檔可能被刪；重要輸出看 harness task output 檔。
- `handoffs/` **未入版控**（勿清）。
- 跑完測試須 `bash scripts/restore_golden_inventory.sh` 還原 golden inventory 副作用。

### 6.5 🔴 治理現況（2026-08-25 實測，**皆既有債，不要以為是自己弄的**）

| 檢查 | 結果 | 歸屬證據 |
|---|---|---|
| `gov_check.sh --no-probe` 段 4 **G-7 scope 淨差** | FAIL，**383 條**「未宣告即修改」 | 於 `HEAD~2` 隔離 worktree 跑同一條閘**亦 FAIL 且路徑集合逐一相同** |
| `pytest tests/governance -q` | **1743 passed / 6 failed** | 於 `HEAD~3` 隔離 worktree 實跑同這 6 條，**同樣 6 failed** |
| `pytest tests/api tests/momentum/event_samples` | **855 passed / 3 failed / 3 errors** | 以 `git stash` 實跑證實改動前後**逐字相同**；名單見下 |

**那 6 條（3 failed + 3 errors）之名單**（B3 若看到同樣這幾條，**不是你弄的**）：
`test_batch_alias.py::test_patch_batch_alias_deleting_returns_409`、
`test_progress_rss_fields.py::test_parity_batch_rest_worker_rss_and_schema_version`、
`test_progress_rss_fields.py::test_parity_concurrent_gt_one_no_fake_stage`、
`test_feature_export.py::test_cgsa_csv_date_subset_uses_sidecar_not_full_kline_cache`、
`test_feature_export.py::test_cgsa_csv_legacy_without_row_index_falls_back_to_integer_on_full_kline_mismatch`、
`test_run_lifecycle_api.py::test_resume_batch_keeps_legacy_completed_item`。
（其中 `test_progress_rss_fields` 兩條**只在全量跑時紅**，單獨跑綠＝`R-B1-1` 之順序污染。）

- 🔴 **連帶效果**：`gov_check` 段 4 FAIL 後**不再往下跑第 5／6 段** ⇒ 全套 pytest 從未經由 gov_check 執行。
- 兩條治理債已登記為 `R-GOV7-1`／`R-GOV7-2`，三值理由 `user-ruling`，**不排工**。

---

## §7 🔴 不要碰的東西

### 7.1 治理（使用者 2026-08-24 定死）

逐字：「當初就是發現你做治理是無解才不做」「你這樣岔題去問委員，永遠沒完沒了」。
⇒ **遇治理工具壞掉：繞過並具名記錄，不修、不開票。要動須使用者明示。**
⇒ **落地出錯就抄仔細**，不要「做一支工具來量自己」。
⇒ **治理／工具問題不得寫進派工單**，那是迴圈的燃料。

🔴 **唯一已獲明示授權之例外（2026-08-25，已完成）**：mutation 併發隔離
`scripts/mutation_worktree.py` ＋ `scripts/verify_mutation.sh`。用法見 §4.1。

### 7.2 已具名封存之殘留（**不排工、不另立票**）

- **SPEC 末節 F-1..F-4**：同輪重派死鎖／補丁包檔名碰撞／編排草圖含 illustrative 佔位／
  `gap3ux_apply_patch.py` 包側 VERIFY 缺陷。
- **TODO（R3 reconcile）四條**：前端 directory-only 路徑 10 處／Task 5.0 驗證 defer SPEC／
  五 Task（1.10／3.3／4.3／7.3／7.5）之 mutation 全文 defer SPEC／B1 須並讀 FROZEN SPEC。

### 7.3 具名殘留全文（**本節為全文；`HANDOFF.md` 只指回這裡**）

| 代號 | 內容 | 三值理由 | owner／觸發 |
|---|---|---|---|
| `R-GOV7-1` | G-7 scope 淨差長期紅（383 條）。判準要求 trailer 落在**該 commit 自身** ⇒ 前向修不掉 | `user-ruling` | 主委 |
| `R-GOV7-2` | 治理 pytest 6 條長期紅；其中 2 條之斷言比 2026-08-14 之使用者裁定舊 | `user-ruling` | 主委 |
| `R-B1-1` | 全量跑之測試順序污染（`test_progress_rss_fields` 兩條）。歸因**未實跑證明**（需以 stashed 樹全量跑一次） | `needs-research` | 主委 |
| `R-A005-1` | `lookahead_registry` 之 `_PRODUCER_SEMANTICS` 表為人工稽核非執跑探針；與 producer 漂移時本閘看不見 | `needs-research` | 主委；**觸發＝下次動到 `CaseSearchEngine` 未來欄計算段時一併做** |
| `D-002 A-004` | 前端下界**值來源**未接上（`lookaheadLowerBound` 恆 `null`） | `blocked-by` Task 2.1（B5） | 主委；B5 收尾接線 |
| `D-001/D-002 provenance` | `gate.sh register-output` 只收 `handoffs/` 或 `stampable_artifacts.txt` 明列者 ⇒ 對 `docs/*.D-00N.md` 跑 `reconcile_stamps_check.sh` 會報 provenance pending（**非戳記造假**） | `user-ruling` | 主委 |
| **`R-B2-1`** | **秒級 t0 之 `event_id` 摩擦**：使用者上傳秒級 `t0` 的 CSV 時，`event_id` 仍須寫 **ms 版**（否則 fail-closed 拒收並列出期望值）。三家一致判**屬 Task 1.5（前端對映 UI 應在單位偵測後預填正規化 ID）** | `blocked-by` Task 1.5（B4） | 主委；B4 一併做 |
| **`R-B2-2`** | **執行期 oracle 之 factory-body 繞法**：新斷言綁 `get_event_import_service()` 之回傳；若日後另立第二個工廠且 route 改呼叫它，本閘看不見（route 之工廠名斷言可再擋一層，但那又是形狀） | `needs-research`（正解為 route 層之執行期 wiring 探針） | 主委；屬 **B10 全棧接線** |
| **純 JS 手刻 sha256** | 不經 `crypto.subtle`／`node:crypto` 入口之手刻實作，前端 ④(a) 之封閉枚舉看不見 | `needs-research` | 主委 |

---

## §8 檔案地圖（B3 會碰到的）

| 用途 | 路徑 |
|---|---|
| 事件樣本模組（新邏輯放這） | `momentum/Analysis/event_samples/`：`pipeline.py`（**1.12 加 `run_event_study_only()`**）／`tables.py`（**1.12 改 `event_split_plan` 為 Optional**）／`event_split.py`（**1.12 拒絕分支**）／`ic_feed.py`（**1.12 拒絕分支**）／`lookahead_registry.py`（**1.11 加 `requires_declaration()`**）／`lookahead_depth.py`（**1.9 呼叫，勿改**）／`import_contract.py`／`canonical_serialize.py`／`alignment.py`／`event_split.py`／`dedupe.py`／`types.py` |
| 契約（欄位／枚舉／reason 之 SoT） | `momentum/Analysis/contracts/event_import_contract.json`（`capability_unavailable_reasons` 已含 `split_blocked_unverifiable_lookahead`）、`future_column_lookahead.json`、`ic_report_contract.json` |
| case 端點 | `api/routes/case.py`：`import_events_file` `:139`／`import_events_json` `:180`／`import_events_csv`（B2 新增，緊鄰 `:180`）／`analyze_event_import`（**1.12 之消費端**） |
| 匯入服務 | `api/services/case_import_service.py::EventImportService`：`parse_upload` `:654`／`csv_records_from_mapping`／`import_records`／`analyze` `:894`（**1.9 寫 derived 欄之落點**） |
| 搜尋結果端點（B2 之 digest 承載點） | `api/routes/case_search.py::get_task_result` ＋ `_attach_canonical_source()` |
| 前端 | `frontend/src/app/`（**1.11／1.9 之宣告 UI**）；`frontend/src/lib/lookaheadDepthLock.ts`（B1）／`eventId.ts`／`ruleDigest.ts`／`eventExport.ts`（B2）；`frontend/src/test/hashEntrySpy.ts`（vitest setupFiles） |
| 搜尋引擎（future 欄之來源） | `momentum/DataExtraction/case_search_engine.py`（`periods_{H}h` `:1385-1387`；⚠️ `periods_72h` 亦用於**過去 3 天 lookback** `:1028-1046`，同名不同義） |
| mutation receipt | `handoffs/run_receipts/gap3ux-b1-all-mutations.receipt.json`（32 條）／`gap3ux-b2-all-mutations.receipt.json`（14 條） |
| mutation runner 範本（**未入版控**） | `handoffs/gap3ux_b2_mutations.py` ＋ `handoffs/gap3ux_b2_expected.json` |
| reconcile 收斂檔 | `handoffs/reconcile/20260824-gap3uxtodo-x-review-r{1,2,3}/synth.md`（TODO 三輪）／`20260825-gap3ux-b2-review-r{1,2}/synth.md`（B2 兩輪） |
| 過程與教訓（給使用者） | `白話說明/GAP-3施工看板.md`（進度）、`白話說明/GAP-3施工進度.md`（歷史）、`白話說明/治理進度日誌.md`、`白話說明/流程摩擦記錄.md` |
