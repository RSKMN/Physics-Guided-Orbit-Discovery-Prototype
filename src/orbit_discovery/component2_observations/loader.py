
import numpy as np
import pandas as pd
from pathlib import Path

from orbit_discovery.core.constants import DAYS_PER_YEAR


REQUIRED_COLUMNS = [
    "time_years",
    "time_days",
    "x_au",
    "y_au",
    "z_au",
    "vx_au_per_year",
    "vy_au_per_year",
    "vz_au_per_year"
]


def load_trajectory(csv_path):
    """
    Load and validate a ground-truth asteroid trajectory.

    Returns:
        Dictionary containing time, position and velocity arrays.
    """

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Trajectory file not found: {csv_path}"
        )

    data = pd.read_csv(csv_path)

    # Check required columns
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Extract required numerical data
    data = data[REQUIRED_COLUMNS].copy()

    # Reject missing or non-numeric values
    data = data.apply(pd.to_numeric, errors="coerce")

    if data.isnull().any().any():
        raise ValueError(
            "Trajectory contains missing or invalid numerical values."
        )

    values = data.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(
            "Trajectory contains infinite or non-finite values."
        )

    # Extract time arrays
    time_years = data["time_years"].to_numpy()
    time_days = data["time_days"].to_numpy()

    # Check timestamps
    if len(time_years) < 2:
        raise ValueError(
            "Trajectory must contain at least two samples."
        )

    if not np.all(np.diff(time_years) > 0):
        raise ValueError(
            "Trajectory timestamps must be strictly increasing."
        )

    if not np.allclose(
        time_days,
        time_years * DAYS_PER_YEAR,
        rtol=0,
        atol=1e-6
    ):
        raise ValueError(
            "Time columns are inconsistent."
        )

    # Extract positions and velocities
    positions = data[
        ["x_au", "y_au", "z_au"]
    ].to_numpy()

    velocities = data[
        [
            "vx_au_per_year",
            "vy_au_per_year",
            "vz_au_per_year"
        ]
    ].to_numpy()

    print("Trajectory loaded successfully.")
    print(f"Number of samples: {len(data)}")
    print(
        f"Duration: {time_years[0]:.3f} "
        f"to {time_years[-1]:.3f} years"
    )

    return {
        "time_years": time_years,
        "time_days": time_days,
        "positions": positions,
        "velocities": velocities,
        "number_of_samples": len(data)
    }
