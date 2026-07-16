from argparse import Namespace

import pytest

from evals.run_v2 import release_gate_failures, validate_gate_args


def _metrics(*, accuracy=1.0, fallback_rate=0.0, provider_results=1):
    return {
        "exact_accuracy": accuracy,
        "fallback_rate": fallback_rate,
        "provider_result_count": provider_results,
    }


def test_release_gate_rejects_hidden_provider_fallback():
    failures = release_gate_failures(
        _metrics(fallback_rate=0.2),
        fail_under=1.0,
        max_fallback_rate=0.0,
        min_provider_results=1,
    )

    assert any("fallback_rate" in failure for failure in failures)


def test_release_gate_requires_a_real_provider_result():
    failures = release_gate_failures(
        _metrics(provider_results=0),
        fail_under=1.0,
        max_fallback_rate=0.0,
        min_provider_results=1,
    )

    assert any("provider_result_count" in failure for failure in failures)


def test_release_gate_accepts_a_clean_provider_run():
    assert release_gate_failures(
        _metrics(),
        fail_under=1.0,
        max_fallback_rate=0.0,
        min_provider_results=1,
    ) == []


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("fail_under", -0.01, "--fail-under"),
        ("fail_under", float("nan"), "--fail-under"),
        ("max_fallback_rate", 1.01, "--max-fallback-rate"),
        ("min_provider_results", -1, "--min-provider-results"),
    ],
)
def test_release_gate_rejects_invalid_limits(field, value, message):
    args = Namespace(
        fail_under=1.0,
        max_fallback_rate=1.0,
        min_provider_results=0,
    )
    setattr(args, field, value)

    with pytest.raises(SystemExit, match=message):
        validate_gate_args(args)
