import logging

import numpy as np
import pandas as pd

from momentum.Analysis.ic_engine import ICEngine


def test_compute_ic_decay_aggregates_fit_warnings(caplog) -> None:
    features = pd.DataFrame(
        {
            "constant_ic": np.linspace(1, 20, 20),
            "variable_ic": [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 55, 34, 21, 13, 8, 5, 3, 2, 1, 1],
        }
    )
    close = pd.Series(np.linspace(100, 125, 20))

    with caplog.at_level(logging.INFO, logger="momentum.Analysis.ic_engine"):
        result = ICEngine({}).compute_ic_decay(
            features,
            close,
            horizons=[1, 2, 3],
            method="spearman",
            return_type="simple",
        )

    warning_records = [
        record for record in caplog.records if record.name == "momentum.Analysis.ic_engine" and record.levelno >= logging.WARNING
    ]
    summary_records = [
        record for record in caplog.records if record.name == "momentum.Analysis.ic_engine" and "Decay:" in record.getMessage()
    ]

    assert result["constant_ic"]["fit_warning_reason"] == "low_variance"
    assert warning_records == []
    assert len(summary_records) == 1
    assert "1/2" in summary_records[0].getMessage()
    assert "low_variance=1" in summary_records[0].getMessage()


def test_compute_ic_decay_logs_summary_when_all_fits_succeed(caplog) -> None:
    features = pd.DataFrame(
        {
            "smooth_cycle": np.sin(np.linspace(0, 10, 200)),
        }
    )
    close = pd.Series(np.exp(np.linspace(0, 1, 200)))

    with caplog.at_level(logging.INFO, logger="momentum.Analysis.ic_engine"):
        result = ICEngine({}).compute_ic_decay(
            features,
            close,
            horizons=[1, 2, 3, 5, 8],
            method="spearman",
            return_type="simple",
        )

    summary_records = [
        record for record in caplog.records if record.name == "momentum.Analysis.ic_engine" and "Decay:" in record.getMessage()
    ]

    assert result["smooth_cycle"]["fit_warning"] is False
    assert len(summary_records) == 1
    assert "0/1" in summary_records[0].getMessage()
    assert "none" in summary_records[0].getMessage()
