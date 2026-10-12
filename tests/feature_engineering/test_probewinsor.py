"""PROBEWINSOR（docs/PROBEWINSOR_SPEC.md §V）驗收：前處理總開關單一判斷、公開域預熱探測縮尾同源、快取身分。

真實 kline（`data_cache/feature_klines/kline_cache.h5`）；設定格唯一定義＝`tests/_golden/probewinsor/contract.json`；
錨點基準＝`tests/_golden/probewinsor/baseline.json`（Task 1.0 凍結，只讀）。同一 pytest 程序內同格只生成一次
（mutation 案一律重新生成、不經快取）。比較鍵與設定回顯之排除見 SPEC §V。
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

import pytest

from tests.feature_engineering import probewinsor_helpers as ph

pytestmark = pytest.mark.requires_kline

_SPEC = ph.contract()
_CELLS = {c["id"]: c for c in _SPEC["cells"]}
_FAMILIES = _SPEC["families"]
_PAIR_FAMILIES = sorted(f for f in _FAMILIES if f"{f}.off.w1" in _CELLS and f"{f}.off.w0" in _CELLS)
_ON_CELLS = sorted(c for c, v in _CELLS.items() if v["pp"])
_OFF_W0_CELLS = sorted(c for c, v in _CELLS.items() if not v["pp"] and not v["winsor"])
_OFF_W1_CELLS = sorted(c for c, v in _CELLS.items() if not v["pp"] and v["winsor"])
_NOSTART_CELLS = sorted(c for c, v in _CELLS.items() if _FAMILIES[v["family"]]["window"][0] is None)

_MSG_PRE = ("FactoryConfig.preprocessing is missing; cannot dispatch L6.5 mode "
            "(expected explicit Mode A/B/C selection).")
_MSG_ENABLED = "FactoryConfig.preprocessing.enabled is missing; cannot dispatch L6.5 mode (expected bool)."

_RUNS: Dict[str, Dict[str, Any]] = {}


@pytest.fixture(scope="module")
def work_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("probewinsor")


def _run(cell_id: str, work_root: Path) -> Dict[str, Any]:
    if cell_id not in _RUNS:
        _RUNS[cell_id] = ph.run_cell(_CELLS[cell_id], work_root)
    return _RUNS[cell_id]


def _fresh(cell_id: str, work_root: Path) -> Dict[str, Any]:
    return ph.run_cell(_CELLS[cell_id], work_root / "mutant")


def _factory() -> Any:
    from momentum.factories import create_feature_factory

    return create_feature_factory(cache_dir=str(ph.REPO / _SPEC["kline_dir"]), validate_continuity=False)


def _hash_of(factory: Any, cell_id: str) -> str:
    cell = _CELLS[cell_id]
    fam = _FAMILIES[cell["family"]]
    config = factory._resolve_config(ph.cell_payload(cell))
    return factory._compute_config_hash(config, _SPEC["symbol"], fam["primary"],
                                        start_date=fam["window"][0], end_date=fam["window"][1])


def _identity_of(factory: Any, cell_id: str) -> str:
    """公開身分入口 `FeatureFactory.config_identity`（批次續跑核對所用，Task 1.4）。"""
    cell = _CELLS[cell_id]
    fam = _FAMILIES[cell["family"]]
    return factory.config_identity(_SPEC["symbol"], fam["primary"], ph.cell_payload(cell),
                                   fam["window"][0], fam["window"][1])


def _hash_violations(factory: Any) -> List[str]:
    """§P Task 1.2 三條邊界之違反清單（空＝通過）。"""
    frozen = ph.baseline()["cells"]
    out: List[str] = []
    for cell_id, cell in _CELLS.items():
        now = _hash_of(factory, cell_id)
        if cell["pp"] or not cell["winsor"]:
            if now != frozen[cell_id]["config_hash"]:
                out.append(f"{cell_id}: hash 應等於錨點")
        else:
            if now == frozen[cell_id]["config_hash"]:
                out.append(f"{cell_id}: hash 應不等於錨點")
            if _hash_of(factory, cell_id) != now:
                out.append(f"{cell_id}: hash 不穩定")
    return out


# ---------------------------------------------------------------- 邊界 01–06（真實生成）

@pytest.mark.parametrize("family", _PAIR_FAMILIES)
def test_boundary_01_master_off_child_inert(family: str, work_root: Path) -> None:
    """總開關關閉時縮尾子開關無任何效果：同族 off.w1 與 off.w0 之全部比較鍵（不含 hash）相等。"""
    on = _run(f"{family}.off.w1", work_root)
    off = _run(f"{family}.off.w0", work_root)
    assert ph.diff(on, off, ph.keys("no_hash")) == []


@pytest.mark.parametrize("cell_id", _ON_CELLS)
def test_boundary_02_master_on_unchanged(cell_id: str, work_root: Path) -> None:
    """總開關開之格修正前後逐位元相同（含 config_hash）。"""
    assert ph.diff(_run(cell_id, work_root), ph.baseline()["cells"][cell_id], ph.keys("all")) == []


@pytest.mark.parametrize("cell_id", _OFF_W0_CELLS)
def test_boundary_03_master_off_child_off_unchanged(cell_id: str, work_root: Path) -> None:
    """總開關關＋縮尾關之格修正前後逐位元相同（含 config_hash）。"""
    assert ph.diff(_run(cell_id, work_root), ph.baseline()["cells"][cell_id], ph.keys("all")) == []


@pytest.mark.parametrize("family", _PAIR_FAMILIES)
def test_boundary_04_child_on_equals_anchor_child_off(family: str, work_root: Path) -> None:
    """刻意差異釘於錨點：修正後 off.w1 等於錨點 off.w0（不含 hash）；錨點兩格之差異面等於 contract 所宣告
    （anchor_differs＝任一比較鍵不同、anchor_public_differs＝公開輸出鍵不同），防 oracle 空轉。"""
    frozen = ph.baseline()["cells"]
    assert ph.diff(_run(f"{family}.off.w1", work_root), frozen[f"{family}.off.w0"], ph.keys("no_hash")) == []
    anchor_gap = ph.diff(frozen[f"{family}.off.w1"], frozen[f"{family}.off.w0"], ph.keys("no_hash"))
    public_gap = ph.diff(frozen[f"{family}.off.w1"], frozen[f"{family}.off.w0"], ph.keys("public"))
    assert bool(anchor_gap) is bool(_FAMILIES[family]["anchor_differs"])
    assert bool(public_gap) is bool(_FAMILIES[family]["anchor_public_differs"])


def test_boundary_05_cache_identity() -> None:
    """off-only 鹽：總開關開或縮尾關之 hash 等於錨點；總開關關＋縮尾開之 hash 不等於錨點且穩定；鹽值取自 contract。"""
    factory = _factory()
    assert _hash_violations(factory) == []
    for cell_id, cell in _CELLS.items():
        config = factory._resolve_config(ph.cell_payload(cell))
        expected = _SPEC["salt"] if (not cell["pp"] and cell["winsor"]) else None
        assert factory._probe_gate_salt(config) == expected, cell_id
        assert _identity_of(factory, cell_id) == _hash_of(factory, cell_id), cell_id


@pytest.mark.parametrize("cell_id", _NOSTART_CELLS)
def test_boundary_06_no_start_date_unchanged(cell_id: str, work_root: Path) -> None:
    """未填起始日（探測不執行）之格修正前後全部比較鍵（不含 hash）相同。"""
    assert ph.diff(_run(cell_id, work_root), ph.baseline()["cells"][cell_id], ph.keys("no_hash")) == []


# ---------------------------------------------------------------- 邊界 07–08（單元）

def _bad_configs() -> List[Any]:
    winsor = SimpleNamespace(enabled=True)
    return [
        (SimpleNamespace(preprocessing=None), _MSG_PRE),
        (SimpleNamespace(preprocessing=SimpleNamespace(enabled=None, winsorization=winsor,
                                                       fractional_differencing=SimpleNamespace(enabled=False),
                                                       adf_differencing=SimpleNamespace(enabled=False))), _MSG_ENABLED),
    ]


@pytest.mark.parametrize("site", ["l65_enabled", "mode", "stack_bars", "stationarity", "winsorizer", "salt"])
@pytest.mark.parametrize("which", [0, 1])
def test_boundary_07_missing_master_key_raises(site: str, which: int) -> None:
    """總開關缺鍵：各呼叫點皆拋 ValueError 且訊息逐字等於 SPEC Task 1.1。"""
    from momentum.FeatureEngineering import warmup_window
    from momentum.FeatureEngineering.feature_config import l65_enabled
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    config, message = _bad_configs()[which]
    factory = _factory()
    calls = {
        "l65_enabled": lambda: l65_enabled(config),
        "mode": lambda: factory._resolve_l65_generation_mode(config),
        "stack_bars": lambda: warmup_window._collect_l65_stack_bars(config),
        "stationarity": lambda: FeatureFactory._stationarity_config_enabled(config),
        "winsorizer": lambda: factory._calibration_winsorizer(config, "1h"),
        "salt": lambda: factory._probe_gate_salt(config),
    }
    with pytest.raises(ValueError) as info:
        calls[site]()
    assert str(info.value) == message


def test_boundary_08_call_site_truth_table() -> None:
    """五個呼叫點於 contract 真值表輸入下之結果等於錨點凍結。"""
    assert ph.truth_table() == ph.baseline()["truth_table"]


def _baseline_add_commit() -> str:
    import subprocess

    proc = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--",
                           str(ph.BASELINE_PATH.relative_to(ph.REPO))],
                          cwd=str(ph.REPO), capture_output=True, text=True)
    commits = [c for c in proc.stdout.split() if c]
    return commits[-1] if proc.returncode == 0 and commits else ""


def test_boundary_10_baseline_provenance() -> None:
    """凍結來源：baseline 之 frozen_at_head 與首次加入 baseline 之提交，皆不含本票生產符號（＝改前碼之產物）。"""
    frozen = ph.baseline()
    assert _baseline_add_commit() != ""
    assert ph.absent_symbol_violations(frozen["frozen_at_head"]) == []
    assert ph.absent_symbol_violations(_baseline_add_commit()) == []
    # 產生 baseline 之輸入（契約、helper、凍結腳本）即 frozen_at_head 之已提交版本
    assert frozen["input_blobs"] == ph.input_blobs(frozen["frozen_at_head"])


# ---------------------------------------------------------------- mutation（改壞必紅）

def _anchor_calibration_winsorizer(self: Any, config: Any, timeframe: str) -> Any:
    """錨點碼態之 `_calibration_winsorizer`（只看縮尾子開關）。"""
    if not config.preprocessing.winsorization.enabled:
        return None
    from momentum.FeatureEngineering.preprocessing._native_tf_helpers import scale_preprocessing_config_for_native
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    winsor_config = scale_preprocessing_config_for_native(
        self._build_l7_raw_preprocessing_config(config), timeframe, config.timeframes.primary,
    )
    return FeaturePreprocessor(winsor_config)


def test_mutation_m1_probe_ignores_master(monkeypatch: pytest.MonkeyPatch, work_root: Path) -> None:
    """M1：探測縮尾器還原為只看子開關 ⇒ 邊界 01、04 之比較器回報差異。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    monkeypatch.setattr(FeatureFactory, "_calibration_winsorizer", _anchor_calibration_winsorizer)
    child_on = _fresh("e1h.off.w1", work_root)
    child_off = _fresh("e1h.off.w0", work_root)
    assert ph.diff(child_on, child_off, ph.keys("no_hash")) != []
    assert ph.diff(child_on, ph.baseline()["cells"]["e1h.off.w0"], ph.keys("no_hash")) != []


def test_mutation_m2_probe_never_winsorizes(monkeypatch: pytest.MonkeyPatch, work_root: Path) -> None:
    """M2：探測縮尾器恆回 None ⇒ 邊界 02 於 e1h 總開關開格偵出（首個有限值表）。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    monkeypatch.setattr(FeatureFactory, "_calibration_winsorizer", lambda self, config, timeframe: None)
    found = ph.diff(_fresh("e1h.on.w1", work_root), ph.baseline()["cells"]["e1h.on.w1"], ph.keys("all"))
    assert any(line.startswith("first_finite_sha256") for line in found)


def test_mutation_m3_mode_ignores_master(monkeypatch: pytest.MonkeyPatch, work_root: Path) -> None:
    """M3：L6.5 模式恆為 ic_first_pre（公開輸出忽略總開關）⇒ 邊界 01 之比較器回報差異。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    monkeypatch.setattr(FeatureFactory, "_resolve_l65_generation_mode", lambda self, config: "ic_first_pre")
    assert ph.diff(_fresh("e1h.off.w1", work_root), _fresh("e1h.off.w0", work_root), ph.keys("no_hash")) != []


def test_mutation_m4_salt_never(monkeypatch: pytest.MonkeyPatch) -> None:
    """M4：鹽恆不加 ⇒ 邊界 05③（總開關關＋縮尾開之 hash 應不等於錨點）偵出。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    monkeypatch.setattr(FeatureFactory, "_probe_gate_salt", lambda self, config: None)
    found = _hash_violations(_factory())
    assert found and all(cell_id in _OFF_W1_CELLS for cell_id in (v.split(":")[0] for v in found))


def test_mutation_m5_salt_always(monkeypatch: pytest.MonkeyPatch) -> None:
    """M5：鹽恆加 ⇒ 邊界 05①（總開關開之 hash 應等於錨點）偵出。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    monkeypatch.setattr(FeatureFactory, "_probe_gate_salt", lambda self, config: _SPEC["salt"])
    found = _hash_violations(_factory())
    assert any(v.split(":")[0] in _ON_CELLS for v in found)


def test_boundary_10b_provenance_detector_flags_post_change_code() -> None:
    """邊界 10b：凍結來源檢查遇「已含本票生產符號」之碼必報違反（邊界 10 之偵測器非空轉）；讀檔失敗亦報。"""
    import json as _json

    contract_rel = str(ph.CONTRACT_PATH.relative_to(ph.REPO))

    def _post_change(commit: str, path: str) -> str:
        if path == contract_rel:  # 清單取自該提交自身之契約
            return _json.dumps(_SPEC)
        return "\n".join(needle for p, needle in _SPEC["anchor_absent_symbols"] if p == path)

    found = ph.absent_symbol_violations("POST", reader=_post_change)
    assert len(found) == len(_SPEC["anchor_absent_symbols"])

    def _unreadable(commit: str, path: str) -> str:
        if path == contract_rel:
            return _json.dumps(_SPEC)
        raise RuntimeError("missing")

    assert len(ph.absent_symbol_violations("POST", reader=_unreadable)) == len(_SPEC["anchor_absent_symbols"])


def _freeze_module() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("freeze_probewinsor_baseline",
                                                  ph.REPO / "scripts" / "freeze_probewinsor_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stub_git(fz: Any, monkeypatch: pytest.MonkeyPatch, *, diff_rc: int = 0, others: str = "",
              head_rc: int = 0) -> None:
    """以確定之 git 結果替換凍結腳本之 `_git`（diff 皆回 diff_rc、ls-files --others 回 others、rev-parse HEAD 回 head_rc）。"""
    import subprocess

    def _git(*args: str) -> subprocess.CompletedProcess:
        if args[0] == "diff":
            return subprocess.CompletedProcess(args, diff_rc, "", "")
        if args[0] == "ls-files":
            return subprocess.CompletedProcess(args, 0, others, "")
        return subprocess.CompletedProcess(args, head_rc, "HEADSHA\n", "" if head_rc == 0 else "boom")

    monkeypatch.setattr(fz, "_git", _git)


def _run_freeze_write(fz: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Tuple[int, bool]:
    """以替身生成（不跑真實生成）執行凍結寫入模式，baseline 導向 tmp；回傳 (rc, 是否寫出 baseline)。"""
    target = tmp_path / "baseline.json"
    monkeypatch.setattr(fz.ph, "BASELINE_PATH", target)
    monkeypatch.setattr(fz, "run_all", lambda ids: {"contract_sha256": "c", "kline_sha256": "k", "cells": {},
                                                    "truth_table": []})
    monkeypatch.setattr(fz.ph, "input_blobs", lambda commit: {"x": "y"})
    return fz.main([]), target.exists()


def test_boundary_10c_freeze_gate_refuses_polluted_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """邊界 10c：實際凍結閘 `provenance_errors` 於 HEAD 含本票生產符號、生產碼或凍結輸入有改動、有未追蹤 .py、git 失敗時
    皆拒（rc 2 且不寫 baseline）；全部乾淨時放行寫入。"""
    fz = _freeze_module()
    _stub_git(fz, monkeypatch)
    monkeypatch.setattr(fz.ph, "absent_symbol_violations", lambda commit, reader=None: ["HEAD 已含本票生產符號"])
    assert _run_freeze_write(fz, monkeypatch, tmp_path / "a") == (2, False)
    monkeypatch.setattr(fz.ph, "absent_symbol_violations", lambda commit, reader=None: [])
    _stub_git(fz, monkeypatch, diff_rc=1)
    assert _run_freeze_write(fz, monkeypatch, tmp_path / "b") == (2, False)
    _stub_git(fz, monkeypatch, others="momentum/x.py\0")
    assert _run_freeze_write(fz, monkeypatch, tmp_path / "c") == (2, False)
    _stub_git(fz, monkeypatch, head_rc=1)
    assert _run_freeze_write(fz, monkeypatch, tmp_path / "d") == (2, False)
    _stub_git(fz, monkeypatch)
    assert _run_freeze_write(fz, monkeypatch, tmp_path / "e") == (0, True)


def test_boundary_10d_anchor_symbols_present_after_fix() -> None:
    """邊界 10d（實作後）：contract `anchor_absent_symbols` 所列字面皆存在於工作樹之生產檔（清單確為本票生產符號）。"""
    assert ph.present_symbol_violations() == []


def test_mutation_m9_freeze_gate_skips_symbol_check(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """M9：凍結閘拿掉本票符號檢查（`provenance_errors` 只回傳 git 結果）⇒ HEAD 含本票符號時仍寫出 baseline（邊界 10c 偵出）。"""
    fz = _freeze_module()
    _stub_git(fz, monkeypatch)
    monkeypatch.setattr(fz.ph, "absent_symbol_violations", lambda commit, reader=None: ["HEAD 已含本票生產符號"])
    monkeypatch.setattr(fz, "provenance_errors", lambda: [])
    assert _run_freeze_write(fz, monkeypatch, tmp_path) != (2, False)


def test_mutation_m6_stack_bars_ignore_master(monkeypatch: pytest.MonkeyPatch, work_root: Path) -> None:
    """M6：D₀ 之 L6.5 堆疊窗忽略總開關 ⇒ 邊界 03 偵出（總開關關＋縮尾關格之預熱深度改變）。"""
    from momentum.FeatureEngineering import warmup_window

    def _stack_ignoring_master(config: Any) -> int:
        pp = config.preprocessing
        total = int(pp.winsorization.window) if pp.winsorization.enabled else 0
        max_lag = int(pp.fractional_differencing.model_dump().get("max_lag", 0) or 0)
        return total + (max_lag if max_lag > 0 else 252)

    monkeypatch.setattr(warmup_window, "_collect_l65_stack_bars", _stack_ignoring_master)
    found = ph.diff(_fresh("e1h.off.w0", work_root), ph.baseline()["cells"]["e1h.off.w0"], ph.keys("all"))
    assert any(line.startswith("output_window") for line in found)
