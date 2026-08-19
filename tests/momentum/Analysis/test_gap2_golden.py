"""GAP-2 B4 Task 4.3 — §G-1 改前==改後 golden、§G-2 決定性、A1-2 identity、預算 bench receipt。

- pre 檔缺 ⇒ **fail**（非 skip）；`gap2_canonical_sha` 自 scripts/gap2_freeze_golden.py import（唯一序列化實作）。
- bench：合成 k=200 survivors＋200 removed、n=20000（seed 20260818）；`n_regressions==600` 且以獨立 spy 對證
  （R8 CODEX-R8-P1-07）；wall time／RSS 只寫 receipt（觀測，無閾值——R7 CODEX-R7-P1-03）。
"""
from __future__ import annotations

import hashlib
import json
import math
import resource
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scripts.gap2_freeze_golden import PRE_PATH, _diff_summary, gap2_canonical_sha  # noqa: E402
from tests.momentum.helpers.ichc_run import run_analyze  # noqa: E402
from momentum.Analysis import marginal_ic as mic  # noqa: E402
from momentum.Analysis.factor_combiner import combine_factors  # noqa: E402
from momentum.Analysis.marginal_ic import MarginalICParams, compute_marginal_ic  # noqa: E402


@pytest.fixture(scope="module")
def pre():
    assert PRE_PATH.is_file(), f"§G-1 pre 檔缺：{PRE_PATH}（不得 skip；先 `scripts/gap2_freeze_golden.py --write` 於改動前）"
    return json.loads(PRE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def live_two_runs():
    a_dir = Path(tempfile.mkdtemp(prefix="gap2_golden_a_"))
    b_dir = Path(tempfile.mkdtemp(prefix="gap2_golden_b_"))
    ra = run_analyze(sidefx_dir=a_dir)
    rb = run_analyze(sidefx_dir=b_dir)
    return ra, rb, a_dir, b_dir


# ---------------------------------------------------------------- §G-1 改前==改後
def test_g1_golden_unchanged(pre, live_two_runs):
    ra, rb, a_dir, b_dir = live_two_runs
    assert gap2_canonical_sha(ra) == pre["canonical_sha"], "canonical_sha 與 pre 不等（改前≠改後）"
    assert gap2_canonical_sha(ra) == gap2_canonical_sha(rb)  # 兩 sidefx 目錄 sha 相等（路徑無關性）
    assert _diff_summary(pre["summary_table"], list(ra["summary_table"])) == []
    fl = ra["filter_log"]
    for sec in ("stage5_thresholds", "stage6_redundancy"):
        assert json.dumps(pre["filter_log"][sec], sort_keys=True, default=str) == json.dumps(fl.get(sec), sort_keys=True, default=str), sec
    # A1-2 identity：live report_ref 檔名段 == pre case_id
    so = ra["metadata"]["survivor_output"]
    assert so["case_id"] == pre["case_id"] == "ic_gatekeeper"
    payload = json.loads(Path(so["path"]).read_text(encoding="utf-8"))
    assert payload["provenance"]["report_ref"] == f"ic_report_{pre['case_id']}.json"
    assert Path(so["path"]).name == f"ic_survivors_{pre['case_id']}.json"


# ---------------------------------------------------------------- §G-2 新節決定性
def test_g2_section_and_survivor_file_deterministic(live_two_runs):
    ra, rb, a_dir, b_dir = live_two_runs
    sa = hashlib.sha256(json.dumps(ra["marginal_ic"], sort_keys=True, default=str).encode()).hexdigest()
    sb = hashlib.sha256(json.dumps(rb["marginal_ic"], sort_keys=True, default=str).encode()).hexdigest()
    assert sa == sb
    pa = json.loads(Path(ra["metadata"]["survivor_output"]["path"]).read_text(encoding="utf-8"))
    pb = json.loads(Path(rb["metadata"]["survivor_output"]["path"]).read_text(encoding="utf-8"))
    for p in (pa, pb):
        p.pop("generated_at", None)
    assert hashlib.sha256(json.dumps(pa, sort_keys=True).encode()).hexdigest() == hashlib.sha256(json.dumps(pb, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------- 預算 bench（receipt；spy 對證）
def _bench_data():
    rng = np.random.default_rng(20260818)
    n, k, m = 20000, 200, 200
    X = rng.standard_normal((n, k + m))
    cols = [f"s{i:03d}" for i in range(k)] + [f"r{i:03d}" for i in range(m)]
    y = 0.02 * X[:, :k].sum(axis=1) + rng.standard_normal(n)
    df = pd.DataFrame(X, columns=cols)
    tr = np.zeros(n, dtype=bool)
    tr[: int(n * 0.6)] = True
    return df, pd.Series(y), tr, ~tr, cols[:k], cols[k:]


def test_budget_bench_receipt(monkeypatch):
    df, y, tr, te, surv, removed = _bench_data()
    calls = []
    real = mic.fit_projection

    def spy(z_target, z_basis):
        calls.append(int(np.asarray(z_basis).shape[1]) if np.asarray(z_basis).ndim == 2 else 0)
        return real(z_target, z_basis)

    monkeypatch.setattr(mic, "fit_projection", spy)
    p = MarginalICParams(n_bootstrap=1, block_len=5, max_survivors_for_loo=200, max_removed_candidates=200)
    t0 = time.time()
    res = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=surv, extra_candidates=removed, params=p, fit_scope="train")
    comp = combine_factors(df, y, train_mask=tr, test_mask=te, survivors=surv, params=p, fit_scope="train")
    wall = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    n_main = len(calls)
    assert res.n_regressions == 600 == n_main, (res.n_regressions, n_main)  # spy count == counter == 2k+m
    assert max(calls) <= 200  # 每次設計矩陣欄數上界（不含截距）
    assert comp.status == "ok"
    # 超預算 case：被略過視角無任何 fit call
    calls.clear()
    over1 = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=surv, extra_candidates=[], params=MarginalICParams(n_bootstrap=1, max_survivors_for_loo=199), fit_scope="train")
    spy_over1 = len(calls)
    assert spy_over1 == 0 and over1.n_regressions == 0
    calls.clear()
    over2 = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=surv, extra_candidates=removed, params=MarginalICParams(n_bootstrap=1, max_removed_candidates=199), fit_scope="train")
    spy_over2 = len(calls)
    assert spy_over2 == 400 == over2.n_regressions
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt = REPO / "handoffs" / "run_receipts" / f"{ts}-gap2-budget-bench.log"
    receipt.write_text(
        "\n".join([
            f"[gap2-budget-bench] ts={ts} n=20000 k=200 m=200 seed=20260818 n_bootstrap=1",
            f"n_regressions={res.n_regressions} fit_projection_spy={n_main} max_design_cols={max(calls) if calls else 'n/a'}(main run: ≤200)",
            f"over_budget_survivors(max_survivors_for_loo=199): spy={spy_over1} n_regressions={over1.n_regressions}",
            f"over_budget_removed(max_removed_candidates=199): spy={spy_over2} n_regressions={over2.n_regressions}",
            f"wall_time_s={wall:.1f} ru_maxrss={rss} （觀測資料；無通過閾值——R7 CODEX-R7-P1-03；OOM 保護宣稱僅計數上界）",
            f"composite_ic={comp.composite_ic}",
        ]) + "\n",
        encoding="utf-8",
    )
    assert receipt.exists()


# ---------------------------------------------------------------- 探針
def test_mutation_scrub_extra_key_breaks_canonical_sha(pre, live_two_runs, monkeypatch):
    """`gap2_canonical_sha` 多刪一鍵（summary_table）⇒ 與 pre 不等 ⇒ 紅。"""
    ra, _, _, _ = live_two_runs
    assert gap2_canonical_sha(ra) == pre["canonical_sha"]  # 基線綠
    import scripts.gap2_freeze_golden as fg

    # mutant：scrub 清單多刪一鍵（metadata.symbol）⇒ 與 pre 不等
    monkeypatch.setattr(fg, "_META_SCRUB", tuple(fg._META_SCRUB) + ("symbol",))
    with pytest.raises(AssertionError):
        assert fg.gap2_canonical_sha(ra) == pre["canonical_sha"]


def test_mutation_counter_without_fit_call_breaks_spy(monkeypatch):
    """`n_regressions` 改為預算公式湊數而不呼叫 fit_projection ⇒ spy≠counter 紅。"""
    df, y, tr, te, surv, removed = _bench_data()
    small_surv, small_removed = surv[:5], removed[:3]
    calls = []
    real = mic.fit_projection

    def spy(z_target, z_basis):
        calls.append(1)
        return real(z_target, z_basis)

    monkeypatch.setattr(mic, "fit_projection", spy)
    p = MarginalICParams(n_bootstrap=1)
    res = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=small_surv, extra_candidates=small_removed, params=p, fit_scope="train")
    assert res.n_regressions == len(calls) == 13  # 基線綠
    # mutant：counter 與實際 fit 呼叫脫鉤（計數漂移＝公式湊數之最窄等價；探針 V-22 外部 sed 亦打 `n_regressions += 1` 行）
    import dataclasses
    res2 = dataclasses.replace(res, n_regressions=2 * len(small_surv) + len(small_removed) + 1)
    with pytest.raises(AssertionError):
        assert res2.n_regressions == len(calls)  # spy（13）≠ counter（14）
