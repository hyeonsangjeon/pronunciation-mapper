#!/usr/bin/env python3
"""동일 golden set을 offline, Microsoft Foundry, Ollama에서 비교 실행합니다."""

import argparse
import asyncio
import json
import math
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pronunciation_mapper.v2 import AgenticPronunciationMapper, ProviderUnavailableError


class OfflineProvider:
    name = "offline"
    model = "deterministic-fallback"

    async def decide(self, request):
        raise ProviderUnavailableError("offline eval intentionally uses deterministic fallback")


def parse_args():
    parser = argparse.ArgumentParser(description="Pronunciation Mapper V2 golden-set evaluation")
    parser.add_argument("--provider", choices=["offline", "azure", "ollama"], default="offline")
    parser.add_argument("--cases", type=Path, default=ROOT / "evals" / "cases.jsonl")
    parser.add_argument("--vocabulary", type=Path, default=ROOT / "evals" / "vocabulary.json")
    parser.add_argument("--fail-under", type=float, default=1.0)
    parser.add_argument(
        "--max-fallback-rate",
        type=float,
        default=1.0,
        help="fail when provider fallback exceeds this fraction (default: 1.0)",
    )
    parser.add_argument(
        "--min-provider-results",
        type=int,
        default=0,
        help="require at least this many non-fallback results from the selected provider",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evals" / "results" / "latest.json",
        help="JSON report path",
    )
    return parser.parse_args()


def load_jsonl(path):
    cases = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from error
    return cases


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return ordered[index]


def release_gate_failures(
    metrics,
    *,
    fail_under,
    max_fallback_rate,
    min_provider_results,
):
    """Return human-readable reasons that an eval cannot be released."""
    failures = []
    if metrics["exact_accuracy"] < fail_under:
        failures.append(
            f"exact_accuracy {metrics['exact_accuracy']:.6f} is below {fail_under:.6f}"
        )
    if metrics["fallback_rate"] > max_fallback_rate:
        failures.append(
            f"fallback_rate {metrics['fallback_rate']:.6f} exceeds {max_fallback_rate:.6f}"
        )
    if metrics["provider_result_count"] < min_provider_results:
        failures.append(
            "provider_result_count "
            f"{metrics['provider_result_count']} is below {min_provider_results}"
        )
    return failures


def validate_gate_args(args):
    for name in ("fail_under", "max_fallback_rate"):
        value = getattr(args, name)
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            option = name.replace("_", "-")
            raise SystemExit(f"--{option} must be between 0 and 1")
    if args.min_provider_results < 0:
        raise SystemExit("--min-provider-results must be at least 0")


async def run(args):
    vocabulary = json.loads(args.vocabulary.read_text(encoding="utf-8"))
    cases = load_jsonl(args.cases)
    provider = OfflineProvider() if args.provider == "offline" else args.provider
    mapper = AgenticPronunciationMapper(
        vocabulary["terms"],
        custom_mappings=vocabulary.get("mappings", {}),
        provider=provider,
        fallback_strategy="heuristic",
    )

    rows = []
    try:
        for case in cases:
            result = await mapper.rewrite(case["input"])
            passed = result.rewritten_text == case["expected"]
            rows.append(
                {
                    "id": case["id"],
                    "input": case["input"],
                    "expected": case["expected"],
                    "actual": result.rewritten_text,
                    "passed": passed,
                    "should_change": bool(case["should_change"]),
                    "provider": result.provider,
                    "model": result.model,
                    "fallback_used": result.fallback_used,
                    "latency_ms": result.latency_ms,
                    "diagnostics": list(result.diagnostics),
                }
            )
    finally:
        await mapper.aclose()

    passed_count = sum(row["passed"] for row in rows)
    preserve_rows = [row for row in rows if not row["should_change"]]
    false_rewrites = sum(row["actual"] != row["expected"] for row in preserve_rows)
    latencies = [row["latency_ms"] for row in rows]
    expected_provider = {
        "azure": "azure-foundry",
        "ollama": "ollama",
    }.get(args.provider)
    provider_result_count = sum(
        not row["fallback_used"] and row["provider"] == expected_provider
        for row in rows
    )
    metrics = {
        "case_count": len(rows),
        "exact_accuracy": passed_count / len(rows) if rows else 0.0,
        "false_rewrite_rate": false_rewrites / len(preserve_rows) if preserve_rows else 0.0,
        "fallback_rate": sum(row["fallback_used"] for row in rows) / len(rows) if rows else 0.0,
        "provider_result_count": provider_result_count,
        "latency_p50_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "latency_p95_ms": round(percentile(latencies, 0.95), 3),
    }
    report = {"provider": args.provider, "metrics": metrics, "cases": rows}

    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    for row in rows:
        marker = "PASS" if row["passed"] else "FAIL"
        print(f"[{marker}] {row['id']}: {row['actual']}")
    print(f"report: {output_path}")
    failures = release_gate_failures(
        metrics,
        fail_under=args.fail_under,
        max_fallback_rate=args.max_fallback_rate,
        min_provider_results=args.min_provider_results,
    )
    for failure in failures:
        print(f"[GATE] {failure}", file=sys.stderr)
    return 1 if failures else 0


def main():
    args = parse_args()
    validate_gate_args(args)
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
