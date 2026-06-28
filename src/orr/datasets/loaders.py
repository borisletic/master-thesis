"""Dataset loaders.

A common in-memory representation (`Prompt`) is used across all datasets so the
experiment runner is dataset-agnostic. Gold labels are normalized to
"should_comply" (benign — a calibrated model must NOT refuse) or "should_refuse"
(harmful control — a calibrated model SHOULD refuse).
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# repo-root/data
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

GOLD_COMPLY = "should_comply"
GOLD_REFUSE = "should_refuse"


@dataclass
class Prompt:
    id: str
    text: str
    gold: str                       # GOLD_COMPLY | GOLD_REFUSE
    dataset: str
    category: str = "unknown"
    trigger_words: list[str] = field(default_factory=list)
    pair_id: str | None = None      # links a benign prompt to its harmful contrast
    source: str = ""
    tier: str = "core"              # "core" (paired) | "hard" (unpaired stress test)
    meta: dict = field(default_factory=dict)


# --------------------------------------------------------------------------------------
# Own dataset: Security-SWE Over-Refusal set (main contribution)
# --------------------------------------------------------------------------------------

def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("//"):
                rows.append(json.loads(line))
    return rows


def load_security_swe(data_dir: Path | None = None) -> list[Prompt]:
    base = (data_dir or _DATA_DIR) / "security_swe"
    prompts: list[Prompt] = []
    files = (
        ("benign.jsonl", GOLD_COMPLY),
        ("harmful.jsonl", GOLD_REFUSE),
        ("benign_hard.jsonl", GOLD_COMPLY),   # unpaired over-refusal stress tests
    )
    _known = {"id", "prompt", "label", "category", "trigger_words",
              "pair_id", "source", "tier"}
    for fname, gold in files:
        path = base / fname
        if not path.exists():
            continue
        for row in _read_jsonl(path):
            prompts.append(
                Prompt(
                    id=row["id"],
                    text=row["prompt"],
                    gold=row.get("label", gold),
                    dataset="security_swe",
                    category=row.get("category", "unknown"),
                    trigger_words=row.get("trigger_words", []),
                    pair_id=row.get("pair_id"),
                    source=row.get("source", ""),
                    tier=row.get("tier", "core"),
                    meta={k: v for k, v in row.items() if k not in _known},
                )
            )
    return prompts


# --------------------------------------------------------------------------------------
# XSTest (Röttger et al., 2024) — fetched by scripts/download_datasets.py
# --------------------------------------------------------------------------------------

def load_xstest(data_dir: Path | None = None) -> list[Prompt]:
    base = (data_dir or _DATA_DIR) / "xstest"
    # the canonical release ships a CSV with columns: id_v2,type,prompt,focus,note,label
    # where label in {safe, contrast(=unsafe)}.
    csv_path = next(iter(base.glob("*.csv")), None)
    if csv_path is None:
        return []
    prompts: list[Prompt] = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            label_raw = (row.get("label") or row.get("type_label") or "").strip().lower()
            type_v = (row.get("type") or "").strip()
            # XSTest label is exactly "safe" / "unsafe"; fall back to the "type"
            # column (unsafe prompt types are prefixed "contrast_") if absent.
            if label_raw in {"safe", "unsafe"}:
                is_safe = label_raw == "safe"
            else:
                is_safe = not type_v.startswith("contrast")
            focus = (row.get("focus") or "").strip()
            prompts.append(
                Prompt(
                    id=row.get("id_v2") or row.get("id") or f"xstest-{i}",
                    text=row["prompt"],
                    gold=GOLD_COMPLY if is_safe else GOLD_REFUSE,
                    dataset="xstest",
                    category=type_v or "unknown",
                    trigger_words=[focus] if focus else [],
                    source="XSTest (Röttger et al. 2024)",
                )
            )
    return prompts


# --------------------------------------------------------------------------------------
# OR-Bench (Cui et al., 2024) — large, benign-only "seemingly toxic" prompts
# --------------------------------------------------------------------------------------

def load_or_bench(data_dir: Path | None = None, limit: int | None = None) -> list[Prompt]:
    base = (data_dir or _DATA_DIR) / "or_bench"
    csv_path = next(iter(base.glob("*.csv")), None)
    if csv_path is None:
        return []
    prompts: list[Prompt] = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if limit is not None and i >= limit:
                break
            prompts.append(
                Prompt(
                    id=row.get("id") or f"orbench-{i}",
                    text=row.get("prompt") or row.get("question") or "",
                    gold=GOLD_COMPLY,  # OR-Bench is benign-by-construction
                    dataset="or_bench",
                    category=row.get("category", "unknown"),
                    source="OR-Bench (Cui et al. 2024)",
                )
            )
    return prompts


DATASET_LOADERS: dict[str, Callable[..., list[Prompt]]] = {
    "security_swe": load_security_swe,
    "xstest": load_xstest,
    "or_bench": load_or_bench,
}


def load_dataset(name: str, limit: int | None = None, **kwargs) -> list[Prompt]:
    if name not in DATASET_LOADERS:
        raise KeyError(f"unknown dataset {name!r}; known: {list(DATASET_LOADERS)}")
    loader = DATASET_LOADERS[name]
    try:
        prompts = loader(limit=limit, **kwargs)  # type: ignore[call-arg]
    except TypeError:
        prompts = loader(**kwargs)
        if limit is not None:
            prompts = prompts[:limit]
    return prompts
