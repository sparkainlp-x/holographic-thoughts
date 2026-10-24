# Changelog

## 0.1.0 (2026-10-24)

First tagged release of the single-page site.

- Five interactive views of toy holographic-membrane models, all computed in the browser from the page itself: projection recall (the thought field), a coupled yin-yang loop, Hebbian crystallization with a live eigendecomposition, a calibrated refusal gate, and outer-product capacity (the shatterpoint).
- Every view links to the Python reference model that measured its numbers; the page states which numbers come from which repository.
- The loop view reports a negative result: at the page default coupling, coupling lowers joint overlap.
- The capacity view states that the browser classifier (W times probe, then argmax) differs from the direct projection used in membrane-capacity.
- Checks added for this release: a standard-library script (`scripts/check_page.py`) that tests HTML structure, offline loading, licence text, citation metadata and wording, with unit tests and a CI workflow on Python 3.10 to 3.13.
- Footer note that words such as thought, memory and resurrect are metaphors for stored patterns and oscillator states.
- Citation metadata: `CITATION.cff` and `.zenodo.json` at version 0.1.0.
- Everything on the page is a SYNTHETIC toy and a classical simulation. It is not physical holography, not quantum hardware and not a model of cognition.
