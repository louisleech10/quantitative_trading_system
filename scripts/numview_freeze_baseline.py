"""NUMVIEW 改前基準凍結（docs/NUMVIEW_SPEC.md §G、Task 0.5）。

於任何產品碼改動前之 HEAD 凍結 §G：
- G1 IC 頁第三步輸出：每個格 A 之 IC-first 選欄，以 `ApplyTransformsRequest` 預設請求，分別於每個現行可達之臂各跑
  `_apply_transforms_sync` 之同一轉換：`polars`（`FFACT_USE_POLARS=1`）、`pandas_optimized`（`=0`）、`pandas_legacy`
  （`=0`＋`FFACT_L65_OPTIMIZATION_PROFILE=legacy`）、`pandas_chunked`（`=0`＋`FFACT_L65_CHUNK_SIZE` 小於選欄數之合法
  正整數）；每份記 `last_post_ic_execution()` 所報實際臂，須等於標示臂，否則 rc≠0。可達條件依契約
  `post_ic_arm_reachability` 逐格判定；不可達之臂不凍結、收據記 `arm_unreachable`（臂名＋條件名＋實際選欄數）。
- G2 判準檔 `cell_rules.freeze_groups.G2` 之格之 L6.5 raw 於 `FFACT_USE_POLARS` 0／1 各一份；G3（`freeze_groups.G3`）依
  `G3_ARTIFACTS`：格 B 之 raw 與 processed、全特徵格 C 之 raw（C 以生產預設生成、不產 processed）。
- 值指紋一律經 `tests/feature_engineering/numview_helpers.py`（`fingerprints`／`frame_fingerprints`；格類屬
  `GROUP_GRANULARITY_KINDS`〔全特徵格 C〕者以 `group_fingerprints` 群組粒度，SPEC §G）。

啟動即呼叫 `handoffs/run_receipts/numview_probes/_estimate_gate.require("freeze_baseline", cells)`（在任何生成呼叫之前）；
格 A／B 逐格單行程串行；生成之 run 目錄保留至 Phase 1 結束（供 Task 1.1–1.3 讀取）。FeatureFactory 之連續性設定依判準檔
`cell_rules.continuity`（同估時器 `estimate.continuity_plan`／`window_gap_violations`）：來源全序列無缺口 ⇒ 生產設定
`validate_continuity=True`；有缺口（長歷史檔 12h 於生成窗外）⇒ False＋生成窗內零缺口判定，窗內缺口 ⇒ 該格 failed（data_gap）。
每格之生成一律於子行程入口 `_child` 內執行、main 以 `_watchdog.run_watched` 啟動之（AST 驗收 test_heavy_scripts_run_generation_children_under_watchdog；預設開、無旗標；`handoffs/run_receipts/numview_probes/_watchdog.py`，門檻＝判準檔
`cell_rules.watchdog`：log 停滯、牆鐘逾 3× 預期或固定上限；判準 v6 起 swap 增長只記錄、不終止）；卡住 ⇒ 終止、記 stalled、
停止後續格、rc≠0、不寫凍結檔。
格 C（判準 v4）只走 `generate_features`，不經 IC-first、不凍 G1，其 raw 屬 G3。Task 1.3 之 L2 兩臂 spy 掛於
凍結之生成（格 A_BTCUSDT_1h 兩個 FFACT_USE_POLARS 生成、格 B／C／A_BTCUSDT_12h 之預設生成），l2_arm_matrix 讀其紀錄、
不另生成（判準檔 run_coverage.l2_arm_matrix）。
輸出：`tests/_golden/numview/pre_change_fingerprints.json`；收據 `handoffs/run_receipts/<date>-numview-freeze-baseline.json`
（含 HEAD、`started_at`、格清單、每格耗時與峰值記憶體、函式庫版本、`arm_unreachable` 條目）。

用法：`venv/bin/python scripts/numview_freeze_baseline.py [--work-root DIR] [--fresh]`（已完成之格之結果檔沿用，`--fresh`
清除重凍）。每格之 run 目錄、sidecar（`numview_cell.json`）與 L2 擷取紀錄留在 `--work-root`（預設
`data_cache/numview_freeze_runs`，不入版控）。
"""

from __future__ import annotations

import argparse
import contextlib

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

REPO: Path = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.feature_engineering import numview_helpers as nh  # noqa: E402
from tests.feature_engineering import preprov_helpers as ph  # noqa: E402

#: 估時收據目錄（呼叫時讀模組屬性，傳給 `_estimate_gate.require(receipts_dir=)`；測試以 monkeypatch 改指）
RECEIPTS_DIR: Path = REPO / "handoffs" / "run_receipts"
PROBES_DIR: Path = REPO / "handoffs" / "run_receipts" / "numview_probes"
DEFAULT_WORK_ROOT: Path = REPO / "data_cache" / "numview_freeze_runs"
FREEZE_RECEIPT_NAME = "{date}-numview-freeze-baseline.json"
RUN_KIND = "freeze_baseline"
#: 每格工作目錄內之 sidecar（生成紀錄：run 位置、狀態、IC-first 選欄、L2 擷取紀錄）
SIDECAR = "numview_cell.json"
#: 子行程每格結果檔（續跑沿用）
RESULT_NAME = "result.json"
#: post-IC 臂之選擇子環境鍵（SPEC §G G1）
ARM_ENV_KEYS = ("FFACT_USE_POLARS", "FFACT_L65_OPTIMIZATION_PROFILE", "FFACT_L65_CHUNK_SIZE")
CHUNK_ENV = "FFACT_L65_CHUNK_SIZE"
G1_ARM_ENV: Dict[str, Dict[str, str]] = {
    "polars": {"FFACT_USE_POLARS": "1"},
    # chunk 未設時預設 2000（feature_preprocessor.py:837-842），選欄 > 2000 即走 chunked ⇒ optimized／legacy 以 chunk 關閉方可達
    "pandas_optimized": {"FFACT_USE_POLARS": "0", "FFACT_L65_CHUNK_SIZE": "0"},
    "pandas_legacy": {"FFACT_USE_POLARS": "0", "FFACT_L65_OPTIMIZATION_PROFILE": "legacy", "FFACT_L65_CHUNK_SIZE": "0"},
    "pandas_chunked": {"FFACT_USE_POLARS": "0"},
}
#: G2 兩份之生成環境：預設生成（Polars 預設開，`polars_adapter.polars_enabled`）與 pandas 生成
G2_ENVS: Dict[str, Dict[str, str]] = {"1": {}, "0": {"FFACT_USE_POLARS": "0"}}
#: G3 各格類之凍結份：格 B（IC-first，含 L6.5）＝raw＋processed；全特徵格 C 以生產預設設定生成、不產 processed
#: （SPEC Task 0.5「C 格只生成並凍結 raw 值指紋」；2026-10-23 正式凍結實測 C 之 manifest artifacts＝['raw']）——缺即拋錯
G3_ARTIFACTS: Dict[str, Tuple[str, ...]] = {"B": ("raw", "processed"), "C": ("raw",)}
BLOCKED_BY_HISTORY = "history"
BLOCKED_BY_HARDWARE = "hardware"
FULLSCALE_KEY = "RM-FULLSCALE"


def _log(message: str) -> None:
    """子行程進度行（卡住偵測以 log 增長判活；長步驟前後各印一行）。"""
    print(f"[freeze {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}", flush=True)


def _load(name: str, path: Path) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"無法載入 {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _gate() -> Any:
    return _load("numview_estimate_gate", PROBES_DIR / "_estimate_gate.py")


def _estimator() -> Any:
    return _load("numview_estimate", PROBES_DIR / "estimate.py")


def _watchdog() -> Any:
    return _load("numview_watchdog", PROBES_DIR / "_watchdog.py")


def _l2() -> Any:
    return _load("numview_l2_arm_matrix", PROBES_DIR / "l2_arm_matrix.py")


def _criteria() -> Dict[str, Any]:
    return json.loads(nh.current_criteria_path().read_text(encoding="utf-8"))


def _contract() -> Dict[str, Any]:
    from momentum.FeatureEngineering import numeric_view

    return numeric_view.load_contract()


def reachable_arms(selected_count: int) -> List[str]:
    """依契約 `post_ic_arm_reachability.<臂>.min_selected_columns` 回傳選欄數（ratio-unsafe 剔除後）為
    `selected_count` 時可達之 post-IC 臂（契約 `post_ic_arm_values` 之順序）；SPEC Task 0.5、R3-D。"""
    contract = _contract()
    reach = contract["post_ic_arm_reachability"]
    return [arm for arm in contract["post_ic_arm_values"]["values"]
            if int(selected_count) >= int(reach[arm]["min_selected_columns"])]


def _cells() -> List[Dict[str, Any]]:
    """現行判準之封閉格清單（格描述子 {id, kind, symbol, timeframes}，判準順序）。"""
    return [{"id": str(c["id"]), "kind": str(c["kind"]), "symbol": str(c["symbol"]),
             "timeframes": [str(t) for t in c["timeframes"]]} for c in _criteria()["cell_rules"]["cell_list"]["cells"]]


def kept_columns(selected: Sequence[str]) -> List[str]:
    """IC 頁第三步之選欄（`ic_analysis_service._apply_transforms_sync` 同規則）：保序去重、ratio-unsafe 欄剔除。"""
    from momentum.factories import ratio_unsafe_category

    return [c for c in dict.fromkeys(str(s) for s in selected) if ratio_unsafe_category(c) is None]


def _training_timeframes(cell: Mapping[str, Any]) -> List[str]:
    """格 B 之訓練週期依估時收據 `b_membership`（排除前史不足之週期）；其餘＝格描述子之週期。"""
    tfs = [str(t) for t in cell["timeframes"]]
    if cell["kind"] != "B":
        return tfs
    receipt = _gate().load_estimate_receipt(RECEIPTS_DIR)
    record = (receipt.get("b_membership") or {}).get(str(cell["id"])) or {}
    return [str(t) for t in (record.get("training_timeframes") or tfs)]


# ---------------------------------------------------------------------------------------------- 生成

class CellRun(ph.RunHandle):
    """`preprov_helpers.RunHandle`，另可作路徑（`os.fspath` ⇒ run 目錄）；屬性 `work` 為格工作目錄（sidecar 所在，
    `_handle_from` 設定）。不另加 dataclass 欄位（以 importlib 載入而未登記 sys.modules 時 dataclass 無法解析註記）。"""

    def __fspath__(self) -> str:
        return str(self.run_dir)


def _sidecar(work: Path) -> Dict[str, Any]:
    return json.loads((Path(work) / SIDECAR).read_text(encoding="utf-8"))


def _handle_from(work: Path) -> CellRun:
    side = _sidecar(work)
    root = Path(work) / "features"
    handle = CellRun(run_dir=root / side["symbol"] / side["primary_tf"] / side["config_hash"], features_root=root,
                     symbol=str(side["symbol"]), tf=str(side["primary_tf"]), config_hash=str(side["config_hash"]))
    object.__setattr__(handle, "work", Path(work))
    return handle


#: 凍結之生成與 IC 頁第三步進入時清除之環境變數（審碼 r27 CODEX-R27-P1-01、r28 CODEX-R28-P1-01）：前綴類（`FFACT_*` 選擇子、
#: `ICFA_*` 記憶體模擬與讀數、`FF_*` 正確性模式、`QTS_*` 抽取開關）與具名類（執行緒數、K 線目錄覆寫）。產品碼讀取之環境變數
#: 須屬清除類或 `ENV_NOT_CLEARED`（`test_freeze_cleared_env_covers_product_env_reads` 掃 momentum／api 機械檢查）。
CLEARED_ENV_PREFIXES: Tuple[str, ...] = ("FFACT_", "ICFA_", "FF_", "QTS_", "NUMBA_", "POLARS_", "OMP_", "MKL_",
                                         "OPENBLAS_")
#: 審碼 r29 CODEX-R29-P1-01：`PYTEST_CURRENT_TEST` 改變抽取之絕對值特徵過濾（`feature_extractor.py:494-495`），Phase 2–4 於
#: pytest 內重生時存在 ⇒ 清除
CLEARED_ENV_NAMES: Tuple[str, ...] = ("KLINE_STORAGE_DIR", "LEGACY_KLINE_CACHE_DIR", "PYTEST_CURRENT_TEST")
#: 產品碼讀取而不清除之環境變數：理由
ENV_NOT_CLEARED: Dict[str, str] = {"BINANCE_API_KEY": "交易所憑證，離線生成不連線", "BINANCE_SECRET_KEY": "交易所憑證，離線生成不連線"}
#: 產品碼中鍵名不可由 AST 解析之環境存取點（`路徑::函式`）：理由（審碼 r29；機械測試要求恰為此集合）
ENV_UNRESOLVED_SITES: Dict[str, str] = {
    "api/services/feature_factory_batch_service.py::_restore_batch_thread_env":
        "只寫回快照之舊值（鍵＝`_BATCH_THREAD_ENV_KEYS` 之快照），不讀值決策；批次服務不在凍結路徑",
    "api/services/feature_factory_service.py::_temporary_environ":
        "寫入 API 請求覆寫並於離開時還原；鍵由請求之 env_overrides 決定，凍結不經此服務（生成經 `_isolated` 直呼 factory）",
}


def _cleared_env_keys() -> List[str]:
    """環境中現有之清除類鍵（`CLEARED_ENV_PREFIXES`／`CLEARED_ENV_NAMES`）。"""
    return sorted(key for key in os.environ if key.startswith(CLEARED_ENV_PREFIXES) or key in CLEARED_ENV_NAMES)


@contextlib.contextmanager
def _clean_env(env: Mapping[str, str]) -> Iterator[Dict[str, str]]:
    """清除全部清除類鍵後套 `env`；結束時清除區塊內留下之清除類鍵並還原進入前之值。"""
    saved = {key: os.environ[key] for key in _cleared_env_keys()}
    applied = {str(k): str(v) for k, v in env.items()}
    for key in _cleared_env_keys():
        os.environ.pop(key, None)
    os.environ.update(applied)
    try:
        yield applied
    finally:
        for key in _cleared_env_keys():
            os.environ.pop(key, None)
        os.environ.update(saved)


def _hardware() -> Dict[str, Any]:
    """硬體自動解析值（審碼 r27 CODEX-R27-P1-01、r28 CODEX-R28-P1-02）：清除類鍵清除後之記憶體級距
    （`hardware_utils.get_memory_tier`）、實體記憶體（`memory_budget.physical_memory_bytes`，記憶體預算之來源）、CPU 數與機型。"""
    import platform

    from momentum.FeatureEngineering import memory_budget
    from momentum.FeatureEngineering.utils import hardware_utils

    with _clean_env({}):
        return {"memory_tier": hardware_utils.get_memory_tier(),
                "physical_memory_bytes": int(memory_budget.physical_memory_bytes()), "cpu_count": os.cpu_count(),
                "machine": platform.machine()}


@contextlib.contextmanager
def _isolated(work: Path, env: Mapping[str, str]) -> Iterator[Path]:
    """本生成之寫入隔離（估時器 `_isolate` 之同一語意：設定檔連結、registry、CGSA 工作目錄、cwd、tempdir、d* 快取導向
    `work`）；生成環境＝清除全部清除類鍵（`_clean_env`；審碼 r27–r28：環境殘留之影響值變數不得進入生成）後套 `env`（空＝
    生產預設）。結束還原環境變數、cwd、tempdir、d* 快取目錄（同行程內呼叫〔Phase 2–4 驗收〕不污染呼叫端）。回傳 features 根。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    saved_cwd, saved_tmp = os.getcwd(), tempfile.tempdir
    saved_dstar = FeaturePreprocessor.__dict__.get("_d_star_cache_dir")
    with _clean_env(env) as applied:
        try:
            yield _estimator()._isolate(Path(work), applied)
        finally:
            os.chdir(saved_cwd)
            tempfile.tempdir = saved_tmp
            if saved_dstar is not None:
                FeaturePreprocessor._d_star_cache_dir = saved_dstar


def generate_cell_run(work: Path, cell: Mapping[str, Any], env: Mapping[str, str], *,
                      observe_l2: bool = False) -> Dict[str, Any]:
    """於 `work` 隔離生成一格（判準檔之格定義：格 A／B＝`run_ic_first`、格 C＝`generate_features`；輸出段＝判準
    `window_rule`、連續性＝`cell_rules.continuity`），寫 sidecar 並回之。生成內擷取 IC-first 選欄（post-IC 之
    `transform_selected` 首次呼叫之選欄）；`observe_l2` ⇒ 掛 `l2_arm_matrix.L2Capture`，紀錄寫入 sidecar。前史判定
    依 `estimate.classify_generated_run`（只因 `*_insufficient_history` 而 partial ⇒ blocked）；其餘失敗原樣上拋。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    est = _estimator()
    criteria = _criteria()
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    kind, symbol, primary = str(cell["kind"]), str(cell["symbol"]), str(cell["timeframes"][0])
    definition = criteria["cell_definitions"][kind]
    entry = est.generation_entry(kind, criteria)
    training = _training_timeframes(cell)
    payload = est.cell_payload(cell, criteria, training)
    source = est.cell_source(cell, criteria)
    start, end = est.cell_window(cell, criteria)
    continuity = est.continuity_plan(cell, criteria, training)
    gaps = est.window_gap_violations(continuity, start)
    if gaps:
        raise est.EstimateError(f"{cell['id']}：輸出段內有 K 線缺口（data_gap）：{gaps}")
    side: Dict[str, Any] = {"cell": dict(cell), "env": dict(env), "entry": entry, "symbol": symbol, "primary_tf": primary,
                            "training_timeframes": training, "output_window": [start, end], "source": str(source),
                            "continuity": continuity, "config_override": definition.get("config_override"),
                            "payload_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str,
                                                                        ensure_ascii=False).encode("utf-8")).hexdigest(),
                            "hardware": _hardware()}
    captured: Dict[str, Any] = {}
    real_ts = FeaturePreprocessor.transform_selected

    def spy_ts(self: Any, selected: Any, groups: Any, config: Any = None, arm: Any = None) -> Any:
        if "selected" not in captured:
            captured["selected"] = [str(s) for s in selected]
        return real_ts(self, selected, groups, config=config, arm=arm)

    capture = _l2().L2Capture() if observe_l2 else contextlib.nullcontext()
    started = time.perf_counter()
    with _isolated(work, env) as features_root:
        side["effective_cleared_env"] = {key: os.environ[key] for key in _cleared_env_keys()}
        factory = create_feature_factory(cache_dir=str(source.parent), validate_continuity=continuity["validate_continuity"])
        factory._storage = FeatureStorage(str(features_root))
        FeaturePreprocessor.transform_selected = spy_ts  # type: ignore[assignment]
        try:
            with capture:
                if entry == "run_ic_first":
                    generation = definition["generation"]
                    config = factory._resolve_config(payload)
                    factory.run_ic_first(symbol, primary, config, start_date=start, end_date=end,
                                         ic_engine=ICEngine(dict(generation["ic_engine_config"])),
                                         feature_reader=FeatureReader(str(features_root)),
                                         ic_threshold=generation["ic_threshold"],
                                         label_horizon=str(generation["label_horizon"]),
                                         cleanup_raw=bool(generation["cleanup_raw"]))
                else:
                    factory.generate_features(symbol, primary, config_override=payload, force_regenerate=True,
                                              persist=True, start_date=start, end_date=end)
            error = None
        except Exception as exc:  # noqa: BLE001 — 前史不足之權威判定在下；其餘原樣上拋
            error = exc
        finally:
            FeaturePreprocessor.transform_selected = real_ts  # type: ignore[assignment]
        verdict = est.classify_generated_run(features_root, symbol, primary, criteria)
    side["seconds"] = time.perf_counter() - started
    if error is not None and verdict["status"] != "blocked":
        raise error
    if error is None and verdict["status"] == "failed":
        raise est.EstimateError(f"{cell['id']}：生成完成而 run 非 complete：{verdict}")
    manifests = sorted((work / "features" / symbol / primary).glob("*/feature_manifest.json"))
    side.update(verdict, config_hash=manifests[0].parent.name if len(manifests) == 1 else None,
                ic_first_selected=captured.get("selected") if entry == "run_ic_first" else None,
                l2_capture=list(capture.records) if observe_l2 else None)
    # sidecar＝本格生成之提交標記：生成完成後最後寫、原子替換（中途中斷 ⇒ 無 sidecar ⇒ 快取不命中）
    staging = work / (SIDECAR + ".tmp")
    staging.write_text(json.dumps(side, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(staging, work / SIDECAR)
    return side


def generate_cell(root: Path, cell: Mapping[str, Any], *, run_kind: str,
                  env: Optional[Mapping[str, str]] = None, observe_l2: bool = False) -> Any:
    """格之真實生成（SPEC Task 0.5、R15-A）：`cell`＝全票唯一格描述子 `{id, kind, symbol, timeframes}`；與凍結同一生成程序、
    同行程、寫入隔離於 `root`、raw 與 processed 皆保留；`env` 覆寫生成環境；回 `preprov_helpers.RunHandle`（子類
    `CellRun`，可作路徑＝run 目錄）。
    🔴 首個陳述式級呼叫須為 `_estimate_gate.require(run_kind, [cell["id"]], receipts_dir=RECEIPTS_DIR)`，先於任何生成呼叫
    （`run_kind`＝呼叫端所屬之估時跑別：凍結為 `freeze_baseline`，Phase 2–4 驗收重產為批次生成跑別 `regen_b3`／`regen_b4`／
    `regen_b5`〔經 `numview_helpers.regen_batch_kind`〕）；估時收據未涵蓋該格 ⇒ `EstimateGateError` 原樣上拋、不生成。
    批次共用生成（判準檔 `cell_rules.batch_cache`）：`root` 恰為 `numview_helpers.regen_batch_root()` 時，run 落於
    `root / numview_helpers.regen_cache_key(cell, env)`（格描述子、env、碼態 sha256），已存在完整 run 即於前置閘後直接回傳、
    不重生；其他 `root`（凍結、Phase 1、mutant 之暫存根）不讀寫該快取。須觀測生成內中間值之檢查（Task 1.3 L2 spy、
    Task 3.1–3.3 核心 spy）之觀測器掛於該唯一生成，觀測紀錄與 run 同存，快取命中時由紀錄回填（不得因命中而重生）。"""
    _gate().require(run_kind, [str(cell["id"])], receipts_dir=RECEIPTS_DIR)
    env = {str(k): str(v) for k, v in (env or {}).items()}
    root = Path(root)
    batched = root.resolve() == nh.regen_batch_root().resolve()
    work = root / (nh.regen_cache_key(cell, env) if batched else _work_name(cell, env))
    if batched and _cache_complete(work):
        return _handle_from(work)
    if work.exists():
        shutil.rmtree(work)
    generate_cell_run(work, cell, env, observe_l2=observe_l2)
    return _handle_from(work)


def _cache_complete(work: Path) -> bool:
    """批次快取命中條件（審碼 r21 CODEX-R21-P1-01、r22 CODEX-R22-P1-01）：sidecar 可讀、狀態 complete、`config_hash` 非空；
    其所指 run 目錄之 `feature_manifest.json` 之有效 run 狀態（`consumer_gate.effective_run_status`，同正式消費端）為
    complete、manifest 之 `symbol`／`tf`／`config_hash` 等於 sidecar；manifest 宣告之 raw 群組檔皆存在。任一不符 ⇒ 不命中
    （呼叫端刪除重生）。"""
    from momentum.FeatureEngineering.consumer_gate import effective_run_status

    try:
        side = _sidecar(work)
        if side.get("status") != "complete" or not side.get("config_hash"):
            return False
        run_dir = _handle_from(work).run_dir
        manifest = ph.load_manifest(run_dir)
        # 正式嚴格讀取端之完整度標記（feature_reader.py:641、:644；writer 不完整窗口 feature_storage.py:2005、:2008）：
        # manifest 根與 raw artifact 之 complete 皆須為 True，不以 explicit run_status 代之（審碼 r23 CODEX-R23-P1-01）
        raw_node = (manifest.get("artifacts") or {}).get("raw")
        if manifest.get("complete") is not True or not isinstance(raw_node, dict) or raw_node.get("complete") is not True:
            return False
        if effective_run_status(manifest) != "complete":
            return False
        if (str(manifest.get("symbol")), str(manifest.get("tf")), str(manifest.get("config_hash"))) != (
                str(side["symbol"]), str(side["primary_tf"]), str(side["config_hash"])):
            return False
        files = ph.declared_group_files(run_dir, "raw")
        return bool(files) and all(p.is_file() for p in files)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _work_name(cell: Mapping[str, Any], env: Mapping[str, str]) -> str:
    """非快取根下之格工作目錄名：格 id＋生成環境（空＝default）。"""
    tag = "_".join(f"{k}-{v}" for k, v in sorted(env.items())) or "default"
    return f"{cell['id']}__{tag}"


# ---------------------------------------------------------------------------------------------- IC 頁第三步

@contextlib.contextmanager
def _arm_env(arm: Optional[str], selected_count: int) -> Iterator[Dict[str, str]]:
    """post-IC 臂之環境（SPEC §G G1）；`pandas_chunked` 之 chunk＝選欄數 − 1（小於選欄數之最大合法正整數）。None ⇒ 不改。
    臂環境＝清除全部清除類鍵（`_clean_env`；審碼 r27–r28）後套該臂之 `G1_ARM_ENV`；結束還原。"""
    if arm is None:
        yield {}
        return
    env = dict(G1_ARM_ENV[arm])
    if arm == "pandas_chunked":
        env[CHUNK_ENV] = str(max(1, int(selected_count) - 1))
    with _clean_env(env) as applied:
        yield applied


def _ic_page_run(handle: Any, work: Path) -> Tuple[Any, Dict[str, Any], List[str]]:
    """IC 頁第三步之一切入口（G1 之 `_g1_parts`、公開 `ic_page_output`）：保留呼叫端所設之臂鍵（`ARM_ENV_KEYS`），清除
    其餘清除類鍵（`_clean_env`；審碼 r28 CODEX-R28-P1-01：公開入口亦不受環境殘留影響、快取鍵＝臂鍵即完整）後執行
    `_ic_page_run_in_env`。"""
    with _clean_env({key: os.environ[key] for key in ARM_ENV_KEYS if key in os.environ}):
        return _ic_page_run_in_env(handle, work)


def _ic_page_run_in_env(handle: Any, work: Path) -> Tuple[Any, Dict[str, Any], List[str]]:
    """IC 頁第三步（`_apply_transforms_sync`，`ApplyTransformsRequest` 預設請求、該格 IC-first 選欄；cwd 隔離於 `work`）；
    回（h5 讀回之 DataFrame, 回應 dict, 實際執行臂〔`last_post_ic_execution` 群組表之臂，去重排序〕）。批次快取之 run
    （`regen_batch_root()` 之下）每 (臂環境) 只算一次、存於該生成之工作目錄。只經 `_ic_page_run` 呼叫。"""
    import pandas as pd

    from api.models.ic_models import ApplyTransformsRequest
    from api.services.ic_analysis_service import ic_analysis_service as svc
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from tests.feature_engineering.ffname_helpers import register_canonical_run

    cell_work = Path(getattr(handle, "work", Path(handle.run_dir).parents[3]))
    side = _sidecar(cell_work)
    arm_env = {key: os.environ[key] for key in ARM_ENV_KEYS if key in os.environ}
    cache_dir = None
    if Path(cell_work).resolve().is_relative_to(nh.regen_batch_root().resolve()):
        key = hashlib.sha256(json.dumps(arm_env, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        cache_dir = cell_work / "icpage_cache" / key
        if (cache_dir / "response.json").is_file():
            cached = json.loads((cache_dir / "response.json").read_text(encoding="utf-8"))
            return pd.read_parquet(cache_dir / "frame.parquet"), cached["response"], cached["executed_arms"]
    request = ApplyTransformsRequest(selected_features=list(side.get("ic_first_selected") or []))
    registry = Path(work) / "icpage_registry.json"
    Path(work).mkdir(parents=True, exist_ok=True)
    register_canonical_run(Path(handle.run_dir) / "feature_manifest.json", registry)
    root = Path(handle.features_root)
    library = FeatureLibrary(FeatureRegistry(registry), FeatureStorage(str(root)), feature_reader=FeatureReader(str(root)))
    executed: List[str] = []
    real_ts = FeaturePreprocessor.transform_selected

    def spy_ts(self: Any, *args: Any, **kwargs: Any) -> Any:
        out = real_ts(self, *args, **kwargs)
        _records, groups = self.last_post_ic_execution()
        executed.extend(str(g.get("arm")) for g in groups.values())
        return out

    task_id = f"numview_freeze_{os.getpid()}_{time.time_ns()}"
    saved_cwd, saved_library = os.getcwd(), svc._feature_library
    svc._tasks[task_id] = {"req_features_path": str(Path(handle.run_dir) / "feature_manifest.json"),
                           "result": {"analysis_status": "ok_oos", "oos_guarantees": True}}
    FeaturePreprocessor.transform_selected = spy_ts  # type: ignore[assignment]
    try:
        os.chdir(str(work))
        svc._feature_library = library
        response = svc._apply_transforms_sync(task_id, list(request.selected_features), request.rank, request.zscore,
                                              request.gaussian, request.rank_window, list(request.zscore_windows))
        output = Path(response["output_path"])
        frame = pd.read_hdf(str(output if output.is_absolute() else Path(work) / output), key="features")
    finally:
        FeaturePreprocessor.transform_selected = real_ts  # type: ignore[assignment]
        svc._feature_library = saved_library
        svc._tasks.pop(task_id, None)
        os.chdir(saved_cwd)
    arms = sorted(set(executed))
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(cache_dir / "frame.parquet")
        (cache_dir / "response.json").write_text(json.dumps({"response": response, "executed_arms": arms}, default=str),
                                                 encoding="utf-8")
    return frame, dict(response), arms


def ic_page_output(handle: Any, work: Path) -> Tuple[Any, Dict[str, Any]]:
    """以 `ApplyTransformsRequest` 預設請求對該格 IC-first 選欄跑 IC 頁第三步（`_apply_transforms_sync`，cwd 隔離於
    `work`），回（h5 讀回之 DataFrame, 回應 dict）；不生成特徵（只讀 `handle` 之 run）。`handle` 屬批次共用快取時
    （判準檔 `cell_rules.batch_cache`），各臂輸出（含臂 spy 紀錄）每 (格描述子, env, 碼態, 臂環境) 只算一次、存於該生成之快取
    目錄，t21／t22／§G 等檢查讀取，不各自重算。"""
    frame, response, _arms = _ic_page_run(handle, work)
    return frame, response


# ---------------------------------------------------------------------------------------------- 凍結份

def _fingerprint(run_dir: Path, artifact: str, kind: str) -> Dict[str, Any]:
    """§G 值指紋：格類屬 `GROUP_GRANULARITY_KINDS` ⇒ 群組粒度（`group_fingerprints`），否則逐欄（`fingerprints`）。"""
    if kind in nh.GROUP_GRANULARITY_KINDS:
        return nh.group_fingerprints(Path(run_dir), artifact)
    return nh.fingerprints(Path(run_dir), artifact)


def _g1_parts(handle: Any, cell: Mapping[str, Any], arms: Sequence[str], work: Path,
              unreachable: List[Dict[str, Any]]) -> Dict[str, Any]:
    """格 A 之 G1 臂份：`arms` 中可達者各跑 IC 頁第三步，記環境、實際臂、值指紋；不可達者記入 `unreachable`。"""
    contract = _contract()
    selected = list(_sidecar(Path(handle.work)).get("ic_first_selected") or [])
    count = len(kept_columns(selected))
    reachable = reachable_arms(count)
    out: Dict[str, Any] = {}
    for arm in arms:
        if arm not in reachable:
            unreachable.append({"cell_id": str(cell["id"]), "arm": arm, "selected_count": count,
                                "condition": contract["post_ic_arm_reachability"][arm]["condition"]})
            continue
        _log(f"{cell['id']}：G1 {arm} 開始（選欄 {count}）")
        with _arm_env(arm, count) as env:
            frame, _response, executed = _ic_page_run(handle, Path(work) / f"icpage_{arm}")
        actual = executed[0] if len(executed) == 1 else ("mixed:" + ",".join(executed) if executed else None)
        out[arm] = {"env": env, "actual_arm": actual, "fingerprint": nh.frame_fingerprints(frame)}
        _log(f"{cell['id']}：G1 {arm} 完成（實際臂 {actual}）")
    return out


def freeze_cell(cell: Mapping[str, Any], work_root: Path, *, arms: Sequence[str], run_kind: str) -> Dict[str, Any]:
    """以現行碼依凍結檔格紀錄重生該格，回與凍結檔同形之 `{"g1": {臂: {env, actual_arm, fingerprint}}, "g2": {...},
    "g3": {...}}`（G1 只跑 `arms`）；生成一律經 `generate_cell(..., run_kind=run_kind)`（故同受估時前置閘；SPEC §G、R15-A）。"""
    record = json.loads(nh.PRE_CHANGE_FINGERPRINTS_PATH.read_text(encoding="utf-8"))["cells"][str(cell["id"])]
    kind = str(cell["kind"])
    out: Dict[str, Any] = {"g1": {}, "g2": {}, "g3": {}}
    handle = generate_cell(work_root, cell, run_kind=run_kind, env=record.get("g1_source_env") or {})
    if kind == "A":
        out["g1"] = _g1_parts(handle, cell, arms, Path(work_root) / f"{cell['id']}__g1", [])
    if str(cell["id"]) in nh.criteria_freeze_group("G2"):
        for value, env in G2_ENVS.items():
            source = handle if not env else generate_cell(work_root, cell, run_kind=run_kind, env=env)
            out["g2"][value] = {"env": {"FFACT_USE_POLARS": value}, "fingerprint": _fingerprint(source.run_dir, "raw", kind)}
    if str(cell["id"]) in nh.criteria_freeze_group("G3") or kind == "B":
        out["g3"] = {artifact: _fingerprint(handle.run_dir, artifact, kind) for artifact in G3_ARTIFACTS[kind]}
    return out


# ---------------------------------------------------------------------------------------------- 子行程（每格）

def _l2_cells() -> Dict[str, List[Dict[str, str]]]:
    """L2 擷取 spy 須掛之 (格, 生成環境)：判準檔 `run_coverage.l2_arm_matrix` 中 `generations`＝0（讀凍結生成）者。"""
    out: Dict[str, List[Dict[str, str]]] = {}
    for run in (_criteria().get("run_coverage") or {}).get("l2_arm_matrix", {}).get("runs") or []:
        if not run.get("generations"):
            out.setdefault(str(run["cell"]), []).append({str(k): str(v) for k, v in (run.get("env") or {}).items()})
    return out


def _peak_rss_bytes() -> int:
    import resource

    scale = 1 if sys.platform == "darwin" else 1024
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * scale)


def _bar_counts(cell: Mapping[str, Any]) -> Dict[str, int]:
    est = _estimator()
    source = est.cell_source(cell, _criteria())
    import h5py

    with h5py.File(str(source), "r") as handle:
        return {str(tf): int(handle[str(cell["symbol"])][str(tf)]["data"].shape[0]) for tf in cell["timeframes"]}


#: 結果身分所涵蓋之判準規則（決定生成者；不含說明字面）
IDENTITY_RULE_KEYS = ("kline_source", "window_rule", "continuity", "insufficient_history")


def generation_inputs(cell: Mapping[str, Any]) -> Dict[str, Any]:
    """格之生成輸入（審碼 r26 CODEX-R26-P1-01、r27 CODEX-R27-P1-01）：以 `generate_cell_run` 同一組估時器函式導出之入口、
    訓練週期（格 B 讀估時收據 `b_membership`）、設定覆寫、K 線來源、輸出段與連續性設定，及硬體自動解析值（`_hardware`）；
    sidecar 記其中各鍵（payload 記 `payload_sha256`），補記時逐鍵對證。環境變數不入：生成與 IC 頁第三步一律清除全部清除類鍵
    （`_clean_env`）後只套明示環境（`G1_ARM_ENV`／`G2_ENVS` 等，屬接縫碼態）。"""
    est = _estimator()
    criteria = _criteria()
    training = _training_timeframes(cell)
    start, end = est.cell_window(cell, criteria)
    return {"entry": est.generation_entry(str(cell["kind"]), criteria), "training_timeframes": training,
            "payload": est.cell_payload(cell, criteria, training), "source": str(est.cell_source(cell, criteria)),
            "output_window": [start, end], "continuity": est.continuity_plan(cell, criteria, training),
            "config_override": criteria["cell_definitions"][str(cell["kind"])].get("config_override"),
            "hardware": _hardware()}


def result_identity(cell: Mapping[str, Any]) -> Dict[str, Any]:
    """每格凍結結果之身分（審碼 r24 CODEX-R24-P1-01、r25 CODEX-R25-P1-01／GROK-R25-P1-01）：產品碼態
    （`numview_helpers.code_state_sha256`）、生成接縫碼態（`numview_helpers.seam_state_sha256`：本腳本〔含 `G1_ARM_ENV`／
    `G2_ENVS`／`G3_ARTIFACTS` 等凍結政策〕、值指紋助手與凍結載入之探針檔之位元組）、格描述子、判準之該格類定義、
    `IDENTITY_RULE_KEYS` 規則與該格之凍結組成員（`freeze_groups` 各組是否含本格）之 sha256（說明字面 `_doc`／`_basis` 不計）、
    生成輸入（`generation_inputs`，含估時收據導出之訓練週期；r26 CODEX-R26-P1-01）之 sha256、格之 K 線資料集紀錄。沿用既有
    結果須與現行身分逐鍵相等。規格審查 r18 後不含 HEAD：決定數值之碼已由產品碼態與接縫碼態逐位元涵蓋，HEAD 另因只改文件／
    測試之提交而變、會使沿用誤失效；生成時之 HEAD 另記於結果 `generation_head`，收據與凍結檔之 `head` 取自之。"""
    criteria = _criteria()

    def strip(node: Any) -> Any:
        if isinstance(node, Mapping):
            return {k: strip(v) for k, v in sorted(node.items()) if not str(k).startswith("_")}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node

    rules = {key: strip(criteria["cell_rules"].get(key)) for key in IDENTITY_RULE_KEYS}
    definition = strip(criteria["cell_definitions"][str(cell["kind"])])
    groups = {name: str(cell["id"]) in members
              for name, members in sorted(strip(criteria["cell_rules"]["freeze_groups"]).items())}
    return {"code_state_sha256": nh.code_state_sha256(), "seam_state_sha256": nh.seam_state_sha256(),
            "cell": {"id": str(cell["id"]), "kind": str(cell["kind"]), "symbol": str(cell["symbol"]),
                     "timeframes": [str(t) for t in cell["timeframes"]]},
            "criteria_cell_sha256": hashlib.sha256(json.dumps({"definition": definition, "rules": rules,
                                                               "freeze_groups": groups}, sort_keys=True,
                                                              ensure_ascii=False).encode("utf-8")).hexdigest(),
            "generation_inputs_sha256": hashlib.sha256(json.dumps(generation_inputs(cell), sort_keys=True, default=str,
                                                                  ensure_ascii=False).encode("utf-8")).hexdigest(),
            "datasets": nh.cell_dataset_records(cell)}


def freeze_one(cell: Mapping[str, Any], work_root: Path) -> Dict[str, Any]:
    """凍結一格（子行程內）：生成（G2 格另生成 pandas 環境）、G1／G2／G3 值指紋、L2 擷取；回每格結果
    {cell_id, status, blocked_by, reason, reason_counts, bar_counts, seconds, peak_rss_bytes, record, arm_unreachable,
    l2_capture}。"""
    kind, cell_id = str(cell["kind"]), str(cell["id"])
    l2_envs = _l2_cells().get(cell_id, [])
    started = time.perf_counter()
    result: Dict[str, Any] = {"cell_id": cell_id, "kind": kind, "symbol": cell["symbol"], "timeframes": cell["timeframes"],
                              "bar_counts": _bar_counts(cell), "blocked_by": None, "reason": None,
                              "arm_unreachable": [], "l2_capture": {}, "identity": result_identity(cell),
                              "generation_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                                                                capture_output=True, text=True).stdout.strip()}
    _log(f"{cell_id}：生成開始（env 預設）")
    handle = generate_cell(work_root, cell, run_kind=RUN_KIND, env={}, observe_l2={} in l2_envs)
    side = _sidecar(Path(handle.work))
    _log(f"{cell_id}：生成完成（{side.get('status')}，{side.get('seconds', 0):.0f} 秒）")
    if side.get("l2_capture") is not None:
        result["l2_capture"]["default"] = side["l2_capture"]
    if side.get("status") == "blocked":
        result.update(status="blocked", blocked_by=BLOCKED_BY_HISTORY, reason_counts=side.get("reason_counts"),
                      reason=f"run 只因前史不足而 partial（判準檔 cell_rules.insufficient_history）：{side.get('reason_counts')}")
        result["seconds"] = time.perf_counter() - started
        return result
    definition = _criteria()["cell_definitions"][kind]
    record: Dict[str, Any] = {"kind": kind, "symbol": cell["symbol"], "timeframes": list(cell["timeframes"]),
                              "config_override": definition.get("config_override"),
                              "output_bars": definition.get("output_bars"), "run_dir": str(handle.run_dir),
                              "g1": {}, "g2": {}, "g3": {}}
    if kind == "A":
        record["ic_first_selected"] = list(side.get("ic_first_selected") or [])
        record["g1_source_env"] = {}
        record["g1"] = _g1_parts(handle, cell, _contract()["post_ic_arm_values"]["values"],
                                 Path(work_root) / f"{cell_id}__g1", result["arm_unreachable"])
    if cell_id in nh.criteria_freeze_group("G2"):
        for value, env in G2_ENVS.items():
            source = handle
            if env:
                _log(f"{cell_id}：G2 生成開始（{env}）")
                source = generate_cell(work_root, cell, run_kind=RUN_KIND, env=env, observe_l2=env in l2_envs)
                extra = _sidecar(Path(source.work))
                if extra.get("l2_capture") is not None:
                    result["l2_capture"]["_".join(f"{k}={v}" for k, v in sorted(env.items()))] = extra["l2_capture"]
                _log(f"{cell_id}：G2 生成完成")
            _log(f"{cell_id}：G2 raw 值指紋（FFACT_USE_POLARS={value}）")
            record["g2"][value] = {"env": {"FFACT_USE_POLARS": value}, "fingerprint": _fingerprint(source.run_dir, "raw", kind)}
    if cell_id in nh.criteria_freeze_group("G3") or kind == "B":
        for artifact in G3_ARTIFACTS[kind]:
            _log(f"{cell_id}：G3 {artifact} 值指紋開始")
            record["g3"][artifact] = _fingerprint(handle.run_dir, artifact, kind)
            _log(f"{cell_id}：G3 {artifact} 值指紋完成")
    result.update(status="frozen", record=record, seconds=time.perf_counter() - started)
    return result


def _child(spec_path: Path) -> int:
    """子行程入口：凍結單一格、寫結果檔；記憶體守護具名終止 ⇒ blocked（hardware）；其他錯誤 ⇒ failed。"""
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    cell = spec["cell"]
    started = time.perf_counter()
    try:
        result = freeze_one(cell, Path(spec["work_root"]))
    except BaseException as exc:  # noqa: BLE001 — 失敗之型別決定 blocked（硬體）或 failed，皆寫結果
        result = {"cell_id": cell["id"], "kind": cell["kind"], "symbol": cell["symbol"], "timeframes": cell["timeframes"],
                  "bar_counts": _bar_counts(cell), "arm_unreachable": [], "seconds": time.perf_counter() - started,
                  "error": f"{type(exc).__name__}: {exc}"[:2000]}
        if _estimator()._is_memory_guard(exc):
            result.update(status="blocked", blocked_by=BLOCKED_BY_HARDWARE,
                          reason=f"生成被記憶體守護具名終止（{type(exc).__name__}）；列入 {FULLSCALE_KEY}")
        else:
            result.update(status="failed", blocked_by=None, reason=result["error"])
    result["peak_rss_bytes"] = _peak_rss_bytes()
    Path(spec["result_path"]).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0 if result.get("status") in ("frozen", "blocked") else 3


# ---------------------------------------------------------------------------------------------- 主入口

def _parse(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NUMVIEW 改前基準凍結（SPEC Task 0.5）")
    parser.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT), help="每格 run 目錄、sidecar 與結果檔之根")
    parser.add_argument("--fresh", action="store_true", help="清除既有結果檔重凍全部格")
    parser.add_argument("--child", default=None, help=argparse.SUPPRESS)
    return parser.parse_args(list(argv) if argv is not None else None)


def _expected_seconds(cell_id: str) -> Optional[float]:
    """卡住偵測之預期單格秒數：估時收據該格生成秒數＋G1 各臂秒數＋固定 300 秒（值指紋與 L2 擷取）；無 ⇒ None。"""
    m = (_gate().load_estimate_receipt(RECEIPTS_DIR).get("measurements") or {}).get(cell_id) or {}
    base = m.get("seconds") or m.get("child_wall_seconds")
    if not isinstance(base, (int, float)):
        return None
    arms = sum(float(v) for v in (m.get("arm_seconds") or {}).values())
    return float(base) + arms + 300.0


def _run_cells(cells: Sequence[Mapping[str, Any]], work_root: Path, fresh: bool) -> Tuple[int, List[Dict[str, Any]]]:
    """逐格以子行程（經卡住偵測）凍結；已完成之結果檔沿用（`fresh` 除外）；卡住或失敗 ⇒ 停止後續格。"""
    wd = _watchdog()
    config = wd.load_config(_criteria())
    results: List[Dict[str, Any]] = []
    for cell in cells:
        cell_dir = work_root / "_results" / str(cell["id"])
        result_path = cell_dir / RESULT_NAME
        if result_path.is_file() and not fresh:
            done = json.loads(result_path.read_text(encoding="utf-8"))
            current = result_identity(cell)
            if done.get("status") in ("frozen", "blocked") and done.get("identity") == current:
                print(f"[freeze] {cell['id']}：沿用既有結果（{done['status']}；身分相符）", flush=True)
                results.append(done)
                continue
            print(f"[freeze] {cell['id']}：既有結果身分不符或狀態非 frozen／blocked ⇒ 重凍", flush=True)
        cell_dir.mkdir(parents=True, exist_ok=True)
        spec_path = cell_dir / "spec.json"
        spec_path.write_text(json.dumps({"cell": dict(cell), "work_root": str(work_root),
                                         "result_path": str(result_path)}, ensure_ascii=False), encoding="utf-8")
        result_path.unlink(missing_ok=True)
        print(f"[freeze] {cell['id']}：子行程開始", flush=True)
        watched = wd.run_watched([sys.executable, str(Path(__file__).resolve()), "--child", str(spec_path)],
                                 log_path=cell_dir / "child.log", config=config,
                                 expected_seconds=_expected_seconds(str(cell["id"])), cwd=str(REPO))
        if watched.status == wd.STALLED or not result_path.is_file():
            print(f"[watchdog] {cell['id']}：{watched.status}（{watched.reason}；rc={watched.returncode}；"
                  f"{watched.wall_seconds:.0f} 秒；見 {cell_dir / 'child.log'}）— 停止後續格，不寫凍結檔", file=sys.stderr, flush=True)
            return 3, results
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["swap_growth_max_mb"] = watched.swap_growth_max_mb
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"[freeze] {cell['id']}：{result.get('status')}（{result.get('seconds', 0):.0f} 秒）", flush=True)
        if result.get("status") not in ("frozen", "blocked"):
            print(f"[freeze] {cell['id']}：失敗 {result.get('reason')}— 停止後續格", file=sys.stderr, flush=True)
            return 3, results
        results.append(result)
    return 0, results


def _product_code_dirty() -> List[str]:
    """產品碼（`numview_helpers.CODE_STATE_PATHSPECS`：momentum／api 之原始碼與契約，不含 numba 快取）對 HEAD 之改動與
    未追蹤檔；git 失敗 ⇒ 視為不乾淨（fail-closed）。"""
    proc = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", *nh.CODE_STATE_PATHSPECS],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return [f"git status 失敗：{proc.stderr.strip()[:200]}"]
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _library_versions() -> Dict[str, Optional[str]]:
    versions: Dict[str, Optional[str]] = {}
    for name in _contract()["library_versions"]["values"]:
        try:
            versions[name] = str(getattr(importlib.import_module(name), "__version__", None))
        except ImportError:
            versions[name] = None
    return versions


def _write_outputs(cells: Sequence[Mapping[str, Any]], results: Sequence[Mapping[str, Any]], started_at: str) -> int:
    """凍結檔與收據；任一 G1 份之實際臂 ≠ 標示臂 ⇒ rc≠0、不寫。`head`＝各格結果之生成時 HEAD（`generation_head`，須全格
    一致；不一致或缺 ⇒ rc≠0、不寫），不取重寫當下之 HEAD（規格審查 r18：沿用結果重寫收據時不得把 head 改成後來之提交）。"""
    heads = {str(r.get("generation_head") or "") for r in results}
    if len(heads) != 1 or "" in heads:
        print(f"[freeze] 各格生成時 HEAD 不一致或缺：{sorted(heads)}", file=sys.stderr, flush=True)
        return 5
    head = heads.pop()
    freeze_cells: Dict[str, Any] = {}
    receipt_cells: List[Dict[str, Any]] = []
    unreachable: List[Dict[str, Any]] = []
    residuals: List[Dict[str, Any]] = []
    mismatches: List[str] = []
    by_id = {str(r["cell_id"]): r for r in results}
    for cell in cells:
        r = by_id[str(cell["id"])]
        receipt_cells.append({key: r.get(key) for key in ("cell_id", "kind", "symbol", "timeframes", "status", "blocked_by",
                                                          "reason", "reason_counts", "bar_counts", "seconds",
                                                          "peak_rss_bytes", "swap_growth_max_mb")})
        unreachable += list(r.get("arm_unreachable") or [])
        if r.get("blocked_by") == BLOCKED_BY_HARDWARE:
            residuals.append({"cell_id": r["cell_id"], "fact_key": FULLSCALE_KEY})
        if r.get("status") == "frozen":
            record = dict(r["record"])
            for arm, copy_ in (record.get("g1") or {}).items():
                if copy_.get("actual_arm") != arm:
                    mismatches.append(f"{r['cell_id']}：G1 標示臂 {arm} 之實際臂 {copy_.get('actual_arm')}")
            freeze_cells[str(r["cell_id"])] = record
    if mismatches:
        print("[freeze] 實際臂 ≠ 標示臂：" + "；".join(mismatches), file=sys.stderr, flush=True)
        return 4
    criteria_path = nh.current_criteria_path()
    nh.PRE_CHANGE_FINGERPRINTS_PATH.write_text(json.dumps({"head": head, "started_at": started_at, "cells": freeze_cells},
                                                          ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    receipt = {"schema_version": 1, "head": head, "started_at": started_at,
               "finished_at": datetime.now(timezone.utc).isoformat(), "exit_code": 0,
               "command": "venv/bin/python scripts/numview_freeze_baseline.py",
               "criteria_sha256": hashlib.sha256(criteria_path.read_bytes()).hexdigest(),
               "code_state_sha256": nh.code_state_sha256(), "library_versions": _library_versions(), "cells": receipt_cells, "arm_unreachable": unreachable,
               "residuals": residuals, "fingerprint_granularity": {"group": list(nh.GROUP_GRANULARITY_KINDS)},
               "l2_capture": {str(r["cell_id"]): r.get("l2_capture") for r in results if r.get("l2_capture")},
               "identity": {str(r["cell_id"]): r.get("identity") for r in results},
               "identity_backfilled": {str(r["cell_id"]): r["identity_backfilled"] for r in results
                                       if r.get("identity_backfilled")}}
    out = RECEIPTS_DIR / FREEZE_RECEIPT_NAME.format(date=datetime.now().strftime("%Y%m%d"))
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"[freeze] 凍結檔 {nh.PRE_CHANGE_FINGERPRINTS_PATH.relative_to(REPO)}；收據 {out.relative_to(REPO)}", flush=True)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """凍結主入口；rc 0＝凍結檔與收據寫出、非 0＝實際臂≠標示臂或生成失敗；估時前置不成立 ⇒ `EstimateGateError` 原樣上拋。
    啟動即 `_estimate_gate.require("freeze_baseline", cells, receipts_dir=RECEIPTS_DIR)`，生成一律經 `generate_cell`。"""
    args = _parse(argv)
    cells = _cells()
    _gate().require("freeze_baseline", [c["id"] for c in cells], receipts_dir=RECEIPTS_DIR)
    if args.child:
        return _child(Path(args.child))
    dirty = _product_code_dirty()
    if dirty:
        print(f"[freeze] 產品碼對 HEAD 有改動，不得凍結（SPEC Task 0.5 不可做）：{dirty[:10]}", file=sys.stderr, flush=True)
        return 5
    started_at = datetime.now(timezone.utc).isoformat()
    work_root = Path(args.work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    with _clean_env({}):  # 子行程繼承已清除之環境（函式庫於 import 時讀之 NUMBA_*／POLARS_* 等亦乾淨；審碼 r29）
        rc, results = _run_cells(cells, work_root, args.fresh)
    if rc != 0:
        return rc
    return _write_outputs(cells, results, started_at)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
