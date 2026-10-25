"""Synthetic classical holographic-autofocus Monte Carlo experiment."""

import argparse
import csv
import json
import platform
from pathlib import Path

import numpy as np


def make_model():
    n = 96
    pitch_m = 6.5e-6
    wavelength_m = 532e-9
    recording_distance_m = 0.004
    carrier_bins = 24
    filter_radius_bins = 9

    y, x = np.indices((n, n))
    X = x - (n - 1) / 2
    Y = y - (n - 1) / 2

    object_field = (
        np.exp(-((X + 12) ** 2 + (Y + 8) ** 2) / 32)
        + 0.7 * np.exp(-((X - 11) ** 2 + (Y - 10) ** 2) / 50)
    ).astype(np.complex128)

    frequencies = np.fft.fftfreq(n, d=pitch_m)
    FX, FY = np.meshgrid(frequencies, frequencies)

    longitudinal_squared = (
        1.0 / wavelength_m**2 - FX**2 - FY**2
    )
    propagating = longitudinal_squared >= 0.0

    kz = np.zeros((n, n))
    kz[propagating] = (
        2.0 * np.pi * np.sqrt(longitudinal_squared[propagating])
    )

    reference = np.exp(
        2j * np.pi * carrier_bins * X / n
    )

    bins = np.fft.fftshift(np.fft.fftfreq(n)) * n
    BX, BY = np.meshgrid(bins, bins)

    # Negative-frequency sideband contains O * conjugate(R).
    radius = np.hypot(BX + carrier_bins, BY)
    inner_radius = 0.75 * filter_radius_bins

    mask = np.zeros((n, n))
    mask[radius <= inner_radius] = 1.0

    transition = (
        (radius > inner_radius)
        & (radius < filter_radius_bins)
    )
    mask[transition] = 0.5 * (
        1.0
        + np.cos(
            np.pi
            * (radius[transition] - inner_radius)
            / (filter_radius_bins - inner_radius)
        )
    )

    return {
        "n": n,
        "pitch_m": pitch_m,
        "wavelength_m": wavelength_m,
        "recording_distance_m": recording_distance_m,
        "carrier_bins": carrier_bins,
        "filter_radius_bins": filter_radius_bins,
        "object_field": object_field,
        "reference": reference,
        "mask": mask,
        "kz": kz,
        "propagating": propagating,
    }


def transfer_function(model, distance_m):
    transfer = np.zeros(
        model["kz"].shape,
        dtype=np.complex128,
    )
    valid = model["propagating"]

    transfer[valid] = np.exp(
        1j * distance_m * model["kz"][valid]
    )
    return transfer


def propagate(field, distance_m, model):
    field = np.asarray(field, dtype=np.complex128)

    if field.shape != model["kz"].shape:
        raise ValueError("Field shape does not match the model.")

    if not np.isfinite(field).all():
        raise ValueError("Field contains nonfinite values.")

    if not np.isfinite(distance_m):
        raise ValueError("Distance must be finite.")

    if distance_m == 0:
        return field.copy()

    return np.fft.ifft2(
        np.fft.fft2(field)
        * transfer_function(model, distance_m)
    )


def clean_hologram(model):
    sensor_field = propagate(
        model["object_field"],
        model["recording_distance_m"],
        model,
    )
    return np.abs(sensor_field + model["reference"]) ** 2


def recover_field(hologram, model):
    hologram = np.asarray(hologram, dtype=float)

    if hologram.shape != model["mask"].shape:
        raise ValueError("Hologram shape does not match the model.")

    if not np.isfinite(hologram).all():
        raise ValueError("Hologram contains nonfinite values.")

    spectrum = np.fft.fftshift(
        np.fft.fft2(hologram)
    )
    selected = np.fft.ifft2(
        np.fft.ifftshift(spectrum * model["mask"])
    )

    # Unit-amplitude reference: remove the negative carrier.
    return selected * model["reference"]


def focus_score(field):
    intensity = np.abs(field) ** 2
    denominator = float(np.mean(intensity**2))

    if denominator <= 0 or not np.isfinite(denominator):
        raise ValueError("Invalid intensity for focus scoring.")

    gy, gx = np.gradient(intensity)
    return float(
        np.mean(gx**2 + gy**2) / denominator
    )


def estimate_focus(hologram, model):
    recovered = recover_field(hologram, model)
    spectrum = np.fft.fft2(recovered)

    def evaluate(distance_m):
        field = np.fft.ifft2(
            spectrum * transfer_function(model, distance_m)
        )
        return focus_score(field)

    coarse_distances = np.linspace(-0.008, 0.0, 65)
    coarse_scores = np.array([
        evaluate(z) for z in coarse_distances
    ])

    index = int(np.argmax(coarse_scores))

    if index in (0, len(coarse_distances) - 1):
        return {
            "distance_m": float(coarse_distances[index]),
            "at_scan_edge": True,
            "score": float(coarse_scores[index]),
        }

    fine_distances = np.linspace(
        coarse_distances[index - 1],
        coarse_distances[index + 1],
        21,
    )
    fine_scores = np.array([
        evaluate(z) for z in fine_distances
    ])

    fine_index = int(np.argmax(fine_scores))

    return {
        "distance_m": float(fine_distances[fine_index]),
        "at_scan_edge": fine_index in (
            0, len(fine_distances) - 1
        ),
        "score": float(fine_scores[fine_index]),
    }


def add_camera_noise(
    hologram,
    rng,
    *,
    peak_electrons,
    read_noise_electrons=3.0,
):
    hologram = np.asarray(hologram, dtype=float)

    if (
        not np.isfinite(hologram).all()
        or np.any(hologram < 0)
        or hologram.max() <= 0
    ):
        raise ValueError("Expected a finite, nonnegative hologram.")

    if not np.isfinite(peak_electrons) or peak_electrons <= 0:
        raise ValueError("peak_electrons must be positive.")

    if (
        not np.isfinite(read_noise_electrons)
        or read_noise_electrons < 0
    ):
        raise ValueError("Read noise must be nonnegative.")

    gain = peak_electrons / float(hologram.max())

    measured = rng.poisson(hologram * gain).astype(float)
    measured += rng.normal(
        0.0,
        read_noise_electrons,
        hologram.shape,
    )

    # No clipping, saturation, or quantization in this idealized model.
    return measured / gain


def run_experiment(trials_per_level=40, seed=42):
    if (
        not isinstance(trials_per_level, int)
        or trials_per_level < 2
    ):
        raise ValueError("Use at least two trials per level.")

    model = make_model()
    hologram = clean_hologram(model)
    baseline = estimate_focus(hologram, model)

    rng = np.random.default_rng(seed)

    levels = (200, 2000)
    read_noise = 3.0
    tolerance_mm = 0.25
    true_distance_mm = (
        -model["recording_distance_m"] * 1e3
    )

    rows = []

    for electrons in levels:
        for trial in range(trials_per_level):
            noisy = add_camera_noise(
                hologram,
                rng,
                peak_electrons=electrons,
                read_noise_electrons=read_noise,
            )

            estimate = estimate_focus(noisy, model)
            distance_mm = estimate["distance_m"] * 1e3
            error_mm = distance_mm - true_distance_mm

            rows.append({
                "peak_expected_electrons": electrons,
                "trial": trial,
                "estimated_distance_mm": distance_mm,
                "error_mm": error_mm,
                "at_scan_edge": estimate["at_scan_edge"],
            })

    results = []

    for electrons in levels:
        subset = [
            row for row in rows
            if row["peak_expected_electrons"] == electrons
        ]

        estimates = np.array([
            row["estimated_distance_mm"] for row in subset
        ])
        errors = estimates - true_distance_mm

        results.append({
            "peak_expected_electrons": electrons,
            "trials": len(subset),
            "mean_distance_mm": float(estimates.mean()),
            "std_distance_mm": float(estimates.std(ddof=1)),
            "bias_mm": float(errors.mean()),
            "rmse_mm": float(
                np.sqrt(np.mean(errors**2))
            ),
            "within_0p25_mm_fraction": float(
                np.mean(np.abs(errors) <= tolerance_mm)
            ),
            "edge_fraction": float(np.mean([
                row["at_scan_edge"] for row in subset
            ])),
            "empirical_2p5_97p5_mm": np.percentile(
                estimates, [2.5, 97.5]
            ).tolist(),
        })

    config = {
        "kind": "SYNTHETIC classical fixed-scene Monte Carlo",
        "seed": seed,
        "trials_per_level": trials_per_level,
        "grid": [model["n"], model["n"]],
        "wavelength_m": model["wavelength_m"],
        "pixel_pitch_m": model["pitch_m"],
        "recording_distance_m": model["recording_distance_m"],
        "true_reconstruction_distance_mm": true_distance_mm,
        "carrier_bins_x": model["carrier_bins"],
        "carrier_bins_y": 0,
        "filter_radius_bins": model["filter_radius_bins"],
        "filter_inner_radius_fraction": 0.75,
        "peak_expected_electrons": list(levels),
        "read_noise_electrons_std": read_noise,
        "tolerance_mm": tolerance_mm,
        "coarse_distance_range_m": [-0.008, 0.0],
        "coarse_points": 65,
        "refinement_points": 21,
        "focus_metric": "normalized intensity gradient",
        "propagation": "periodic scalar angular spectrum",
        "evanescent_components": "discarded",
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "limitations": [
            "One fixed synthetic scene.",
            "Periodic propagation without padding.",
            "No saturation, quantization, or fixed-pattern noise.",
            "Chosen Fourier filter; not a bandwidth guarantee.",
            "Focus metric is not universally valid.",
            "Percentiles describe trial spread, not a truth confidence interval.",
            "No hardware or quantum validation.",
        ],
    }

    summary = {
        "noise_free_estimate_mm": baseline["distance_m"] * 1e3,
        "noise_free_at_scan_edge": baseline["at_scan_edge"],
        "results": results,
    }

    return rows, config, summary


def save_results(output_dir, rows, config, summary):
    output = Path(output_dir)
    names = ("trials.csv", "config.json", "summary.json")

    if any((output / name).exists() for name in names):
        raise FileExistsError(
            "Results already exist. Use a new output directory."
        )

    output.mkdir(parents=True, exist_ok=True)

    with (output / "trials.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0]),
        )
        writer.writeheader()
        writer.writerows(rows)

    (output / "config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    for name in names:
        path = output / name
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Missing or empty result: {name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "results",
    )
    args = parser.parse_args()

    rows, config, summary = run_experiment(
        trials_per_level=args.trials,
        seed=args.seed,
    )
    save_results(args.output, rows, config, summary)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
