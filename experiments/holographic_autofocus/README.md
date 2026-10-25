# Synthetic holographic-autofocus Monte Carlo experiment

A small, reproducible numerical experiment. It generates an off-axis
interference hologram of a fixed synthetic scene, adds camera-like noise,
recovers the complex field with a Fourier sideband filter, and estimates the
reconstruction distance with an intensity-gradient focus metric.

It is separate from the Holographic Thoughts page (`index.html`). It does not
change the page, its models, or any of its claims.

## 1. Scope and non-claims

This is a **classical, synthetic, fixed-scene numerical experiment.** It tests:

- scalar optical propagation (periodic angular spectrum);
- off-axis interference hologram generation;
- Poisson photoelectron noise plus Gaussian read noise;
- Fourier sideband filtering;
- coarse distance scanning followed by local grid refinement;
- the noise sensitivity of an intensity-gradient focus estimator.

It does **not** demonstrate:

- physical holographic-display hardware;
- quantum hardware, quantum advantage, or quantum-wave generation;
- a calibrated physical membrane;
- autofocus performance across different scenes;
- submicron physical accuracy merely because the refinement uses a fine grid.

It is not a hardware-calibrated optical experiment.

## 2. Installation and reproduction

From the repository root:

```bash
python -m pip install -r experiments/holographic_autofocus/requirements.txt

python -m unittest discover -s experiments/holographic_autofocus -p "test_*.py" -v

# Smoke run into a temporary directory
python experiments/holographic_autofocus/experiment.py \
  --trials 2 --seed 42 --output /tmp/holographic_autofocus_smoke

# Full run (writes experiments/holographic_autofocus/results/)
python experiments/holographic_autofocus/experiment.py --trials 40 --seed 42
```

The script refuses to overwrite existing results; use a new `--output`
directory to re-run. Only NumPy (>=1.24) is needed, plus the standard library.

## 3. Model parameters

| Quantity | Value |
| --- | --- |
| Grid | 96 x 96 samples |
| Pixel pitch | 6.5 um |
| Wavelength | 532 nm |
| Recording distance | 4 mm |
| Object | Two Gaussian amplitude blobs centred at (-12, -8) and (+11, +10) pixels, amplitudes 1.0 and 0.7, real-valued (flat phase) |
| Reference | Unit-amplitude tilted plane wave, carrier at 24 bins along x, 0 along y |
| Propagation | Scalar angular-spectrum method; evanescent components discarded |
| Fourier mask | Centred on the negative-frequency sideband (-24, 0) bins, radius 9 bins, flat inside 0.75 of the radius, raised-cosine roll-off to zero at 9 bins |

The hologram is `|propagated object + reference|^2`. The test suite checks
that the carrier plus mask radius fits inside the sampling grid and that the
mask radius is smaller than the carrier.

## 4. Noise conversion

```
gain             = peak_electrons / max(clean_hologram)
expected counts  = gain * clean_hologram
measurement      = Poisson(expected counts) + Gaussian read noise
```

The result is divided by `gain` to return to hologram units. Read noise has
a standard deviation of 3 electrons. Illumination levels are 200 and 2000
peak expected electrons.

## 5. Negative values

The read-noise samples are zero-mean Gaussian offsets added after the Poisson
draw, so individual measured values can be negative. The model has no black
level and applies no clipping, saturation, or quantization.

## 6. Fixed gain

Within each illumination level the gain is fixed by the clean hologram. Each
trial draws new noise at that gain, with no per-trial renormalization to the
noisy hologram's maximum.

## 7. Correct distance

Under the chosen convention the recorded field is propagated by +4 mm, so the
correct numerical reconstruction distance is **-4 mm**.

## 8. Focus metric and refinement

The recovered complex field is back-propagated to each candidate distance,
and the focus score is

```
mean(|grad I|^2) / mean(I^2),   I = |field|^2
```

This is invariant to overall scale. The coarse scan has 65 points from -8 mm
to 0 mm (0.125 mm spacing). The best coarse point is refined on a 21-point
grid between its two neighbours (0.0125 mm spacing). If the best coarse point
is at either end of the scan, or the best fine point is, the estimate is
flagged `at_scan_edge`. The fine grid sets only the resolution of the search.
It does not set the physical accuracy.

## 9. Limitations of the model

- Propagation is **periodic** (FFT-based) with no padding, so light wraps
  around the grid edges.
- The Fourier filter is a chosen one. It is not a bandwidth guarantee, and
  the filter radius trades noise rejection against loss of object detail.
- There is one fixed scene. The focus metric is not universally valid.
- There is no saturation, quantization, or fixed-pattern noise.

## 10. Bias, repeatability, RMSE

- **Bias** is the mean error against the true distance. It is a systematic offset.
- **Repeatability** (reported as `std_distance_mm`) is the sample standard
  deviation of the estimates across trials. It measures spread, not
  correctness.
- **RMSE** combines both: `RMSE^2 = bias^2 + (population variance)`.

## 11. Percentile intervals

The `empirical_2p5_97p5_mm` values are the 2.5th and 97.5th percentiles of
the trial estimates. They summarize **trial spread**. They are not
confidence intervals for the true object distance.

## 12. Success counts

The within +/-0.25 mm fraction is an observed frequency over a finite number
of trials in one scene and one noise model. For example, 40/40 successes do
not prove a future 100% success probability.

## 13. Synthetic and classical

All results come from a synthetic, classical numerical computation. There is
no physical validation, hardware, or quantum component.

## 14. What the round-trip test checks

`test_periodic_propagation_round_trip` checks only that periodic numerical
propagation by +4 mm followed by -4 mm returns the original field. It does
**not** test the full hologram, filtering, and reconstruction chain. That
chain is covered only by the noise-free focus test on this one scene.

## Results of the full run (`--trials 40 --seed 42`)

Generated by `experiment.py` into `results/` (`config.json`, `summary.json`,
`trials.csv`). The run used Python 3.13.5 and NumPy 2.5.4, recorded in
`results/config.json`.

Noise-free estimate: **-4.000 mm** (not at a scan edge).

| Peak expected electrons | Trials | Mean (mm) | Std (mm) | Bias (mm) | RMSE (mm) | Within +/-0.25 mm | At scan edge | Empirical 2.5-97.5 % (mm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | 40 | -3.98625 | 0.260943 | +0.01375 | 0.258027 | 28/40 (0.70) | 0/40 | -4.3791 to -3.6147 |
| 2000 | 40 | -3.984375 | 0.082855 | +0.015625 | 0.083292 | 40/40 (1.00) | 0/40 | -4.1378 to -3.8372 |

For this scene and noise model, the lower illumination level gives a spread
about three times larger and 28 of 40 estimates within 0.25 mm. At 2000 peak
electrons all 40 are within 0.25 mm. Neither result says anything about other
scenes, a physical device, or future runs.

### Note on an earlier computation

An earlier execution of the original formulation (noise-free -4.000 mm; 200 e-
mean -3.98625, std 0.260943, 28/40; 2000 e- mean -3.984375, std 0.082855,
40/40) was kept for comparison only. It was not used as a target and nothing
was tuned to it. The numbers above come from this run. They agree with it at
the printed precision for the same seed on the Python and NumPy versions
above.
