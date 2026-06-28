"""Fetch the public third-party benchmarks (XSTest, OR-Bench) into data/.

These are downloaded rather than committed (see .gitignore) to respect their
licenses and keep the repo small. Network access is required.

Usage:
    python -m scripts.download_datasets --datasets xstest
    python -m scripts.download_datasets --datasets xstest or_bench
"""
from __future__ import annotations

try:
    from . import _bootstrap  # noqa: F401  (sys.path shim; -m scripts.x)
except ImportError:
    import _bootstrap  # noqa: F401  (direct file run)

import argparse
import sys
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DATA = _REPO / "data"

# Canonical raw sources. Verify licenses before use (both are openly licensed).
SOURCES = {
    "xstest": {
        "dir": _DATA / "xstest",
        "files": {
            # XSTest v2 prompts (CC BY 4.0). Hosted in the paper's GitHub repo.
            "xstest_v2_prompts.csv": "https://raw.githubusercontent.com/paul-rottger/xstest/main/xstest_prompts.csv",
        },
    },
    "or_bench": {
        "dir": _DATA / "or_bench",
        "files": {
            # OR-Bench is distributed on HuggingFace; programmatic CSV export below.
            # Replace with the exact split you want (or_bench_hard_1k / 80k / toxic).
            "or_bench_hard_1k.csv": "https://huggingface.co/datasets/bench-llm/or-bench/resolve/main/or-bench-hard-1k.csv",
        },
    },
}


def fetch(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        print(f"  GET {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "orr-thesis/0.1"})
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (trusted hosts)
            data = resp.read()
        dest.write_bytes(data)
        print(f"  -> {dest} ({len(data)} bytes)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  [fail] {exc}", file=sys.stderr)
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasets", nargs="+", default=["xstest"], choices=list(SOURCES))
    args = ap.parse_args(argv)

    ok = True
    for name in args.datasets:
        spec = SOURCES[name]
        print(f"[{name}] -> {spec['dir']}")
        for fname, url in spec["files"].items():
            if not fetch(url, spec["dir"] / fname):
                ok = False
        print(
            f"[{name}] note: if a URL 404s, the dataset may have moved — check the "
            "paper's repo/HF page and update SOURCES in this script."
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
