"""GAP-3 UX **Task 7.7** 驗收（`pytest tests/api -q -k feature_coverage_gate`；SPEC L3330–3360）。

🔴 **本檔用結構化 fixture（`WindowRow`）而非合成價格**：gate 吃的是**對齊後的收據欄位**
（`decision_at_ms`／`label_end_ms`／`timeframe`），不是 bar 表。造 WindowRow 不違反
「禁合成 kline」——那條規範的是價格資料，而這裡一根 bar 都沒碰。
真實 kline 之驗收在 `-k analysis_label_producer`（那邊才是算數字的地方）。

🔴 每一格都有 **under**（該擋擋住）與 **over**（不該擋沒被擋）兩向——B9 五輪的病根就是只測單向。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.models.feature_factory_models import RunInfo
from api.services.ic_analysis_service import (
    FeatureRunCoverageError,
    check_feature_run_coverage,
)
from momentum.Analysis.event_samples.label_value_from_case import WindowRow

REPO = Path(__file__).resolve().parents[2]
TF_SECONDS = {"1h": 3600, "12h": 43200}

DAY = 86400_000
T0 = 1704067200000  # 2024-01-01 00:00 UTC（ms）


def win(eid: str, *, tf: str = "12h", decision: int, end: int,
        label_start: int | None = None) -> WindowRow:
    """🔴 `label_start_ms` **預設與 `decision_at_ms` 不同**（預設＝t0，即 decision 之後）。

    首版把兩者設成同值，結果「左界用 `decision_at` 還是用 `label_start`」這件事在 fixture 裡
    **不可分辨**——mutation 把左界改成 `label_start` 時 rc=0、錄到空紅集合。
    真實資料裡 `k>0` 時 `decision_at < t0 <= label_start`，fixture 必須反映這個差距，
    否則 ④ 那條「左界回歸」根本沒有鑑別力。
    """
    return WindowRow(
        event_id=eid, symbol="ETHUSDT", timeframe=tf,
        decision_at_ms=decision, entry_at_ms=decision,
        label_start_ms=T0 if label_start is None else label_start, label_end_ms=end,
    )


def rng(start: str | None, end: str | None) -> dict:
    return {"start": start, "end": end}


def secs(ms: int) -> str:
    """epoch ms → **epoch 秒之數字字串**（現存 manifest 之實際形態）。"""
    return str(ms // 1000)


# ── ① RunInfo 有該欄，且真實 manifest 之值原樣可讀（型別為 str 或 None，未被轉型） ──

def test_feature_coverage_gate_01_runinfo_declares_time_range():
    assert "time_range" in RunInfo.model_fields


def test_feature_coverage_gate_01c_list_runs_actually_carries_time_range():
    """🔴 **service 真的把 `time_range` 帶出來**（不是只有 model 宣告了）。

    這條是 mutation 抓出來的**真實覆蓋缺口**：原本 ① 只驗 `RunInfo.model_fields`、
    ①b 直接讀 manifest 檔，**兩條都沒有經過 `list_runs()`**
    ⇒ 把 `_browse_metadata_for_run` 的 `time_range` 整個拿掉，全部測試照樣綠。
    型別宣告不會讓任何東西在執行期出現——這正是 §4.2 假綠形態 5 的另一面。
    """
    from api.services.feature_factory_service import feature_factory_service

    rows = feature_factory_service.list_runs()
    if not rows:
        pytest.skip("本機 registry 無 run，無法對證")
    assert all("time_range" in row for row in rows), \
        "list_runs() 的每一列都必須帶 time_range 鍵（值可為 None，但鍵不得缺）"


def test_feature_coverage_gate_01b_real_manifest_values_are_strings_or_none():
    """讀**真實** manifest：值須為 `str` 或 `None`，**不得**被轉成 int／datetime。

    🔴 這條同時是我偵察輪的實跑結論之回歸：14 份裡 12 份有 `time_range`（epoch 秒字串）、
    2 份**完全沒有該鍵**。若哪天有人「順手」把它轉成 epoch ms int，gate 那端的
    數字字串分支就會變成死碼，而錯誤要到覆蓋判斷偏移時才看得出來。
    """
    manifests = sorted((REPO / "data_cache" / "features").rglob("feature_manifest.json"))
    if not manifests:
        pytest.skip("本機無 feature manifest，無法做真實對證")
    seen_with_key = 0
    for path in manifests:
        payload = json.loads(path.read_text(encoding="utf-8"))
        tr = payload.get("time_range")
        if tr is None:
            continue  # 缺鍵之 legacy run（實掃確有；由 ⑨b 那條驗其處置）
        seen_with_key += 1
        for key in ("start", "end"):
            value = tr.get(key)
            assert value is None or isinstance(value, str), \
                f"{path}: time_range[{key}] 型別為 {type(value).__name__}，須為 str 或 None"
    assert seen_with_key > 0, "全部 manifest 都缺 time_range——本條失去鑑別力"


# ── ② 契約之 analysis_rejected 最終集合 ─────────────────────────────────────

def test_feature_coverage_gate_02_contract_reasons_final_set():
    contract = json.loads(
        (REPO / "momentum" / "Analysis" / "contracts" / "ic_report_contract.json").read_text("utf-8")
    )
    assert contract["reasons"]["analysis_rejected"] == [
        "feature_count_exceeds_cap",
        "feature_coverage_insufficient",
        "feature_coverage_unknown_legacy_run",
        "feature_coverage_unknown_timeframe",
        "feature_coverage_unknown_timestamp_format",
    ]


# ── ③ over 向：完全涵蓋 ⇒ 放行 ─────────────────────────────────────────────

def test_feature_coverage_gate_03_fully_covered_passes():
    """③ 事件期全落在 run 區間內 ⇒ **放行**（本檔的 over 向基準；沒有它其餘都可能是恆擋）。"""
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=rng(secs(T0 - DAY), secs(T0 + 10 * DAY)),
        event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
    )


# ── ④ 左界回歸：run_start 落在 decision_at 與 t0 之間 ⇒ 仍擋 ────────────────

def test_feature_coverage_gate_04_left_bound_uses_decision_at_not_t0():
    """④ `decision_offset_bars=3` ⇒ `decision_at < t0`；run_start 落在兩者之間 ⇒ **fail-closed**。

    🔴 這條擋的是「左界用 `min(t0)`」那個 fail-open 窗口：用 t0 判會放行，
    但 IC 的特徵截止規則是 `max_close_ms <= decision_at`，run 沒涵蓋 decision_at 就是不夠。
    """
    decision = T0 - 3 * 43200_000  # k=3 根 12h
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,
            feature_manifest_time_range=rng(secs(T0), secs(T0 + 10 * DAY)),  # 起點正好是 t0
            event_windows=[win("ev0", decision=decision, end=T0 + DAY)],
        )
    assert ei.value.reason == "feature_coverage_insufficient"
    # 🔴 **over 向對照**：run_start 提前到 decision_at 之前 ⇒ 須放行（證明不是恆擋）
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=rng(secs(decision - DAY), secs(T0 + 10 * DAY)),
        event_windows=[win("ev0", decision=decision, end=T0 + DAY)],
    )


# ── ⑤ 右界含答案窗 ─────────────────────────────────────────────────────────

def test_feature_coverage_gate_05_right_bound_includes_label_window():
    """⑤ `max(t0)` 在區間內但 `label_end` 超出右界 ⇒ **仍 fail-closed**。"""
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,
            feature_manifest_time_range=rng(secs(T0 - DAY), secs(T0 + DAY)),
            event_windows=[win("ev0", decision=T0, end=T0 + 5 * DAY)],
        )
    assert ei.value.reason == "feature_coverage_insufficient"
    # 🔴 **over 向對照（`GROK-R1-P2-01` 指出本格原本只有 under）**：
    #    右界剛好等於 `label_end` ⇒ **須放行**（`<=` 是閉區間，不得多擋一根）
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=rng(secs(T0 - DAY), secs(T0 + 5 * DAY)),
        event_windows=[win("ev0", decision=T0, end=T0 + 5 * DAY)],
    )


# ── ⑥⑦ 逐列用該列自己的 tf（非批內 max／min） ──────────────────────────────

def test_feature_coverage_gate_06_per_row_timeframe_not_batch_scalar():
    """⑥ 1h 與 12h 同 `decision_at`、同 horizon 根數 ⇒ 右界相差 12 倍：12h 被擋、1h 放行。"""
    horizon_bars = 4
    end_1h = T0 + horizon_bars * 3600_000
    end_12h = T0 + horizon_bars * 43200_000
    run = rng(secs(T0 - DAY), secs(end_1h))          # 恰好蓋得住 1h、蓋不住 12h
    check_feature_run_coverage(                       # over 向：1h 放行
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=run,
        event_windows=[win("ev1h", tf="1h", decision=T0, end=end_1h)],
    )
    with pytest.raises(FeatureRunCoverageError) as ei:  # under 向：12h 被擋
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,
            feature_manifest_time_range=run,
            event_windows=[win("ev12h", tf="12h", decision=T0, end=end_12h)],
        )
    assert ei.value.reason == "feature_coverage_insufficient"


def test_feature_coverage_gate_07_mixed_tf_matches_per_row_evaluation():
    """⑦ 批內混 1h 與 12h ⇒ 結果與逐列單獨計算一致（此處：12h 那列決定整批被擋）。"""
    end_1h = T0 + 4 * 3600_000
    end_12h = T0 + 4 * 43200_000
    run = rng(secs(T0 - DAY), secs(end_1h))
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,
            feature_manifest_time_range=run,
            event_windows=[
                win("ev1h", tf="1h", decision=T0, end=end_1h),
                win("ev12h", tf="12h", decision=T0, end=end_12h),
            ],
        )
    assert ei.value.reason == "feature_coverage_insufficient"
    # over 向：把右界拉到蓋得住 12h ⇒ 混批放行（證明混批本身不是被擋的理由）
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=rng(secs(T0 - DAY), secs(end_12h)),
        event_windows=[
            win("ev1h", tf="1h", decision=T0, end=end_1h),
            win("ev12h", tf="12h", decision=T0, end=end_12h),
        ],
    )


# ── ⑧ 未知 timeframe（注入之鍵集，非 module 常數） ─────────────────────────

def test_feature_coverage_gate_08_unknown_timeframe_uses_injected_keyset():
    """⑧ `e.timeframe='3h'` 不在**注入之** `timeframe_seconds` 鍵集 ⇒ 整批 fail-closed。

    🔴 `3h` 在 `momentum/core/constants.py::TIMEFRAME_SECONDS` 裡是**存在**的——
    本條之所以會紅，正是因為 gate 讀的是**注入的 map** 而不是 module 常數。
    若哪天有人在 gate 內直讀常數，本條會轉綠，那正是要防的事。
    """
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,  # 只有 1h／12h
            feature_manifest_time_range=rng(secs(T0 - DAY), secs(T0 + 10 * DAY)),
            event_windows=[win("ev0", tf="3h", decision=T0, end=T0 + DAY)],
        )
    assert ei.value.reason == "feature_coverage_unknown_timeframe"
    # over 向：把 3h 加進注入之 map ⇒ 放行（證明擋的是「不在注入鍵集」而非「叫 3h」）
    check_feature_run_coverage(
        timeframe_seconds={**TF_SECONDS, "3h": 10800},
        feature_manifest_time_range=rng(secs(T0 - DAY), secs(T0 + 10 * DAY)),
        event_windows=[win("ev0", tf="3h", decision=T0, end=T0 + DAY)],
    )


# ── ⑨ legacy／缺鍵／tz-naive ────────────────────────────────────────────────

def test_feature_coverage_gate_09_legacy_none_pair():
    """⑨ `{"start": None, "end": None}` ⇒ `feature_coverage_unknown_legacy_run`。"""
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,
            feature_manifest_time_range=rng(None, None),
            event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
        )
    assert ei.value.reason == "feature_coverage_unknown_legacy_run"
    # 🔴 **over 向對照（`GROK-R1-P2-01`）**：兩端皆為合法值 ⇒ 須放行。
    #    少了這條，一個「凡是 legacy 分支就擋」的過寬實作也會綠。
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=rng(secs(T0 - DAY), secs(T0 + 10 * DAY)),
        event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
    )


@pytest.mark.parametrize("missing", [None, {}, {"start": secs(T0)}, "not-a-dict"])
def test_feature_coverage_gate_09b_missing_key_same_as_legacy(missing):
    """🔴 **缺鍵與 legacy 同等處置**（偵察輪裁定 1；SPEC ⑤ 只裁定了 `{None,None}`）。

    實掃 14 份 manifest 有 **2 份完全沒有** `time_range` 鍵。兩者資訊量相同（都拿不到區間），
    分成兩個 reason 只會讓前端多一種字面要處理；且 §C0 只能更嚴，缺鍵放行才是弱化。
    """
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,
            feature_manifest_time_range=missing,
            event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
        )
    assert ei.value.reason == "feature_coverage_unknown_legacy_run"


@pytest.mark.parametrize("present", [
    {"start": secs(T0 - DAY), "end": secs(T0 + 10 * DAY)},
    {"start": secs(T0 - DAY), "end": secs(T0 + 10 * DAY), "extra_key": "ignored"},
])
def test_feature_coverage_gate_09b_over_present_keys_pass(present):
    """🔴 **09b 之 over 向對照（`GROK-R1-P2-01`）**：鍵齊全且值合法 ⇒ **須放行**。

    第二個 param 刻意多帶一個無關鍵——**多餘鍵不得使 gate 誤判為畸形**
    （三件套之 ②malformed probe：多餘鍵藏東西是一種攻法，但「因為多一個鍵就整批擋掉」
    是另一種錯，兩者都要驗）。
    """
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=present,
        event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
    )


def test_feature_coverage_gate_09c_tz_naive_iso_rejected():
    """⑨ tz-naive ISO ⇒ `feature_coverage_unknown_timestamp_format`（不得當成 UTC）。"""
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,
            feature_manifest_time_range=rng("2024-01-01T00:00:00", "2024-12-31T00:00:00+00:00"),
            event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
        )
    assert ei.value.reason == "feature_coverage_unknown_timestamp_format"
    # 🔴 **over 向對照**：兩端皆 tz-aware ISO ⇒ 解析成功並正常判定
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=rng("2023-12-01T00:00:00+00:00", "2024-12-31T00:00:00+00:00"),
        event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
    )


# ── ⑩ epoch 秒數字字串正例（防「照 R5 版實作而擋掉全部現存 run」） ──────────

def test_feature_coverage_gate_10_epoch_second_strings_parse():
    """⑩ `{"start":"1704067200","end":"1777330800"}` ⇒ **解析成功**且正常判定。

    🔴 這是**回歸條**：SPEC R5 版指定先用 `datetime.fromisoformat`，
    對數字字串直接 raise ⇒ 會把**全部現存 run** 判成 parse failure。三家以真實 manifest 打穿。
    """
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range={"start": "1704067200", "end": "1777330800"},
        event_windows=[win("ev0", decision=T0 + DAY, end=T0 + 2 * DAY)],
    )


# ── ⑪ 超出合理範圍之數字字串 ───────────────────────────────────────────────

def test_feature_coverage_gate_11_out_of_range_epoch_rejected():
    """⑪ `start == "99999999999"`（超出 2100-01-01）⇒ `feature_coverage_unknown_timestamp_format`。"""
    with pytest.raises(FeatureRunCoverageError) as ei:
        check_feature_run_coverage(
            timeframe_seconds=TF_SECONDS,
            feature_manifest_time_range={"start": "99999999999", "end": "1777330800"},
            event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
        )
    assert ei.value.reason == "feature_coverage_unknown_timestamp_format"
    # 🔴 **⑪ 之 over 向對照（`GROK-R1-P2-01`）**：**剛好在界內**之大數字須放行。
    #    `4102444799` = 2100-01-01 前一秒；少了這條，一個「數字太大就擋」的過寬實作也會綠。
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range={"start": secs(T0 - DAY), "end": "4102444799"},
        event_windows=[win("ev0", decision=T0, end=T0 + DAY)],
    )


# ── 空窗：不是錯誤 ────────────────────────────────────────────────────────

def test_feature_coverage_gate_12_empty_windows_is_not_an_error():
    """🔴 **over 向**：沒有窗就沒有東西要涵蓋 ⇒ 放行。

    「全部對齊失敗」有它自己的 loud 路徑（`capability unavailable`），
    在這裡再擋一次會讓使用者看到一個**指錯方向**的 reason（說是 run 不夠，其實是對齊失敗）。
    """
    check_feature_run_coverage(
        timeframe_seconds=TF_SECONDS,
        feature_manifest_time_range=rng(None, None),  # 連 legacy 都不該觸發
        event_windows=[],
    )


# ── ⑩ G3-D10（UAT B15）：註冊 run 之 manifest 由 registry 路徑取得，不在物化暫存檔附近找 ──

def test_feature_coverage_gate_10_registry_manifest_path_is_first_candidate(tmp_path: Path):
    """真路徑形態：`features_path`＝`data_cache/reports/ic_ingest_cache/<sym>_<tf>_<hash>.h5`（附近無 manifest），
    registry 條目 `hdf5_relative_path`＝`<run_dir>/feature_manifest.json`（有 `time_range`）。

    under：只給物化暫存路徑 ⇒ `None`（＝B15 實際撞到的 legacy 誤判，證明候選順序有鑑別力）；
    over：manifest 路徑在第一候選 ⇒ 原樣取出 `time_range`。
    mutation：`_run_event_label_stages` 不傳 `feature_manifest_path` ⇒ 本條 under 側仍綠但 ⑪ 紅。
    """
    from api.services.ic_analysis_service import _feature_run_time_range

    run_dir = tmp_path / "features" / "ETHUSDT" / "12h" / "abc9"
    run_dir.mkdir(parents=True)
    manifest = run_dir / "feature_manifest.json"
    manifest.write_text(json.dumps({"time_range": {"start": "1704067200", "end": "1777291200"}}), encoding="utf-8")
    cache_dir = tmp_path / "reports" / "ic_ingest_cache"
    cache_dir.mkdir(parents=True)
    h5 = cache_dir / "ETHUSDT_12h_abc9.h5"
    h5.write_bytes(b"")
    meta = cache_dir / "ETHUSDT_12h_abc9_meta.json"
    meta.write_text("{}", encoding="utf-8")

    assert _feature_run_time_range(str(h5), str(meta)) is None                       # B15 之誤判形態
    assert _feature_run_time_range(str(manifest), str(h5), str(meta)) == rng("1704067200", "1777291200")
    assert _feature_run_time_range(None, str(h5), str(meta)) is None


def test_feature_coverage_gate_11_service_passes_registry_manifest_to_gate(monkeypatch):
    """`_run_event_label_stages` 對 gate 之 `feature_manifest_time_range` 來自 `feature_manifest_path`（第一候選）。

    以探針取代 `_feature_run_time_range`，斷言第一個引數就是 registry 之 manifest 路徑。
    """
    import api.services.ic_analysis_service as svc_mod

    seen: list = []

    def probe(*candidates):
        seen.append(tuple(candidates))
        return rng("1704067200", "1777291200")

    monkeypatch.setattr(svc_mod, "_feature_run_time_range", probe)
    # 讓其餘階段不真的跑：`prepare_analysis_windows` 之後就 raise，只驗到 gate 之呼叫
    class _Stop(Exception):
        pass

    def fake_check(**kw):
        raise _Stop()

    monkeypatch.setattr(svc_mod, "check_feature_run_coverage", fake_check)

    class _Pipe:
        def timeframe_seconds_for(self, tfs):
            return {tf: TF_SECONDS[tf] for tf in tfs}

        def bars_from_kline_cache(self, symbols, tfs):
            return {}

        def prepare_analysis_windows(self, *a, **kw):
            class _P:
                windows = ()
            return _P()

    monkeypatch.setattr("momentum.factories.create_event_sample_pipeline", lambda: _Pipe())
    req = type("Req", (), {"event_import_id": "imp-1"})()
    batch = {"records": ({"symbol": "ETHUSDT", "timeframe": "12h"},), "event_label_spec": None,
             "lookahead_bars_declared": {"12h": 2}}
    with pytest.raises(_Stop):
        svc_mod.ICAnalysisService._run_event_label_stages(
            req, batch, features_path="data_cache/reports/ic_ingest_cache/x.h5", meta_path=None,
            feature_manifest_path="data_cache/features/ETHUSDT/12h/abc9/feature_manifest.json")
    assert seen and seen[0][0] == "data_cache/features/ETHUSDT/12h/abc9/feature_manifest.json"
