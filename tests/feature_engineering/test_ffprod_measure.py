"""FFPROD Task 2.1 量測腳本（`scripts/ffprod_measure.py`）之輕量契約測試。

不生成特徵、不跑 IC：候選集合＝盤點收據 measure 項、計畫估時來源、探針自證判定（含改壞對照）、探針於真實產品函式上之換源／
換精度（子行程內安裝，避免污染本 pytest 行程）、值差導出、IC 替換重排、收據欄位、續跑不重算、自證失敗拒寫。
全特徵格之真實量測與 IC 實跑不在此（重型；見腳本 `run`／`ic` 子命令）。
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "ffprod_measure.py"


def _load() -> Any:
    name = "ffprod_measure_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fm = _load()


def _snippet(code: str, tmp_path: Path) -> str:
    """於獨立子行程執行（探針會 monkeypatch 產品模組，不得在 pytest 行程內安裝）；rc≠0 ⇒ 測試失敗並附輸出。"""
    prelude = (f"import sys, json\nsys.path.insert(0, {str(REPO)!r})\n"
               f"import importlib.util\n_s = importlib.util.spec_from_file_location('fm', {str(SCRIPT)!r})\n"
               "fm = importlib.util.module_from_spec(_s); sys.modules['fm'] = fm; _s.loader.exec_module(fm)\n"
               f"PROOF = {str(tmp_path / 'proof')!r}\n")
    proc = subprocess.run([sys.executable, "-c", prelude + code], cwd=str(REPO), capture_output=True, text=True,
                          timeout=120)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    return proc.stdout


def _proofs(tmp_path: Path) -> List[Dict[str, Any]]:
    proofs, errors = fm.read_proofs(tmp_path / "proof")
    assert not errors
    return proofs


# ---------------------------------------------------------------------------------------------- 候選集合與計畫

def test_candidate_set_equals_inventory_measure_items(tmp_path: Path) -> None:
    fm.assert_candidate_set()
    inv_path = next(fm.RECEIPTS_DIR.glob(fm.INVENTORY_GLOB))
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    measure = [i for i in inv["items"] if i.get("disposition") == "measure"]
    assert sorted(i["candidate_id"] for i in measure) == sorted(fm.CANDIDATES)
    assert [c["candidate_id"] for c in fm.candidates()] == sorted(fm.CANDIDATES)
    assert fm.L2_OPTIONS == ("polars_public", "pandas_category")  # 同 SPEC Task 2.1 與決定紀錄 canonical_source 值域
    # 改壞對照：盤點少一個 measure 項 ⇒ 斷言失敗
    broken = copy.deepcopy(inv)
    first = next(i for i in broken["items"] if i.get("disposition") == "measure")
    first["disposition"] = "keep"
    path = tmp_path / "inv.json"
    path.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AssertionError):
        fm.assert_candidate_set(path)


def test_plan_generation_count_and_freeze_estimate() -> None:
    plan = fm.plan(fm.DEFAULT_CELL)
    freeze = json.loads(next(fm.RECEIPTS_DIR.glob(fm.FREEZE_RECEIPT_GLOB)).read_text(encoding="utf-8"))
    assert plan["per_generation_seconds"] == freeze["freeze"]["cells"][fm.DEFAULT_CELL]["seconds"]
    # SPEC v9：改前 3（default、sigma、stat）＋選項 6（l2 兩、sigma 一、layer 一、winsor_core 兩；d* 不可達不生成、
    # winsor_responsibility 只 IC）＋交互 1 ＝ 10 次生成
    assert plan["generations_total"] == 10
    keys = [r["key"] for r in plan["items"]]
    assert len(keys) == len(set(keys))
    assert {r["key"] for r in plan["items"] if not r["generation"]} == {
        "winsor_responsibility__ic_winsor_off", "dstar_adf_sample_direction__unreachable"}
    assert not any(k.startswith("dstar_adf_sample_direction__first") or k.startswith("dstar_adf_sample_direction__last")
                   for k in keys)
    # 不同選項之 run 目錄不得相同：項目鍵即 run 目錄名
    assert "sigma_float64+preserve" in keys
    # 設定變體之秒數：凍結收據只有凍結設定之實測 ⇒ 不以之代替
    rows = {r["key"]: r for r in plan["items"]}
    assert rows["baseline__default"]["estimated_generation_seconds"] == plan["per_generation_seconds"]
    assert rows["baseline__stat"]["estimated_generation_seconds"] is None


def test_winsor_core_measured_on_stationarity_cell() -> None:
    """SPEC v9 補①：校準縮尾只在平穩化開啟時執行 ⇒ `winsor_core_calibration` 之改前與選項於「C 格＋fracdiff／ADF 開」。"""
    cell = fm.measure_cell(fm.DEFAULT_CELL, "stat")
    assert cell["id"] == "C_BTCUSDT_1h__stat" and cell["kind"] == "C"
    pre = fm.cell_preprocessing(cell)
    assert pre["fractional_differencing"] and pre["adf_differencing"]
    base_pre = fm.cell_preprocessing(fm.measure_cell(fm.DEFAULT_CELL, "default"))
    assert pre["winsorization"] == base_pre["winsorization"]  # 只開平穩化，縮尾設定不變
    rows = {r["key"]: r for r in fm.plan(fm.DEFAULT_CELL, ["winsor_core_calibration"])["items"]}
    assert set(rows) == {"baseline__stat", "winsor_core_calibration__unify_numba",
                         "winsor_core_calibration__unify_pandas"}
    assert all(r["baseline"] == "stat" and r["conflicts"] == [] for r in rows.values())
    # 改壞對照：若仍於預設 C 格（平穩化關）⇒ 計畫具名列出衝突
    spec = dict(fm.CANDIDATES["winsor_core_calibration"], baseline="default")
    original = fm.CANDIDATES["winsor_core_calibration"]
    fm.CANDIDATES["winsor_core_calibration"] = spec
    try:
        assert fm.requirement_conflicts("winsor_core_calibration", fm.DEFAULT_CELL)
    finally:
        fm.CANDIDATES["winsor_core_calibration"] = original


# ---------------------------------------------------------------------------------------------- 自證判定（純函式）

def _proof(role: str = "main", counters: Mapping[str, int] = (), violations: int = 0, **extra: Any) -> Dict[str, Any]:
    return {"pid": 1 if role == "main" else 2, "role": role, "counters": dict(counters),
            "violations": ["x"] * violations, "violation_count": violations, "overhead_seconds": 0.0,
            "samples": {}, "bindings": {}, "extra": extra}


@pytest.mark.parametrize("probes,good,bad_counters,bad_violations", [
    ({"sigma": "float64"}, {"sigma.calls": 3}, {}, 0),
    ({"sigma": "float64"}, {"sigma.calls": 3}, {"sigma.calls": 3}, 1),
    ({"layer_dtype": "preserve"}, {"layer_dtype.calls": 6, "layer_dtype.forced": 6}, {"layer_dtype.calls": 6}, 0),
    ({"layer_dtype": "preserve"}, {"layer_dtype.calls": 6, "layer_dtype.forced": 6},
     {"layer_dtype.calls": 6, "layer_dtype.forced": 6}, 1),
    ({"winsor_core": "unify_numba"}, {"winsor_core.calibration_fast_calls": 2, "winsor_core.preflight_calls": 1,
                                      "winsor_core.calibration_calls.preflight": 2}, {}, 0),
    ({"winsor_core": "unify_pandas"}, {"winsor_core.public_routed_to_pandas": 5, "winsor_core.preflight_calls": 1,
                                       "winsor_core.calibration_calls.preflight": 2},
     {"winsor_core.public_routed_to_pandas": 5, "winsor_core.preflight_calls": 1,
      "winsor_core.calibration_calls.preflight": 2}, 1),
    # 校準前置未執行（平穩化關）⇒ 自證失敗，即使核心改道有發生
    ({"winsor_core": "unify_numba"}, {"winsor_core.calibration_fast_calls": 2, "winsor_core.preflight_calls": 1,
                                      "winsor_core.calibration_calls.preflight": 2},
     {"winsor_core.calibration_fast_calls": 2, "winsor_core.calibration_calls.warmup_probe": 2}, 0),
    ({"l2": "polars_public"}, {"l2.polars_public_calls": 1, "l2.use.L5": 1}, {"l2.polars_public_calls": 1}, 0),
    ({"l2": "pandas_category"}, {"l2.pandas_category_calls": 1, "l2.use.L5": 1},
     {"l2.pandas_category_calls": 1, "l2.use.L5": 1, "l2.compute_all_polars": 1}, 0),
])
def test_verify_proof_pass_and_mutation(probes: Dict[str, str], good: Dict[str, int], bad_counters: Dict[str, int],
                                        bad_violations: int) -> None:
    assert fm.verify_proof(probes, [_proof(counters=good)])["passed"]
    bad = fm.verify_proof(probes, [_proof(counters=bad_counters, violations=bad_violations)])
    assert not bad["passed"] and bad["failures"]


def test_verify_proof_dstar_requires_effective_and_worker_records() -> None:
    probes = {"dstar": "first_n"}
    ok = [_proof(counters={"dstar.map_parallel_items": 4}),
          _proof("worker", {"dstar.parallel.calls": 10, "dstar.parallel.effective": 4})]
    assert fm.verify_proof(probes, ok)["passed"]
    # 平行派工而 worker 無探針紀錄（sitecustomize 未生效）⇒ 失敗
    no_worker = [_proof(counters={"dstar.map_parallel_items": 4, "dstar.serial.calls": 3, "dstar.serial.effective": 1})]
    assert not fm.verify_proof(probes, no_worker)["passed"]
    # 校準序列皆 ≤ N（取樣方向無從生效）⇒ 失敗
    ineffective = [_proof(counters={"dstar.serial.calls": 5})]
    assert not fm.verify_proof(probes, ineffective)["passed"]
    # 子行程安裝錯誤 ⇒ 失敗
    assert not fm.verify_proof(probes, ok, ["ImportError: x"])["passed"]


def test_dstar_slice_first_and_last_n() -> None:
    values = np.arange(30, dtype=np.float64)
    values[[3, 17]] = np.nan
    first, info_f = fm.dstar_slice(values, 10, "first_n")
    last, info_l = fm.dstar_slice(values, 10, "last_n")
    finite = values[np.isfinite(values)]
    assert info_f == {"L": 28, "N": 10, "start": 0, "end": 10} and np.array_equal(first, finite[:10])
    assert info_l == {"L": 28, "N": 10, "start": 18, "end": 28} and np.array_equal(last, finite[-10:])


# ---------------------------------------------------------------------------------------------- 探針於產品函式（子行程）

def test_sigma_probe_computes_float64_on_product_bindings(tmp_path: Path) -> None:
    out = _snippet(
        "import numpy as np, bottleneck as bn\n"
        "fm.install_probes({'sigma': 'float64'}, fm.Path(PROOF), 'main')\n"
        "from momentum.FeatureEngineering.preprocessing import _numba_transforms as nt, feature_preprocessor as fp\n"
        "rng = np.random.default_rng(0); arr = (1e6 + rng.standard_normal((300, 3))).astype(np.float32)\n"
        "m, s = fp._rolling_mean_std(arr, 50, min_periods=20)\n"
        "ref_m = bn.move_mean(arr.astype(np.float64), window=50, min_count=20, axis=0)\n"
        "f32_m = bn.move_mean(arr, window=50, min_count=20, axis=0)\n"
        "out = nt.transform_array_fast(arr, winsorize=True, winsor_method='sigma', winsor_window=50, winsor_min_periods=20)\n"
        "fm._log().flush()\n"
        "print(json.dumps({'dtype': str(m.dtype), 'equal_ref': bool(np.array_equal(m, ref_m, equal_nan=True)),"
        " 'differs_f32': bool(not np.array_equal(m, f32_m.astype(np.float64), equal_nan=True)), 'out': str(out.dtype)}))\n",
        tmp_path)
    got = json.loads(out.strip().splitlines()[-1])
    assert got == {"dtype": "float64", "equal_ref": True, "differs_f32": True, "out": "float32"}
    proofs = _proofs(tmp_path)
    verdict = fm.verify_proof({"sigma": "float64"}, proofs)
    assert verdict["passed"], verdict
    main = proofs[0]
    assert main["counters"]["sigma.calls"] >= 2 and main["counters"].get("sigma.input.float32", 0) >= 1
    assert all(main["bindings"]["sigma"].values()) and len(main["bindings"]["sigma"]) == 3


def test_dstar_probe_routes_parallel_and_only_dstar_serial_calls(tmp_path: Path) -> None:
    out = _snippet(
        "import numpy as np\n"
        "fm.install_probes({'dstar': 'last_n'}, fm.Path(PROOF), 'main')\n"
        "from momentum.FeatureEngineering.preprocessing import _slow_path_parallel as sp\n"
        "from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor as FP\n"
        "x = np.cumsum(np.random.default_rng(1).standard_normal(900))\n"
        "p_par = sp._statsmodels_adf_pvalue(x, sample_size=300)\n"
        "p_non = FP._adf_pvalue_for_values(x, sample_size=300)\n"
        "fm._log().flush()\n"
        "print(json.dumps({'p_par': p_par, 'p_non': p_non}))\n", tmp_path)
    got = json.loads(out.strip().splitlines()[-1])
    assert 0.0 <= got["p_par"] <= 1.0
    proofs = _proofs(tmp_path)
    counters = proofs[0]["counters"]
    assert counters["dstar.parallel.calls"] == 1 and counters["dstar.parallel.effective"] == 1
    # `_find_min_d` 之外之串行 ADF（非 d* 搜尋）原樣，不改取樣
    assert counters["dstar.serial.non_dstar_calls"] == 1 and "dstar.serial.calls" not in counters
    assert proofs[0]["samples"]["dstar.parallel"][0] == {"L": 900, "N": 300, "start": 600, "end": 900}
    assert fm.verify_proof({"dstar": "last_n"}, proofs)["passed"]


def test_layer_dtype_probe_preserves_single_tf_layer_dtype(tmp_path: Path) -> None:
    out = _snippet(
        "import numpy as np, pandas as pd\n"
        "from momentum.factories import create_feature_factory\n"
        "f = create_feature_factory(validate_continuity=False)\n"
        "frame = pd.DataFrame({'a': np.arange(5, dtype=np.float64) + 1e-9})\n"
        "before = str(f._execute_layer1_6('Layer X', lambda: frame).data['a'].dtype)\n"
        "fm.install_probes({'layer_dtype': 'preserve'}, fm.Path(PROOF), 'main')\n"
        "after = str(f._execute_layer1_6('Layer X', lambda: frame).data['a'].dtype)\n"
        "fm._log().flush()\n"
        "print(json.dumps({'before': before, 'after': after}))\n", tmp_path)
    assert json.loads(out.strip().splitlines()[-1]) == {"before": "float32", "after": "float64"}
    proofs = _proofs(tmp_path)
    assert fm.verify_proof({"layer_dtype": "preserve"}, proofs)["passed"]


def test_winsor_core_probes_route_calibration_and_public_cores(tmp_path: Path) -> None:
    out = _snippet(
        "import numpy as np, pandas as pd\n"
        "from momentum.factories import create_feature_factory\n"
        "from momentum.FeatureEngineering.feature_factory import FeatureFactory\n"
        "mode = sys.argv[-1] if False else None\n"
        "f = create_feature_factory(validate_continuity=False)\n"
        "cfg = f._resolve_config({})\n"
        "rng = np.random.default_rng(2); arr = rng.standard_cauchy((400, 4)).astype(np.float32)\n"
        "frame = pd.DataFrame(arr, columns=list('abcd'))\n"
        "w_real = FeatureFactory._calibration_winsorizer(f, cfg, '1h')\n"
        "pandas_out = w_real._apply_winsorization(frame).to_numpy(np.float32)\n"
        "ctx = w_real._build_registry_transform_context()\n"
        "fast_out = np.asarray(w_real._registry_fast_transform(np.ascontiguousarray(arr), ctx), np.float32)\n"
        "fm.install_probes({'winsor_core': 'unify_numba'}, fm.Path(PROOF), 'main')\n"
        "w = f._calibration_winsorizer(cfg, '1h')\n"
        "probe_out = w._apply_winsorization(frame).to_numpy(np.float32)\n"
        "fm._log().flush()\n"
        "print(json.dumps({'calib_eq_fast': bool(np.array_equal(probe_out, fast_out, equal_nan=True)),"
        " 'pandas_ne_fast': bool(not np.array_equal(pandas_out, fast_out, equal_nan=True))}))\n", tmp_path)
    got = json.loads(out.strip().splitlines()[-1])
    assert got["calib_eq_fast"] is True
    proofs = _proofs(tmp_path)
    assert proofs[0]["counters"]["winsor_core.calibration_fast_calls"] == 1
    assert proofs[0]["counters"]["winsor_core.calibration_calls.warmup_probe"] == 1
    # 直接呼叫（非校準前置內）⇒ 自證須失敗：校準前置未執行（SPEC v9 補①）
    verdict = fm.verify_proof({"winsor_core": "unify_numba"}, proofs)
    assert not verdict["passed"] and any("校準前置" in f for f in verdict["failures"])

    tmp2 = tmp_path / "p2"
    tmp2.mkdir()
    out2 = _snippet(
        "import numpy as np, pandas as pd\n"
        "from momentum.factories import create_feature_factory\n"
        "from momentum.FeatureEngineering.feature_factory import FeatureFactory\n"
        "f = create_feature_factory(validate_continuity=False)\n"
        "cfg = f._resolve_config({})\n"
        "rng = np.random.default_rng(2); arr = rng.standard_cauchy((400, 4)).astype(np.float32)\n"
        "w = FeatureFactory._calibration_winsorizer(f, cfg, '1h')\n"
        "pandas_ref = w._apply_winsorization(pd.DataFrame(arr, columns=list('abcd'))).to_numpy(np.float32)\n"
        "ctx = w._build_registry_transform_context()\n"
        "fm.install_probes({'winsor_core': 'unify_pandas'}, fm.Path(PROOF), 'main')\n"
        "routed = np.asarray(w._registry_fast_transform(np.ascontiguousarray(arr), ctx), np.float32)\n"
        "fm._log().flush()\n"
        "print(json.dumps({'public_eq_pandas': bool(np.array_equal(routed, pandas_ref, equal_nan=True))}))\n", tmp2)
    assert json.loads(out2.strip().splitlines()[-1]) == {"public_eq_pandas": True}
    counters = _proofs(tmp2)[0]["counters"]
    assert counters["winsor_core.public_routed_to_pandas"] == 1 and "winsor_core.transform_array_fast_calls" not in counters


def test_winsor_core_records_ratio_unsafe_calibration_selection(tmp_path: Path) -> None:
    """SPEC v9 補①：校準域縮尾對 ratio-unsafe 欄亦作用（公開快速臂跳過）——探針記欄集合、變動欄與最大差，並依呼叫點
    （校準前置內／預熱探測）分列。ratio-unsafe 判定以子行程內替換之判定函式模擬（只測記錄邏輯）。"""
    _snippet(
        "import numpy as np, pandas as pd\n"
        "import momentum.FeatureEngineering.feature_naming as fnm\n"
        "fnm.is_ratio_unsafe_column = lambda c: str(c).startswith('ru_')\n"
        "from momentum.factories import create_feature_factory\n"
        "from momentum.FeatureEngineering.feature_factory import FeatureFactory\n"
        "f = create_feature_factory(validate_continuity=False)\n"
        "cfg = f._resolve_config({})\n"
        "rng = np.random.default_rng(5); arr = rng.standard_cauchy((400, 3)).astype(np.float32)\n"
        "frame = pd.DataFrame(arr, columns=['ru_a', 'b', 'ru_c'])\n"
        "# 校準前置本體以替身代之（只驗呼叫點歸屬；探針包裝於其外）\n"
        "def fake_preflight(self, *a, **k):\n"
        "    return self._calibration_winsorizer(cfg, '1h')._apply_winsorization(frame)\n"
        "FeatureFactory.run_calibration_preflight = fake_preflight\n"
        "fm.install_probes({'winsor_core': 'observe'}, fm.Path(PROOF), 'main')\n"
        "f.run_calibration_preflight()\n"
        "f._calibration_winsorizer(cfg, '1h')._apply_winsorization(frame)\n"
        "fm._log().flush()\n", tmp_path)
    proofs = _proofs(tmp_path)
    ru = fm.ratio_unsafe_selection(proofs)
    assert ru is not None and set(ru) == {"preflight", "warmup_probe"}
    for node in ru.values():
        assert node["columns"] == ["ru_a", "ru_c"] and node["columns_winsorized_in_calibration"] == 2
        # 縮尾作用（含窗未湊滿之列遮 NaN）使兩欄皆變；對照之非 ratio-unsafe 欄 `b` 不入集合
        assert node["changed_columns"] == 2 and node["calls"] == 1 and "b" not in node["changed"]
    counters = proofs[0]["counters"]
    assert counters["winsor_core.calibration_pandas_core_calls"] == 2 and counters["winsor_core.preflight_calls"] == 1
    assert counters["winsor_core.calibration_calls.preflight"] == 1
    # observe 只記錄不判定
    assert fm.verify_proof({"winsor_core": "observe"}, proofs)["passed"]


# ---------------------------------------------------------------------------------------------- L2 取值點指紋

def test_l2_point_fingerprints_detect_single_cell_perturbation() -> None:
    import pandas as pd

    rng = np.random.default_rng(3)
    a = pd.DataFrame(rng.standard_normal((50, 6)), columns=[f"c{i}" for i in range(6)])
    b = a.copy()
    fa, fb_ = fm.f32_fingerprints(a), fm.f32_fingerprints(b.astype(np.float32))
    assert fm.compare_points(fa, fb_)["equal"]  # 共同消費 dtype（float32）比對：原生 float64 與其 float32 視為同值
    b.iloc[7, 2] += 1e-3  # SPEC Phase 3 邊界③ 之 mutation 量級
    cmp = fm.compare_points(fa, fm.f32_fingerprints(b))
    assert not cmp["equal"] and cmp["diff_values"] == 1 and cmp["examples"]["diff_values"] == ["c2"]
    reordered = fm.f32_fingerprints(a.iloc[:, ::-1])
    cmp2 = fm.compare_points(fa, reordered)
    assert cmp2["equal"] and not cmp2["order_equal"]
    merged = fm.merge_point_fps([fm.f32_fingerprints(a.iloc[:, :3]), fm.f32_fingerprints(a.iloc[:, 3:])])
    assert fm.compare_points(fa, merged)["equal"] and fm.compare_points(fa, merged)["order_equal"]


# ---------------------------------------------------------------------------------------------- 值差與 IC 導出

def _fp_cols(values: Mapping[str, np.ndarray]) -> Dict[str, Any]:
    return {n: fm.column_fingerprint(v, "float") for n, v in values.items()}


def test_value_diff_column_and_group_granularity() -> None:
    before = {"x": np.array([1.0, 2.0, np.nan], np.float32), "y": np.array([1.0, 1.0, 1.0], np.float32),
              "z": np.array([0.5, np.nan, 0.5], np.float32)}
    after = {"x": np.array([1.0, 2.5, np.nan], np.float32), "y": before["y"].copy(),
             "z": np.array([0.5, 0.25, 0.5], np.float32)}
    sides = {"before": before, "after": after}

    def reader(side: str, names: List[str]) -> Dict[str, Any]:
        return {n: (sides[side][n], "float") for n in names if n in sides[side]}

    col = fm.value_diff({"columns": _fp_cols(before)}, {"columns": _fp_cols(after)}, reader, lambda s, k: [])
    assert col["changed"] == ["x", "z"]
    assert col["summary"]["max_abs_diff"] == pytest.approx(0.5) and col["summary"]["nan_mask_diff_columns"] == 1
    assert set(col["fingerprints"]["before"]) == {"x", "z"} and set(col["fingerprints"]["after"]) == {"x", "z"}

    groups = {"g1": ["x", "y"], "g2": ["z"]}

    def gfp(vals: Mapping[str, np.ndarray]) -> Dict[str, Any]:
        return {"granularity": "group",
                "columns": {g: {k: "|".join(fm.column_fingerprint(vals[n], "float")[k] for n in ns)
                                for k in ("dtype", "nan", "values_native")} for g, ns in groups.items()}}

    grp = fm.value_diff(gfp(before), gfp(after), reader, lambda s, keys: [n for k in keys for n in groups[k]])
    assert grp["changed"] == ["x", "z"] and grp["summary"]["granularity"] == "group"
    same = fm.value_diff(gfp(before), gfp(before), reader, lambda s, keys: [n for k in keys for n in groups[k]])
    assert same["changed"] == [] and same["summary"]["changed_columns"] == 0


class _FakeAnalyzer:
    @staticmethod
    def _apply_thresholds(table: List[Dict[str, Any]], thresholds: Any, alpha: float, **_: Any) -> Any:
        passed = [r["feature_name"] for r in table if abs(r["ic_mean"]) >= 0.02 and r["p_value_adj"] <= alpha]
        return passed, {}


def _tools() -> Dict[str, Any]:
    def fdr(p: Mapping[str, float], alpha: float, method: str) -> Any:
        return dict(p), len(p)

    return {"analyzer": _FakeAnalyzer(), "config": type("C", (), {"thresholds": None})(), "alpha": 0.05,
            "apply_fdr": fdr, "fdr_enabled": True, "fdr_method": "fdr_bh"}


def test_ic_effect_sign_flips_and_selection_substitution() -> None:
    def row(name: str, ic: float, p: float) -> Dict[str, Any]:
        return {"feature_name": name, "ic_mean": ic, "p_value": p}

    base = {"a": row("a", 0.05, 0.01), "b": row("b", -0.03, 0.01), "c": row("c", 0.01, 0.5), "d": row("d", 0.04, 0.02)}
    option = {"a": row("a", -0.05, 0.01), "c": row("c", 0.06, 0.001)}
    eff = fm.ic_effect(base, option, ["a", "c"], _tools())
    assert eff["sign_flips"] == 1 and eff["sign_flip_examples"] == ["a"]
    assert eff["passed_before"] == 3 and eff["passed_after"] == 4
    assert eff["selection_in"] == 1 and eff["selection_in_examples"] == ["c"] and eff["selection_out"] == 0
    # 改值欄於選項 run 被剔除（無列）⇒ 自 universe 移除、計為選出
    eff2 = fm.ic_effect(base, {"a": row("a", 0.05, 0.01)}, ["a", "d"], _tools())
    assert eff2["selection_out"] == 1 and eff2["selection_out_examples"] == ["d"] and eff2["ic_nan_status_changes"] == 1


# ---------------------------------------------------------------------------------------------- 收據、續跑、拒寫

def _fake_gen(status: str = "ok", passed: bool = True) -> Dict[str, Any]:
    return {"status": status, "run_dir": "/nonexistent/run", "fingerprints": {"columns": {}},
            "identity": {"head": "h", "config_sha256": "c", "dataset_sha256": "d"}, "generation_seconds": 1.0,
            "seconds": 1.5, "peak_rss_bytes": 10, "peak_rss_tree_bytes": 12, "output_bytes": 100,
            "proof": {"passed": passed, "failures": [] if passed else ["mutation"], "per_probe": {},
                      "overhead_seconds": 0.0}}


def _diff(_b: Any, _g: Any) -> Dict[str, Any]:
    return {"summary": {"changed_columns": 1, "max_abs_diff": 0.5, "nan_mask_diff_columns": 0}, "changed": ["x"],
            "fingerprints": {"before": {"x": {"dtype": "float"}}, "after": {"x": {"dtype": "float"}}}}


def test_execute_writes_required_fields_and_resumes_without_regenerating(tmp_path: Path) -> None:
    calls: List[str] = []

    def generate(item: Mapping[str, Any], cell: Mapping[str, Any], item_dir: Path) -> Dict[str, Any]:
        calls.append(item["key"])
        return _fake_gen()

    items = fm.plan_items("A_BTCUSDT_1h", ["layer_dtype", "winsor_responsibility"])
    receipt_path = tmp_path / "r.json"
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff) == 0
    assert calls == ["baseline__default", "layer_dtype__preserve"]  # 只 IC 之選項不生成
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert sorted(receipt["candidates"]) == fm.inventory_measure_ids()
    rec = receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"]
    assert all(k in rec for k in fm.OPTION_REQUIRED_KEYS)
    assert rec["changed_columns"] == ["x"] and rec["value_diff"]["max_abs_diff"] == 0.5
    assert rec["identity"]["probe_sha256"] and rec["probe"]["paths"]["layer_dtype"].endswith("_install_layer_dtype")
    ic_only = receipt["candidates"]["winsor_responsibility"]["options"]["ic_winsor_off"]["cells"]["A_BTCUSDT_1h"]
    assert ic_only["changed_columns"] == [] and ic_only["run_dir"] == "/nonexistent/run"
    # 續跑：已完成者不重生
    calls.clear()
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff) == 0
    assert calls == []


def test_execute_refuses_option_when_self_proof_fails(tmp_path: Path) -> None:
    def generate(item: Mapping[str, Any], cell: Mapping[str, Any], item_dir: Path) -> Dict[str, Any]:
        return _fake_gen(passed=item["kind"] == "baseline")

    items = fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"])
    receipt_path = tmp_path / "r.json"
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff) == 3
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"] == {}
    # 對照：自證通過 ⇒ 寫入
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path,
                      generate=lambda i, c, d: _fake_gen(), diff=_diff) == 0
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert "A_BTCUSDT_1h" in receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]


def test_execute_records_hardware_block_without_perf_numbers(tmp_path: Path) -> None:
    def generate(item: Mapping[str, Any], cell: Mapping[str, Any], item_dir: Path) -> Dict[str, Any]:
        return _fake_gen() if item["kind"] == "baseline" else {**_fake_gen("blocked"), "error": "GenerationMemoryBudgetExceeded"}

    items = fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"])
    receipt_path = tmp_path / "r.json"
    fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff)
    rec = json.loads(receipt_path.read_text(encoding="utf-8"))["candidates"]["layer_dtype"]["options"]["preserve"][
        "cells"]["A_BTCUSDT_1h"]
    assert rec["status"] == "blocked"
    for key in ("seconds", "peak_rss_bytes", "output_bytes"):
        assert rec[key] == {"blocked_by": "hardware"}
    assert rec["value_diff"] is None and rec["value_diff_unavailable"]


def _dstar_gen(tests: int, effective: int, extra_failures: Sequence[str] = (), violations: int = 0) -> Dict[str, Any]:
    gen = _fake_gen(passed=effective > 0 and not extra_failures and not violations)
    gen["proof"]["failures"] = ([] if effective > 0 else [fm.DSTAR_NO_EFFECTIVE]) + list(extra_failures)
    gen["proof"]["violation_count"] = violations
    gen["proof"]["per_probe"] = {"dstar": {"serial_calls": tests, "parallel_calls": 0, "effective_calls": effective,
                                           "max_L": 1000 + effective, "N_values": [1000]}}
    return gen


def test_unreachable_candidate_records_evidence_without_cell_generation(tmp_path: Path) -> None:
    """SPEC v9 補②：d* 取樣方向不排本格生成；只於探針格（A）取一次探針收據，收據記 unreachable_difference＋碼證。"""
    seen: List[str] = []

    def generate(item: Mapping[str, Any], cell: Mapping[str, Any], item_dir: Path) -> Dict[str, Any]:
        seen.append(cell["id"])
        return _dstar_gen(382, 0)

    items = fm.plan_items(fm.DEFAULT_CELL, ["dstar_adf_sample_direction"])
    assert [i["kind"] for i in items] == ["unreachable"]  # 無改前基準、無選項生成
    receipt_path = tmp_path / "r.json"
    assert fm.execute(fm.DEFAULT_CELL, items, receipt_path, tmp_path, generate=generate, diff=_diff) == 0
    assert seen == ["A_BTCUSDT_1h__default"]
    node = json.loads(receipt_path.read_text(encoding="utf-8"))["candidates"]["dstar_adf_sample_direction"]
    assert node["status"] == "unreachable_difference"
    assert node["probe_receipt"]["tests"] == 382 and node["probe_receipt"]["L_gt_N_tests"] == 0
    assert node["probe_receipt"]["max_L"] == 1000 and node["probe_receipt"]["N_values"] == [1000]
    assert any(e.startswith("momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:2786")
               for e in node["evidence"])
    # 續跑不重跑探針
    seen.clear()
    assert fm.execute(fm.DEFAULT_CELL, items, receipt_path, tmp_path, generate=generate, diff=_diff) == 0
    assert seen == []


def test_unreachable_candidate_flags_reachable_when_probe_sees_l_gt_n(tmp_path: Path) -> None:
    items = fm.plan_items(fm.DEFAULT_CELL, ["dstar_adf_sample_direction"])
    receipt_path = tmp_path / "r.json"
    rc = fm.execute(fm.DEFAULT_CELL, items, receipt_path, tmp_path, generate=lambda i, c, d: _dstar_gen(10, 3),
                    diff=_diff)
    assert rc == 3
    node = json.loads(receipt_path.read_text(encoding="utf-8"))["candidates"]["dstar_adf_sample_direction"]
    assert node["status"] == "reachable_measure_required" and node["probe_receipt"]["L_gt_N_tests"] == 3


@pytest.mark.parametrize("extra,violations", [(["mutation"], 0), ([], 1),
                                              (["dstar：平行派工 4 項而 worker 無探針紀錄"], 0)])
def test_unreachable_candidate_rejects_broken_probe(tmp_path: Path, extra: List[str], violations: int) -> None:
    """自證完整性：只豁免「無 L＞N 檢定」本身；其他自證失敗或取樣違規 ⇒ probe_invalid、rc 3，不記不可達、續跑重做。"""
    items = fm.plan_items(fm.DEFAULT_CELL, ["dstar_adf_sample_direction"])
    receipt_path = tmp_path / "r.json"
    gen = lambda i, c, d: _dstar_gen(382, 0, extra, violations)  # noqa: E731
    assert fm.execute(fm.DEFAULT_CELL, items, receipt_path, tmp_path, generate=gen, diff=_diff) == 3
    node = json.loads(receipt_path.read_text(encoding="utf-8"))["candidates"]["dstar_adf_sample_direction"]
    assert node["status"] == "probe_invalid" and node["unexpected_failures"] == extra
    assert node["probe_receipt"]["violation_count"] == violations
    seen: List[str] = []
    assert fm.execute(fm.DEFAULT_CELL, items, receipt_path, tmp_path,
                      generate=lambda i, c, d: (seen.append(c["id"]), _dstar_gen(382, 0))[1], diff=_diff) == 0
    assert seen == ["A_BTCUSDT_1h__default"]


def test_baseline_self_proof_failure_is_not_frozen_and_reruns(tmp_path: Path) -> None:
    """改前基準自證失敗 ⇒ 記 self_proof_failed（非 frozen）、rc 3、依賴之選項不跑；續跑重做基準。"""
    calls: List[str] = []

    def generate(item: Mapping[str, Any], cell: Mapping[str, Any], item_dir: Path) -> Dict[str, Any]:
        calls.append(item["kind"])
        return _fake_gen(passed=item["kind"] != "baseline" or len(calls) > 1)

    items = fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"])
    receipt_path = tmp_path / "r.json"
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff) == 3
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["baselines"]["A_BTCUSDT_1h"]["default"]["status"] == "self_proof_failed"
    assert calls == ["baseline"]  # 選項未以壞基準生成
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff) == 0
    assert calls == ["baseline", "baseline", "option"]


def test_measured_without_ic_is_not_done_and_resume_only_runs_ic(tmp_path: Path) -> None:
    """`--skip-ic`（ic=None）留下之 measured 紀錄於要求 IC 時非完成；續跑不重生成、只補 IC。"""
    gens: List[str] = []
    ic_calls: List[str] = []

    def generate(item: Mapping[str, Any], cell: Mapping[str, Any], item_dir: Path) -> Dict[str, Any]:
        gens.append(item["kind"])
        return _fake_gen()

    def ic(receipt: Dict[str, Any], cell_id: str, item: Mapping[str, Any]) -> None:
        ic_calls.append(item["key"])
        fm._item_node(receipt, cell_id, item)["ic"] = {"mode": "changed_columns", "ic_settings": fm.IC_MEASURE_SETTINGS}

    items = fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"])
    receipt_path = tmp_path / "r.json"
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff) == 0
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    opt = next(i for i in items if i["kind"] == "option")
    assert fm._item_done(receipt, "A_BTCUSDT_1h", opt, need_ic=False)
    assert not fm._item_done(receipt, "A_BTCUSDT_1h", opt)
    assert fm.plan("A_BTCUSDT_1h", ["layer_dtype"], receipt)["items"][-1]["status"] == "pending"
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff, ic=ic) == 0
    assert gens == ["baseline", "option"] and ic_calls == [opt["key"]]
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff, ic=ic) == 0
    assert gens == ["baseline", "option"] and ic_calls == [opt["key"]]


def test_ic_failure_persists_state_and_resume_retries_ic(tmp_path: Path) -> None:
    """IC 步失敗：其就地改之狀態落盤；未寫 `ic` ⇒ 續跑只補 IC（不重生成）；IC 自證失敗（self_proof_failed）⇒ 續跑重做該項。"""
    gens: List[str] = []
    attempts: List[str] = []

    def generate(item: Mapping[str, Any], cell: Mapping[str, Any], item_dir: Path) -> Dict[str, Any]:
        gens.append(item["kind"])
        return _fake_gen()

    def ic(receipt: Dict[str, Any], cell_id: str, item: Mapping[str, Any]) -> None:
        attempts.append(item["key"])
        node = fm._item_node(receipt, cell_id, item)
        if len(attempts) == 1:
            raise RuntimeError("IC 子行程未寫結果")
        if len(attempts) == 2:
            node["ic"] = {"self_proof": {"passed": False}}
            node["status"] = "self_proof_failed"
            raise fm.SelfProofFailed("IC 自證失敗")
        node["ic"] = {"mode": "changed_columns", "ic_settings": fm.IC_MEASURE_SETTINGS}

    items = fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"])
    receipt_path = tmp_path / "r.json"
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff, ic=ic) == 3
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff, ic=ic) == 3
    assert gens == ["baseline", "option"]  # 第二次只補 IC
    opt = next(i for i in items if i["kind"] == "option")
    node = fm._item_node(json.loads(receipt_path.read_text(encoding="utf-8")), "A_BTCUSDT_1h", opt)
    assert node["status"] == "self_proof_failed"  # IC 步改之狀態已落盤
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=generate, diff=_diff, ic=ic) == 0
    assert gens == ["baseline", "option", "option"] and len(attempts) == 3


def test_heartbeat_line_only_when_cpu_advances_by_fraction() -> None:
    """心跳只在窗內行程樹 CPU 前進 ≥ 四分之一經過秒數時寫；閒置（取樣執行緒約 1% 核）與 0 秒窗不寫。"""
    assert fm.heartbeat_line(100.0, 160.0, 60.0) is not None  # 一核滿載
    assert fm.heartbeat_line(100.0, 115.0, 60.0) is not None  # 恰四分之一核
    assert fm.heartbeat_line(100.0, 114.9, 60.0) is None
    assert fm.heartbeat_line(100.0, 100.6, 60.0) is None  # 閒置
    assert fm.heartbeat_line(100.0, 200.0, 0.0) is None
    before = fm.tree_cpu_seconds()  # 真讀取器：忙迴圈後行程樹 CPU 前進
    end = fm.time.perf_counter() + 0.3
    while fm.time.perf_counter() < end:
        pass
    assert fm.tree_cpu_seconds() - before >= 0.2


def test_cpu_heartbeat_writes_while_busy_and_stays_silent_when_idle(capsys: pytest.CaptureFixture[str]) -> None:
    """忙（CPU 隨牆鐘前進）⇒ 有心跳行；卡住（CPU 不動）⇒ 無心跳行，log 靜默條件照常生效。"""
    import time as _time

    t0 = _time.monotonic()
    with fm.cpu_heartbeat(interval=0.05, read_cpu=lambda: (_time.monotonic() - t0) * 2.0):
        _time.sleep(0.4)
    assert "[ffprod-heartbeat]" in capsys.readouterr().err
    with fm.cpu_heartbeat(interval=0.05, read_cpu=lambda: 5.0):
        _time.sleep(0.4)
    assert "[ffprod-heartbeat]" not in capsys.readouterr().err


def test_hang_stops_whole_run_without_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """程式卡住（HangDetected）⇒ 整跑停止、rc 4、不自動重跑（execute 只呼叫一次）；現場檔已寫。"""
    import argparse
    import types

    calls: List[int] = []

    def fake_execute(*a: Any, **k: Any) -> int:
        calls.append(1)
        watched = types.SimpleNamespace(reason="log 檔 600 秒未增長且 CPU 無進度", cause="hang", wall_seconds=900.0,
                                        diagnosis={"stacks_file": "/x.stacks.txt", "native_stacks": {}})
        fm.raise_hang("C 生成", watched, tmp_path)
        return 0

    monkeypatch.setattr(fm, "execute", fake_execute)
    args = argparse.Namespace(cell=fm.DEFAULT_CELL, candidates=None, receipt=str(tmp_path / "r.json"),
                              work_root=str(tmp_path), skip_ic=True)
    assert fm.run(args) == 4 and calls == [1]
    diag = json.loads((tmp_path / "stall_diagnosis.json").read_text(encoding="utf-8"))
    assert diag["cause"] == "hang" and diag["stacks_file"] == "/x.stacks.txt"
    assert not hasattr(fm, "run_with_retries") and not hasattr(fm, "MAX_PASSES")


def test_watchdog_stopped_results_are_never_done(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """監看終止（watchdog_timeout）之結果不算完成：IC 結果與改前全欄 IC 快取皆重算；硬體受阻者沿用。"""
    item = next(i for i in fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"]) if i["kind"] == "option")
    tagged = {"ic_settings": fm.IC_MEASURE_SETTINGS, "mode": "changed_columns"}
    assert fm.ic_current(tagged)
    assert not fm.ic_current({**tagged, "selection": {"blocked_by": "watchdog_timeout"}})
    assert not fm.ic_current({**tagged, "sign_flips": {"blocked_by": "hardware+watchdog_timeout"}})
    assert fm.ic_current({**tagged, "selection": {"blocked_by": "hardware"}})
    assert fm._needs_ic({"status": "measured", "ic": {**tagged, "selection": {"blocked_by": "watchdog_timeout"}}}, item)
    calls: List[Any] = []

    def watched(run_dir: Path, symbol: str, tf: str, include: Any, winsor_off: bool, item_dir: Path) -> Dict[str, Any]:
        calls.append(include)
        return {"status": "blocked", "blocked_by": "hardware", "reason": "記憶體守護"}

    monkeypatch.setattr(fm, "ic_watched", watched)
    for cause, rerun in (("watchdog_timeout", True), ("hardware", False)):
        calls.clear()
        receipt = fm.new_receipt("A_BTCUSDT_1h", tmp_path)
        receipt["baselines"]["A_BTCUSDT_1h"] = {"default": {"status": "frozen", "run_dir": str(tmp_path / "base")}}
        receipt["ic"]["baselines"]["A_BTCUSDT_1h"] = {"default": {"status": "blocked", "blocked_by": cause,
                                                                   "ic_settings": fm.IC_MEASURE_SETTINGS}}
        receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"] = {
            "status": "measured", "run_dir": str(tmp_path / "opt"), "changed_columns": ["x"]}
        fm.make_ic_step(tmp_path / "w")(receipt, "A_BTCUSDT_1h", item)
        assert (None in calls) == rerun, cause  # 改前全欄 IC：監看終止者重算、硬體受阻者沿用


def test_run_passes_expected_seconds_only_for_frozen_preprocessing(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """預期秒數（監看牆鐘上限之基準）只給與凍結格同設定之生成；設定變體（sigma、平穩化開）傳 None。"""
    seen: Dict[str, Any] = {}

    def fake_execute(cell_id: str, items: Any, receipt_path: Path, work_root: Path, *, generate: Any, diff: Any,
                     ic: Any = None) -> int:
        for bid in ("default", "sigma", "stat"):
            generate({"probes": {}}, fm.measure_cell(cell_id, bid), tmp_path / bid)
        unreachable = next(i for i in fm.plan_items(cell_id, ["dstar_adf_sample_direction"]))
        generate(unreachable, fm.measure_cell(unreachable["probe_cell"], unreachable["baseline"]), tmp_path / "probe")
        return 0

    monkeypatch.setattr(fm, "execute", fake_execute)
    monkeypatch.setattr(fm, "generate_watched",
                        lambda cell, probes, item_dir, expected: seen.__setitem__(Path(item_dir).name, expected) or {})
    import argparse

    args = argparse.Namespace(cell=fm.DEFAULT_CELL, candidates=None, receipt=str(tmp_path / "r.json"),
                              work_root=str(tmp_path), skip_ic=True)
    assert fm.run(args) == 0
    assert seen["default"] == fm.freeze_seconds(fm.DEFAULT_CELL) and seen["default"]
    assert seen["sigma"] is None and seen["stat"] is None
    # 不可達探針於 A 格生成 ⇒ 取 A 格自身之凍結秒數（非主格 C）
    assert seen["probe"] == fm.freeze_seconds("A_BTCUSDT_1h") != fm.freeze_seconds(fm.DEFAULT_CELL)
    plan = fm.plan(fm.DEFAULT_CELL, ["dstar_adf_sample_direction"])
    assert plan["items"][0]["probe_estimated_seconds"] == fm.freeze_seconds("A_BTCUSDT_1h")


def test_tree_cpu_seconds_degrades_when_children_unlistable(monkeypatch: pytest.MonkeyPatch,
                                                           capsys: pytest.CaptureFixture[str]) -> None:
    """子孫不可列舉（沙箱 PermissionError）⇒ 降級為本行程＋已回收子行程，仍隨計算前進；心跳執行緒遇讀取失敗不退出。"""
    import psutil
    import time as _time

    def deny(self: Any, recursive: bool = False) -> Any:
        raise PermissionError(1, "Operation not permitted (originated from sysctl(KERN_PROC_ALL))")

    monkeypatch.setattr(psutil.Process, "children", deny)
    before = fm.tree_cpu_seconds()
    end = _time.perf_counter() + 0.3
    while _time.perf_counter() < end:
        pass
    assert fm.tree_cpu_seconds() - before >= 0.2
    t0 = _time.monotonic()
    calls = {"n": 0}

    def flaky() -> float:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise PermissionError("denied")
        return (_time.monotonic() - t0) * 2.0

    with fm.cpu_heartbeat(interval=0.05, read_cpu=flaky):
        _time.sleep(0.5)
    assert "[ffprod-heartbeat]" in capsys.readouterr().err and calls["n"] > 3


@pytest.mark.parametrize("watched,expected", [
    # 程式卡住（監看判 hang）⇒ 整跑停止（HangDetected），不記為受阻、不自動重跑
    ({"status": "stalled", "reason": "log 檔 600 秒未增長且 CPU 無進度", "returncode": -15, "cause": "hang"}, "hang"),
    # 記憶體證據 ⇒ hardware：監看判 memory、訊號終止未寫結果、子行程記憶體守護
    ({"status": "stalled", "reason": "swap 自啟動增長 3000 MB > 門檻 1000 MB 連續 2 次", "returncode": -15,
      "swap": 3000.0, "threshold": 1000.0, "cause": "memory"}, "hardware"),
    ({"status": "exited", "reason": None, "returncode": -9}, "hardware"),
    ({"status": "exited", "reason": None, "returncode": 0, "child": {"status": "blocked", "error": "MemoryError"}},
     "hardware"),
])
def test_ic_watched_separates_hang_from_hardware(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, watched: Dict[str, Any], expected: str) -> None:
    """IC 監看依監看之原因判定分流：hang ⇒ 留現場、拋 HangDetected（整跑停止）；記憶體證據 ⇒ blocked hardware。"""
    import types

    result = types.SimpleNamespace(status=watched["status"], reason=watched["reason"], returncode=watched["returncode"],
                                   wall_seconds=1.0, swap_growth_max_mb=watched.get("swap", 0.0),
                                   swap_growth_threshold_mb=watched.get("threshold"), cause=watched.get("cause"),
                                   diagnosis={"stacks_file": None, "native_stacks": {}})
    real = fm._fb()

    def run_watched(*a: Any, **k: Any) -> Any:
        if "child" in watched:
            real._write_atomic(tmp_path / "ic" / "ic_result.json", watched["child"])
        return result

    real_wd = real._watchdog()
    wd = types.SimpleNamespace(STALLED="stalled", run_watched=run_watched, load_config=real_wd.load_config,
                               CAUSE_MEMORY=real_wd.CAUSE_MEMORY, CAUSE_HANG=real_wd.CAUSE_HANG)
    fake = types.SimpleNamespace(_watchdog=lambda: wd, _criteria=real._criteria, _write_atomic=real._write_atomic)
    monkeypatch.setattr(fm, "_fb", lambda: fake)
    if expected == "hang":
        with pytest.raises(fm.HangDetected):
            fm.ic_watched(tmp_path / "run", "BTCUSDT", "1h", None, False, tmp_path / "ic")
        assert json.loads((tmp_path / "ic" / "stall_diagnosis.json").read_text(encoding="utf-8"))["cause"] == "hang"
        return
    out = fm.ic_watched(tmp_path / "run", "BTCUSDT", "1h", None, False, tmp_path / "ic")
    assert out["status"] == "blocked" and out["blocked_by"] == expected
    summary = fm.blocked_summary({"baseline_full": out, "option_changed": {"status": "ok"}})
    assert summary["blocked_by"] == expected and set(summary["causes"]) == {"baseline_full"}
    mixed = fm.blocked_summary({"a": out, "b": {"status": "blocked", "blocked_by": "hardware"}})
    assert mixed["blocked_by"] == "+".join(sorted({expected, "hardware"}))


def test_ic_override_turns_decay_off_and_self_proof_rejects_decay(tmp_path: Path) -> None:
    """量測之 IC 一律關衰減（IC 頁預設請求深合併 IC_MEASURE_OVERRIDE；縮尾關者亦同）；報告帶 ic_decay ⇒ 自證拒收。"""
    request = fm.ic_request("BTCUSDT", "1h", "h", ["x"])
    for winsor_off in (False, True):
        override = fm.ic_override(request, winsor_off)
        assert override["report"]["include_decay_analysis"] is False
        assert (override.get("preprocessing", {}).get("winsorization", {}).get("enabled") is False) == winsor_off
    off = fm.ic_override(request, False)
    assert fm.assert_decay_off({"ic_decay": {}}, off) == 0
    for report, ov in (({"ic_decay": {"x": {"half_life": None}}}, off),  # 報告有衰減結果
                       ({}, off),  # 報告缺 ic_decay 鍵
                       ({"ic_decay": None}, off),
                       ({"ic_decay": {}}, {"report": {"include_decay_analysis": True}}),  # 覆寫未關
                       ({"ic_decay": {}}, {}),  # 覆寫缺鍵
                       ({"ic_decay": {}}, None)):
        with pytest.raises(RuntimeError):
            fm.assert_decay_off(report, ov)


def test_premise_mismatches_cover_stage5_inputs_and_nan() -> None:
    """替換前提逐欄比第 5 階段實讀之輸入（非只四欄）；兩側皆 NaN 為一致；stage1 去留不同為不一致。"""
    nan = float("nan")
    row = {k: 0.1 for k in fm.PREMISE_KEYS}
    assert fm.premise_mismatches({"x": row}, {"x": dict(row)}, ["x"]) == []
    for key in fm.PREMISE_KEYS:
        assert fm.premise_mismatches({"x": row}, {"x": {**row, key: 0.2}}, ["x"]) == ["x"], key
    assert fm.premise_mismatches({"x": {**row, "coverage": nan}}, {"x": {**row, "coverage": nan}}, ["x"]) == []
    assert fm.premise_mismatches({"x": row}, {}, ["x"]) == ["x"]
    assert fm.premise_mismatches({}, {"x": row}, ["x"]) == ["x"]
    assert fm.premise_mismatches({}, {}, ["x"]) == []
    assert "p_value_adj" not in fm.PREMISE_KEYS  # 全 universe FDR，替換後重算


def test_ic_results_from_other_settings_are_recomputed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """收據中非現行設定（衰減開）所算之 IC 結果與改前全欄 IC 快取皆非完成：續跑只重算 IC、不重生成；無改值欄者不依設定。"""
    item = next(i for i in fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"]) if i["kind"] == "option")
    node = {"status": "measured", "ic": {"mode": "changed_columns", "sign_flips": 0}}
    assert fm._needs_ic(node, item)
    node["ic"]["ic_settings"] = fm.IC_MEASURE_SETTINGS
    assert not fm._needs_ic(node, item)
    assert not fm._needs_ic({"status": "measured", "ic": {"mode": "no_changed_columns"}}, item)
    calls: List[Any] = []

    def watched(run_dir: Path, symbol: str, tf: str, include: Any, winsor_off: bool, item_dir: Path) -> Dict[str, Any]:
        calls.append(include)
        return {"status": "blocked", "blocked_by": "watchdog_timeout", "reason": "牆鐘"}

    monkeypatch.setattr(fm, "ic_watched", watched)
    receipt = fm.new_receipt("A_BTCUSDT_1h", tmp_path)
    receipt["baselines"]["A_BTCUSDT_1h"] = {"default": {"status": "frozen", "run_dir": str(tmp_path / "base")}}
    receipt["ic"]["baselines"]["A_BTCUSDT_1h"] = {"default": {"status": "blocked", "blocked_by": "watchdog_timeout"}}
    receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"] = {
        "status": "measured", "run_dir": str(tmp_path / "opt"), "changed_columns": ["x"],
        "ic": {"mode": "changed_columns", "sign_flips": 0}}
    fm.make_ic_step(tmp_path / "w")(receipt, "A_BTCUSDT_1h", item)
    assert None in calls  # 舊設定之改前全欄 IC 快取（無 ic_settings）被重算
    rec = receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"]
    assert rec["ic"]["ic_settings"] == fm.IC_MEASURE_SETTINGS
    assert receipt["ic"]["baselines"]["A_BTCUSDT_1h"]["default"]["ic_settings"] == fm.IC_MEASURE_SETTINGS


def test_receipt_spec_version_follows_spec_header(tmp_path: Path) -> None:
    """收據之 spec 欄取 SPEC 檔頭現行版本（不寫死字面）並附 SPEC 雜湊。"""
    spec = tmp_path / "S.md"
    spec.write_text("# T\n\n> 版本：v12（2026-10-27；說明）；v11（舊）\n", encoding="utf-8")
    assert fm.spec_version(spec) == "v12"
    header = fm.SPEC_PATH.read_text(encoding="utf-8").splitlines()[2]
    assert fm.new_receipt(fm.DEFAULT_CELL, tmp_path)["spec"] == \
        f"docs/FFPROD_SPEC.md {header.split('版本：', 1)[1].split('（', 1)[0]} Task 2.1"
    spec.write_text("# T\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        fm.spec_version(spec)


def test_ic_step_sign_flips_on_changed_columns_and_selection_blocked_by_hardware(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC v9 補③：翻轉只用改值欄之兩側 IC；改前全欄 IC 受阻（卡死監看／逾記憶體）⇒ 選欄進出記 blocked_by hardware，
    第 6 階段註明不導出。對照：全欄 IC 可得 ⇒ 第 5 階段選欄由替換推導並驗替換前提。"""
    def row(ic: float) -> Dict[str, Any]:
        return {"ic_mean": ic, "icir": 1.0, "p_value": 0.01, "t_stat": 2.0}

    calls: List[Any] = []

    def make_watched(full_blocked: bool) -> Any:
        def watched(run_dir: Path, symbol: str, tf: str, include: Any, winsor_off: bool, item_dir: Path) -> Dict[str, Any]:
            calls.append((str(run_dir), include))
            if include is None:
                if full_blocked:
                    return {"status": "blocked", "blocked_by": "hardware", "reason": "卡死監看終止"}
                return {"status": "ok", "rows": {"x": {**row(0.05), "feature_name": "x"},
                                                 "y": {**row(0.03), "feature_name": "y"}},
                        "override": None, "seconds": 1.0, "peak_rss_bytes": 1, "config_sha256": "c",
                        "stage1_winsorized_count": 2, "passed_count_from_report": 2, "stage5": {}}
            ic = -0.01 if str(run_dir).endswith("opt") else 0.05  # 選項：翻號且跌破門檻；改前子集＝全欄列（替換前提成立）
            return {"status": "ok", "rows": {"x": {**row(ic), "feature_name": "x"}}, "seconds": 1.0, "peak_rss_bytes": 1}
        return watched

    monkeypatch.setattr(fm, "_selection_tools", lambda override: _tools())
    for full_blocked in (True, False):
        receipt = fm.new_receipt("A_BTCUSDT_1h", tmp_path)
        receipt["baselines"]["A_BTCUSDT_1h"] = {"default": {"status": "frozen", "run_dir": str(tmp_path / "base")}}
        item = next(i for i in fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"]) if i["kind"] == "option")
        receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"] = {
            "status": "measured", "run_dir": str(tmp_path / "opt"), "changed_columns": ["x"]}
        monkeypatch.setattr(fm, "ic_watched", make_watched(full_blocked))
        fm.make_ic_step(tmp_path / f"w{full_blocked}")(receipt, "A_BTCUSDT_1h", item)
        ic = receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"]["ic"]
        assert ic["sign_flips"] == 1 and ic["sign_flip_columns"] == 1
        assert ic["stage6_redundancy"].startswith("不導出")
        if full_blocked:
            assert ic["selection"]["blocked_by"] == "hardware"
            assert receipt["ic"]["baselines"]["A_BTCUSDT_1h"]["default"]["status"] == "blocked"
        else:
            assert ic["substitution_premise"]["holds"] is True
            assert ic["selection"]["selection_out"] == 1 and ic["selection"]["passed_before"] == 2


@pytest.mark.parametrize("mode", ["baseline_changed_blocked", "premise_mismatch", "premise_mismatch_hit_rate"])
def test_ic_step_selection_requires_substitution_premise(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    """選欄由替換推導，須改前改值欄子集可得且與改前全欄 IC 相同：子集受阻 ⇒ selection 記 blocked_by hardware；
    子集與全欄不符 ⇒ 前提不成立、不輸出選欄數字。"""
    def row(ic: float) -> Dict[str, Any]:
        return {"ic_mean": ic, "icir": 1.0, "p_value": 0.01, "t_stat": 2.0}

    def watched(run_dir: Path, symbol: str, tf: str, include: Any, winsor_off: bool, item_dir: Path) -> Dict[str, Any]:
        if include is None:
            return {"status": "ok", "rows": {"x": {**row(0.05), "feature_name": "x"},
                                             "y": {**row(0.03), "feature_name": "y"}},
                    "override": None, "seconds": 1.0, "peak_rss_bytes": 1, "config_sha256": "c",
                    "stage1_winsorized_count": 2, "passed_count_from_report": 2, "stage5": {}}
        if str(run_dir).endswith("opt"):
            return {"status": "ok", "rows": {"x": {**row(-0.01), "feature_name": "x"}}, "seconds": 1.0, "peak_rss_bytes": 1}
        if mode == "baseline_changed_blocked":
            return {"status": "blocked", "blocked_by": "hardware", "reason": "卡死監看終止"}
        if mode == "premise_mismatch_hit_rate":  # 四欄相同、只第 5 階段另讀之 ic_hit_rate 不同
            return {"status": "ok", "rows": {"x": {**row(0.05), "ic_hit_rate": 0.1, "feature_name": "x"}},
                    "seconds": 1.0, "peak_rss_bytes": 1}
        return {"status": "ok", "rows": {"x": {**row(0.04), "feature_name": "x"}}, "seconds": 1.0, "peak_rss_bytes": 1}

    monkeypatch.setattr(fm, "_selection_tools", lambda override: _tools())
    monkeypatch.setattr(fm, "ic_watched", watched)
    receipt = fm.new_receipt("A_BTCUSDT_1h", tmp_path)
    receipt["baselines"]["A_BTCUSDT_1h"] = {"default": {"status": "frozen", "run_dir": str(tmp_path / "base")}}
    item = next(i for i in fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"]) if i["kind"] == "option")
    receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"] = {
        "status": "measured", "run_dir": str(tmp_path / "opt"), "changed_columns": ["x"]}
    fm.make_ic_step(tmp_path / "w")(receipt, "A_BTCUSDT_1h", item)
    ic = receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"]["ic"]
    assert "selection_out" not in ic["selection"] and "selection_in" not in ic["selection"]
    if mode == "baseline_changed_blocked":
        assert ic["selection"]["blocked_by"] == "hardware"
        assert set(ic["selection"]["reason"]) == {"baseline_changed"}
    else:
        assert ic["substitution_premise"] == {**ic["substitution_premise"], "holds": False, "mismatched": 1,
                                              "checked_columns": 1}
        assert ic["selection"]["mismatched"] == 1 and "not_derived" in ic["selection"]


def test_large_fingerprint_sets_go_to_sidecar_with_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fm, "SIDECAR_MIN_COLUMNS", 0)
    items = fm.plan_items("A_BTCUSDT_1h", ["layer_dtype"])
    receipt_path = tmp_path / "r.json"
    assert fm.execute("A_BTCUSDT_1h", items, receipt_path, tmp_path, generate=lambda i, c, d: _fake_gen(),
                      diff=_diff) == 0
    rec = json.loads(receipt_path.read_text(encoding="utf-8"))["candidates"]["layer_dtype"]["options"]["preserve"][
        "cells"]["A_BTCUSDT_1h"]
    side = receipt_path.parent / rec["fingerprints"]["sidecar"]
    assert fm._sha256_file(side) == rec["fingerprints"]["sha256"]
    assert json.loads(side.read_text(encoding="utf-8"))["after"] == {"x": {"dtype": "float"}}


def test_check_receipt_rejects_missing_option_fields(tmp_path: Path) -> None:
    receipt = fm.new_receipt("A_BTCUSDT_1h", tmp_path)
    receipt["candidates"]["layer_dtype"]["options"]["preserve"]["cells"]["A_BTCUSDT_1h"] = {"option": "preserve"}
    with pytest.raises(AssertionError):
        fm.check_receipt(receipt)
    receipt2 = fm.new_receipt("A_BTCUSDT_1h", tmp_path)
    receipt2["candidates"].pop("layer_dtype")
    with pytest.raises(AssertionError):
        fm.check_receipt(receipt2)
