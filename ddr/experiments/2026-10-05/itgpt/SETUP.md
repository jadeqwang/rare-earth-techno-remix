ITGPT inference environment for Rare Earth
==========================================

Environment checked on 2026-10-05:

- Official source: https://github.com/miguelomalley/ITGPT
- Source checkout: `/tmp/rare-earth-itgpt`, commit `81de0bfebe02d7aba722ddcb3b417e3a94b89d7c`
- No AGENTS.md exists in that checkout.
- Python: `/tmp/rare-earth-itgpt/.venv/bin/python` (CPython 3.13.5).
- PyTorch: 2.14.1+cpu. CUDA is unavailable; nvidia-smi cannot communicate with the driver.
- Host CPU: AMD Ryzen 9 7900X, 12 cores/24 threads. Set torch threads to 2 or 4 for inference.
- The venv is isolated. Dependencies were installed with uv and a task-specific writable cache.
- Models: `/tmp/rare-earth-itgpt/trained_models/onset_paper.pt` and `sym_paper.pt`.
- Model source: https://huggingface.co/miguelomalley/ITGPT/tree/246ead2665282658b25e05c9363ea5c3e244d9c8

Checkpoint SHA-256 hashes:

```
fa47f78d02e7ce72bc2e627382bfc7a30ef6ded6c94862c19d4a7b87a4f200fe  onset_paper.pt
fcb63e505994dde1079d967ca5d031f18f2bd8b06ab3e325443fb73d75f44450  sym_paper.pt
```

Runnable smoke check:

```bash
# From the project root, using the original runtime path:
ITGPT_REPO=/tmp/rare-earth-itgpt /tmp/rare-earth-itgpt/.venv/bin/python \
  ddr/experiments/2026-10-05/itgpt/load_models.py --smoke
```

Import `load_models()` from the sibling `load_models.py` in an adapter. This returns
the onset and symbolic models in eval mode, loading the checkpoint-provided configs.
Set `ITGPT_REPO` to relocate the checkout/checkpoints. No stock BPM detector is run.

Compatibility fixes
-------------------

The checkpoints serialize `__main__.OnsetConfig` and `__main__.ModelConfig`.
The helper allowlists only those names mapped to the official imported dataclasses
and retains `torch.load(weights_only=True)`. It does not use unrestricted pickle
loading or mutate global `__main__` definitions.

The public paper symbolic checkpoint includes `audio_enc.layer_norm.bias`, while
the current repository uses RMSNorm for that encoder module. Official commit
[a4ab71f](https://github.com/miguelomalley/ITGPT/commit/a4ab71fc7a029b2b6c7d33ed128c5d12d719d24d)
changed this module from LayerNorm to RMSNorm. The loader restores that single
module to the original official LayerNorm when the checkpoint contains its bias.
All tensors then load with `strict=True`; no model keys or trained weights are dropped.
Both models pass a shape-correct CPU generation smoke check; see `setup_report.json`.

Measured timing integration
--------------------------

The root adapter must preserve `ddr/analysis/timing.json`, including beat zero and
the accelerating BPM grid. The upstream `set_bpm` produces only a constant tempo.

Audio features should use the official `create_analyzers(nhop=441)` and
`extract_mel_feats(..., nhop=441)`: 44.1kHz mono, 100 feature frames per second,
three FFT scales, 80 mel bands, log magnitude.

Onset contexts use `make_onset_feature_context_range` with consecutive measured
beat times, `frame_density=32`, then `(contexts-contexts.mean(0)) /
(contexts.std(0)+1e-6)` as in official training. The input shape is
`(1, beats, 32, 80, 3)`; output is `(beats, 48)` within-beat grid slots.
The BPM conditioning is one scalar per sequence, so use an appropriate local
mean BPM for overlapping chunks or a representative BPM for the full song.
Timing remains measured per beat regardless of this conditioning scalar.

For symbolic input, official `sym_generators.py` normalizes full-song feature
frames per mel-band/channel using `(features-mean(axis=0))/std(axis=0)` before
extracting 41-frame windows. The stock generation script omits this operation;
training-consistent normalization is recommended, adding 1e-6 to handle flat
channels. Inputs are `(1, steps, 41, 80, 3)` and beat delta pairs
`(1, steps, 2)`; output is integer token IDs 0..255. Use the official
`unravel_onehot(token, 4)` to map IDs to left/down/up/right `0123` symbols.

The 256-token vocabulary permits invalid hold transitions and simultaneous
three/four-panel patterns. Preserve raw results for audit before enforcing
playability and simfile legality. Symbolic sampling is stochastic; seed torch
explicitly and retain generation parameters with each candidate.

Upstream prefix support carries prior token IDs but does not also prepend their
audio/beat-delta contexts. For faithful aligned context, use overlapping audio
windows with corresponding prefix tokens and keep only the newly generated tail,
or omit prefixes at chunk boundaries and document those boundaries.

Recreate the environment
------------------------

The durable `official-source.tar.gz` archive contains the exact upstream tracked
files at the pinned commit, including its MIT license; it is about 1.1 MB compressed.
It excludes git metadata, the virtual environment, checkpoints, and download cache.
An additional license copy is included as `UPSTREAM_LICENSE.md`.

Run the saved script with a fresh writable runtime path:

```bash
# From the project root:
bash ddr/experiments/2026-10-05/itgpt/setup.sh /tmp/rare-earth-itgpt-repro
```

The script checks source and lock hashes, extracts the archived pinned source,
creates a Python 3.13.5 environment, syncs every exact package pin, downloads the
two models from the pinned Hugging Face revision, verifies checkpoint hashes,
and runs the strict model smoke check. Existing unrelated directories and
checkpoint hash mismatches cause a clear failure instead of being overwritten.
Set `ITGPT_REPO` to the restored path when invoking the generation adapter.

Exact installed dependency versions are recorded in `requirements-lock.txt`;
the lock was checked against all 43 distributions in the successful inference
environment. Origin URLs, revisions, hashes, and compatibility changes are
recorded in `provenance.json`. The recreation script has been syntax-checked;
no duplicate environment installation was performed.
