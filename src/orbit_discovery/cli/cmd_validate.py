"""`orbit validate` — Read-only validation command.

Validates configuration files and supported data files (trajectory CSVs,
observation CSVs + metadata pairs). All validation is read-only: no files
are modified, no repairs are attempted, and no scientific assumptions are
introduced beyond what the existing validation logic already checks.

See docs/development/PHASE_1_STEP_4_6_VALIDATE_COMMAND.md for the full
implementation documentation.
"""

from __future__ import annotations

import sys
from pathlib import Path

from orbit_discovery.core.paths import (
    ProjectRootNotFoundError,
    resolve_project_root,
    resolve_config_path,
)

import pandas as pd
import numpy as np


# Default file paths (relative to project root)
DEFAULT_TRAJECTORY = Path("data/trajectory_two_body.csv")
DEFAULT_OBSERVATIONS = Path("data/observations/synthetic_asteroid_observations/observations.csv")
DEFAULT_METADATA = Path("data/observations/synthetic_asteroid_observations/metadata.json")


# ── Trajectory column sets ────────────────────────────────────────────────

# Schema for Component 1 trajectory data (synthetic_asteroid runs)
_TRAJ_COLUMNS_SYNTHETIC = {
    "time_years", "time_days", "x_au", "y_au", "z_au",
    "vx_au_per_year", "vy_au_per_year", "vz_au_per_year",
}

# Schema for Component 1 two-body trajectory data
_TRAJ_COLUMNS_TWO_BODY = {
    "time_yr", "x_AU", "y_AU", "z_AU",
    "vx_AU_per_yr", "vy_AU_per_yr", "vz_AU_per_yr",
    "distance_AU",
}


def _has_traj_synthetic_columns(df: pd.DataFrame) -> bool:
    """Check if DataFrame has synthetic asteroid trajectory format."""
    return _TRAJ_COLUMNS_SYNTHETIC.issubset(set(df.columns))


def _has_traj_two_body_columns(df: pd.DataFrame) -> bool:
    """Check if DataFrame has two-body trajectory format."""
    return _TRAJ_COLUMNS_TWO_BODY.issubset(set(df.columns))


# ── Observation column sets ───────────────────────────────────────────────

# Schema for Component 2 observation data
_OBS_COLUMNS = {
    "time_years", "time_days", "ra_deg", "dec_deg",
    "sigma_ra_cosdec_arcsec", "sigma_dec_arcsec",
    "true_ra_deg", "true_dec_deg",
}


def _has_obs_columns(df: pd.DataFrame) -> bool:
    """Check if DataFrame has Component 2 observation format."""
    return _OBS_COLUMNS.issubset(set(df.columns))


# ── Validation helpers ────────────────────────────────────────────────────

def _check_required_columns(df: pd.DataFrame, required: set[str]) -> list[str]:
    """Return sorted list of missing required columns."""
    missing = required - set(df.columns)
    return sorted(missing)


def _check_values_finite(df: pd.DataFrame, cols: list[str]) -> bool:
    """Check that specified columns contain only finite values."""
    try:
        values = df[cols].to_numpy(dtype=float)
        return np.isfinite(values).all()
    except (ValueError, TypeError):
        return False


def _check_timestamps_increasing(df: pd.DataFrame, col: str) -> bool:
    """Check that timestamps in the specified column are strictly increasing."""
    values = df[col].values
    return bool(np.all(np.diff(values) > 0))


def _check_time_consistency(df: pd.DataFrame) -> bool:
    """Check that time_days ≈ time_years * 365.25 within tolerance."""
    try:
        years = df["time_years"].astype(float)
        days = df["time_days"].astype(float)
        expected = years * 365.25
        return np.allclose(days, expected, rtol=0, atol=1e-8)
    except (ValueError, TypeError):
        return False


# ── Core validation functions ────────────────────────────────────────────

def validate_trajectory(path: Path) -> list[str]:
    """Validate a trajectory CSV file.

    Returns a list of zero or more human-readable issue descriptions.
    An empty list means the file passed all checks.

    Does NOT modify the file.
    """
    issues: list[str] = []

    # Read the file
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return [f"Error reading CSV file: {e}"]

    # Determine format and check columns
    has_synthetic = _has_traj_synthetic_columns(df)
    has_two_body = _has_traj_two_body_columns(df)

    if has_synthetic:
        required = _TRAJ_COLUMNS_SYNTHETIC
        missing = _check_required_columns(df, required)
        if missing:
            issues.append(
                f"Missing required columns: {', '.join(missing)}"
            )
        else:
            # Check values are finite
            if not _check_values_finite(df, list(required)):
                issues.append("Trajectory contains NaN or infinite values.")
            # Check timestamps strictly increasing
            if not _check_timestamps_increasing(df, "time_years"):
                issues.append("time_years are not strictly increasing.")
            # Check time consistency
            if not _check_time_consistency(df):
                issues.append("time_years and time_days are inconsistent.")
    elif has_two_body:
        required = _TRAJ_COLUMNS_TWO_BODY
        missing = _check_required_columns(df, required)
        if missing:
            issues.append(
                f"Missing required columns: {', '.join(missing)}"
            )
        else:
            # Check values are finite
            if not _check_values_finite(df, list(required)):
                issues.append("Trajectory contains NaN or infinite values.")
            # Check timestamps strictly increasing
            if not _check_timestamps_increasing(df, "time_yr"):
                issues.append("time_yr are not strictly increasing.")
            # Check time consistency (two-body uses time_yr, not time_days)
            # Skip time_days check if column doesn't exist
            if "time_days" in df.columns and not _check_time_consistency(df):
                issues.append("time_yr and time_days are inconsistent.")
    else:
        issues.append(
            "Unknown trajectory format: could not detect required columns. "
            "Expected synthetic format (time_years, x_au, y_au, z_au, vx_au_per_year, "
            "vy_au_per_year, vz_au_per_year) or two-body format "
            "(time_yr, x_AU, y_AU, z_AU, vx_AU_per_yr, vy_AU_per_yr, vz_AU_per_yr, distance_AU)."
        )

    return issues


def validate_observation(path: Path) -> list[str]:
    """Validate an observation CSV file.

    Returns a list of zero or more human-readable issue descriptions.
    An empty list means the file passed all checks.

    Does NOT modify the file.
    """
    issues: list[str] = []

    # Read the file
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return [f"Error reading CSV file: {e}"]

    # Check columns
    if not _has_obs_columns(df):
        missing = _check_required_columns(df, _OBS_COLUMNS)
        issues.append(
            f"Missing required observation columns: {', '.join(missing)}. "
            f"Expected: time_years, time_days, ra_deg, dec_deg, "
            f"sigma_ra_cosdec_arcsec, sigma_dec_arcsec, true_ra_deg, true_dec_deg"
        )
        return issues

    # Check values are finite
    obs_required = sorted(_OBS_COLUMNS)
    if not _check_values_finite(df, obs_required):
        issues.append("Observation data contains NaN or infinite values.")

    # Check timestamps strictly increasing
    if not _check_timestamps_increasing(df, "time_years"):
        issues.append("time_years are not strictly increasing.")

    # Check time consistency
    if not _check_time_consistency(df):
        issues.append("time_years and time_days are inconsistent.")

    # Check coordinate ranges (RA: 0-360, Dec: -90 to +90)
    try:
        ra = df["ra_deg"].astype(float)
        dec = df["dec_deg"].astype(float)
        if (ra < 0).any() or (ra > 360).any():
            issues.append("RA values outside expected range [0, 360] degrees.")
        if (dec < -90).any() or (dec > 90).any():
            issues.append("Dec values outside expected range [-90, 90] degrees.")
    except (ValueError, TypeError):
        pass  # If conversion fails, just skip this check

    return issues


# ── CLI command ───────────────────────────────────────────────────────────

def cmd(args: list[str] | None = None) -> int:
    """Handle the ``orbit validate`` subcommand.

    Args:
        args: Remaining command-line arguments after ``orbit validate``.

    Returns:
        Exit code (0 = all validations pass, 1 = validation failure,
        2 = configuration or runtime error).
    """
    if args is None:
        args = sys.argv[1:]

    # ── Help ──
    if "--help" in args or "-h" in args or args == []:
        print("orbit validate -- Read-only validation of trajectory and observation files")
        print()
        print("Usage: orbit validate [--trajectory CSV] [--project-root DIR]")
        print("                      [--validate-observations] [--help] [--version]")
        print()
        print("Options:")
        print("  --trajectory CSV         Path to trajectory CSV to validate")
        print("                           (default: data/trajectory_two_body.csv)")
        print("  --project-root DIR       Explicit project root directory")
        print("  --validate-observations  Also validate observation CSV + metadata pair")
        print("  --help, -h               Show this help message and exit")
        print("  --version, -V            Show version and exit")
        print()
        print("Validation types:")
        print("  --trajectory:   Validate trajectory CSV columns, timestamps,")
        print("                  and numerical constraints.")
        print("  --validate-observations: Also validate observation CSV columns,")
        print("                          coordinate ranges, and time consistency.")
        print()
        print("Exit codes:")
        print("  0 = all validations pass")
        print("  1 = one or more validations failed (see output for details)")
        print("  2 = configuration error (missing file, project root not found)")
        print()
        print("The command is read-only: no files are modified or rewritten.")
        return 0

    # ── Version ──
    if "--version" in args or "-V" in args:
        print("orbit CLI prototype v0.2.0")
        return 0

    # ── Parse arguments ──
    trajectory_path = None
    project_root_arg = None
    validate_obs = False

    i = 0
    while i < len(args):
        if args[i] == "--trajectory" and i + 1 < len(args):
            trajectory_path = args[i + 1]
            i += 2
        elif args[i] == "--project-root" and i + 1 < len(args):
            project_root_arg = args[i + 1]
            i += 2
        elif args[i] == "--validate-observations":
            validate_obs = True
            i += 1
        else:
            i += 1

    # ── Resolve project root ──
    try:
        if project_root_arg is not None:
            project_root = resolve_project_root(project_root_arg)
        else:
            project_root = resolve_project_root()
    except ProjectRootNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # ── Validate trajectory ──
    if trajectory_path is not None:
        traj_path = Path(trajectory_path)
    else:
        traj_path = Path("data/trajectory_two_body.csv")

    if not traj_path.is_file():
        print(
            f"Error: Trajectory file not found: {traj_path}",
            file=sys.stderr,
        )
        return 1

    traj_issues = validate_trajectory(traj_path)

    # ── Validate observations (if requested) ──
    obs_issues: list[str] = []
    if validate_obs:
        obs_path = project_root / DEFAULT_OBSERVATIONS
        meta_path = project_root / DEFAULT_METADATA

        if not obs_path.is_file():
            print(
                f"Error: Observation file not found: {obs_path}",
                file=sys.stderr,
            )
            return 1

        if not meta_path.is_file():
            print(
                f"Error: Metadata file not found: {meta_path}",
                file=sys.stderr,
            )
            return 1

        obs_issues = validate_observation(obs_path)

    # ── Report results ──
    all_issues = traj_issues + obs_issues

    if not all_issues:
        print(f"Validation passed for: {traj_path}")
        if validate_obs:
            print(f"  (also validated observation file: {DEFAULT_OBSERVATIONS})")
        print(f"  Project root: {project_root}")
        return 0
    else:
        print(f"Validation failed for: {traj_path}", file=sys.stderr)
        for issue in all_issues:
            print(f"  - {issue}", file=sys.stderr)
        if validate_obs and obs_issues:
            print()
            print("Observation validation issues:", file=sys.stderr)
            for issue in obs_issues:
                print(f"  - {issue}", file=sys.stderr)
        return 1