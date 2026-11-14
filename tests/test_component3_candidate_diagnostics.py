import unittest
import numpy as np
from orbit_discovery.component3.models import OrbitCandidate, OrbitState
from orbit_discovery.component3.candidate_diagnostics import compute_candidate_diagnostics

class TestCandidateDiagnostics(unittest.TestCase):

    def _create_candidate(self, state_arr, metadata, epoch_years=0.0):
        return OrbitCandidate(
            state=OrbitState(
                rx=state_arr[0], ry=state_arr[1], rz=state_arr[2],
                vx=state_arr[3], vy=state_arr[4], vz=state_arr[5]
            ),
            epoch_years=epoch_years,
            metadata=metadata
        )

    def _base_metadata(self):
        return {
            "chi2_reduced": 1.0,
            "chi2": 1.0,
            "start_index": 0,
            "epoch_years": 0.0,
            "coordinate_frame": "heliocentric ecliptic inertial",
            "position_unit": "AU",
            "velocity_unit": "AU/year",
        }

    # ---- Existing tests (retained) ----

    def test_empty_ensemble(self):
        res = compute_candidate_diagnostics([])
        self.assertEqual(res.n_retained_candidates, 0)
        self.assertEqual(res.assessment, "no_candidates")

    def test_empty_pairwise_statistics_none(self):
        res = compute_candidate_diagnostics([])
        self.assertEqual(res.pairwise_distances, [])
        self.assertIsNone(res.mean_pairwise_distance)
        self.assertIsNone(res.max_pairwise_distance)
        self.assertIsNone(res.median_pairwise_distance)
        self.assertIsNone(res.min_pairwise_distance)
        self.assertIsNone(res.std_pairwise_distance)

    def test_single_candidate(self):
        c = self._create_candidate(np.zeros(6), self._base_metadata())
        res = compute_candidate_diagnostics([c])
        self.assertEqual(res.n_retained_candidates, 1)
        self.assertEqual(res.n_clusters, 1)
        self.assertEqual(res.assessment, "insufficient_candidates")

    def test_single_candidate_pairwise_statistics_none(self):
        c = self._create_candidate(np.zeros(6), self._base_metadata())
        res = compute_candidate_diagnostics([c])
        self.assertEqual(res.pairwise_distances, [])
        self.assertIsNone(res.mean_pairwise_distance)
        self.assertIsNone(res.max_pairwise_distance)
        self.assertIsNone(res.median_pairwise_distance)
        self.assertIsNone(res.min_pairwise_distance)
        self.assertIsNone(res.std_pairwise_distance)
        # Per-coordinate spread may legitimately be zero.
        for key in ["rx", "ry", "rz", "vx", "vy", "vz"]:
            self.assertEqual(res.per_coordinate_spread[key]["range"], 0.0)
            self.assertEqual(res.per_coordinate_spread[key]["std"], 0.0)

    def test_compact_group(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([1e-6, 0, 0, 0, 0, 0]), self._base_metadata())
        res = compute_candidate_diagnostics([c1, c2], compactness_threshold_d=0.5)
        self.assertEqual(res.n_clusters, 1)
        self.assertEqual(res.assessment, "single_compact_group")

    def test_separated_groups(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([10.0, 0, 0, 0, 0, 0]), self._base_metadata())
        res = compute_candidate_diagnostics([c1, c2], clustering_threshold_d=2.0)
        self.assertEqual(res.n_clusters, 2)
        self.assertEqual(res.assessment, "multiple_separated_groups")

    def test_determinism(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([1e-6, 0, 0, 0, 0, 0]), self._base_metadata())
        c3 = self._create_candidate(np.array([2e-6, 0, 0, 0, 0, 0]), self._base_metadata())

        res1 = compute_candidate_diagnostics([c1, c2, c3])
        res2 = compute_candidate_diagnostics([c1, c2, c3])

        self.assertEqual(res1.cluster_assignments, res2.cluster_assignments)
        self.assertEqual(res1.n_clusters, res2.n_clusters)

    def test_invalid_candidate(self):
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([None]) # type: ignore

    def test_threshold_boundary_below_equal_above(self):
        tol_pos = 0.005

        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([tol_pos, 0, 0, 0, 0, 0]), self._base_metadata())
        c3 = self._create_candidate(np.array([50.0 * tol_pos, 0, 0, 0, 0, 0]), self._base_metadata())

        res_low = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=0.5)
        self.assertEqual(res_low.n_clusters, 3)

        res_equal = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=1.0)
        self.assertEqual(res_equal.n_clusters, 3)

        res_above = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=1.1)
        self.assertEqual(res_above.n_clusters, 2)

    def test_threshold_sensitivity(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([2.0 * 0.005, 0, 0, 0, 0, 0]), self._base_metadata())
        c3 = self._create_candidate(np.array([4.0 * 0.005, 0, 0, 0, 0, 0]), self._base_metadata())

        res_1 = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=1.0)
        res_2 = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=2.1)

        self.assertLess(res_2.n_clusters, res_1.n_clusters)

    def test_invalid_metadata_missing_key(self):
        meta = self._base_metadata()
        del meta["start_index"]
        c = self._create_candidate(np.zeros(6), meta)
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

    def test_spread_fields_present(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([1.0, 2.0, 3.0, 0.1, 0.2, 0.3]), self._base_metadata())
        res = compute_candidate_diagnostics([c1, c2])
        for key in ["rx", "ry", "rz", "vx", "vy", "vz"]:
            self.assertIn(key, res.per_coordinate_spread)
            self.assertIn("min", res.per_coordinate_spread[key])
            self.assertIn("max", res.per_coordinate_spread[key])
            self.assertIn("range", res.per_coordinate_spread[key])

    def test_pairwise_distances(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([0.01, 0, 0, 0, 0, 0]), self._base_metadata())
        res = compute_candidate_diagnostics([c1, c2])
        self.assertEqual(len(res.pairwise_distances), 1)

    def test_chaining_prevention(self):
        tol_pos = 0.005

        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([tol_pos, 0, 0, 0, 0, 0]), self._base_metadata())
        c3 = self._create_candidate(np.array([2.2 * tol_pos, 0, 0, 0, 0, 0]), self._base_metadata())

        res = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=2.0)
        self.assertEqual(res.n_clusters, 2)
        self.assertEqual(res.assessment, "multiple_separated_groups")

    # ---- New tests required by review ----

    def test_invalid_epoch(self):
        meta = self._base_metadata()
        c = self._create_candidate(np.zeros(6), meta, epoch_years=1.0)
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("epoch_years", str(ctx.exception))
        self.assertIn("0", str(ctx.exception))

    def test_invalid_coordinate_frame(self):
        meta = self._base_metadata()
        meta["coordinate_frame"] = "geocentric equatorial"
        c = self._create_candidate(np.zeros(6), meta)
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("coordinate_frame", str(ctx.exception))

    def test_invalid_position_unit(self):
        meta = self._base_metadata()
        meta["position_unit"] = "km"
        c = self._create_candidate(np.zeros(6), meta)
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("position_unit", str(ctx.exception))

    def test_invalid_velocity_unit(self):
        meta = self._base_metadata()
        meta["velocity_unit"] = "km/s"
        c = self._create_candidate(np.zeros(6), meta)
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("velocity_unit", str(ctx.exception))

    def test_non_finite_ranking_metadata(self):
        meta = self._base_metadata()
        meta["chi2_reduced"] = np.inf
        c = self._create_candidate(np.zeros(6), meta)
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("chi2_reduced", str(ctx.exception))

        meta2 = self._base_metadata()
        meta2["chi2"] = np.nan
        c2 = self._create_candidate(np.zeros(6), meta2)
        with self.assertRaises(ValueError) as ctx2:
            compute_candidate_diagnostics([c2])
        self.assertIn("chi2", str(ctx2.exception))

    def test_invalid_start_index(self):
        meta = self._base_metadata()
        meta["start_index"] = True  # bool is not valid integer
        c = self._create_candidate(np.zeros(6), meta)
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("start_index", str(ctx.exception))

        meta2 = self._base_metadata()
        meta2["start_index"] = 1.5  # float is not valid integer
        c2 = self._create_candidate(np.zeros(6), meta2)
        with self.assertRaises(ValueError) as ctx2:
            compute_candidate_diagnostics([c2])
        self.assertIn("start_index", str(ctx2.exception))

    def test_invalid_tolerances_and_thresholds(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([1e-6, 0, 0, 0, 0, 0]), self._base_metadata())

        for kw, bad in (
            ("tol_pos", 0.0), ("tol_pos", -0.001), ("tol_pos", np.nan),
            ("tol_vel", 0.0), ("tol_vel", -1e-6), ("tol_vel", np.inf),
            ("clustering_threshold_d", 0.0), ("clustering_threshold_d", -2.0),
            ("compactness_threshold_d", 0.0), ("compactness_threshold_d", np.nan),
        ):
            kwargs = {kw: bad}
            with self.assertRaises(ValueError) as ctx:
                compute_candidate_diagnostics([c1, c2], **kwargs)
            self.assertIn(kw, str(ctx.exception))

    def test_missing_metadata_dict(self):
        c = self._create_candidate(np.zeros(6), {})  # type: ignore[arg-type]
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("missing metadata key", str(ctx.exception))

    def test_compactness_threshold_boundary(self):
        tol_pos = 0.005
        # d_max == compactness_threshold_d -> broadly_dispersed (strict <)
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([0.5 * tol_pos, 0, 0, 0, 0, 0]), self._base_metadata())
        res_at = compute_candidate_diagnostics([c1, c2], compactness_threshold_d=0.5)
        self.assertEqual(res_at.n_clusters, 1)
        self.assertEqual(res_at.assessment, "broadly_dispersed")

        # Just below threshold -> single_compact_group
        c3 = self._create_candidate(np.array([0.4 * tol_pos, 0, 0, 0, 0, 0]), self._base_metadata())
        res_below = compute_candidate_diagnostics([c1, c3], compactness_threshold_d=0.5)
        self.assertEqual(res_below.assessment, "single_compact_group")

    def test_representative_selection_ranking_tiebreaking(self):
        # Tie-break by chi2
        meta1 = self._base_metadata()
        meta1["chi2_reduced"] = 1.0
        meta1["chi2"] = 10.0
        meta1["start_index"] = 0

        meta2 = self._base_metadata()
        meta2["chi2_reduced"] = 1.0
        meta2["chi2"] = 5.0
        meta2["start_index"] = 1

        c1 = self._create_candidate(np.zeros(6), meta1)
        c2 = self._create_candidate(np.array([1e-6, 0, 0, 0, 0, 0]), meta2)

        res = compute_candidate_diagnostics([c1, c2], compactness_threshold_d=1.0)
        # Should pick c2 (chi2=5.0) as representative
        self.assertEqual(res.cluster_representatives[0], 1)

        # Tie-break by start_index
        meta3 = self._base_metadata()
        meta3["chi2_reduced"] = 1.0
        meta3["chi2"] = 10.0
        meta3["start_index"] = 1

        meta4 = self._base_metadata()
        meta4["chi2_reduced"] = 1.0
        meta4["chi2"] = 10.0
        meta4["start_index"] = 0

        c3 = self._create_candidate(np.zeros(6), meta3)
        c4 = self._create_candidate(np.array([1e-6, 0, 0, 0, 0, 0]), meta4)

        res2 = compute_candidate_diagnostics([c3, c4], compactness_threshold_d=1.0)
        # Should pick c4 (start_index=0) as representative
        self.assertEqual(res2.cluster_representatives[0], 1)

    def test_threshold_sensitivity_1_2_3(self):
        # c1-c2 D=2.0, c2-c3 D=2.0, c1-c3 D=4.0 (exact integer multiples of tol_pos)
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([2.0 * 0.005, 0, 0, 0, 0, 0]), self._base_metadata())
        c3 = self._create_candidate(np.array([4.0 * 0.005, 0, 0, 0, 0, 0]), self._base_metadata())

        res_1 = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=1.0)
        res_2 = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=2.0)
        res_3 = compute_candidate_diagnostics([c1, c2, c3], clustering_threshold_d=3.0)

        # t=1.0: no merges → 3 clusters
        self.assertEqual(res_1.n_clusters, 3)
        # t=2.0: no merges (D=2.0 is not < 2.0) → 3 clusters
        self.assertEqual(res_2.n_clusters, 3)
        # t=3.0: c1-c2 merge, c2-c3 merge, but max(d(c1,c3)=4.0, d(c2,c3)=2.0) >= 3.0
        # prevents complete-linkage merge → 2 clusters
        self.assertEqual(res_3.n_clusters, 2)

    def test_pairwise_statistics_with_distances(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([0.01, 0, 0, 0, 0, 0]), self._base_metadata())
        c3 = self._create_candidate(np.array([0.02, 0, 0, 0, 0, 0]), self._base_metadata())
        res = compute_candidate_diagnostics([c1, c2, c3])
        self.assertEqual(len(res.pairwise_distances), 3)
        self.assertIsInstance(res.mean_pairwise_distance, float)
        self.assertIsInstance(res.max_pairwise_distance, float)
        self.assertIsInstance(res.median_pairwise_distance, float)
        self.assertIsInstance(res.min_pairwise_distance, float)
        self.assertIsInstance(res.std_pairwise_distance, float)

    def test_clustering_config_contains_all_fields(self):
        c1 = self._create_candidate(np.zeros(6), self._base_metadata())
        c2 = self._create_candidate(np.array([1e-6, 0, 0, 0, 0, 0]), self._base_metadata())
        res = compute_candidate_diagnostics([c1, c2])
        cfg = res.clustering_config
        self.assertEqual(cfg["tol_pos"], 0.005)
        self.assertEqual(cfg["tol_vel"], 5e-5)
        self.assertEqual(cfg["clustering_threshold_d"], 2.0)
        self.assertEqual(cfg["compactness_threshold_d"], 0.5)
        self.assertEqual(cfg["algorithm"], "complete-linkage")

    def test_metadata_none(self):
        c = OrbitCandidate(state=OrbitState(0,0,0,0,0,0), epoch_years=0.0, metadata=None) # type: ignore
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

    def test_state_none(self):
        c = OrbitCandidate(state=None, epoch_years=0.0, metadata=self._base_metadata()) # type: ignore
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

    def test_to_array_typeerror(self):
        class BadState:
            def to_array(self): raise TypeError("boom")
        c = OrbitCandidate(state=BadState(), epoch_years=0.0, metadata=self._base_metadata()) # type: ignore
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

    def test_to_array_valueerror(self):
        class BadState:
            def to_array(self): raise ValueError("boom")
        c = OrbitCandidate(state=BadState(), epoch_years=0.0, metadata=self._base_metadata()) # type: ignore
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

    def test_to_array_overflowerror(self):
        class BadState:
            def to_array(self): raise OverflowError("boom")
        c = OrbitCandidate(state=BadState(), epoch_years=0.0, metadata=self._base_metadata()) # type: ignore
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

    def test_invalid_state_shape(self):
        # 2x3 array, size=6 but shape (2,3) != (6,)
        class State2x3:
            def to_array(self):
                return np.zeros((2, 3))
        c = OrbitCandidate(
            state=State2x3(),
            epoch_years=0.0,
            metadata=self._base_metadata(),
        )  # type: ignore[arg-type]
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("shape", str(ctx.exception))

    def test_state_not_orbitstate(self):
        # Custom state whose to_array() returns a valid (6,) array, but not an OrbitState.
        class NotOrbitState:
            def to_array(self):
                return np.zeros(6)

        c = OrbitCandidate(
            state=NotOrbitState(),
            epoch_years=0.0,
            metadata=self._base_metadata(),
        )  # type: ignore[arg-type]
        with self.assertRaises(ValueError) as ctx:
            compute_candidate_diagnostics([c])
        self.assertIn("OrbitState", str(ctx.exception))

    def test_invalid_state_array_values(self):
        c = self._create_candidate(np.array([1,2,3,4,5,np.inf]), self._base_metadata())
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

    def test_epoch_invalid_types(self):
        meta = self._base_metadata()
        # epoch_years is boolean
        c1 = OrbitCandidate(state=OrbitState(0,0,0,0,0,0), epoch_years=True, metadata=meta) # type: ignore
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c1])

        # epoch_years is string
        c2 = OrbitCandidate(state=OrbitState(0,0,0,0,0,0), epoch_years="0.0", metadata=meta) # type: ignore
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c2])

    def test_epoch_non_finite(self):
        meta = self._base_metadata()
        c = OrbitCandidate(state=OrbitState(0,0,0,0,0,0), epoch_years=np.nan, metadata=meta)
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

    def test_epoch_inconsistent_metadata(self):
        meta = self._base_metadata()
        meta["epoch_years"] = 1.0 # Inconsistent with attribute 0.0
        c = OrbitCandidate(state=OrbitState(0,0,0,0,0,0), epoch_years=0.0, metadata=meta)
        with self.assertRaises(ValueError):
            compute_candidate_diagnostics([c])

if __name__ == "__main__":
    unittest.main()
