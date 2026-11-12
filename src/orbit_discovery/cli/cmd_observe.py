"""`orbit observe` — Component 2 observation generation command.

See docs/development/PHASE_1_STEP_4_1_CLI_ASSESSMENT.md for the full
CLI architecture design. This command integrates the existing Component 2
observation generator with the CLI, using the project's approved path
policy from core.paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

from orbit_discovery.core.paths import (
    ProjectRootNotFoundError,
    resolve_config_path,
    resolve_output_root,
    resolve_project_root,
)

from orbit_discovery.component2_observations.generator import (
    generate_observations,
    load_config,
)


def _compute_output_directory(config: dict, project_root: Path) -> Path:
    """Compute the output directory, mirroring the generator's logic.

    The generator resolves output paths as:
      PROJECT_ROOT / output_config.directory / observation_name
    """
    output_config = config["output"]
    output_dir = Path(output_config["directory"])
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    observation_name = config["observation_name"]
    return output_dir / observation_name


def cmd(args: list[str] | None = None) -> int:
    """Handle the ``orbit observe`` subcommand.

    Args:
        args: Remaining command-line arguments after ``orbit observe``.

    Returns:
        Exit code (0 = success, 1 = configuration error, 2 = runtime error).
    """
    if args is None:
        args = sys.argv[1:]

    if "--help" in args or "-h" in args or args == []:
        print("orbit observe -- Component 2 observation generation")
        print()
        print("Usage: orbit observe [--config CONFIG] [--project-root DIR]")
        print("       orbit observe --help          This help message")
        print("       orbit observe --version       Show version")
        print()
        print("Options:")
        print("  --config CONFIG          Path to observation JSON config (default: configs/synthetic_observations.json)")
        print("  --project-root DIR       Explicit project root directory")
        print("  --output-root DIR        Base output directory (relative to project root)")
        print("  --help, -h               Show this help message and exit")
        print("  --version, -V            Show program version and exit")
        print()
        print("Generates synthetic astronomical observations from a configuration file.")
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
                "configs/synthetic_observations.json", project_root
            )
    except (ProjectRootNotFoundError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # --- Load config to determine output location ---
    try:
        config, config_file = load_config(resolved_config_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Failed to load configuration: {e}", file=sys.stderr)
        return 1

    # --- Compute output directory (mirrors generator logic) ---
    try:
        output_dir = _compute_output_directory(config, project_root)
    except Exception as e:
        print(f"Error: Failed to compute output directory: {e}", file=sys.stderr)
        return 1

    # --- Run the observation generation pipeline ---
    try:
        observations, metadata = generate_observations(resolved_config_path)
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
        print(f"Error: Unexpected generation failure: {e}", file=sys.stderr)
        return 2

    # --- Report success ---
    observation_name = metadata["observation_name"]
    csv_path = output_dir / "observations.csv"
    metadata_path = output_dir / "metadata.json"

    # Ensure the output directory exists (generator already created it,
    # but ensure it's reported correctly)
    output_dir_str = str(output_dir)

    print()
    print("Synthetic observation generation successful.")
    print(f"Observation name: {observation_name}")
    print(f"Number of observations: {metadata['number_of_observations']}")
    print(
        f"Observation period: "
        f"{observations['time_days'].iloc[0]:.2f} to "
        f"{observations['time_days'].iloc[-1]:.2f} days"
    )
    print(f"\nOutput directory: {output_dir_str}")
    print(f"CSV file: {csv_path}")
    print(f"Metadata file: {metadata_path}")
    print(f"Configuration file: {resolved_config_path}")

    if output_root_arg is not None:
        try:
            resolved_output_root = resolve_output_root(output_root_arg, project_root)
            print(f"Output root (configured): {resolved_output_root}")
        except ProjectRootNotFoundError:
            print(f"Output root (configured): {output_root_arg}")

    print(f"Project root: {project_root}")

    # Print first observation summary
    print()
    print("First observation:")
    first = observations.iloc[0]
    print(f"  time_years: {first['time_years']}")
    print(f"  ra_deg: {first['ra_deg']}")
    print(f"  dec_deg: {first['dec_deg']}")
    print(f"  true_ra_deg: {first.get('true_ra_deg', 'N/A')}")
    print(f"  true_dec_deg: {first.get('true_dec_deg', 'N/A')}")

    return 0