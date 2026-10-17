"""EVTLABEL Task 3.10：真實 kline 端到端（三方簽核之可證偽 oracle）。

SPEC：`docs/EVTLABEL_SPEC.md` Task 3.10　TODO：Task 3.10

🔴 **禁合成價格**：一律用 `data_cache/feature_klines/kline_cache.h5` 之真實 K 線
（本專案鐵律：Feature Factory／IC 之驗證不得用合成 fixture）。

規則與 SPEC 同源：t₀＝12h 根；label ＝ `close[t0+1]/close[t0]-1 >= 2%`。

## 這批測試在防什麼

單元測試各自綠、但**串起來對不上**——那是本 epic 反覆出現的失敗形態
（「兩端都有、但沒接上」）。故本檔用真實資料跑一次，並以
**與 label 規則同源的植入特徵**當 oracle：它必須被判為完全可分（AUC 恰為 1）。
若管線任何一段把訊號弄丟或錯位，這條就會紅。

**沒有 sign oracle**：我們不宣稱「某個真實特徵應該是正相關」——那是研究結論，不是測試。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.binary_discrimination import block_ids_for_events, mann_whitney_table
from momentum.core.contracts import (
    AlignmentViolationError,
    derive_label_kind,
    validate_consumed_label,
)

REPO = Path(__file__).resolve().parents[3]
KLINE = REPO / "data_cache/feature_klines/kline_cache.h5"
SYMBOL = "ETHUSDT"
THRESHOLD = 0.02
TF_MS = 12 * 3_600_000


def _bars() -> pd.DataFrame:
    import h5py

    if not KLINE.is_file():
        pytest.skip(f"kline cache 不存在：{KLINE}（禁以合成價格替代）")
    with h5py.File(KLINE, "r") as f:
        if SYMBOL not in f or "12h" not in f[SYMBOL]:
            pytest.skip(f"kline cache 無 {SYMBOL}/12h（禁以合成價格替代）")
        d = f[SYMBOL]["12h"]["data"][:]
    # 🔴 本 cache 之 timestamp 是**秒**（實測 1704067200）。寫死 ms 會讓日期落在 1970、
    #    事件間距縮小 1000 倍 ⇒ 區塊尺度整個錯掉（探針首跑即踩到）。
    raw = d["timestamp"].astype("int64")
    unit = "ms" if int(raw[0]) >= 1_000_000_000_000 else "s"
    return pd.DataFrame(
        {"close": d["close"].astype("float64")},
        index=pd.to_datetime(raw, unit=unit),
    )


@pytest.fixture(scope="module")
def case():
    bars = _bars()
    close = bars["close"].to_numpy()
    fwd = close[1:] / close[:-1] - 1.0
    idx = bars.index[:-1]
    y = (fwd >= THRESHOLD).astype(int)
    if min(int((y == 1).sum()), int((y == 0).sum())) < 10:
        pytest.skip("真實資料在此門檻下某一類不足 10 個")
    rng = np.random.default_rng(20260910)
    feats = pd.DataFrame(
        {"feat_planted": fwd, "feat_noise": rng.standard_normal(len(idx))}, index=idx,
    )
    return feats, y, (idx.asi8 // 10**6).astype("int64")


_EVENT_CONTEXT = {
    "event_manifest_hash": "1" * 64, "label_definition_hash": "2" * 64,
    "decision_time_rule": "t0_open_minus_k_bars", "feature_cutoff_rule": "max_close_le_decision_at",
    "label_window_rule": "close_to_close:horizon_bars=1", "control_kind": "user_labeled_same_trigger",
}


def _write_pipeline_inputs(tmp_path: Path, case) -> tuple[str, str, str, dict]:
    """把 `case` 之真實 12h 特徵與 return_1 標籤寫成 IC 管線輸入（features／labels h5＋meta）。

    末根之 forward return 未定義 ⇒ 特徵與標籤末列皆 NaN（stage0 對齊契約：尾端 NaN 數＝lag）。
    事件＝每一根已知 forward return 之 12h 根；0/1＝同一 2% 門檻（與 label 規則同源）。
    """
    import json

    import h5py

    feats, y, ms = case
    bars = _bars()
    sec = (bars.index.asi8 // 10**9).astype("int64")
    planted_full = np.append(feats["feat_planted"].to_numpy(), np.nan)
    noise_full = np.append(feats["feat_noise"].to_numpy(), np.nan)
    str_dtype = h5py.string_dtype(encoding="utf-8")
    fp, lp, mp = tmp_path / "features.h5", tmp_path / "labels.h5", tmp_path / "meta.json"
    with h5py.File(fp, "w") as f:
        g = f.create_group(f"{SYMBOL}/12h")
        g.create_dataset("features", data=np.column_stack([planted_full, noise_full]))
        g.create_dataset("timestamps", data=sec)
        g.create_dataset("feature_names", data=np.array(["feat_planted", "feat_noise"], dtype=object),
                         dtype=str_dtype)
    with h5py.File(lp, "w") as f:
        g = f.create_group(f"{SYMBOL}/12h")
        g.create_dataset("labels", data=planted_full.reshape(-1, 1))
        g.create_dataset("timestamps", data=sec)
        g.create_dataset("label_names", data=np.array(["return_1"], dtype=object), dtype=str_dtype)
    meta = {n: {"name": n, "category": "price", "layer": 1} for n in ("feat_planted", "feat_noise")}
    meta.update({"symbol": SYMBOL, "timeframe": "12h"})
    mp.write_text(json.dumps(meta), encoding="utf-8")
    kwargs = {
        "event_timestamps": [int(t) for t in ms],
        "event_label_values": {int(t): float(v) for t, v in zip(ms, feats["feat_planted"].to_numpy())},
        "event_label_owners": {int(t): f"e{i}" for i, t in enumerate(ms)},
        "event_binary_labels": {int(t): int(v) for t, v in zip(ms, y)},
        "label_mode_requested": "imported_binary",
        "event_label_binary_meta": {"import_id": "evtlabel-e2e-realkline", "label_origin_values": ["0", "1"]},
        "event_context": dict(_EVENT_CONTEXT),
    }
    return str(fp), str(lp), str(mp), kwargs


@pytest.mark.ic_persist_redirect
@pytest.mark.usefixtures("ic_persist_redirect")
def test_planted_feature_is_perfectly_separable(case, tmp_path):
    """🔴 承重 oracle：與 label 規則**同源**的特徵 ⇒ AUC 恰為 1。

    除單元層 `mann_whitney_table` 外，另經 `ICFilterOrchestrator.analyze` 之 imported_binary 路徑
    （stage0 ingestion → stage3 0/1 綁定 → stage5 binary 統計與門檻 → report）：植入特徵之
    auc／rank_biserial 須恰為 1、binary_status＝ok，且列入通過清單；雜訊特徵不得通過。
    管線任何一段把訊號弄丟或錯位，這條就紅。
    """
    from momentum.Analysis.ic_config_schema import load_ic_config
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    feats, y, _ = case
    tbl = mann_whitney_table(feats, y, min_class_n=10)
    assert tbl.loc["feat_planted", "auc"] == pytest.approx(1.0, abs=1e-12)
    assert tbl.loc["feat_planted", "rank_biserial"] == pytest.approx(1.0, abs=1e-12)
    assert tbl.loc["feat_planted", "status"] == "ok"

    fp, lp, mp, kwargs = _write_pipeline_inputs(tmp_path, case)
    report = ICFilterOrchestrator(load_ic_config()).analyze(
        fp, lp, mp, config_override={"event_filter": {"enabled": True}}, **kwargs,
    )
    event_filter = report["metadata"]["event_filter"]
    assert event_filter["label_mode"]["effective"] == "imported_binary"
    assert event_filter["label_source"] == "imported_binary_label"
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    planted = rows["feat_planted"]
    assert planted["auc"] == pytest.approx(1.0, abs=1e-12)
    assert planted["rank_biserial"] == pytest.approx(1.0, abs=1e-12)
    assert planted["binary_status"] == "ok"
    # stage5 通過＝未出現在任何剔除鍵（binary 模式下「略過」之報酬版門檻鍵不算剔除）
    s5 = report["filter_log"]["stage5_thresholds"]
    removed = {
        name
        for key, names in s5["removed_features"].items()
        if not key.endswith("_skipped_binary_mode") and key != "icir_skipped_event_path"
        for name in names
    }
    assert "feat_planted" not in removed
    assert s5["output_features"]["count"] == len({"feat_planted", "feat_noise"} - removed)


def test_noise_feature_is_not_separable(case):
    """雜訊特徵不得被判為可分（否則就是統計本身在造訊號）。"""
    feats, y, _ = case
    tbl = mann_whitney_table(feats, y, min_class_n=10)
    assert abs(float(tbl.loc["feat_noise", "rank_biserial"])) < 0.3


def test_same_input_gives_same_output(case):
    """決定性：同一份輸入兩次必須逐值相同（否則報告不可重現）。"""
    feats, y, _ = case
    a = mann_whitney_table(feats, y, min_class_n=10)
    b = mann_whitney_table(feats, y, min_class_n=10)
    cols = ["auc", "rank_biserial", "mw_u", "p_value", "n_pos", "n_neg", "n_used"]
    assert a[cols].equals(b[cols])


def test_label_shifted_by_one_event_is_caught(case):
    """🔴 label 往前錯一個事件 ⇒ 契約必須 raise。

    真實資料上錯位**不會**讓任何統計爆掉——只會讓結論指向錯的列，所以要有這道。
    """
    feats, y, ms = case
    owners = {int(t): f"e{i}" for i, t in enumerate(ms)}
    expected = {int(t): float(v) for t, v in zip(ms, y)}
    frame = pd.DataFrame({"f": feats["feat_noise"].to_numpy()}, index=feats.index)

    ok = validate_consumed_label(
        frame, pd.Series(y.astype(float), index=feats.index),
        label_kind=derive_label_kind("imported_binary_label"),
        expected_values=expected, event_owners=owners,
    )
    assert ok["checked_samples"] == len(y)

    with pytest.raises(AlignmentViolationError):
        validate_consumed_label(
            frame, pd.Series(np.roll(y, 1).astype(float), index=feats.index),
            label_kind=derive_label_kind("imported_binary_label"),
            expected_values=expected, event_owners=owners,
        )


def test_block_scale_on_real_spacing(case):
    """真實 12h 事件、答案窗 1 根 ⇒ 每個事件自成一塊（不綁）。

    🔴 若時間戳單位判錯（秒當成毫秒），間距會縮小 1000 倍、區塊長度暴增——
    本條同時釘住那個坑。
    """
    _, _, ms = case
    _, block_len, n_blocks = block_ids_for_events(ms, 1, TF_MS)
    assert block_len == 1, f"答案窗 1 根不該綁塊，實得 L={block_len}"
    assert n_blocks == len(ms)


def test_real_batch_class_balance_is_disclosed(case):
    """receipt：真實資料之正反比例（供三方簽核對照，不是斷言某個數字）。"""
    _, y, _ = case
    n_pos, n_neg = int((y == 1).sum()), int((y == 0).sum())
    assert n_pos > 0 and n_neg > 0
    assert n_pos + n_neg == len(y)
