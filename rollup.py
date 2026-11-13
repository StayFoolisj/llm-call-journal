"""Summarise a journal: estimated cost, p50 and p95 latency, and a breakdown.

    python rollup.py fixtures/sample_journal.jsonl

The rate card is a placeholder. Change RATES_ PER_MILLION to your own prices.
An unknown model is counted, and left out of the cost total.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# model -> (input USD per 1M tokens, output USD per 1M tokens)
RATES_PER_MILLION = {
    "gpt-4o-mini": (0.15, 0.60),
    "claude-3-5-haiku": (0.80, 4.00),
    "local-llama-3-8b": (0.0, 0.0),
}


def load(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSONL journal. A bad line stops the run and names its number."""
    records = []
    with Path(path).open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{number}: {exc}") from exc
    return records


def cost_usd(record: dict[str, Any]) -> float | None:
    """Return the cost of one call, or None when the model has no rate."""
    rates = RATES_PER_MILLION.get(record.get("model") or "")
    if rates is None:
        return None
    input_tokens = record.get("input_tokens") or 0
    output_tokens = record.get("output_tokens") or 0
    return (input_tokens * rates[0] + output_tokens * rates[1]) / 1_000_000


def percentile(values: list[float], share: float) -> float:
    """Return a percentile with linear interpolation. Empty input gives 0."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * share
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * weight


def _group(records: list[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = record.get(field) or "(none)"
        groups.setdefault(key, []).append(record)
    return groups


def _line(label: str, calls: int, cost: float, p50: float, p95: float) -> str:
    return f"  {label:<26} {calls:>5}  {p50:>7.0f}  {p95:>7.0f}  {cost:>9.4f}"


def summarise(records: list[dict[str, Any]]) -> None:
    """Print the summary. Plain text, one block per section."""
    latencies = [float(record.get("latency_ms") or 0) for record in records]
    costs = [cost for record in records if (cost := cost_usd(record)) is not None]
    unpriced = [record for record in records if cost_usd(record) is None]
    tokens_in = sum(record.get("input_tokens") or 0 for record in records)
    tokens_out = sum(record.get("output_tokens") or 0 for record in records)

    print(f"records: {len(records)}   tokens: {tokens_in} in / {tokens_out} out")
    print("\ncost estimate (USD, placeholder rates)")
    print(f"  total: ${sum(costs):.4f}")
    if unpriced:
        models = sorted({record.get("model") or "?" for record in unpriced})
        print(f"  unpriced calls: {len(unpriced)} ({', '.join(models)})")

    print("\nlatency (ms)")
    print(
        f"  p50: {percentile(latencies, 0.50):.0f}"
        f"   p95: {percentile(latencies, 0.95):.0f}"
        f"   min: {min(latencies):.0f}   max: {max(latencies):.0f}"
    )

    for field in ("call_site", "prompt_version"):
        print(f"\nby {field}")
        print(f"  {'':<26} {'calls':>5}  {'p50':>7}  {'p95':>7}  {'cost USD':>9}")
        groups = _group(records, field)
        rows = sorted(
            groups.items(),
            key=lambda item: -sum(cost or 0.0 for cost in map(cost_usd, item[1])),
        )
        for key, group in rows:
            group_latencies = [float(record.get("latency_ms") or 0) for record in group]
            group_cost = sum(cost or 0.0 for cost in map(cost_usd, group))
            print(
                _line(
                    key,
                    len(group),
                    group_cost,
                    percentile(group_latencies, 0.50),
                    percentile(group_latencies, 0.95),
                )
            )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else Path("journal.jsonl")
    if not path.exists():
        print(f"no journal at {path}")
        print("run: python journal.py")
        return 2
    print(f"journal: {path}")
    records = load(path)
    if not records:
        print("the journal is empty")
        return 1
    summarise(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
