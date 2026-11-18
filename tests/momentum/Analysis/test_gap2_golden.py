"""GAP-2 B4 Task 4.3 — §G-1 改前==改後 golden、§G-2 決定性、A1-2 identity、預算 bench receipt。

- pre 檔缺 ⇒ **fail**（非 skip）；`gap2_canonical_sha` 自 scripts/gap2_freeze_golden.py import（唯一序列化實作）。
- bench：合成 survivors／removed（seed 20260818）；`n_regressions==2k+m` 且以獨立 spy 對證（R8 CODEX-R8-P1-07）；
  測試以小規模（k＝m＝20、n＝2,000）驗計數語意；SPEC 原規模（k＝m＝200、n＝20,000）之 wall time／RSS 觀測
  （無閾值——R7 CODEX-R7-P1-03）改手動 `scripts/gap2_budget_bench.py --write-receipt`（TESTSEL I10）。
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scripts.gap2_freeze_golden import (  # noqa: E402
    PRE_PATH,
    SURVIVOR_CONFIG_OVERRIDE,
    _diff_summary,
    gap2_canonical_sha,
)
from tests.momentum.helpers.ichc_run import run_analyze  # noqa: E402
from momentum.Analysis import marginal_ic as mic  # noqa: E402
from momentum.Analysis.marginal_ic import MarginalICParams, compute_marginal_ic  # noqa: E402


@pytest.fixture(scope="module")
def pre():
    assert PRE_PATH.is_file(), f"§G-1 pre 檔缺：{PRE_PATH}（不得 skip；先 `scripts/gap2_freeze_golden.py --write` 於改動前）"
    return json.loads(PRE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def live_two_runs():
    a_dir = Path(tempfile.mkdtemp(prefix="gap2_golden_a_"))
    b_dir = Path(tempfile.mkdtemp(prefix="gap2_golden_b_"))
    # ICPERF ㊹ r95：同凍結之設定（scripts/gap2_freeze_golden.SURVIVOR_CONFIG_OVERRIDE；保住倖存者下游路徑）
    ra = run_analyze(config_override=copy.deepcopy(SURVIVOR_CONFIG_OVERRIDE), sidefx_dir=a_dir)
    rb = run_analyze(config_override=copy.deepcopy(SURVIVOR_CONFIG_OVERRIDE), sidefx_dir=b_dir)
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
#: TESTSEL I10：計數語意（n_regressions＝2k＋m＝spy 次數、欄數上界 k、超預算視角零 fit）與規模無關 ⇒ 測試以
#: n＝2,000、k＝m＝20 驗同一路徑；SPEC 原規模（n＝20,000、k＝m＝200）之 wall／RSS 觀測改手動
#: `venv/bin/python scripts/gap2_budget_bench.py --write-receipt`（原測試每次約 146 秒且把收據寫進 repo；
#: IC_QUANT_GAP_REGISTRY G2-R7 已建議拆出）。收據改寫 tmp_path。
_BENCH_N, _BENCH_K, _BENCH_M = 2000, 20, 20


def _bench_data():
    """原規模合成資料（n＝20,000、k＝m＝200，seed 20260818；生成式見 scripts/gap2_budget_bench.bench_data）。"""
    from scripts.gap2_budget_bench import FULL_SCALE, bench_data

    return bench_data(**FULL_SCALE)


def test_budget_bench_receipt(tmp_path):
    from scripts.gap2_budget_bench import budget_bench, write_receipt

    k, m = _BENCH_K, _BENCH_M
    r = budget_bench(_BENCH_N, k, m)
    n_main = r["spy_main"]
    assert r["n_regressions"] == 2 * k + m == n_main, (r["n_regressions"], n_main)  # spy count == counter == 2k+m
    assert r["max_design_cols_main"] <= k  # 每次設計矩陣欄數上界（不含截距）
    assert r["combine_status"] == "ok"
    # 超預算 case：被略過視角無任何 fit call
    assert r["over1_spy"] == 0 and r["over1_n_regressions"] == 0
    assert r["over2_spy"] == 2 * k == r["over2_n_regressions"]
    receipt = write_receipt(r, tmp_path)
    assert receipt.exists()
    assert f"n_regressions={2 * k + m} fit_projection_spy={2 * k + m}" in receipt.read_text(encoding="utf-8")


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


def test_fit_projection_spy_matches_counter_and_basis_widths(monkeypatch):
    """生產 compute_marginal_ic 之 fit_projection 實呼叫（spy）須逐次對上獨立手算之設計矩陣寬度多重集，且計數器＝spy。

    oracle（不經生產碼）：k 個 survivors、m 個 removed ⇒ LOO k 次各 k-1 欄、sequential k 次依序 0..k-1 欄、
    removed m 次各 k 欄 ⇒ 共 2k+m 次。
    """
    df, y, tr, te, surv, removed = _bench_data()
    small_surv, small_removed = surv[:5], removed[:3]
    widths = []
    real = mic.fit_projection

    def spy(z_target, z_basis):
        widths.append(int(np.asarray(z_basis).shape[1]))
        return real(z_target, z_basis)

    monkeypatch.setattr(mic, "fit_projection", spy)
    res = compute_marginal_ic(df, y, train_mask=tr, test_mask=te, survivors=small_surv, extra_candidates=small_removed, params=MarginalICParams(n_bootstrap=1), fit_scope="train")
    k, m = len(small_surv), len(small_removed)
    expected = sorted([k - 1] * k + list(range(k)) + [k] * m)
    assert res.n_regressions == len(widths) and sorted(widths) == expected, (res.n_regressions, sorted(widths), expected)
