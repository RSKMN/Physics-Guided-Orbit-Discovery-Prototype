"""`orbit compare` — Same-type trajectory/observation comparison command.

See docs/development/PHASE_1_STEP_4_5_2_COMPARE_COMMAND.md for the full
implementation documentation. This command supports same-type comparisons
within Component 1 trajectory data and within Component 2 observation data,
with summary statistics and residual analysis modes.

Cross-type (Component 1 vs. Component 2) comparison is intentionally not
supported without frame alignment and time-mapping studies.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from orbit_discovery.core.paths import (
    ProjectRootNotFoundError,
    resolve_project_root,
)


# Default file paths (relative to project root)
DEFAULT_COMPONENT1_TRAJECTORY = Path("data/runs/synthetic_asteroid/trajectory.csv")
DEFAULT_COMPONENT2_OBSERVATION = Path("data/observations/synthetic_asteroid_observations/observations.csv")


def _read_trajectory_csv(path: Path) -> pd.DataFrame:
    """Read a trajectory CSV with UTF-8 encoding."""
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="utf-8-sig")
    return df


def _has_component1_columns(df: pd.DataFrame) -> bool:
    """Check if DataFrame has Component 1 trajectory columns."""
    required = {"time_years", "x_au", "y_au", "z_au"}
    return required.issubset(set(df.columns))


def _has_component2_columns(df: pd.DataFrame) -> bool:
    """Check if DataFrame has Component 2 observation columns."""
    required = {"time_years", "ra_deg", "dec_deg"}
    return required.issubset(set(df.columns))


def _compute_summary_statistics(df: pd.DataFrame, cols: list[str]) -> dict[str, dict]:
    """Compute summary statistics for specified columns in a DataFrame."""
    result: dict[str, dict] = {}
    for col in cols:
        if col in df.columns:
            s = df[col]
            result[col] = {
                "mean": float(s.mean()),
                "std": float(s.std()),
                "min": float(s.min()),
                "max": float(s.max()),
                "rms": float((s ** 2).mean() ** 0.5),
            }
    return result


def _compute_residuals(df1: pd.DataFrame, df2: pd.DataFrame, shared_cols: list[str]) -> dict[str, dict]:
    """Compute residuals between two DataFrames for shared columns."""
    result: dict[str, dict] = {}
    for col in shared_cols:
        if col in df1.columns and col in df2.columns:
            s1 = df1[col].astype(float)
            s2 = df2[col].astype(float)
            # Align by index (assume same length/row order)
            min_len = min(len(s1), len(s2))
            diff = s1.iloc[:min_len] - s2.iloc[:min_len]
            result[col] = {
                "mean_residual": float(diff.mean()),
                "std_residual": float(diff.std()),
                "max_abs_residual": float(diff.abs().max()),
                "residuals": diff.iloc[:min_len].tolist(),
            }
    return result


def cmd(args: list[str] | None = None) -> int:
    """Handle the ``orbit compare`` subcommand.

    Args:
        args: Remaining command-line arguments after ``orbit compare``.

    Returns:
        Exit code (0 = success, 1 = configuration error, 2 = runtime error).
    """
    if args is None:
        args = sys.argv[1:]

    # --- Help ---
    if "--help" in args or "-h" in args or args == []:
        print("orbit compare -- Same-type trajectory/observation comparison")
        print()
        print("Usage: orbit compare [--simulation SIM] [--observation OBS]")
        print("                       [--project-root DIR] [--output-dir DIR] [--mode MODE]")
        print("       orbit compare --help          This help message")
        print("       orbit compare --version       Show version")
        print()
        print("Options:")
        print("  --simulation SIM          Path to Component 1 trajectory CSV")
        print("  --observation OBS         Path to Component 2 observation CSV")
        print("  --project-root DIR        Project root directory")
        print("  --output-dir DIR          Output directory for comparison results")
        print("  --mode MODE               Comparison mode: summary, residuals, overlay")
        print("  --help, -h                Show this help message and exit")
        print("  --version, -V             Show version and exit")
        print()
        print("Comparisons are same-type only:")
        print("  --simulation: Compare Component 1 trajectories (heliocentric ecliptic)")
        print("  --observation: Compare Component 2 observations (equatorial coordinates)")
        print()
        print("Cross-type (Component 1 vs. Component 2) is not supported without")
        print("frame alignment and time-mapping studies.")
        print()
        print("Use 'orbit compare --help' for detailed mode descriptions.")
        return 0

    # --- Version ---
    if "--version" in args or "-V" in args:
        print("orbit CLI prototype v0.2.0")
        return 0

    # --- Parse arguments ---
    simulation_path = None
    observation_path = None
    project_root_arg = None
    output_dir_arg = None
    mode = "summary"

    i = 0
    while i < len(args):
        if args[i] == "--simulation" and i + 1 < len(args):
            simulation_path = args[i + 1]
            i += 2
        elif args[i] == "--observation" and i + 1 < len(args):
            observation_path = args[i + 1]
            i += 2
        elif args[i] == "--project-root" and i + 1 < len(args):
            project_root_arg = args[i + 1]
            i += 2
        elif args[i] == "--output-dir" and i + 1 < len(args):
            output_dir_arg = args[i + 1]
            i += 2
        elif args[i] == "--mode" and i + 1 < len(args):
            mode = args[i + 1]
            i += 2
        else:
            i += 1

    # --- Validate: --simulation and --observation are mutually exclusive ---
    if simulation_path is not None and observation_path is not None:
        print(
            "Error: Cannot specify both --simulation and --observation. "
            "Use one or the other for same-type comparison.",
            file=sys.stderr,
        )
        print(
            "  --simulation: Component 1 trajectory comparison",
            file=sys.stderr,
        )
        print(
            "  --observation: Component 2 observation comparison",
            file=sys.stderr,
        )
        return 1

    # --- Resolve project root ---
    try:
        if project_root_arg is not None:
            project_root = resolve_project_root(project_root_arg)
        else:
            project_root = resolve_project_root()
    except ProjectRootNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # --- Determine comparison type and resolve file paths ---
    if simulation_path is not None:
        # Component 1 same-type comparison
        sim_path = Path(simulation_path)
        if not sim_path.is_file():
            print(
                f"Error: Component 1 trajectory file not found: {sim_path}",
                file=sys.stderr,
            )
            return 1

        default_file = project_root / DEFAULT_COMPONENT1_TRAJECTORY
        if not default_file.is_file():
            print(
                f"Error: Default Component 1 trajectory file not found: {default_file}",
                file=sys.stderr,
            )
            return 1

        try:
            df1 = _read_trajectory_csv(sim_path)
            df2 = _read_trajectory_csv(default_file)
        except (ValueError, UnicodeDecodeError) as e:
            print(f"Error: Failed to read CSV: {e}", file=sys.stderr)
            return 1

        # Check file type by column presence
        if not _has_component1_columns(df1):
            print(
                "Error: Expected Component 1 trajectory format "
                f"(missing columns {set({'time_years', 'x_au', 'y_au', 'z_au'} - set(df1.columns))}). "
                "Got columns: " + str(list(df1.columns))[:100],
                file=sys.stderr,
            )
            return 1

        # --- Execute comparison based on mode ---
        try:
            if mode == "summary":
                # Compute summary statistics for all columns present in both files
                all_cols = [c for c in df1.columns if c in df2.columns]
                stats = _compute_summary_statistics(df1, all_cols)

                print(f"Component 1 trajectory comparison summary")
                print(f"  File 1: {sim_path}")
                print(f"  File 2 (default): {default_file}")
                print(f"  Mode: {mode}")
                print()
                for col in sorted(all_cols):
                    if col in df1.columns and col in df2.columns:
                        s = _compute_summary_statistics(df1, [col])[col]
                        print(f"Column: {col}")
                        print(f"  Mean:   {s['mean']:.6g}")
                        print(f"  Std:    {s['std']:.6g}")
                        print(f"  Min:    {s['min']:.6g}")
                        print(f"  Max:    {s['max']:.6g}")
                        print(f"  RMS:    {s['rms']:.6g}")
                print()

            elif mode == "residuals":
                # Compute residuals between the two files
                shared_cols = [c for c in df1.columns if c in df2.columns]
                res = _compute_residuals(df1, df2, shared_cols)

                print(f"Component 1 trajectory residuals")
                print(f"  File 1: {sim_path}")
                print(f"  File 2 (default): {default_file}")
                print(f"  Mode: {mode}")
                print()
                for col in sorted(res.keys()):
                    r = res[col]
                    print(f"Column: {col}")
                    print(f"  Mean residual: {r['mean_residual']:.6g}")
                    print(f"  Std of residual: {r['std_residual']:.6g}")
                    print(f"  Max |residual|: {r['max_abs_residual']:.6g}")
                    if r["residuals"]:
                        print(f"  Number of residual points: {len(r['residuals'])}")
                print()

            elif mode == "overlay":
                # Report overlay data (time-series) without requiring matplotlib
                shared_cols = [c for c in df1.columns if c in df2.columns]
                n_rows = min(len(df1), len(df2))

                print(f"Component 1 trajectory overlay data")
                print(f"  File 1: {sim_path}")
                print(f"  File 2 (default): {default_file}")
                print(f"  Mode: {mode}")
                print(f"  Shared columns: {shared_cols}")
                print()
                for col in shared_cols:
                    v1 = df1[col].iloc[:n_rows].values
                    v2 = df2[col].iloc[:n_rows].values
                    print(f"Column: {col}")
                    print(f"  File 1 first 5: {v1[:5].tolist()}")
                    print(f"  File 2 first 5: {v2[:5].tolist()}")
                print()
                print("Overlay data reported above. Use --mode summary or --mode residuals")
                print("for statistical analysis, or plotting software for visualization.")

            else:
                print(
                    f"Error: Unsupported comparison mode '{mode}'. "
                    "Use: summary, residuals, or overlay.",
                    file=sys.stderr,
                )
                return 1

        except Exception as e:
            print(f"Error: Comparison failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return 2

        # --- Report output directory if specified ---
        if output_dir_arg is not None:
            output_dir = Path(output_dir_arg)
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                print(f"Output directory: {output_dir}")
            except OSError as e:
                print(f"Error: Cannot create output directory: {e}", file=sys.stderr)
                return 1

        return 0

    elif observation_path is not None:
        # Component 2 same-type comparison
        comp_path = Path(observation_path)

        if not comp_path.is_file():
            print(
                f"Error: Component 2 observation file not found: {comp_path}",
                file=sys.stderr,
            )
            return 1

        default_comp_path = project_root / DEFAULT_COMPONENT2_OBSERVATION
        if not default_comp_path.is_file():
            print(
                f"Error: Default Component 2 observation file not found: {default_comp_path}",
                file=sys.stderr,
            )
            return 1

        try:
            df1 = _read_trajectory_csv(comp_path)
            df2 = _read_trajectory_csv(default_comp_path)
        except (ValueError, UnicodeDecodeError) as e:
            print(f"Error: Failed to read CSV: {e}", file=sys.stderr)
            return 1

        # Check file type by column presence
        if not _has_component2_columns(df1):
            print(
                "Error: Expected Component 2 observation format "
                f"(missing columns {set({'time_years', 'ra_deg', 'dec_deg'} - set(df1.columns))}). "
                "Got columns: " + str(list(df1.columns))[:100],
                file=sys.stderr,
            )
            return 1

        # --- Execute comparison based on mode ---
        try:
            if mode == "summary":
                all_cols = [c for c in df1.columns if c in df2.columns]
                stats = _compute_summary_statistics(df1, all_cols)

                print(f"Component 2 observation comparison summary")
                print(f"  File 1: {comp_path}")
                print(f"  File 2 (default): {default_comp_path}")
                print(f"  Mode: {mode}")
                print()
                for col in sorted(all_cols):
                    if col in df1.columns and col in df2.columns:
                        s = _compute_summary_statistics(df1, [col])[col]
                        print(f"Column: {col}")
                        print(f"  Mean:   {s['mean']:.6g}")
                        print(f"  Std:    {s['std']:.6g}")
                        print(f"  Min:    {s['min']:.6g}")
                        print(f"  Max:    {s['max']:.6g}")
                        print(f"  RMS:    {s['rms']:.6g}")
                print()

            elif mode == "residuals":
                shared_cols = [c for c in df1.columns if c in df2.columns]
                res = _compute_residuals(df1, df2, shared_cols)

                print(f"Component 2 observation residuals")
                print(f"  File 1: {comp_path}")
                print(f"  File 2 (default): {default_comp_path}")
                print(f"  Mode: {mode}")
                print()
                for col in sorted(res.keys()):
                    r = res[col]
                    print(f"Column: {col}")
                    print(f"  Mean residual: {r['mean_residual']:.6g}")
                    print(f"  Std of residual: {r['std_residual']:.6g}")
                    print(f"  Max |residual|: {r['max_abs_residual']:.6g}")
                    if r["residuals"]:
                        print(f"  Number of residual points: {len(r['residuals'])}")
                print()

            elif mode == "overlay":
                shared_cols = [c for c in df1.columns if c in df2.columns]
                n_rows = min(len(df1), len(df2))

                print(f"Component 2 observation overlay data")
                print(f"  File 1: {comp_path}")
                print(f"  File 2 (default): {default_comp_path}")
                print(f"  Mode: {mode}")
                print(f"  Shared columns: {shared_cols}")
                print()
                for col in shared_cols:
                    v1 = df1[col].iloc[:n_rows].values
                    v2 = df2[col].iloc[:n_rows].values
                    print(f"Column: {col}")
                    print(f"  File 1 first 5: {v1[:5].tolist()}")
                    print(f"  File 2 first 5: {v2[:5].tolist()}")
                print()
                print("Overlay data reported above. Use --mode summary or --mode residuals")
                print("for statistical analysis.")

            else:
                print(
                    f"Error: Unsupported comparison mode '{mode}'. "
                    "Use: summary, residuals, or overlay.",
                    file=sys.stderr,
                )
                return 1

        except Exception as e:
            print(f"Error: Comparison failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return 2

        # --- Report output directory if specified ---
        if output_dir_arg is not None:
            output_dir = Path(output_dir_arg)
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                print(f"Output directory: {output_dir}")
            except OSError as e:
                print(f"Error: Cannot create output directory: {e}", file=sys.stderr)
                return 1

        return 0

    else:
        # No arguments provided: default to --simulation mode with default paths
        print("orbit compare: no comparison arguments specified.")
        print("Use 'orbit compare --simulation <file>' or 'orbit compare --observation <file>'")
        print("Use 'orbit compare --help' for usage information.")
        return 0