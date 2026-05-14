from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from app.core.config import get_settings


@dataclass
class MetricsCollector:
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    timings: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def increment(self, name: str, value: int = 1) -> None:
        if not get_settings().metrics_enabled:
            return
        with self._lock:
            self.counters[name] += value

    def observe(self, name: str, duration_ms: float) -> None:
        if not get_settings().metrics_enabled:
            return
        with self._lock:
            values = self.timings[name]
            values.append(duration_ms)
            if len(values) > 500:
                del values[:-500]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            timings = {}
            for name, values in self.timings.items():
                if not values:
                    continue
                sorted_values = sorted(values)
                count = len(sorted_values)
                timings[name] = {
                    "count": count,
                    "avg_ms": sum(sorted_values) / count,
                    "p95_ms": sorted_values[min(count - 1, int(count * 0.95))],
                    "max_ms": sorted_values[-1],
                }
            return {
                "enabled": get_settings().metrics_enabled,
                "counters": dict(self.counters),
                "timings": timings,
            }


metrics = MetricsCollector()


class Timer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.started_at = 0.0

    def __enter__(self) -> Timer:
        self.started_at = perf_counter()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        metrics.observe(self.name, (perf_counter() - self.started_at) * 1000)
