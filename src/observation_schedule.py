
import numpy as np


def generate_observation_times(
    start_day,
    end_day,
    cadence_days,
    available_start_day,
    available_end_day
):
    """
    Generate sparse observation timestamps.

    The exact end time is included if the cadence does not
    land on it.
    """

    if cadence_days <= 0:
        raise ValueError("Cadence must be greater than zero.")

    if end_day <= start_day:
        raise ValueError("End day must be greater than start day.")

    if start_day < available_start_day:
        raise ValueError("Start day is outside trajectory range.")

    if end_day > available_end_day:
        raise ValueError("End day is outside trajectory range.")

    times = np.arange(
        start_day,
        end_day,
        cadence_days,
        dtype=float
    )

    # Include the exact endpoint
    if len(times) == 0 or not np.isclose(
        times[-1], end_day, atol=1e-9
    ):
        times = np.append(times, end_day)

    return times


def interpolate_positions(
    ground_truth_times_days,
    ground_truth_positions,
    observation_times_days
):
    """
    Interpolate asteroid positions at observation timestamps.

    Returns an array of shape (number_of_observations, 3).
    """

    ground_truth_times_days = np.asarray(
        ground_truth_times_days, dtype=float
    )

    ground_truth_positions = np.asarray(
        ground_truth_positions, dtype=float
    )

    observation_times_days = np.asarray(
        observation_times_days, dtype=float
    )

    if ground_truth_positions.shape != (
        len(ground_truth_times_days), 3
    ):
        raise ValueError(
            "Ground-truth positions must have shape (N, 3)."
        )

    if len(ground_truth_times_days) < 2:
        raise ValueError("At least two ground-truth samples are required.")

    if not np.all(np.diff(ground_truth_times_days) > 0):
        raise ValueError(
            "Ground-truth timestamps must be strictly increasing."
        )

    if not np.isfinite(ground_truth_positions).all():
        raise ValueError("Ground-truth positions contain invalid values.")

    if not np.isfinite(observation_times_days).all():
        raise ValueError("Observation times contain invalid values.")

    if (
        np.any(observation_times_days < ground_truth_times_days[0])
        or np.any(observation_times_days > ground_truth_times_days[-1])
    ):
        raise ValueError(
            "Observation time falls outside ground-truth range."
        )

    interpolated = np.column_stack([
        np.interp(
            observation_times_days,
            ground_truth_times_days,
            ground_truth_positions[:, axis]
        )
        for axis in range(3)
    ])

    return interpolated
