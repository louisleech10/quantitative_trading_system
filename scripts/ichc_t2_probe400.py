"""ICHC B4 證據探針（臨時）：n=400 等距子集是否過 warmup、事件語意是否保留。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests.momentum.helpers.ichc_run import feature_index, run_analyze  # noqa: E402

subset = list(feature_index(400))
report = run_analyze(
    config_override={"event_filter": {"enabled": True}}, event_timestamps=subset
)
ev = report["metadata"]["event_filter"]
print("PROBE400:", {
    "mode": ev.get("mode"),
    "n_events": ev.get("n_events"),
    "tier": ev.get("tier"),
    "fallback": ev.get("fallback"),
    "analysis_status": report.get("analysis_status"),
    "n_timestamps_requested": ev.get("n_timestamps_requested"),
})
