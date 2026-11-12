"""Focused tests for :mod:`orbit_discovery.core.paths`.

The tests use temporary directories only and never write into the repository.
They are written with the standard-library ``unittest`` framework because pytest
is not installed in the development environment; pytest can still collect them.

Run directly with::

    python tests/test_core_paths.py -v
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from orbit_discovery.core import paths
from orbit_discovery.core.paths import (
    ProjectRootNotFoundError,
    resolve_config_path,
    resolve_output_root,
    resolve_project_root,
)


class _TempDirTestCase(unittest.TestCase):
    """Base class that provides a disposable temporary directory."""

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        self.tmp_path = Path(self._temporary_directory.name)

    def make_directory(self, name: str, *, marker: bool = False) -> Path:
        """Create a directory, optionally containing a project-root marker."""

        directory = self.tmp_path / name
        directory.mkdir(parents=True, exist_ok=True)
        if marker:
            (directory / "pyproject.toml").write_text(
                "[project]\nname = \"fixture\"\n",
                encoding="utf-8",
            )
        return directory


class ProjectRootResolutionTests(_TempDirTestCase):
    """Tests for :func:`resolve_project_root`."""

    def test_explicit_absolute_root_is_used(self) -> None:
        root = self.make_directory("explicit-absolute")

        result = resolve_project_root(root, env={})

        self.assertEqual(result, root.resolve())
        self.assertTrue(result.is_absolute())

    def test_explicit_relative_root_resolves_against_cwd(self) -> None:
        root = self.make_directory("explicit-relative")

        result = resolve_project_root("explicit-relative", cwd=self.tmp_path, env={})

        self.assertEqual(result, root.resolve())

    def test_environment_root_is_used(self) -> None:
        root = self.make_directory("environment-root")

        result = resolve_project_root(
            env={"ORBIT_DISCOVERY_ROOT": str(root)},
            cwd=self.tmp_path,
        )

        self.assertEqual(result, root.resolve())

    def test_relative_environment_root_resolves_against_cwd_and_warns(self) -> None:
        root = self.make_directory("environment-relative")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = resolve_project_root(
                env={"ORBIT_DISCOVERY_ROOT": "environment-relative"},
                cwd=self.tmp_path,
            )

        self.assertEqual(result, root.resolve())
        self.assertTrue(caught)
        self.assertTrue(
            any("ORBIT_DISCOVERY_ROOT" in str(item.message) for item in caught)
        )
        self.assertTrue(issubclass(caught[0].category, UserWarning))

    def test_discovery_from_nested_directory_finds_marker_ancestor(self) -> None:
        root = self.make_directory("project", marker=True)
        nested = root / "data" / "nested"
        nested.mkdir(parents=True)

        result = resolve_project_root(cwd=nested, env={})

        self.assertEqual(result, root.resolve())
        self.assertTrue(result.is_absolute())

    def test_discovery_from_explicit_search_location(self) -> None:
        root = self.make_directory("project", marker=True)
        nested = root / "deeply" / "nested"
        nested.mkdir(parents=True)

        result = resolve_project_root(
            search_from=nested,
            cwd=self.tmp_path,
            env={},
        )

        self.assertEqual(result, root.resolve())

    def test_discovery_selects_nearest_marker_ancestor(self) -> None:
        outer = self.make_directory("outer", marker=True)
        inner = outer / "inner"
        inner.mkdir()
        (inner / "pyproject.toml").write_text(
            "[project]\nname = \"inner\"\n",
            encoding="utf-8",
        )
        nested = inner / "a" / "b"
        nested.mkdir(parents=True)

        result = resolve_project_root(cwd=nested, env={})

        self.assertEqual(result, inner.resolve())

    def test_discovery_failure_raises_without_cwd_fallback(self) -> None:
        empty = self.make_directory("empty")

        with self.assertRaises(ProjectRootNotFoundError) as context:
            resolve_project_root(cwd=empty, env={})

        message = str(context.exception)
        self.assertIn("pyproject.toml", message)
        self.assertIn("ORBIT_DISCOVERY_ROOT", message)
        self.assertEqual(list(empty.iterdir()), [])

    def test_explicit_root_takes_precedence_over_environment_and_discovery(self) -> None:
        explicit = self.make_directory("explicit")
        environment = self.make_directory("environment", marker=True)
        discovered = self.make_directory("discovered", marker=True)
        nested = discovered / "nested"
        nested.mkdir()

        result = resolve_project_root(
            explicit,
            env={"ORBIT_DISCOVERY_ROOT": str(environment)},
            cwd=nested,
        )

        self.assertEqual(result, explicit.resolve())

    def test_environment_takes_precedence_over_discovery(self) -> None:
        environment = self.make_directory("environment")
        discovered = self.make_directory("discovered", marker=True)
        nested = discovered / "nested"
        nested.mkdir()

        result = resolve_project_root(
            env={"ORBIT_DISCOVERY_ROOT": str(environment)},
            cwd=nested,
        )

        self.assertEqual(result, environment.resolve())

    def test_missing_explicit_root_is_rejected(self) -> None:
        missing = self.tmp_path / "missing"

        with self.assertRaises(ProjectRootNotFoundError) as context:
            resolve_project_root(missing, env={})

        self.assertIn("does not exist", str(context.exception))

    def test_file_as_explicit_root_is_rejected(self) -> None:
        not_a_directory = self.tmp_path / "not-a-directory.txt"
        not_a_directory.write_text("content", encoding="utf-8")

        with self.assertRaises(ProjectRootNotFoundError) as context:
            resolve_project_root(not_a_directory, env={})

        self.assertIn("not a directory", str(context.exception))

    def test_empty_explicit_root_is_rejected(self) -> None:
        with self.assertRaises(ProjectRootNotFoundError):
            resolve_project_root("", env={})

    def test_invalid_environment_root_is_rejected(self) -> None:
        missing = self.tmp_path / "missing-environment-root"

        with self.assertRaises(ProjectRootNotFoundError):
            resolve_project_root(
                env={"ORBIT_DISCOVERY_ROOT": str(missing)},
                cwd=self.tmp_path,
            )

    def test_environment_mapping_is_not_mutated(self) -> None:
        root = self.make_directory("environment")
        environment = {"ORBIT_DISCOVERY_ROOT": str(root)}
        original = dict(environment)

        resolve_project_root(env=environment, cwd=self.tmp_path)

        self.assertEqual(environment, original)

    def test_module_has_no_third_party_imports(self) -> None:
        module_path = Path(paths.__file__)
        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])

        allowed = set(sys.stdlib_module_names) | {"__future__"}
        self.assertEqual(imported - allowed, set())


class ConfigPathResolutionTests(_TempDirTestCase):
    """Tests for :func:`resolve_config_path`."""

    def setUp(self) -> None:
        super().setUp()
        self.root = self.make_directory("project")

    def test_relative_path_resolves_against_project_root(self) -> None:
        result = resolve_config_path(
            "configs/synthetic_asteroid.json",
            self.root,
        )

        expected = (self.root / "configs" / "synthetic_asteroid.json").resolve()
        self.assertEqual(result, expected)
        self.assertTrue(result.is_absolute())

    def test_absolute_path_is_preserved(self) -> None:
        absolute = (self.tmp_path / "external" / "custom.json").resolve()

        result = resolve_config_path(absolute, self.root)

        self.assertEqual(result, absolute)

    def test_path_containing_parent_segments_is_resolved(self) -> None:
        result = resolve_config_path(
            "configs/../configs/synthetic_asteroid.json",
            self.root,
        )

        expected = (self.root / "configs" / "synthetic_asteroid.json").resolve()
        self.assertEqual(result, expected)

    def test_nonexistent_path_is_returned_without_error(self) -> None:
        result = resolve_config_path("configs/does-not-exist.json", self.root)

        self.assertEqual(
            result,
            (self.root / "configs" / "does-not-exist.json").resolve(),
        )
        self.assertFalse(result.exists())

    def test_resolution_does_not_create_directories(self) -> None:
        resolve_config_path("configs/synthetic_asteroid.json", self.root)

        self.assertFalse((self.root / "configs").exists())


class OutputRootResolutionTests(_TempDirTestCase):
    """Tests for :func:`resolve_output_root`."""

    def setUp(self) -> None:
        super().setUp()
        self.root = self.make_directory("project")

    def test_relative_output_root_resolves_against_project_root(self) -> None:
        result = resolve_output_root("generated/run", self.root)

        self.assertEqual(result, (self.root / "generated" / "run").resolve())
        self.assertTrue(result.is_absolute())

    def test_absolute_output_root_is_preserved(self) -> None:
        absolute = (self.tmp_path / "elsewhere" / "output").resolve()

        result = resolve_output_root(absolute, self.root)

        self.assertEqual(result, absolute)

    def test_none_defaults_to_project_root(self) -> None:
        result = resolve_output_root(None, self.root)

        self.assertEqual(result, self.root.resolve())

    def test_resolution_does_not_create_directories(self) -> None:
        output = resolve_output_root("generated/run", self.root)

        self.assertFalse(output.exists())
        self.assertFalse((self.root / "generated").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
