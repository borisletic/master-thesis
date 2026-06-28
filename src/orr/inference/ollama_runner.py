"""Thin wrapper around the Ollama HTTP API.

Uses the `/api/generate` endpoint over plain HTTP (via `requests`) so the only
hard dependency is `requests`. Designed to be deterministic by default
(temperature 0, fixed seed) for the primary runs, with optional temperature
sweeps for the stochastic-robustness runs.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests


@dataclass
class GenerationResult:
    """Outcome of a single generation request."""

    model: str
    prompt: str
    response: str
    # generation parameters actually used
    temperature: float
    seed: int | None
    # bookkeeping
    latency_s: float
    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class OllamaRunner:
    """Minimal client for a local Ollama server."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        timeout: int = 180,
        system_prompt: str | None = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.system_prompt = system_prompt

    # -- server / model management -------------------------------------------------

    def is_up(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def available_models(self) -> list[str]:
        r = requests.get(f"{self.host}/api/tags", timeout=10)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    def ensure_model(self, model: str, pull: bool = False) -> bool:
        """Return True if `model` is present locally; optionally pull it."""
        present = any(m == model or m.split(":")[0] == model for m in self.available_models())
        if present or not pull:
            return present
        # streaming pull; block until done
        with requests.post(
            f"{self.host}/api/pull", json={"name": model}, stream=True, timeout=None
        ) as resp:
            resp.raise_for_status()
            for _ in resp.iter_lines():
                pass
        return True

    # -- generation ----------------------------------------------------------------

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.0,
        seed: int | None = 42,
        num_predict: int = 512,
        system_prompt: str | None = None,
    ) -> GenerationResult:
        options: dict[str, Any] = {
            "temperature": temperature,
            "num_predict": num_predict,
        }
        if seed is not None:
            options["seed"] = seed

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        sys_p = system_prompt if system_prompt is not None else self.system_prompt
        if sys_p:
            payload["system"] = sys_p

        t0 = time.perf_counter()
        try:
            r = requests.post(
                f"{self.host}/api/generate", json=payload, timeout=self.timeout
            )
            r.raise_for_status()
            data = r.json()
            return GenerationResult(
                model=model,
                prompt=prompt,
                response=data.get("response", ""),
                temperature=temperature,
                seed=seed,
                latency_s=time.perf_counter() - t0,
                raw=data,
            )
        except requests.RequestException as exc:
            return GenerationResult(
                model=model,
                prompt=prompt,
                response="",
                temperature=temperature,
                seed=seed,
                latency_s=time.perf_counter() - t0,
                error=str(exc),
            )
