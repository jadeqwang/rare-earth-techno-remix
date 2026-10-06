"""Load the pinned official ITGPT paper checkpoints for CPU inference.

The author's checkpoints pickle config dataclasses under ``__main__``.
Allow only the official imported config definitions with explicit alias names;
retain PyTorch's restricted weights-only loader rather than unpickling code.
This module performs no inference or writes until main() is invoked.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
from pathlib import Path
import sys
import time

REPO = Path(os.environ.get("ITGPT_REPO", "/tmp/rare-earth-itgpt"))
sys.path.insert(0, str(REPO))

import numpy as np
import torch

from onset import OnsetConfig, OnsetModel
from sym_config import ModelConfig
from sym import ITGPTSymModel


def load_models(device="cpu", repo=REPO):
    """Return (onset_model, symbol_model) loaded strictly from paper weights."""
    repo = Path(repo)
    with torch.serialization.safe_globals([
        (OnsetConfig, "__main__.OnsetConfig"),
        (ModelConfig, "__main__.ModelConfig"),
    ]):
        onset_checkpoint = torch.load(
            repo / "trained_models/onset_paper.pt",
            map_location=device, weights_only=True,
        )
        sym_checkpoint = torch.load(
            repo / "trained_models/sym_paper.pt",
            map_location=device, weights_only=True,
        )
    onset_config = onset_checkpoint["cfg"]
    sym_config = sym_checkpoint["cfg"]
    if type(onset_config) is not OnsetConfig or type(sym_config) is not ModelConfig:
        raise TypeError("Checkpoint config types do not match official definitions")
    onset_model = OnsetModel(onset_config).to(device)
    onset_model.load_state_dict(onset_checkpoint["model_state"], strict=True)
    symbol_model = ITGPTSymModel(3, sym_config).to(device)
    # The released paper weights predate official commit a4ab71fc7a029b2b6c7d33ed128c5d12d719d24d,
    # which changed this module from LayerNorm to RMSNorm. Keep the architecture
    # represented by the weights, including the learned bias; never drop keys.
    if "audio_enc.layer_norm.bias" in sym_checkpoint["model"]:
        symbol_model.audio_enc.layer_norm = torch.nn.LayerNorm(sym_config.VQ_dim).to(device)
    symbol_model.load_state_dict(sym_checkpoint["model"], strict=True)
    onset_model.eval()
    symbol_model.eval()
    return onset_model, symbol_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    torch.manual_seed(32026)
    start = time.monotonic()
    onset, sym = load_models()
    report = {
        "repo": str(REPO),
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "threads": torch.get_num_threads(),
        "onset_config": dataclasses.asdict(onset.cfg),
        "symbol_config": dataclasses.asdict(sym.cfg),
        "onset_parameters": sum(p.numel() for p in onset.parameters()),
        "symbol_parameters": sum(p.numel() for p in sym.parameters()),
        "strict_state_dict_load": True,
        "weights_only": True,
        "symbol_encoder_norm": type(sym.audio_enc.layer_norm).__name__,
        "load_seconds": time.monotonic() - start,
    }
    if args.smoke:
        start = time.monotonic()
        with torch.inference_mode():
            contexts = torch.randn(1, 64, onset.cfg.nframes, onset.cfg.nfreq, 3)
            predictions = onset.generate(contexts, 132, 6, threshold=0.5)
            audio = torch.randn(1, 8, 41, onset.cfg.nfreq, 3)
            deltas = torch.ones(1, 8, 2)
            tokens = sym.generate(audio_steps=audio, aux_steps=deltas, max_len=8,
                                  temperature=0, top_p=None)
        report["smoke"] = {
            "onset_input_shape": list(contexts.shape),
            "onset_output_shape": list(predictions.shape),
            "onset_nonzero": int(np.count_nonzero(predictions)),
            "symbol_output_shape": list(tokens.shape),
            "symbol_tokens": tokens.tolist(),
            "finite_valid_outputs": bool(np.isfinite(predictions).all()
                and np.isfinite(tokens).all() and ((tokens >= 0) & (tokens < 256)).all()),
            "seconds": time.monotonic() - start,
        }
    print(json.dumps(report, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
