"""Component 3 Phase 5C: Candidate Ensemble Diagnostics.

Computes descriptive spread and clustering diagnostics for a set of plausible
orbit candidates.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np
from orbit_discovery.component3.models import OrbitCandidate, OrbitState

#: Required metadata keys present on every Phase 4 candidate.
_REQUIRED_METADATA_KEYS = ("chi2_reduced", "chi2", "start_index")

#: Coordinate frame required on Phase 4 candidate metadata.
_COORDINATE_FRAME = "heliocentric ecliptic inertial"

#: Units required on Phase 4 candidate metadata.
_POSITION_UNIT = "AU"
_VELOCITY_UNIT = "AU/year"

#: Epoch required on Phase 4 candidate metadata.
_EPOCH_YEARS = 0.0


@dataclass(frozen=True)
class CandidateEnsembleDiagnostics:
    """Diagnostics for a candidate orbit ensemble."""
    n_retained_candidates: int
    per_coordinate_spread: Dict[str, Dict[str, float]]
    pairwise_distances: List[float]
    mean_pairwise_distance: Optional[float]
    max_pairwise_distance: Optional[float]
    median_pairwise_distance: Optional[float]
    min_pairwise_distance: Optional[float]
    std_pairwise_distance: Optional[float]
    n_non_duplicate_pairs: int
    clustering_config: Dict[str, Any]
    n_clusters: int
    cluster_assignments: Dict[int, int]
    cluster_sizes: List[int]
    cluster_representatives: List[int]
    cluster_internal_max_distance: Dict[int, float]
    assessment: str
    caveats: List[str]
    coordinate_order: List[str] = field(default_factory=lambda: ["rx", "ry", "rz", "vx", "vy", "vz"])
    position_unit: str = "AU"
    velocity_unit: str = "AU/year"


def _is_finite_number(value: Any) -> bool:
    """Return True if value is a finite int/float (excluding bool)."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float, np.integer, np.floating)):
        return False
    return bool(np.isfinite(float(value)))


def _is_valid_int(value: Any) -> bool:
    """Return True if value is a valid integer (excluding bool)."""
    return isinstance(value, (int, np.integer)) and not isinstance(value, bool)


def _validate_candidate(cand: Any, index: int) -> None:
    """Validate a single candidate against Phase 4 metadata invariants.

    Raises ValueError naming the candidate index and problematic field.
    """
    if not isinstance(cand, OrbitCandidate):
        raise ValueError(f"Candidate {index} is not an OrbitCandidate.")

    if not isinstance(cand.metadata, dict):
        raise ValueError(f"Candidate {index} metadata is not a dictionary.")

    # State access and finiteness — must not leak AttributeError/TypeError/ValueError/OverflowError.
    try:
        state_arr = cand.state.to_array()
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError(
            f"Candidate {index} state.to_array() failed: {exc}"
        ) from exc
    try:
        state_arr = np.asarray(state_arr, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(
            f"Candidate {index} state cannot be converted to float array: {exc}"
        ) from exc
    if not np.all(np.isfinite(state_arr)):
        raise ValueError(f"Candidate {index} has non-finite state.")
    if state_arr.shape != (6,):
        raise ValueError(
            f"Candidate {index} state must have exactly 6 coordinates; "
            f"got shape {state_arr.shape}."
        )

    if not isinstance(cand.state, OrbitState):
        raise ValueError(
            f"Candidate {index} state must be an instance of OrbitState; "
            f"got {type(cand.state).__name__}."
        )

    # Epoch must be finite numeric (excluding bool/str) and exactly 0.0.
    try:
        epoch_attr = cand.epoch_years
    except AttributeError as exc:
        raise ValueError(
            f"Candidate {index} has no epoch_years attribute: {exc}"
        ) from exc
    if isinstance(epoch_attr, bool):
        raise ValueError(
            f"Candidate {index} epoch_years must be numeric, not bool; "
            f"got {epoch_attr!r}."
        )
    if not isinstance(epoch_attr, (int, float, np.integer, np.floating)):
        raise ValueError(
            f"Candidate {index} epoch_years must be finite numeric; "
            f"got {epoch_attr!r}."
        )
    epoch_attr = float(epoch_attr)
    if not np.isfinite(epoch_attr):
        raise ValueError(
            f"Candidate {index} epoch_years must be finite; "
            f"got {epoch_attr!r}."
        )
    if epoch_attr != _EPOCH_YEARS:
        raise ValueError(
            f"Candidate {index} epoch_years must be {_EPOCH_YEARS}; "
            f"got {epoch_attr!r}."
        )

    # Validate metadata epoch_years when present; it must agree with attribute.
    if "epoch_years" in cand.metadata:
        meta_epoch = cand.metadata["epoch_years"]
        if isinstance(meta_epoch, bool):
            raise ValueError(
                f"Candidate {index} metadata 'epoch_years' must be numeric, "
                f"not bool; got {meta_epoch!r}."
            )
        if not isinstance(meta_epoch, (int, float, np.integer, np.floating)):
            raise ValueError(
                f"Candidate {index} metadata 'epoch_years' must be finite "
                f"numeric; got {meta_epoch!r}."
            )
        meta_epoch = float(meta_epoch)
        if not np.isfinite(meta_epoch):
            raise ValueError(
                f"Candidate {index} metadata 'epoch_years' must be finite; "
                f"got {meta_epoch!r}."
            )
        if meta_epoch != epoch_attr:
            raise ValueError(
                f"Candidate {index} metadata 'epoch_years' ({meta_epoch}) "
                f"does not agree with candidate attribute ({epoch_attr})."
            )

    # Required metadata keys.
    for key in _REQUIRED_METADATA_KEYS:
        if key not in cand.metadata:
            raise ValueError(
                f"Candidate {index} missing metadata key: {key}"
            )

    # Coordinate frame, position unit, velocity unit — exact string match.
    frame = cand.metadata.get("coordinate_frame")
    if frame != _COORDINATE_FRAME:
        raise ValueError(
            f"Candidate {index} coordinate_frame must be "
            f"{_COORDINATE_FRAME!r}; got {frame!r}."
        )

    pos_unit = cand.metadata.get("position_unit")
    if pos_unit != _POSITION_UNIT:
        raise ValueError(
            f"Candidate {index} position_unit must be {_POSITION_UNIT!r}; "
            f"got {pos_unit!r}."
        )

    vel_unit = cand.metadata.get("velocity_unit")
    if vel_unit != _VELOCITY_UNIT:
        raise ValueError(
            f"Candidate {index} velocity_unit must be {_VELOCITY_UNIT!r}; "
            f"got {vel_unit!r}."
        )

    # chi2_reduced and chi2 must be finite numeric values.
    for key in ("chi2_reduced", "chi2"):
        val = cand.metadata[key]
        if not _is_finite_number(val):
            raise ValueError(
                f"Candidate {index} metadata '{key}' must be a finite "
                f"numeric value; got {val!r}."
            )

    # start_index must be a valid integer.
    start_index = cand.metadata["start_index"]
    if not _is_valid_int(start_index):
        raise ValueError(
            f"Candidate {index} metadata 'start_index' must be a valid "
            f"integer (not bool); got {start_index!r}."
        )


def _validate_config(
    tol_pos: float,
    tol_vel: float,
    clustering_threshold_d: float,
    compactness_threshold_d: float,
) -> None:
    """Validate clustering configuration parameters."""
    for name, value in (
        ("tol_pos", tol_pos),
        ("tol_vel", tol_vel),
        ("clustering_threshold_d", clustering_threshold_d),
        ("compactness_threshold_d", compactness_threshold_d),
    ):
        if not _is_finite_number(value):
            raise ValueError(
                f"Configuration '{name}' must be a finite numeric value; "
                f"got {value!r}."
            )
        if float(value) <= 0.0:
            raise ValueError(
                f"Configuration '{name}' must be positive; got {value!r}."
            )


def _compute_duplicate_distance(
    state_a: OrbitState,
    state_b: OrbitState,
    tol_pos: float,
    tol_vel: float,
) -> float:
    """Compute normalized state-space distance D_ij based on Phase 4 formula."""
    r_a = np.array([state_a.rx, state_a.ry, state_a.rz], dtype=float)
    r_b = np.array([state_b.rx, state_b.ry, state_b.rz], dtype=float)
    v_a = np.array([state_a.vx, state_a.vy, state_a.vz], dtype=float)
    v_b = np.array([state_b.vx, state_b.vy, state_b.vz], dtype=float)

    dr_sq = float(np.sum((r_a - r_b) ** 2)) / (tol_pos ** 2)
    dv_sq = float(np.sum((v_a - v_b) ** 2)) / (tol_vel ** 2)
    return float(np.sqrt(dr_sq + dv_sq))


def _pairwise_stats(dists: List[float]) -> Dict[str, Optional[float]]:
    """Compute pairwise distance statistics, returning None when undefined."""
    if not dists:
        return {
            "mean_pairwise_distance": None,
            "max_pairwise_distance": None,
            "median_pairwise_distance": None,
            "min_pairwise_distance": None,
            "std_pairwise_distance": None,
        }
    arr = np.asarray(dists, dtype=float)
    return {
        "mean_pairwise_distance": float(np.mean(arr)),
        "max_pairwise_distance": float(np.max(arr)),
        "median_pairwise_distance": float(np.median(arr)),
        "min_pairwise_distance": float(np.min(arr)),
        "std_pairwise_distance": float(np.std(arr, ddof=0)),
    }


def compute_candidate_diagnostics(
    candidates: List[OrbitCandidate],
    tol_pos: float = 0.005,
    tol_vel: float = 5e-5,
    clustering_threshold_d: float = 2.0,
    compactness_threshold_d: float = 0.5,
) -> CandidateEnsembleDiagnostics:
    """Compute spread and clustering diagnostics for orbit candidates."""
    # --- Configuration validation ---
    _validate_config(tol_pos, tol_vel, clustering_threshold_d, compactness_threshold_d)

    n = len(candidates)
    if n == 0:
        return CandidateEnsembleDiagnostics(
            n_retained_candidates=0,
            per_coordinate_spread={},
            pairwise_distances=[],
            mean_pairwise_distance=None,
            max_pairwise_distance=None,
            median_pairwise_distance=None,
            min_pairwise_distance=None,
            std_pairwise_distance=None,
            n_non_duplicate_pairs=0,
            clustering_config={
                "tol_pos": float(tol_pos),
                "tol_vel": float(tol_vel),
                "clustering_threshold_d": float(clustering_threshold_d),
                "compactness_threshold_d": float(compactness_threshold_d),
                "algorithm": "complete-linkage",
            },
            n_clusters=0,
            cluster_assignments={},
            cluster_sizes=[],
            cluster_representatives=[],
            cluster_internal_max_distance={},
            assessment="no_candidates",
            caveats=["Descriptive statistics only; not a calibrated statistical confidence region."],
        )

    # --- Candidate validation ---
    for i, cand in enumerate(candidates):
        _validate_candidate(cand, i)

    # --- Spread ---
    states = np.array([c.state.to_array() for c in candidates])
    spread = {}
    keys = ["rx", "ry", "rz", "vx", "vy", "vz"]
    for j, key in enumerate(keys):
        col = states[:, j]
        spread[key] = {
            "min": float(np.min(col)),
            "max": float(np.max(col)),
            "mean": float(np.mean(col)),
            "std": float(np.std(col, ddof=0)),
            "range": float(np.max(col) - np.min(col)),
        }

    # --- Pairwise distances ---
    dists = []
    for i in range(n):
        for j in range(i + 1, n):
            dists.append(_compute_duplicate_distance(
                candidates[i].state, candidates[j].state, tol_pos, tol_vel
            ))

    stats = _pairwise_stats(dists)

    # --- Clustering (Complete Linkage) ---
    if n == 1:
        cluster_assignments = {0: 0}
        n_clusters = 1
        sizes = [1]
        reps = [0]
        internal_dists = {0: 0.0}
        assessment = "insufficient_candidates"
    else:
        # Distance matrix
        mat = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                d = _compute_duplicate_distance(
                    candidates[i].state, candidates[j].state, tol_pos, tol_vel
                )
                mat[i, j] = mat[j, i] = d

        # Agglomerative clustering with complete linkage.
        # Merge the pair of clusters whose worst (maximum) cross-member
        # distance is smallest, provided it is strictly below the threshold.
        # Ties are broken deterministically by
        # (complete_linkage_distance, min_index_cluster_1, min_index_cluster_2)
        # where cluster minimum indices are ordered before comparison.
        clusters = {i: {i} for i in range(n)}

        while len(clusters) > 1:
            best_pair = None
            best_d_max = float("inf")
            best_min1 = None
            best_min2 = None

            cluster_ids = sorted(clusters.keys())
            for i_idx in range(len(cluster_ids)):
                id1 = cluster_ids[i_idx]
                min1 = min(clusters[id1])
                for id2 in cluster_ids[i_idx + 1:]:
                    min2 = min(clusters[id2])
                    # Ordered min indices for deterministic tie-breaking.
                    lo, hi = (min1, min2) if min1 < min2 else (min2, min1)

                    # Complete linkage: max distance between any two members.
                    d_max = 0.0
                    for c1 in clusters[id1]:
                        for c2 in clusters[id2]:
                            d_max = max(d_max, mat[c1, c2])

                    if d_max >= clustering_threshold_d:
                        continue

                    key = (d_max, lo, hi)
                    current_best_key = (best_d_max, best_min1, best_min2)

                    if best_pair is None or key < current_best_key:
                        best_pair = (id1, id2)
                        best_d_max = d_max
                        best_min1 = lo
                        best_min2 = hi

            if best_pair is None:
                break

            id1, id2 = best_pair
            clusters[id1].update(clusters[id2])
            del clusters[id2]

        # Final Cluster IDs: 0...n_c, ordered by minimum original candidate index.
        final_ids = sorted(clusters.keys(), key=lambda id: min(clusters[id]))
        id_map = {old_id: new_id for new_id, old_id in enumerate(final_ids)}

        cluster_assignments = {}
        cluster_data = {new_id: [] for new_id in range(len(final_ids))}
        for old_id, members in clusters.items():
            new_id = id_map[old_id]
            for member in members:
                cluster_assignments[member] = new_id
                cluster_data[new_id].append(member)

        n_clusters = len(final_ids)
        sizes = [len(cluster_data[i]) for i in range(n_clusters)]

        # Representatives (Phase 4 ranking: chi2_reduced, chi2, start_index).
        def ranking_tuple(cand):
            return (
                cand.metadata["chi2_reduced"],
                cand.metadata["chi2"],
                cand.metadata["start_index"],
            )

        reps = []
        internal_dists = {}
        for i in range(n_clusters):
            members = cluster_data[i]
            rep = min(members, key=lambda idx: ranking_tuple(candidates[idx]))
            reps.append(rep)

            # Internal max distance (complete linkage within cluster).
            d_max = 0.0
            for c1 in members:
                for c2 in members:
                    d_max = max(d_max, mat[c1, c2])
            internal_dists[i] = d_max

        # Assessment: separated groups vs compact vs broadly dispersed.
        if n_clusters > 1:
            assessment = "multiple_separated_groups"
        else:
            d_max = internal_dists[0]
            if d_max < compactness_threshold_d:
                assessment = "single_compact_group"
            else:
                assessment = "broadly_dispersed"

    return CandidateEnsembleDiagnostics(
        n_retained_candidates=n,
        per_coordinate_spread=spread,
        pairwise_distances=dists,
        mean_pairwise_distance=stats["mean_pairwise_distance"],
        max_pairwise_distance=stats["max_pairwise_distance"],
        median_pairwise_distance=stats["median_pairwise_distance"],
        min_pairwise_distance=stats["min_pairwise_distance"],
        std_pairwise_distance=stats["std_pairwise_distance"],
        n_non_duplicate_pairs=sum(1 for d in dists if d >= 1.0),
        clustering_config={
            "tol_pos": float(tol_pos),
            "tol_vel": float(tol_vel),
            "clustering_threshold_d": float(clustering_threshold_d),
            "compactness_threshold_d": float(compactness_threshold_d),
            "algorithm": "complete-linkage",
        },
        n_clusters=n_clusters,
        cluster_assignments=cluster_assignments,
        cluster_sizes=sizes,
        cluster_representatives=reps,
        cluster_internal_max_distance=internal_dists,
        assessment=assessment,
        caveats=["Descriptive statistics only; not a calibrated statistical confidence region."],
    )
