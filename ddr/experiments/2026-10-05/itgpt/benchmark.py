"""Benchmark paper-model symbolic inference on synthetic, shape-correct inputs."""

import argparse
import json
from pathlib import Path
import time
import torch

from load_models import load_models

parser = argparse.ArgumentParser()
parser.add_argument("--report", type=Path)
args = parser.parse_args()
torch.set_num_threads(4)
onset, sym = load_models()
reports = []
for threads in [2, 4]:
    torch.set_num_threads(threads)
    for length in [128, 320]:
        torch.manual_seed(123)
        audio = torch.randn(1, length, 41, 80, 3)
        deltas = torch.ones(1, length, 2) * 0.5
        start = time.monotonic()
        with torch.inference_mode():
            tokens = sym.generate(audio_steps=audio, aux_steps=deltas,
                                  max_len=length, temperature=1.0, top_p=0.9)
        reports.append({"threads": threads, "length": length,
                        "seconds": time.monotonic()-start,
                        "symbols_generated": len(tokens)})
        print(json.dumps(reports[-1]), flush=True)
if args.report:
    args.report.write_text(json.dumps(reports, indent=2) + "\n")
