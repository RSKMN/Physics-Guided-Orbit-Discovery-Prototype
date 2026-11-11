
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_NAMES = {
    "Standard (e=0.2)": "synthetic_asteroid_observations",
    "Inclined (e=0.3, i=10)": "synthetic_asteroid_inclined_observations",
    "Eccentric (e=0.5)": "synthetic_asteroid_eccentric_observations",
}

DATASET_COLORS = {
    "Standard (e=0.2)": "tab:blue",
    "Inclined (e=0.3, i=10)": "tab:orange",
    "Eccentric (e=0.5)": "tab:green",
}

OUTPUT_DIR = PROJECT_ROOT / "results" / "component-2"
FIGURE_DIR = OUTPUT_DIR / "figures"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def load_datasets():

    datasets = {}

    for label, folder_name in DATASET_NAMES.items():

        csv_path = (
            PROJECT_ROOT
            / "data"
            / "observations"
            / folder_name
            / "observations.csv"
        )

        metadata_path = (
            PROJECT_ROOT
            / "data"
            / "observations"
            / folder_name
            / "metadata.json"
        )

        observations = pd.read_csv(csv_path)

        with open(metadata_path, "r", encoding="utf-8") as file:
            metadata = json.load(file)

        datasets[label] = {
            "observations": observations,
            "metadata": metadata,
        }

        print(f"\n{label}")
        print(f"CSV: {csv_path}")

        selected = observations.loc[
            np.isclose(observations["time_days"], 385.0),
            ["time_days", "ra_deg", "dec_deg"]
        ]

        print(selected.to_string(index=False))

    return datasets

def save_figure(fig, filename):

    fig.savefig(
        FIGURE_DIR / f"{filename}.png",
        dpi=300,
        bbox_inches="tight",
    )

    fig.savefig(
        FIGURE_DIR / f"{filename}.pdf",
        bbox_inches="tight",
    )

    plt.close(fig)



def plot_ra_vs_time(datasets):

    fig, ax = plt.subplots(figsize=(12, 6))

    for label, data in datasets.items():

        observations = data["observations"]

        ra = observations["ra_deg"].to_numpy()
        time = observations["time_days"].to_numpy()

        # Detect RA wrap-around.
        wrap_indices = np.where(np.abs(np.diff(ra)) > 180)[0] + 1

        time_segments = np.split(time, wrap_indices)
        ra_segments = np.split(ra, wrap_indices)

        for time_segment, ra_segment in zip(
            time_segments, ra_segments
        ):

            ax.plot(
                time_segment,
                ra_segment,
                color=DATASET_COLORS[label],
                linewidth=1.2,
                label=label if time_segment is time_segments[0] else None,
            )

    ax.set_title("Right Ascension vs Observation Time")
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Right Ascension (degrees)")

    ax.set_ylim(0, 360)
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    save_figure(fig, "ra_vs_time")



def plot_dec_vs_time(datasets):

    fig, ax = plt.subplots(figsize=(12, 6))

    for label, data in datasets.items():

        observations = data["observations"]

        ax.plot(
            observations["time_days"],
            observations["dec_deg"],
            label=label,
            linewidth=1.2,
        )

    ax.set_title("Declination vs Observation Time")
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Declination (degrees)")

    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    save_figure(fig, "dec_vs_time")





def plot_sky_track(datasets):

    fig, ax = plt.subplots(figsize=(12, 8))

    line_styles = {
        "Standard (e=0.2)": "-",
        "Inclined (e=0.3, i=10)": "--",
        "Eccentric (e=0.5)": ":",
    }

    for label, data in datasets.items():

        observations = data["observations"]

        ra = observations["ra_deg"].to_numpy()
        dec = observations["dec_deg"].to_numpy()

        # Detect RA wrap-around boundaries.
        wrap_indices = np.where(np.abs(np.diff(ra)) > 180)[0] + 1

        ra_segments = np.split(ra, wrap_indices)
        dec_segments = np.split(dec, wrap_indices)

        for index, (ra_segment, dec_segment) in enumerate(
            zip(ra_segments, dec_segments)
        ):

            ax.plot(
                ra_segment,
                dec_segment,
                color=DATASET_COLORS[label],
                linestyle=line_styles[label],
                linewidth=1.8,
                marker="o",
                markersize=2.5,
                markevery=8,
                label=label if index == 0 else None,
            )

    ax.set_title("Apparent Asteroid Sky Tracks")
    ax.set_xlabel("Right Ascension (degrees)")
    ax.set_ylabel("Declination (degrees)")

    ax.set_xlim(0, 360)
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    save_figure(fig, "sky_track")





def plot_time_colored_sky_tracks(datasets):

    fig, axes = plt.subplots(
        1, 3,
        figsize=(18, 6),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )

    scatter = None

    for ax, (label, data) in zip(axes, datasets.items()):

        observations = data["observations"]

        ra = observations["ra_deg"].to_numpy()
        dec = observations["dec_deg"].to_numpy()
        time = observations["time_days"].to_numpy()

        scatter = ax.scatter(
            ra,
            dec,
            c=time,
            cmap="viridis",
            vmin=0,
            vmax=1826.25,
            s=16,
            alpha=0.85,
        )

        ax.set_title(label)
        ax.set_xlabel("Right Ascension (degrees)")
        ax.set_xlim(0, 360)
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("Declination (degrees)")

    colorbar = fig.colorbar(
        scatter,
        ax=axes,
        location="right",
        shrink=0.85,
        pad=0.04,
        fraction=0.035,
    )

    colorbar.set_label("Observation Time (days)")

    fig.suptitle(
        "Time-Colored Apparent Asteroid Sky Tracks",
        fontsize=15,
    )

    save_figure(fig, "time_colored_sky_tracks")




def plot_noise_distribution(datasets):

    fig, axes = plt.subplots(
        3, 2,
        figsize=(13, 12),
        sharex=True,
        sharey=True,
    )

    for row, (label, data) in enumerate(datasets.items()):

        observations = data["observations"]

        # Calculate RA residual in arcseconds.
        ra_difference = (
            observations["ra_deg"]
            - observations["true_ra_deg"]
            + 180
        ) % 360 - 180

        ra_residual = (
            ra_difference
            * np.cos(np.deg2rad(observations["true_dec_deg"]))
            * 3600
        )

        # Calculate Dec residual in arcseconds.
        dec_residual = (
            observations["dec_deg"]
            - observations["true_dec_deg"]
        ) * 3600

        color = DATASET_COLORS[label]

        axes[row, 0].hist(
            ra_residual,
            bins=25,
            color=color,
            alpha=0.75,
            edgecolor="black",
        )

        axes[row, 1].hist(
            dec_residual,
            bins=25,
            color=color,
            alpha=0.75,
            edgecolor="black",
        )

        axes[row, 0].axvline(
            0,
            color="black",
            linestyle="--",
            linewidth=1,
        )

        axes[row, 1].axvline(
            0,
            color="black",
            linestyle="--",
            linewidth=1,
        )

        axes[row, 0].set_ylabel(
            f"{label}\nFrequency"
        )

        axes[row, 0].grid(True, alpha=0.25)
        axes[row, 1].grid(True, alpha=0.25)

    axes[0, 0].set_title("RA Measurement Noise")
    axes[0, 1].set_title("Dec Measurement Noise")

    for row in range(3):
        axes[row, 0].set_xlim(-2, 2)
        axes[row, 1].set_xlim(-2, 2)

    axes[2, 0].set_xlabel("RA residual (arcseconds)")
    axes[2, 1].set_xlabel("Dec residual (arcseconds)")

    fig.suptitle(
        "Measurement Noise Distribution Across Orbital Scenarios",
        fontsize=15,
    )

    fig.tight_layout()
    save_figure(fig, "noise_distribution")



def generate_comparison_summary(datasets):

    results = []

    for label, data in datasets.items():

        observations = data["observations"]

        ra_difference = (
            observations["ra_deg"]
            - observations["true_ra_deg"]
            + 180
        ) % 360 - 180

        ra_residual = (
            ra_difference
            * np.cos(np.deg2rad(observations["true_dec_deg"]))
            * 3600
        )

        dec_residual = (
            observations["dec_deg"]
            - observations["true_dec_deg"]
        ) * 3600

        results.append({
            "dataset": label,
            "observation_count": len(observations),
            "ra_min_deg": observations["ra_deg"].min(),
            "ra_max_deg": observations["ra_deg"].max(),
            "dec_min_deg": observations["dec_deg"].min(),
            "dec_max_deg": observations["dec_deg"].max(),
            "ra_noise_mean_arcsec": np.mean(ra_residual),
            "ra_noise_std_arcsec": np.std(ra_residual, ddof=1),
            "dec_noise_mean_arcsec": np.mean(dec_residual),
            "dec_noise_std_arcsec": np.std(dec_residual, ddof=1),
        })

    summary = pd.DataFrame(results)

    summary.to_csv(
        OUTPUT_DIR / "comparison_summary.csv",
        index=False,
    )


def main():

    print("Loading observation datasets...")

    datasets = load_datasets()

    print("Generating comparative plots...")

    plot_ra_vs_time(datasets)
    plot_dec_vs_time(datasets)
    plot_sky_track(datasets)
    plot_time_colored_sky_tracks(datasets)
    plot_noise_distribution(datasets)

    print("Generating numerical comparison summary...")

    generate_comparison_summary(datasets)

    print("\nComparative visualization completed successfully.")
    print(f"Figures saved in: {FIGURE_DIR}")
    print(f"Summary saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
