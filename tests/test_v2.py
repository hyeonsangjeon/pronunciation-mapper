import unittest
from unittest.mock import patch

from pronunciation_mapper.v2 import (
    AgenticPronunciationMapper,
    DecisionAction,
    ProviderResponse,
    ProviderSelection,
    ReasonCode,
)


class ScriptedProvider:
    name = "scripted"
    model = "fixture"

    def __init__(self, action="replace", confidence=0.95, invalid_candidate=False, error=None):
        self.action = action
        self.confidence = confidence
        self.invalid_candidate = invalid_candidate
        self.error = error
        self.calls = []

    async def decide(self, request):
        self.calls.append(request)
        if self.error:
            raise self.error
        selections = []
        for span in request.spans:
            candidate_id = None
            if self.action == "replace":
                candidate_id = "not-allowed" if self.invalid_candidate else span.candidates[0].id
            selections.append(
                ProviderSelection(
                    span_id=span.id,
                    action=DecisionAction(self.action),
                    candidate_id=candidate_id,
                    confidence=self.confidence,
                    reason_code=ReasonCode.CONTEXT if self.action == "replace" else ReasonCode.AMBIGUOUS,
                )
            )
        return ProviderResponse(tuple(selections), self.name, self.model, {"input_tokens": 10})


class TestAgenticPronunciationMapper(unittest.IsolatedAsyncioTestCase):
    async def test_exact_aliases_are_local_and_preserve_layout(self):
        provider = ScriptedProvider()
        mapper = AgenticPronunciationMapper(
            ["customer", "server"],
            custom_mappings={"커스터머": "customer", "서버": "server"},
            provider=provider,
        )

        result = await mapper.rewrite("커스터머,  서버에서!")

        self.assertEqual(result.rewritten_text, "customer,  server에서!")
        self.assertEqual(result.provider, "local-deterministic")
        self.assertFalse(result.fallback_used)
        self.assertEqual(provider.calls, [])

    async def test_exact_compound_alias_is_local(self):
        provider = ScriptedProvider()
        mapper = AgenticPronunciationMapper(
            ["cloud", "server"],
            custom_mappings={"클라우드": "cloud", "서버": "server"},
            provider=provider,
        )

        result = await mapper.rewrite("클라우드서버 상태")

        self.assertEqual(result.rewritten_text, "cloud server 상태")
        self.assertEqual(provider.calls, [])

    async def test_agent_selects_only_local_candidate(self):
        provider = ScriptedProvider()
        mapper = AgenticPronunciationMapper(["transaction"], provider=provider)

        result = await mapper.rewrite("트랜잭숑 로그")

        self.assertEqual(result.rewritten_text, "transaction 로그")
        self.assertEqual(result.provider, "scripted")
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("transaction", provider.calls[0].spans[0].candidates[0].canonical_terms)

    async def test_agent_can_keep_ambiguous_source(self):
        provider = ScriptedProvider(action="keep")
        mapper = AgenticPronunciationMapper(["transaction"], provider=provider)

        result = await mapper.rewrite("트랜잭숑")

        self.assertEqual(result.rewritten_text, "트랜잭숑")
        self.assertFalse(result.fallback_used)

    async def test_low_confidence_replacement_is_not_applied(self):
        provider = ScriptedProvider(confidence=0.2)
        mapper = AgenticPronunciationMapper(["transaction"], provider=provider, minimum_confidence=0.7)

        result = await mapper.rewrite("트랜잭숑")

        self.assertEqual(result.rewritten_text, "트랜잭숑")
        self.assertEqual(result.decisions[0].action, "keep")
        self.assertEqual(result.decisions[0].reason_code, "ambiguous")
        self.assertIsNone(result.decisions[0].candidate_id)
        self.assertIn("low-confidence:s0", result.diagnostics)

    async def test_invalid_candidate_triggers_heuristic_fallback(self):
        provider = ScriptedProvider(invalid_candidate=True)
        mapper = AgenticPronunciationMapper(["transaction"], provider=provider)

        result = await mapper.rewrite("트랜잭숑")

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.rewritten_text, "transaction")
        self.assertIn("provider-fallback:InvalidProviderOutputError", result.diagnostics)

    async def test_provider_failure_can_preserve_original(self):
        provider = ScriptedProvider(error=ConnectionError("offline"))
        mapper = AgenticPronunciationMapper(
            ["transaction"], provider=provider, fallback_strategy="original"
        )

        result = await mapper.rewrite("트랜잭숑")

        self.assertTrue(result.fallback_used)
        self.assertEqual(result.rewritten_text, "트랜잭숑")

    async def test_number_normalization_does_not_need_provider(self):
        provider = ScriptedProvider()
        mapper = AgenticPronunciationMapper(["transaction"], provider=provider)

        result = await mapper.rewrite("삼백이십일번 조회")

        self.assertEqual(result.rewritten_text, "321번 조회")
        self.assertIn("number-normalization-applied", result.diagnostics)

    async def test_partial_alias_keeps_prefix_suffix_and_particle(self):
        provider = ScriptedProvider()
        mapper = AgenticPronunciationMapper(
            ["customer", "cloud", "server"],
            custom_mappings={
                "커스터머": "customer",
                "클라우드": "cloud",
                "서버": "server",
            },
            provider=provider,
        )

        first = await mapper.rewrite("신규커스터머정보")
        second = await mapper.rewrite("클라우드서버만")

        self.assertEqual(first.rewritten_text, "신규customer정보")
        self.assertEqual(second.rewritten_text, "cloud server만")
        self.assertEqual(provider.calls, [])

    async def test_identifier_suffix_is_never_deleted_by_phonetic_fallback(self):
        provider = ScriptedProvider(error=ConnectionError("offline"))
        mapper = AgenticPronunciationMapper(["account", "id", "XPN36"], provider=provider)

        self.assertEqual((await mapper.rewrite("account_id")).rewritten_text, "account_id")
        self.assertEqual((await mapper.rewrite("XPN36_prod")).rewritten_text, "XPN36_prod")
        self.assertEqual((await mapper.rewrite("accountId")).rewritten_text, "accountId")
        self.assertEqual((await mapper.rewrite("XPN36prod")).rewritten_text, "XPN36prod")
        self.assertEqual(provider.calls, [])

    async def test_punctuated_canonical_identifier_is_not_duplicated(self):
        provider = ScriptedProvider(error=ConnectionError("offline"))
        mapper = AgenticPronunciationMapper(
            ["customer-id", "schema.table", "api/v1"], provider=provider
        )

        value = "customer-id schema.table api/v1"
        self.assertEqual((await mapper.rewrite(value)).rewritten_text, value)
        self.assertEqual(provider.calls, [])

    async def test_mixed_canonical_and_alias_compound_is_deterministic(self):
        provider = ScriptedProvider()
        mapper = AgenticPronunciationMapper(
            ["cloud", "server"],
            custom_mappings={"서버": "server"},
            provider=provider,
        )

        self.assertEqual((await mapper.rewrite("cloud서버")).rewritten_text, "cloud server")
        self.assertEqual((await mapper.rewrite("서버cloud")).rewritten_text, "server cloud")
        self.assertEqual(provider.calls, [])

    async def test_canonical_term_does_not_reverse_into_an_alias(self):
        mapper = AgenticPronunciationMapper(
            ["transaction", "트랜잭션"], provider=ScriptedProvider()
        )
        self.assertEqual(
            (await mapper.rewrite("transaction 로그")).rewritten_text,
            "transaction 로그",
        )

    async def test_particle_like_last_syllable_does_not_pollute_best_candidate(self):
        provider = ScriptedProvider()
        mapper = AgenticPronunciationMapper(
            ["MSI", "Kafka"],
            custom_mappings={"엠에스아이": "MSI", "카프카": "Kafka"},
            provider=provider,
        )

        self.assertEqual((await mapper.rewrite("엠에쓰아이")).rewritten_text, "MSI")
        self.assertEqual((await mapper.rewrite("카프가")).rewritten_text, "Kafka")

    async def test_all_alias_pronunciations_participate_in_retrieval(self):
        provider = ScriptedProvider()
        mapper = AgenticPronunciationMapper(
            ["customer"], custom_mappings={"고객": "customer"}, provider=provider
        )

        self.assertEqual((await mapper.rewrite("고갹")).rewritten_text, "customer")

    async def test_invalid_custom_provider_contract_falls_back_safely(self):
        for confidence in (float("inf"), 10**400):
            with self.subTest(confidence_type=type(confidence).__name__):
                provider = ScriptedProvider(confidence=confidence)
                mapper = AgenticPronunciationMapper(
                    ["transaction"], provider=provider, fallback_strategy="original"
                )

                result = await mapper.rewrite("트랜잭숑")

                self.assertEqual(result.rewritten_text, "트랜잭숑")
                self.assertTrue(result.fallback_used)
                self.assertIn(
                    "provider-fallback:InvalidProviderOutputError", result.diagnostics
                )

    async def test_provider_metadata_and_usage_are_revalidated(self):
        class InvalidUsageProvider(ScriptedProvider):
            async def decide(self, request):
                response = await super().decide(request)
                return ProviderResponse(
                    response.selections,
                    provider="invalid-usage",
                    model=response.model,
                    usage={"input_tokens": 10**400},
                )

        mapper = AgenticPronunciationMapper(
            ["transaction"], provider=InvalidUsageProvider(), fallback_strategy="original"
        )
        result = await mapper.rewrite("트랜잭숑")

        self.assertEqual(result.rewritten_text, "트랜잭숑")
        self.assertTrue(result.fallback_used)

    async def test_input_limits_bound_untrusted_work(self):
        mapper = AgenticPronunciationMapper(
            ["customer"], provider=ScriptedProvider(), max_input_chars=3, max_spans=2
        )
        with self.assertRaises(ValueError):
            await mapper.rewrite("다섯글자")
        with self.assertRaises(ValueError):
            AgenticPronunciationMapper(["customer"], threshold=10**400)

    async def test_mapper_closes_only_factory_owned_provider(self):
        class ClosableProvider(ScriptedProvider):
            def __init__(self):
                super().__init__()
                self.close_calls = 0

            async def aclose(self):
                self.close_calls += 1

        owned = ClosableProvider()
        with patch("pronunciation_mapper.v2.engine.create_provider", return_value=owned):
            async with AgenticPronunciationMapper(["customer"], provider="azure"):
                pass
        self.assertEqual(owned.close_calls, 1)

        injected = ClosableProvider()
        async with AgenticPronunciationMapper(["customer"], provider=injected):
            pass
        self.assertEqual(injected.close_calls, 0)

    def test_sync_projection(self):
        mapper = AgenticPronunciationMapper(
            ["customer"],
            custom_mappings={"커스터머": "customer"},
            provider=ScriptedProvider(),
        )
        self.assertEqual(mapper.map_sentence("커스터머 조회"), "customer 조회")


if __name__ == "__main__":
    unittest.main()
