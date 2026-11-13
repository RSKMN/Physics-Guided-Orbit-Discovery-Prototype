"""Document the current truth-leak gap until Phase 1 separates truth.

The 0.2.0 observation CSVs contain ``true_ra_deg`` and ``true_dec_deg`` in the
same file a future estimator would read. Phase 0 must not implement the Phase 1
truth-separation work, so this test is a strict xfail: it records the required
end state and will fail loudly (xpass) once the data are fixed, prompting the
xfail marker to be removed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

DATASETS = [
    "synthetic_asteroid_observations",
    "synthetic_asteroid_inclined_observations",
    "synthetic_asteroid_eccentric_observations",
]

TRUTH_COLUMNS = {"true_ra_deg", "true_dec_deg"}


@pytest.mark.xfail(
    strict=True,
    reason="Phase 1 will move true_* columns out of the measurement CSV.",
)
def test_tracked_observations_contain_no_truth_columns() -> None:
    leaked = {}
    for dataset in DATASETS:
        path = ROOT / "data" / "observations" / dataset / "observations.csv"
        columns = set(pd.read_csv(path, nrows=0).columns)
        present = columns & TRUTH_COLUMNS
        if present:
            leaked[dataset] = sorted(present)

    assert not leaked, f"Truth columns found in measurement files: {leaked}"
