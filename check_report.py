import pytest
from tests.test_cgsa_pipeline import test_cgsa_vs_legacy_numeric_equivalence
import json
import os
import sys

# Mocking the test to extract the report
def run_test_and_print_report():
    # We need to manually setup the environment or just call the function if possible
    # But since it's a test, let's try to monkeypatch the assertion or just run the logic
    
    # Re-implementing the core logic of the test to get the report
    from scripts.validate_cgsa_ab import run_validation
    from pathlib import Path
    
    PROJECT_ROOT = Path(".").resolve()
    cgsa_layers = {
        "L1": PROJECT_ROOT / "results/cgsa_ab/cgsa_l1.parquet",
        "L2": PROJECT_ROOT / "results/cgsa_ab/cgsa_l2.parquet",
        "L3": PROJECT_ROOT / "results/cgsa_ab/cgsa_l3.parquet",
    }
    legacy_layers = {
        "L1": PROJECT_ROOT / "results/cgsa_ab/legacy_l1.parquet",
        "L2": PROJECT_ROOT / "results/cgsa_ab/legacy_l2.parquet",
        "L3": PROJECT_ROOT / "results/cgsa_ab/legacy_l3.parquet",
    }
    
    structural_baseline = {
        "L1": {"columns": ["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]},
        "L2": {"columns": ["Date", "Symbol", "EMA_10", "EMA_20"]},
        "L3": {"columns": ["Date", "Symbol", "Signal"]},
    }

    report = run_validation(
        cgsa_layers=cgsa_layers,
        legacy_layers=legacy_layers,
        structural_baseline=structural_baseline,
        strict_missing_layers=True,
    )
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run_test_and_print_report()
