#!/usr/bin/env python3
"""동일 golden set을 offline, Microsoft Foundry, Ollama에서 비교 실행합니다."""

import argparse
import asyncio
import json
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
    metrics = {
        "case_count": len(rows),
        "exact_accuracy": passed_count / len(rows) if rows else 0.0,
        "false_rewrite_rate": false_rewrites / len(preserve_rows) if preserve_rows else 0.0,
        "fallback_rate": sum(row["fallback_used"] for row in rows) / len(rows) if rows else 0.0,
        "latency_p50_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "latency_p95_ms": round(percentile(latencies, 0.95), 3),
    }
    report = {"provider": args.provider, "metrics": metrics, "cases": rows}

    output_dir = ROOT / "evals" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "latest.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    for row in rows:
        marker = "PASS" if row["passed"] else "FAIL"
        print(f"[{marker}] {row['id']}: {row['actual']}")
    print(f"report: {output_path}")
    return 0 if metrics["exact_accuracy"] >= args.fail_under else 1


def main():
    args = parse_args()
    if not 0.0 <= args.fail_under <= 1.0:
        raise SystemExit("--fail-under must be between 0 and 1")
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
