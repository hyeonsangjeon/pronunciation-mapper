import os

import pytest

from pronunciation_mapper.v2 import AgenticPronunciationMapper


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_foundry_rewrites_an_unresolved_phonetic_candidate():
    if os.getenv("RUN_FOUNDRY_LIVE_TESTS") != "1":
        pytest.skip("set RUN_FOUNDRY_LIVE_TESTS=1 to enable the live Foundry test")

    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    model = os.getenv("FOUNDRY_MODEL")
    missing = [
        name
        for name, value in {
            "FOUNDRY_PROJECT_ENDPOINT": endpoint,
            "FOUNDRY_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        pytest.fail(f"live Foundry test is enabled but missing: {', '.join(missing)}")

    mapper = AgenticPronunciationMapper(
        ["transaction", "server", "log"],
        custom_mappings={"서버": "server", "로그": "log"},
        provider="azure",
        provider_options={
            "endpoint": endpoint,
            "model": model,
            "timeout": 60.0,
            "max_retries": 1,
        },
        fallback_strategy="raise",
        minimum_confidence=0.0,
    )

    try:
        result = await mapper.rewrite("트랜잭숑 서버 로그")
    finally:
        await mapper.aclose()

    assert result.rewritten_text == "transaction server log"
    assert result.provider == "azure-foundry"
    assert result.model == model
    assert result.fallback_used is False
    assert not any(
        diagnostic.startswith("provider-fallback:")
        for diagnostic in result.diagnostics
    )

    decision = next(item for item in result.decisions if item.source == "트랜잭숑")
    assert decision.action == "replace"
    assert decision.replacement == "transaction"
