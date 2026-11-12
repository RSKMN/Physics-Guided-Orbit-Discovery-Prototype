"""Compatibility shim for the old ``src.observation_generator`` path."""

from orbit_discovery.component2_observations.generator import (
    DAYS_PER_YEAR,
    PROJECT_ROOT,
    generate_observations,
    load_config,
    main,
)

__all__ = [
    "DAYS_PER_YEAR",
    "PROJECT_ROOT",
    "generate_observations",
    "load_config",
    "main",
]


if __name__ == "__main__":
    main()
