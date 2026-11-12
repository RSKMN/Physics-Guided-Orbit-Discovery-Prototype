"""Focused tests for :mod:`orbit_discovery.core.constants`.

The tests use no temporary files. They are written with the standard-library
``unittest`` framework because pytest is not installed in the development
environment; pytest can still collect them.

Run directly with::

    python tests/test_core_constants.py -v
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from orbit_discovery.core import constants


class ConstantsTests(unittest.TestCase):
    """Tests for the approved shared constants."""

    def test_days_per_year_has_exact_expected_value(self) -> None:
        self.assertEqual(constants.DAYS_PER_YEAR, 365.25)
        self.assertIsInstance(constants.DAYS_PER_YEAR, float)

    def test_arcsec_to_deg_has_exact_expected_value(self) -> None:
        self.assertEqual(constants.ARCSEC_TO_DEG, 1.0 / 3600.0)
        self.assertIsInstance(constants.ARCSEC_TO_DEG, float)

    def test_existing_conversion_expressions_are_preserved(self) -> None:
        self.assertAlmostEqual(constants.DAYS_PER_YEAR * 4.0, 1461.0)
        self.assertAlmostEqual(constants.ARCSEC_TO_DEG * 3600.0, 1.0)
        self.assertAlmostEqual(2.0 / constants.DAYS_PER_YEAR, 2.0 / 365.25)

    def test_only_approved_public_constants_are_exported(self) -> None:
        public_constants = {
            name
            for name in vars(constants)
            if name.isupper() and not name.startswith("_")
        }

        self.assertEqual(
            public_constants,
            {"DAYS_PER_YEAR", "ARCSEC_TO_DEG"},
        )
        self.assertFalse(hasattr(constants, "OBLIQUITY_DEG"))

    def test_module_has_no_third_party_imports(self) -> None:
        module_path = Path(constants.__file__)
        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])

        allowed = set(sys.stdlib_module_names) | {"__future__"}
        self.assertEqual(imported - allowed, set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
