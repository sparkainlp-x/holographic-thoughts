# Holographic Thoughts

**Live demo: https://sparkainlp-x.github.io/holographic-thoughts/**

A single self-contained HTML page (no external dependencies, works offline) with five interactive views of toy holographic-membrane models: one-shot projection recall, a coupled loop, Hebbian crystallization with live eigendecomposition, a calibrated refusal gate, and outer-product capacity (the Shatterpoint).

> SYNTHETIC toy, classical simulation. Not physical holography or quantum hardware. The browser views are illustrative; measured numbers come from the Python models below.

| View | Python reference model |
|---|---|
| Field (projection recall) | [quantum-projection](https://github.com/sparkainlp-x/quantum-projection) |
| Loop (coupled membranes) | [yin-yang-membranes](https://github.com/sparkainlp-x/yin-yang-membranes) (negative result) |
| Crystallization | [membrane-crystallization](https://github.com/sparkainlp-x/membrane-crystallization) |
| Refusal gate | [refusing-membrane](https://github.com/sparkainlp-x/refusing-membrane) |
| Shatterpoint (capacity) | [membrane-capacity](https://github.com/sparkainlp-x/membrane-capacity) |

Run locally: open `index.html` in any browser.

## What this is

- A visual explanation of five small classical models: complex oscillators, projection onto stored patterns, Hebbian updates with an eigendecomposition, a calibrated acceptance threshold, and an outer-product memory.
- Every pixel is computed in your browser from the model on the page. Nothing is a recording.
- A companion to five Python repositories that hold the measured numbers (table above). Numbers quoted on the page are copied from those repositories' READMEs.
- A teaching and exploration tool at toy scale (at most 64 oscillators).

## What this is not

- Not physical holography, not an optical or photonic device, and not a quantum computation: nothing here runs on quantum hardware.
- Not a model of the brain, of thought or of consciousness. The words thought, memory and resurrect are metaphors for stored patterns and oscillator states.
- Not a benchmark, a product or a measurement. The live views use random draws in your browser, so a single run is anecdotal; the repeatable numbers are in the Python repositories, with their seeds.
- Not a medical or clinical tool, and not evidence about any real system.

## Claims and evidence tags

| Statement | Tag |
|---|---|
| The five views run as described in a modern browser, offline | SYNTHETIC (generated inputs, checked by `scripts/check_page.py` for structure and offline loading only) |
| Reference numbers shown beside each view | SYNTHETIC, measured in the linked Python repositories, with seeds stated there |
| Loop view: coupling lowers joint overlap at the default setting | SYNTHETIC negative result, from yin-yang-membranes |
| Any physical, optical, quantum or neural reading of the models | Not claimed |

## Checks

```
python3 scripts/check_page.py            # HTML structure, offline loading, licence, metadata, wording
python3 scripts/check_page.py --online   # also requests the external links
python3 -m unittest discover -s tests    # tests for the checker
```

The script uses only the Python standard library. It does not run the simulations in a browser or test their numerical output; the numbers are checked in the Python repositories. CI runs these on Python 3.10 to 3.13 (`.github/workflows/ci.yml`).

## Release and citation

Releases are archived on Zenodo; see [CHANGELOG.md](CHANGELOG.md) and [CITATION.cff](CITATION.cff). Version 0.1.0 is the first tagged release.

Cite the concept DOI [10.5281/zenodo.23619508](https://doi.org/10.5281/zenodo.23619508) for all versions, or the version DOI [10.5281/zenodo.23619509](https://doi.org/10.5281/zenodo.23619509) for v0.1.0. See also [CITATION.cff](CITATION.cff).

Author: Jean-François Brisson ([ORCID 0009-0000-9778-5374](https://orcid.org/0009-0000-9778-5374)), Spark AI NLP, Fredericton, New Brunswick, Canada.

Copyright (c) 2026 Jean-François Brisson, Spark AI NLP.

Licence: AGPL-3.0-only; see [LICENSE](LICENSE).
