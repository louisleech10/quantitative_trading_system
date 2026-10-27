"""ICPERF Phase 0（docs/ICPERF_SPEC.md §G、Task 0.1／0.2）：以現行碼凍結改前輸出、寫出檔捕獲與比對、規模盤點之路徑清冊。

空殼（施工前）：全部入口 `raise NotImplementedError`；具名驗收見 `tests/momentum/Analysis/test_icperf_gate.py`。

用法（重型，列 `scripts/heavy_commands.json` 之 `self_watched`：須背景、先寫估時收據〔coverage_path_ids＝ICPERF-BUDGET-1／-2〕，
子行程一律經本檔 `run_watched` 以共用監看啟動）：
  venv/bin/python scripts/icperf_freeze_baseline.py freeze [--out tests/_golden/icperf/pre_change.json]
  venv/bin/python scripts/icperf_freeze_baseline.py repro --cols 500
  venv/bin/python scripts/icperf_freeze_baseline.py inventory --out handoffs/run_receipts/<日期>-icperf-path-inventory.json
  venv/bin/python scripts/icperf_freeze_baseline.py measure --inventory <清冊> --out handoffs/run_receipts/<日期>-icperf-scale-before.json

凍結檔 `tests/_golden/icperf/pre_change.json` 之形狀（§G）：
  {"schema": "icperf-pre-change/1", "code_state": {...}, "volatile": [<每次必異欄位之路徑，FACT-RECEIPT 寫入 SPEC>],
   "items": {
     "ic_report"|"deep_analysis"|"event_report"|"icfirst_post_ic": {
        "request": {...請求設定...}, "output_roots": [...],
        "response": {<欄位路徑>: <sha256>},            # 回應／回傳物件之全部欄位（flatten_fields）
        "files": {<path_key>: describe_file(...)},      # 快照差集之全部寫出檔
        "transient": [<path_key>...],                   # 審計記錄有而差集無變化（寫後刪除），記入不比
        "features": {<特徵>: {<欄位>: {"sha256", "nan_mask_sha256"}}},   # 第 (1)–(4) 項
        "selected": [<選欄通過之特徵>...],              # 第 (1)、(4) 項
        "pit_labels": {<特徵>: {"q", "q_insufficient", "skipped_all_nan", "label_sha256"|None, "label_nan_count"}}},
     "stage5_subset": {"seed": 20261027, "n_cols_requested": 2000, "stage_cols": <實際進第 5 段欄數>,
        "features": {...同上...}, "pit_labels": {...同上...}}}}

path_key 規則：位於 repo 根之下者＝repo 相對 POSIX 路徑；其餘（TMPDIR／HOME 隔離目錄）＝解析後之絕對路徑。

逐特徵欄位（"features"）之來源與命名：回應中 `feature_tables(item)` 所列之逐特徵表（JSON pointer 所指之 DataFrame，
index＝特徵名）；欄位名＝"<pointer>/<欄名>"；值摘要＝`value_digest(df.loc[[特徵], 欄].to_numpy())`（1 元素、原生 dtype）。

PIT 標籤（"pit_labels"）：照單調性之現行輸入定義（特徵與標籤同時非 NaN 之列壓縮、`_select_num_quantiles` 選 q、
q=3 退回）；`q`＝最終採用之 q；`q_insufficient`＝最終 q 小於請求 q（樣本數不足而降為 3，或 bin 數不足退回 3）；
`label_sha256`＝壓縮後之 PIT 標籤序列轉 float64 之原生位元組 sha256；`label_nan_count`＝其中 NaN 數。

施工前註記（ICPERF 施工清單審查 r10 群集 A）：本檔列 `scripts/heavy_commands.json` 之 `self_watched`，heavy_run_guard
以 AST 驗原始碼確有 `run_watched(...)` 呼叫；空殼只有定義、無呼叫 ⇒ 實跑時被擋屬施工前預期之 fail-closed。實作之
`run_watched` 須呼叫共用監看（`_watchdog.run_watched`）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
GOLDEN_PATH = REPO / "tests" / "_golden" / "icperf" / "pre_change.json"
CELL = "A_BTCUSDT_1h"
SEED = 20261027
SUBSET_COLS = 2000
REPRO_COLS = 500
SCALE_POINTS = (500, 1000, 2000)

#: §G (1)–(5)：A 格完整 IC 報告、2,000 欄子集第 5 段、A 格深度分析、A 格事件型 IC 報告、A 格 IC-first post-IC HDF5
G_ITEMS = ("ic_report", "stage5_subset", "deep_analysis", "event_report", "icfirst_post_ic")
#: 須含「回應全部欄位＋快照差集之全部寫出檔」之項（§G 凍結範圍：第 (1)、(3)、(4)、(5) 項）
OUTPUT_ITEMS = ("ic_report", "deep_analysis", "event_report", "icfirst_post_ic")

#: 寫出捕獲記錄之審計事件；本行程之 hook 與注入子行程之 sitecustomize 皆於呼叫當下讀本常數（mutation 探針改之）
AUDIT_EVENTS = ("open", "os.rename", "os.replace")
#: `open` 事件之 mode 含任一字元即視為寫入／附加／建立；`os.open` 依 flags（O_WRONLY／O_RDWR／O_CREAT／O_APPEND）判定
WRITE_MODE_CHARS = frozenset("wax+")
#: 子行程經此環境變數取得同一審計記錄檔
CAPTURE_LOG_ENV = "ICPERF_WRITE_AUDIT_LOG"
#: 快照排除之目錄名（任一層）：git、虛擬環境、位元組碼快取、測試選取工具狀態目錄
SNAPSHOT_EXCLUDE_DIRS = (".git", "venv", "__pycache__", ".testsel")
#: numba 快取檔副檔名（任一目錄；另含 NUMBA_CACHE_DIR 所指目錄）
NUMBA_CACHE_SUFFIXES = (".nbi", ".nbc")

INVENTORY_GLOB = "handoffs/run_receipts/*-icperf-path-inventory.json"
SCALE_BEFORE_GLOB = "handoffs/run_receipts/*-icperf-scale-before.json"

_STUB = "ICPERF Phase 0（docs/ICPERF_SPEC.md §G、Task 0.1／0.2）尚未施工"


class FreezeError(RuntimeError):
    """凍結／比對之 fail-closed 錯誤：審計記錄之路徑或輸出根落在快照範圍外、收據份數不為一等；訊息須含具名路徑。"""


# ── §G (a)(b)(c) 寫出捕獲 ─────────────────────────────────────────────────────────────────────────────


def install_write_audit(log_path: Path) -> None:
    """於本行程以 `sys.addaudithook` 記錄 `AUDIT_EVENTS` 之寫入事件至 `log_path`（JSON lines）。

    每列 {"event": "open"|"os.rename"|"os.replace", "path": <解析後絕對路徑；rename／replace 為目的地>,
    "src": <rename／replace 之來源或 None>, "mode": <open 之 mode 或 None>, "flags": <os.open 之 flags 或 None>,
    "pid": <行程 id>}；只記寫入／附加／建立模式之開檔（見 `WRITE_MODE_CHARS`），唯讀開檔不記；記錄檔本身之寫入不記。
    hook 只裝一次，重複呼叫改切換記錄檔。"""
    raise NotImplementedError(_STUB)


def capture_sitecustomize_source(log_path: Path) -> str:
    """回注入子行程之 sitecustomize 原始碼：讀 `CAPTURE_LOG_ENV`（缺則用 `log_path`）安裝與 `install_write_audit` 相同之
    hook（事件集合取呼叫當下之 `AUDIT_EVENTS`），並串接 sys.path 上原有之 sitecustomize（含共用監看之堆疊傾印注入）。"""
    raise NotImplementedError(_STUB)


def isolated_env(base_env: Mapping[str, str], iso_root: Path) -> Dict[str, str]:
    """回 `base_env` 之副本，`TMPDIR`＝`iso_root/tmp`、`HOME`＝`iso_root/home`（皆建立、互異）；其餘鍵原樣保留。"""
    raise NotImplementedError(_STUB)


def capture_env(base_env: Mapping[str, str], *, log_path: Path, iso_root: Path, site_dir: Path) -> Dict[str, str]:
    """子行程環境＝`isolated_env` ＋ `CAPTURE_LOG_ENV`＝`log_path` ＋ `site_dir`（寫入 `capture_sitecustomize_source`）
    前置 `PYTHONPATH`；孫行程繼承同一環境，故寫入進同一記錄。"""
    raise NotImplementedError(_STUB)


def read_write_log(log_path: Path) -> List[Dict[str, Any]]:
    """讀審計記錄（`install_write_audit` 之列格式）；檔不存在 ⇒ 空清單；列不可解析 ⇒ FreezeError。"""
    raise NotImplementedError(_STUB)


def snapshot_files(roots: Sequence[Path], *, repo_root: Path) -> Dict[str, str]:
    """對 `roots` 下全部檔案取 {path_key: 位元組 sha256}；排除任一層名為 `SNAPSHOT_EXCLUDE_DIRS` 之目錄、副檔名為
    `NUMBA_CACHE_SUFFIXES` 之檔與呼叫當下環境變數 `NUMBA_CACHE_DIR` 所指目錄之整棵（不論副檔名；未設則不排除該目錄）；
    不跟隨指向 roots 外之 symlink。"""
    raise NotImplementedError(_STUB)


def snapshot_diff(before: Mapping[str, str], after: Mapping[str, str]) -> Dict[str, List[str]]:
    """回 {"added": [...], "changed": [...], "removed": [...]}（皆排序之 path_key）。"""
    raise NotImplementedError(_STUB)


def hdf5_digest(path: Path) -> Dict[str, Dict[str, Any]]:
    """HDF5 逐物件摘要：{<物件名，如 "/" "/g" "/g/v">: {"kind": "group"|"dataset", "attrs": {<屬性名>: <sha256>},
    資料集另 "dtype", "shape", "sha256"（原生 dtype 位元組）}}。"""
    raise NotImplementedError(_STUB)


def flatten_fields(obj: Any) -> Dict[str, str]:
    """把回應物件攤平為 {<欄位路徑>: <sha256>}。路徑規則（boundary_01 之獨立 oracle 依此重算鍵集合）：根＝""；
    dict 每鍵接 "/<鍵>"（鍵以 str() 轉、`~`→`~0`、`/`→`~1`）、list／tuple 每元素接 "/<索引>"，遞迴；
    DataFrame ⇒ "<路徑>#index" 與每欄 "<路徑>/<欄名>#values"、"<路徑>/<欄名>#nan_mask"；Series／ndarray ⇒
    "<路徑>#values"、"<路徑>#nan_mask"（Series 另 "<路徑>#index"）；其餘（純量、None）⇒ "<路徑>" 以正準 JSON 位元組。
    值取原生 dtype 位元組之 sha256。"""
    raise NotImplementedError(_STUB)


def describe_file(path: Path) -> Dict[str, Any]:
    """單一寫出檔之摘要：{"sha256": <位元組>, "hdf5": hdf5_digest(...)|None, "fields": flatten_fields(<JSON 內容>)|None}；
    HDF5 以檔頭簽章判定，JSON 以副檔名 .json 判定。"""
    raise NotImplementedError(_STUB)


def check_scope(write_log: Sequence[Mapping[str, Any]], output_roots: Sequence[Path],
                snapshot_roots: Sequence[Path]) -> None:
    """§G (c) fail-closed：審計記錄任一路徑（含 rename／replace 目的地）或任一輸出根不在 `snapshot_roots` 之下 ⇒
    FreezeError（訊息列出該路徑之解析後絕對路徑）。不得把範圍外之已記路徑補入快照範圍而視為成功收集。"""
    raise NotImplementedError(_STUB)


def collect_written_files(write_log: Sequence[Mapping[str, Any]], before: Mapping[str, str], after: Mapping[str, str],
                          *, repo_root: Path, snapshot_roots: Sequence[Path],
                          output_roots: Sequence[Path]) -> Dict[str, Any]:
    """先 `check_scope`；回 {"files": {path_key: describe_file(...)}（差集之新增與變更檔）, "transient": [path_key...]
    （審計記錄有而差集無變化者，記入不比）}。"""
    raise NotImplementedError(_STUB)


def run_watched(cmd: Sequence[str], *, log_path: Path, env: Mapping[str, str], cwd: Path) -> Dict[str, Any]:
    """以共用監看（`handoffs/run_receipts/numview_probes/_watchdog.py` 之 run_watched，判準取 NUMVIEW 判準檔
    `cell_rules.watchdog`；不設時間上限）啟動子行程；回 {"rc", "status", "log_path"}；卡死 ⇒ FreezeError 附診斷路徑。"""
    raise NotImplementedError(_STUB)


def capture_run(cmd: Sequence[str], *, repo_root: Path, iso_root: Path, output_roots: Sequence[Path],
                work_dir: Path) -> Dict[str, Any]:
    """一次請求之寫出捕獲：快照（repo_root＋iso_root）→ `run_watched`（`capture_env`，cwd＝repo_root）→ 快照 →
    `collect_written_files`。回 {"rc", "files", "transient", "write_log"}；審計記錄與 sitecustomize 置於 `work_dir`
    （不在快照範圍內，不入記錄）。範圍外路徑（含經 os.replace／os.rename 落到範圍外之目的地）或輸出根 ⇒ FreezeError。"""
    raise NotImplementedError(_STUB)


# ── 比對（改後對凍結；Phase 1–5 收尾共用） ───────────────────────────────────────────────────────────────


def compared_paths(frozen_files: Mapping[str, Any], current_files: Mapping[str, Any]) -> Set[str]:
    """比對之檔集合＝兩側 path_key 之聯集（只在一側者即為多一檔／少一檔）。`compare_capture` 經本模組層函式取之。"""
    raise NotImplementedError(_STUB)


def compare_capture(frozen: Mapping[str, Any], current: Mapping[str, Any], *,
                    volatile: Sequence[str] = ()) -> List[str]:
    """比對一項之 "response" 與 "files"；回問題清單（空＝逐位元相同）。檔集合取 `compared_paths`：只在一側者、sha256
    不等者、HDF5 任一物件之 sha256／dtype／shape／屬性不等者皆列（訊息含 path_key 與物件／屬性名）。
    `volatile` 項之格式：`response:<欄位路徑>` 或 `file:<path_key>#<欄位路徑>`；只對所列路徑排除——該檔改以
    "fields" 逐欄位比（排除所列），未列欄位不等仍列為問題。"""
    raise NotImplementedError(_STUB)


def compare_golden(frozen: Mapping[str, Any], current: Mapping[str, Any]) -> List[str]:
    """§G 全部凍結項之逐位元比對（依 `frozen["volatile"]` 排除）；任一不等即列出項、特徵與欄位。"""
    raise NotImplementedError(_STUB)


# ── Task 0.1 凍結 ───────────────────────────────────────────────────────────────────────────────────────


def default_request(item: str, cell: str = CELL) -> Dict[str, Any]:
    """各路徑之預設請求設定（IC 頁預設、衰減關以外照預設；事件型取事件篩選模式預設；IC-first 取預設）；
    第 (4)、(5) 項之設定於凍結時以 FACT-RECEIPT 寫入 SPEC。"""
    raise NotImplementedError(_STUB)


def resolve_output_roots(item: str, request: Mapping[str, Any], repo_root: Path = REPO) -> List[Path]:
    """自請求設定與產品寫死之相對路徑解析該路徑之全部輸出根（如 `data_cache/features/`、`data_cache/reports/`）。"""
    raise NotImplementedError(_STUB)


def small_request(item: str, request: Mapping[str, Any], n_features: int) -> Dict[str, Any]:
    """同一請求（凍結檔所記之 `request`）限縮為前 n_features 個真實特徵（排序後之特徵名；IC 頁為 `feature_filter`，
    其餘路徑用其對應之選欄設定），其餘設定不變；供 boundary_01／02 之獨立 oracle 以小規模真實請求對照。"""
    raise NotImplementedError(_STUB)


def feature_tables(item: str) -> List[str]:
    """該項回應中逐特徵表之 JSON pointer 清單（index＝特徵名之 DataFrame，如 summary_table）；"features" 之來源。"""
    raise NotImplementedError(_STUB)


def selected_pointer(item: str) -> Optional[str]:
    """該項回應中選欄通過集合（特徵名清單）之 JSON pointer；無此概念之項 ⇒ None。"""
    raise NotImplementedError(_STUB)


def load_cell(cell: str = CELL) -> Tuple[Any, Any]:
    """讀真實資料格之 IC 讀入結果（第 0 段後）：回 (features: DataFrame, label: Series)；不存在 ⇒ FreezeError。"""
    raise NotImplementedError(_STUB)


def value_digest(values: Any) -> Dict[str, str]:
    """{"sha256": <原生 dtype 位元組>, "nan_mask_sha256": <NaN 遮罩位元組>}。"""
    raise NotImplementedError(_STUB)


def pit_label_digests(features: Any, label: Any, *, num_quantiles: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """以現行碼（單調性之輸入定義：特徵與標籤同時非 NaN 壓縮、逐欄選 q、q=3 退回）逐欄求 PIT 標籤序列；回
    {<特徵>: {"q", "q_insufficient", "skipped_all_nan", "label_sha256"|None, "label_nan_count"}}；全 NaN 欄照現行跳過
    （skipped_all_nan＝True、label_sha256＝None）。"""
    raise NotImplementedError(_STUB)


def stage5_subset_digests(n_cols: int, *, seed: int = SEED) -> Dict[str, Any]:
    """改前基準全特徵 run 交接 h5 之 n_cols 欄巢狀隨機子集（seed 同探針 `icperf_probes/prep.py`）以產品
    `create_ic_analyzer(...).analyze()` 跑第 5 段；回 {"stage_cols", "features": {<特徵>: {<欄位>: value_digest}},
    "pit_labels": {...}}；交接 h5 不存在 ⇒ FreezeError（不以其他 run 代替）。"""
    raise NotImplementedError(_STUB)


def freeze_item(item: str, *, request: Mapping[str, Any], repo_root: Path, work_root: Path) -> Dict[str, Any]:
    """凍結 §G 單一項：第 (1)、(3)、(4)、(5) 項經 `capture_run` 取回應全部欄位與寫出檔；第 (2) 項經
    `stage5_subset_digests(SUBSET_COLS)`。子行程把回傳物件原樣以 pickle 寫 `work_root/<item>/response.pkl`，隔離目錄
    ＝`work_root/<item>/iso`（審計記錄與 sitecustomize 亦置於 `work_root/<item>`，pickle 與記錄不在快照範圍）；回之記錄
    另含 "request"、"output_roots"（repo 相對 POSIX）。"""
    raise NotImplementedError(_STUB)


def freeze(out_path: Path = GOLDEN_PATH, *, repo_root: Path = REPO, work_root: Optional[Path] = None) -> Dict[str, Any]:
    """依序凍結 `G_ITEMS` 並寫 `out_path`；任一項 FreezeError ⇒ 不寫檔。"""
    raise NotImplementedError(_STUB)


# ── Task 0.2 路徑清冊與規模盤點 ─────────────────────────────────────────────────────────────────────────


def load_single_receipt(pattern: str, *, repo_root: Path = REPO) -> Dict[str, Any]:
    """`repo_root.glob(pattern)` 恰一份 ⇒ 回其 JSON；零份或多份 ⇒ FreezeError。"""
    raise NotImplementedError(_STUB)


def build_path_inventory(repo_root: Path = REPO) -> Dict[str, Any]:
    """讀碼列 Task 0.2 範圍內每一計算入口：{"entries": [{"id": "<模組>:<限定名>", "stage", "input_axes"
    （⊆ cols／rows／passed_cols）, "ic_page", "ic_first", "loop"（per_bar／per_column／per_group／none）, "measure",
    "no_measure_reason", "evidence": "<檔>:<行>"}]}。"""
    raise NotImplementedError(_STUB)


def measured_ids(scale_receipt: Mapping[str, Any]) -> Set[str]:
    """量測收據之入口 id 集合（`scale_receipt["entries"]` 之鍵）。"""
    raise NotImplementedError(_STUB)


def uncovered_entries(inventory: Mapping[str, Any], scale_receipt: Mapping[str, Any]) -> List[str]:
    """清冊中標需量測（measure＝True）之 id − `measured_ids`；排序回傳（空＝無漏量）。"""
    raise NotImplementedError(_STUB)


def evaluate_criteria(entry: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """判準①–⑤（SPEC Task 0.2 固定規則；①之門檻引 `scripts/scale_probe.py` 之 SUPERLINEAR_EXPONENT／MIN_R2）；
    回 {"1".."5": {"result": bool, "basis": str}}。"""
    raise NotImplementedError(_STUB)


def measure_inventory(inventory: Mapping[str, Any], *, scales: Sequence[int] = SCALE_POINTS,
                      out_path: Path) -> Dict[str, Any]:
    """以 `scripts/scale_probe.py` 量清冊每一需量測入口於 `scales` 之耗時與峰值 RSS（行程樹），寫 `out_path`：
    {"head": <量測時之 40 位提交雜湊>, "meter": {"tool", "rss_scope", "sample_interval_seconds"}, "chunk_cap": {"bytes", "basis"},
    "budget_seconds",
    "entries": {<清冊 id>: {"probe": {"cmd", "data", "config"}, "row_probe": {"cmd", "data", "config"}|None,
    "points": [{"input_cols", "stage_cols", "seconds", "peak_rss_bytes", "scale_probe_receipt"}],
    "row_points": [{"rows", "seconds", "peak_rss_bytes", "scale_probe_receipt"}], "fit": {"exponent", "r2"},
    "extrapolation_unreliable", "projected_seconds", "reduction", "two_point_exception": {"projected_2000_seconds"}|None,
    "complexity_analysis", "lower_bound_seconds_per_unit", "lower_bound_analysis", "criteria"}}}。
    入口 id 只取清冊 id；每一點之 seconds／peak_rss_bytes 逐欄抄自其 `scale_probe_receipt`（scale_probe 寫出之收據，
    該收據 points 中 scale＝input_cols〔列長點為 rows〕之點）；`probe`／`row_probe` 為交給 scale_probe 之量測命令
    （cmd 含清冊 id）與其 --data／--config，該收據之 identity.match 須與之逐欄相符（量測前先提交量測碼，`head` 即該提交）；同一收據之三點者 fit／extrapolation_unreliable 等於該收據。
    500／1000 兩點推估 2000 欄逾 10 分鐘之入口不量 2000 欄點，記 two_point_exception 與碼層複雜度分析。"""
    raise NotImplementedError(_STUB)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI：freeze／repro／inventory／measure（見模組說明）。"""
    raise NotImplementedError(_STUB)


if __name__ == "__main__":
    raise SystemExit(main())
