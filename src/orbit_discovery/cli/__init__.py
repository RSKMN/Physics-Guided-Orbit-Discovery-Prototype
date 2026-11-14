"""Command-line interface for physics-guided orbit discovery.

Provides a shared entry point with subcommands:
  orbit simulate   -- Component 1 simulation
  orbit observe    -- Component 2 observation generation
  orbit compare    -- Trajectory/observation comparison
  orbit validate   -- Read-only validation
"""

from __future__ import annotations

import sys
from importlib import import_module

__all__ = []


def list_subcommands() -> list[str]:
    """Discover available subcommand modules in the cli package."""
    subcommands = []
    cli_dir = Path(__file__).parent
    for name in sorted(cli_dir.glob("cmd_*.py")):
        module_name = f"orbit_discovery.cli.{name.stem}"
        # Import the module to check it has a cmd function
        try:
            mod = import_module(module_name)
            if hasattr(mod, "cmd") and callable(getattr(mod, "cmd")):
                subcommands.append(name.stem[4:])  # strip "cmd_" prefix
        except Exception:
            pass
    return subcommands


def main(args: list[str] | None = None) -> int:
    """Entry point for the orbit CLI.

    Dispatches to the appropriate subcommand handler.
    """
    if args is None:
        args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        _print_help()
        return 0

    if args[0] in ("--version", "-V"):
        print("orbit CLI prototype v0.2.0")
        return 0

    # Dispatch to subcommand
    command = args[0]
    # Remove command from args for potential sub-arguments
    sub_args = args[1:]

    # Map command name to module
    command_map = {
        "simulate": "cmd_simulate",
        "observe": "cmd_observe",
        "compare": "cmd_compare",
        "validate": "cmd_validate",
        "estimate": "cmd_estimate",
    }

    if command not in command_map:
        print(f"Unknown command: {command}", file=sys.stderr)
        _print_help()
        return 2

    module_name = f"orbit_discovery.cli.{command_map[command]}"
    try:
        mod = import_module(module_name)
        return mod.cmd(sub_args)
    except ImportError as e:
        print(f"Error loading command '{command}': {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error running command '{command}': {e}", file=sys.stderr)
        return 2


def _print_help() -> None:
    """Print help message with available commands."""
    from pathlib import Path
    cli_dir = Path(__file__).parent
    subcommands = []
    for name in sorted(cli_dir.glob("cmd_*.py")):
        module_name = f"orbit_discovery.cli.{name.stem}"
        try:
            mod = import_module(module_name)
            if hasattr(mod, "cmd") and callable(getattr(mod, "cmd")):
                subcommands.append(name.stem[4:])
        except Exception:
            pass

    print("Orbit CLI - Physics-guided orbit discovery prototype")
    print()
    print("Usage: orbit <command> [options]")
    print()
    print("Available commands:")
    for cmd in sorted(subcommands):
        print(f"  orbit {cmd:<15} -- {_cmd_description(cmd)}")
    print()
    print("Use 'orbit <command> --help' for command-specific options.")
    print("Use 'orbit --version' to show version.")


def _cmd_description(cmd: str) -> str:
    """Return a short description of a command."""
    descriptions = {
        "simulate": "Component 1 N-body simulation",
        "observe": "Component 2 observation generation",
        "compare": "Trajectory/observation comparison",
        "validate": "Read-only validation",
        "estimate": "Component 3 orbit estimation and candidate discovery",
    }
    return descriptions.get(cmd, "")