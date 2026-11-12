"""Explicit project-root and path-resolution helpers.

The module implements the project's path policy without any third-party
dependency and without filesystem writes. It does not read scientific data or
create directories; those responsibilities belong to the component runners and
CLI commands.

Project-root precedence is:

1. an explicit root argument;
2. the ``ORBIT_DISCOVERY_ROOT`` environment variable;
3. the nearest ancestor of the supplied search location (or current working
   directory) that contains ``pyproject.toml``.

There is deliberately no fallback to the current working directory when
discovery fails. See :class:`ProjectRootNotFoundError`.
"""

from __future__ import annotations

import os
import warnings
from collections.abc import Mapping
from pathlib import Path


_PROJECT_ROOT_ENV_VAR = "ORBIT_DISCOVERY_ROOT"
_ROOT_MARKER = "pyproject.toml"


class ProjectRootNotFoundError(FileNotFoundError):
    """Raised when no usable project root can be resolved.

    This is raised for an invalid explicit or environment-provided root and
    when marker discovery finds no ``pyproject.toml`` ancestor. It prevents a
    silent fallback to the current working directory.
    """


def resolve_project_root(
    project_root: str | Path | None = None,
    *,
    search_from: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
) -> Path:
    """Resolve the project root using an explicit value, environment or marker.

    Precedence is:

    1. ``project_root`` when supplied;
    2. ``ORBIT_DISCOVERY_ROOT`` from ``env`` or the process environment;
    3. the nearest ancestor of ``search_from`` (or ``cwd``) containing
       ``pyproject.toml``.

    Relative explicit and environment values are resolved against ``cwd``,
    which defaults to the current working directory. The returned path is
    absolute and resolved. No current-directory fallback is used when discovery
    fails.

    The environment-variable path may either be absolute or relative to the
    current working directory. A relative value emits a ``UserWarning`` because
    absolute values are preferred for reproducibility.

    Args:
        project_root: Optional explicit project root.
        search_from: Optional location from which to begin marker discovery.
            A file path starts discovery from its parent directory.
        env: Optional environment mapping. When omitted, ``os.environ`` is
            used. Pass an empty mapping to disable environment lookup.
        cwd: Optional current working directory used to resolve relative
            values. Defaults to the process working directory.

    Returns:
        An absolute, resolved project-root path.

    Raises:
        ProjectRootNotFoundError: If a supplied root does not exist or is not a
            directory, or if marker discovery finds no root.
    """

    cwd_path = _resolve_cwd(cwd)

    if project_root is not None:
        if isinstance(project_root, str) and not project_root.strip():
            raise ProjectRootNotFoundError(
                "An explicit project root must not be empty."
            )
        candidate = _resolve_against(project_root, cwd_path)
        return _validate_root(candidate, "explicit project root")

    env_map = os.environ if env is None else env
    env_value = env_map.get(_PROJECT_ROOT_ENV_VAR)

    if env_value:
        env_path = Path(env_value)
        if not env_path.is_absolute():
            warnings.warn(
                f"{_PROJECT_ROOT_ENV_VAR} is relative; resolving it against "
                f"the current working directory ({cwd_path}).",
                UserWarning,
                stacklevel=2,
            )
        candidate = _resolve_against(env_path, cwd_path)
        return _validate_root(
            candidate,
            f"{_PROJECT_ROOT_ENV_VAR} environment variable",
        )

    start = cwd_path if search_from is None else _resolve_against(
        search_from,
        cwd_path,
    )
    discovered = _find_marker_root(start)

    if discovered is None:
        raise ProjectRootNotFoundError(
            "Could not find a project root containing "
            f"'{_ROOT_MARKER}' starting from {start}. "
            "Pass project_root=... or set "
            f"{_PROJECT_ROOT_ENV_VAR}."
        )

    return discovered


def resolve_config_path(
    config_path: str | Path,
    project_root: str | Path,
) -> Path:
    """Resolve a configuration path against a resolved project root.

    Absolute configuration paths are kept absolute; relative paths are joined
    to ``project_root``. The returned path is absolute and resolved. The file is
    not required to exist and no filesystem write is performed.

    Args:
        config_path: Configuration path to resolve.
        project_root: Project root used as the base for relative paths.

    Returns:
        An absolute, resolved configuration path.
    """

    root = _resolve_root_reference(project_root)
    return _resolve_against(config_path, root)


def resolve_output_root(
    output_root: str | Path | None,
    project_root: str | Path,
) -> Path:
    """Resolve the output root, defaulting to the project root.

    An absolute ``output_root`` is kept absolute. A relative value is resolved
    against ``project_root``. When ``output_root`` is ``None`` the resolved
    project root is returned. No directory is created.

    Args:
        output_root: Optional output root.
        project_root: Project root used as the base for relative paths and as
            the default output root.

    Returns:
        An absolute, resolved output root.
    """

    root = _resolve_root_reference(project_root)

    if output_root is None:
        return root

    return _resolve_against(output_root, root)


def _resolve_cwd(cwd: str | Path | None) -> Path:
    """Return an absolute working directory for relative root arguments."""

    if cwd is None:
        return Path.cwd().resolve()
    return Path(cwd).resolve()


def _resolve_root_reference(project_root: str | Path) -> Path:
    """Return an absolute root reference without requiring it to exist."""

    return Path(project_root).resolve()


def _resolve_against(value: str | Path, base: Path) -> Path:
    """Resolve ``value`` relative to ``base`` when it is not absolute."""

    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _validate_root(path: Path, source: str) -> Path:
    """Validate an explicit or environment-provided project root."""

    if not path.exists():
        raise ProjectRootNotFoundError(
            f"The {source} does not exist: {path}"
        )
    if not path.is_dir():
        raise ProjectRootNotFoundError(
            f"The {source} is not a directory: {path}"
        )
    return path


def _find_marker_root(start: Path) -> Path | None:
    """Find the nearest ancestor of ``start`` containing the marker file."""

    if start.is_file():
        start = start.parent

    for candidate in (start, *start.parents):
        if (candidate / _ROOT_MARKER).is_file():
            return candidate.resolve()

    return None
