"""`orbit simulate` — Component 1 N-body simulation command.

See docs/development/PHASE_1_STEP_4_1_CLI_ASSESSMENT.md for the full
CLI architecture design. This command integrates the existing Component 1
simulator (configurable_simulator) with the CLI, using the project's approved
path policy from core.paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

from orbit_discovery.core.paths import (
    ProjectRootNotFoundError,
    resolve_config_path,
    resolve_project_root,
)

# Import configurable_simulator from src/ (not from orbit_discovery package)
import configurable_simulator as _cs
from configurable_simulator import generate_trajectory


def cmd(args: list[str] | None = None) -> int:
    """Handle the ``orbit simulate`` subcommand.

    Args:
        args: Remaining command-line arguments after ``orbit simulate``.

    Returns:
        Exit code (0 = success, 1 = configuration error, 2 = runtime error).
    """
    if args is None:
        args = sys.argv[1:]

    if "--help" in args or "-h" in args or args == []:
        print("orbit simulate -- Component 1 N-body simulation")
        print()
        print("Usage: orbit simulate [--config CONFIG] [--project-root DIR]")
        print("       orbit simulate --help          This help message")
        print("       orbit simulate --version       Show version")
        print()
        print("Options:")
        print("  --config CONFIG          Path to simulation JSON config (default: configs/synthetic_asteroid.json)")
        print("  --project-root DIR       Explicit project root directory")
        print("  --help, -h               Show this help message and exit")
        print("  --version, -V            Show program version and exit")
        print()
        print("Generates an asteroid trajectory using the configurable N-body simulator.")
        print("See: docs/development/PHASE_1_STEP_4_1_CLI_ASSESSMENT.md")
        return 0

    if "--version" in args or "-V" in args:
        print("orbit CLI prototype v0.2.0")
        return 0

    # --- Parse arguments ---
    config_arg = None
    project_root_arg = None
    output_root_arg = None

    i = 0
    while i < len(args):
        if args[i] == "--config" and i + 1 < len(args):
            config_arg = args[i + 1]
            i += 2
        elif args[i] == "--project-root" and i + 1 < len(args):
            project_root_arg = args[i + 1]
            i += 2
        elif args[i] == "--output-root" and i + 1 < len(args):
            output_root_arg = args[i + 1]
            i += 2
        else:
            i += 1

    # --- Check for unsupported --output-root argument ---
    # The configurable simulator uses its own internal output.directory from the
    # configuration file.  CLI-level --output-root is not supported in this phase.
    if output_root_arg is not None:
        print(
            "Error: --output-root is not supported in this phase. "
            "The configurable simulator determines its output directory from "
            "the configuration file's output.directory field. "
            "Please omit --output-root and use --config to control output location.",
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

    # --- Resolve config path ---
    try:
        if config_arg is not None:
            resolved_config_path = resolve_config_path(config_arg, project_root)
        else:
            # Default config: relative to project root
            resolved_config_path = resolve_config_path(
                "configs/synthetic_asteroid.json", project_root
            )
    except (ProjectRootNotFoundError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # --- Detect conflict between CLI project root and simulator's internal ROOT
    # The simulator always uses ROOT = Path(__file__).resolve().parents[1] (repo root).
    # If the user provided an explicit --project-root that differs from the simulator's
    # ROOT, this is an unsupported configuration for this checkpoint.
    simulator_root = Path("src/configurable_simulator.py").resolve().parents[1]
    explicit_project_root_given = project_root_arg is not None
    root_conflicts = explicit_project_root_given and project_root != simulator_root

    if root_conflicts:
        print(
            f"Error: --project-root '{project_root_arg}' conflicts with the "
            f"simulator's fixed repository root '{simulator_root}'. "
            "The simulator always resolves paths relative to its repository root. "
            "Please run from the repository root or omit --project-root.",
            file=sys.stderr,
        )
        return 1

    # --- Run the simulation using the existing Component 1 simulator ---
    try:
        generate_trajectory(resolved_config_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"Error: Missing required configuration key: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Unexpected simulation failure: {e}", file=sys.stderr)
        return 2

    # --- Report success ---
    import pandas as pd

    # Resolve the output location from the configuration that was actually run.
    # The simulator resolves relative output directories against its own ROOT
    # (the repository root), so mirror that rule here instead of hardcoding a
    # scenario name.
    config = _cs.load_config(resolved_config_path)
    simulation_name = config["simulation_name"]
    output_dir = Path(_cs.ROOT) / config["output"]["directory"]
    trajectory_path = output_dir / "trajectory.csv"

    if trajectory_path.exists():
        df = pd.read_csv(trajectory_path)
        n_samples = len(df)
    else:
        n_samples = "?"

    print()
    print("Simulation completed successfully.")
    print(f"Simulation name: {simulation_name}")
    print(f"Number of samples: {n_samples}")
    print(f"Output directory: {output_dir}")
    print(f"CSV file: {trajectory_path}")
    print(f"Config file: {output_dir / 'config.json'}")
    print(f"Metadata file: {output_dir / 'metadata.json'}")
    print(f"Configuration file: {resolved_config_path}")
    print(f"Project root: {project_root}")

    print(f"Simulator ROOT: {simulator_root}")

    return 0