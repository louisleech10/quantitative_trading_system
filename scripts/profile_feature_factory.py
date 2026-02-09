import cProfile
import io
import os
import pstats
import time
import tracemalloc
from pathlib import Path

from momentum.factories import create_feature_factory


def main() -> None:
    output_path = Path("results/feature_factory_profile.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    factory = create_feature_factory()

    tracemalloc.start()
    start = time.perf_counter()
    profiler = cProfile.Profile()
    profiler.enable()
    force_regenerate = os.getenv("FORCE_REGENERATE", "0") == "1"
    result = factory.generate_features(
        "BTCUSDT",
        "12h",
        config_override={"preset": "standard"},
        force_regenerate=force_regenerate,
    )
    profiler.disable()
    end = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(40)

    report = []
    report.append(f"elapsed_seconds={end - start:.4f}")
    report.append(f"features={result.feature_count}")
    report.append(f"tracemalloc_current_mb={current / (1024 * 1024):.2f}")
    report.append(f"tracemalloc_peak_mb={peak / (1024 * 1024):.2f}")
    report.append("\nTop 40 cumulative:\n")
    report.append(stream.getvalue())

    output_path.write_text("\n".join(report), encoding="utf-8")
    print(f"profile_written={output_path}")


if __name__ == "__main__":
    main()
