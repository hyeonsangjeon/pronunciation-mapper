import asyncio
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from pronunciation_mapper.v2 import (
    AzureFoundryProvider,
    Candidate,
    CandidateSpan,
    DecisionRequest,
    InvalidProviderOutputError,
    OllamaProvider,
    ProviderConfigurationError,
    ProviderUnavailableError,
    UnsupportedProviderError,
    create_provider,
)


DECISION = {
    "decisions": [
        {
            "span_id": "s0",
            "action": "replace",
            "candidate_id": "s0:c0",
            "confidence": 0.9,
            "reason_code": "context",
        }
    ]
}


def request_fixture():
    candidate = Candidate("s0:c0", "transaction", ("transaction",), 0.2, "phonetic")
    span = CandidateSpan("s0", 0, 5, "트랜잭숑", (candidate,))
    return DecisionRequest("트랜잭숑", (span,))


class FakeFoundryResponses:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            output_text=json.dumps(DECISION),
            usage={"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
        )


class FakeFoundryClient:
    def __init__(self):
        self.responses = FakeFoundryResponses()
        self.close_calls = 0

    def close(self):
        self.close_calls += 1


class FakeOllamaClient:
    def __init__(self):
        self.kwargs = None
        self.chat_calls = 0
        self.close_calls = 0

    async def chat(self, **kwargs):
        self.kwargs = kwargs
        self.chat_calls += 1
        return {
            "message": {"content": json.dumps(DECISION)},
            "prompt_eval_count": 9,
            "eval_count": 4,
        }

    async def close(self):
        self.close_calls += 1


class FakeHTTPError(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class RaisingFoundryResponses:
    def __init__(self, error):
        self.error = error

    def create(self, **kwargs):
        raise self.error


class RaisingFoundryClient:
    def __init__(self, error):
        self.responses = RaisingFoundryResponses(error)


class RaisingOllamaClient:
    def __init__(self, error):
        self.error = error

    async def chat(self, **kwargs):
        raise self.error


class FakeCredential:
    instances = []

    def __init__(self):
        self.close_calls = 0
        self.__class__.instances.append(self)

    def close(self):
        self.close_calls += 1


class FakeProjectClient:
    instances = []

    def __init__(self, *, endpoint, credential):
        self.endpoint = endpoint
        self.credential = credential
        self.openai_client = FakeFoundryClient()
        self.get_openai_client_kwargs = None
        self.close_calls = 0
        self.__class__.instances.append(self)

    def get_openai_client(self, **kwargs):
        self.get_openai_client_kwargs = kwargs
        return self.openai_client

    def close(self):
        self.close_calls += 1


class PerCallOllamaClient(FakeOllamaClient):
    instances = []

    def __init__(self, *, host, timeout):
        super().__init__()
        self.host = host
        self.timeout = timeout
        self.created_loop = None
        self.__class__.instances.append(self)

    async def chat(self, **kwargs):
        self.created_loop = asyncio.get_running_loop()
        return await super().chat(**kwargs)


class SlowProjectClient(FakeProjectClient):
    instances = []

    def __init__(self, *, endpoint, credential):
        time.sleep(0.02)
        super().__init__(endpoint=endpoint, credential=credential)


class TestProviderAdapters(unittest.IsolatedAsyncioTestCase):
    async def test_foundry_uses_project_responses_structured_schema(self):
        client = FakeFoundryClient()
        provider = AzureFoundryProvider(model="deployment", client=client)

        response = await provider.decide(request_fixture())

        self.assertEqual(response.provider, "azure-foundry")
        self.assertEqual(response.selections[0].candidate_id, "s0:c0")
        kwargs = client.responses.kwargs
        self.assertEqual(kwargs["model"], "deployment")
        self.assertFalse(kwargs["store"])
        self.assertEqual(kwargs["max_output_tokens"], 2048)
        self.assertEqual(kwargs["text"]["format"]["type"], "json_schema")
        self.assertTrue(kwargs["text"]["format"]["strict"])
        schema = kwargs["text"]["format"]["schema"]
        self.assertNotIn("maxItems", schema["properties"]["decisions"])
        confidence_schema = schema["properties"]["decisions"]["items"]["properties"]["confidence"]
        self.assertNotIn("minimum", confidence_schema)
        self.assertNotIn("maximum", confidence_schema)

    async def test_ollama_uses_native_schema_format(self):
        client = FakeOllamaClient()
        provider = OllamaProvider(model="qwen", client=client)

        response = await provider.decide(request_fixture())

        self.assertEqual(response.provider, "ollama")
        self.assertEqual(response.usage["input_tokens"], 9)
        self.assertEqual(client.kwargs["format"]["type"], "object")
        self.assertEqual(client.kwargs["options"]["temperature"], 0)

    async def test_foundry_validates_model_before_creating_client(self):
        provider = AzureFoundryProvider(endpoint="https://example", model="deployment")
        provider.model = ""
        provider._ensure_client = Mock(side_effect=AssertionError("must not allocate"))

        with self.assertRaises(ProviderConfigurationError):
            await provider.decide(request_fixture())
        provider._ensure_client.assert_not_called()

    async def test_foundry_forwards_transport_limits_and_closes_owned_resources(self):
        FakeCredential.instances.clear()
        FakeProjectClient.instances.clear()
        provider = AzureFoundryProvider(
            endpoint="https://example",
            model="deployment",
            timeout=12.5,
            max_retries=3,
            max_output_tokens=321,
        )
        provider._load_sdk = lambda: (FakeProjectClient, FakeCredential)

        async with provider:
            await provider.decide(request_fixture())

        credential = FakeCredential.instances[-1]
        project = FakeProjectClient.instances[-1]
        self.assertEqual(
            project.get_openai_client_kwargs,
            {"timeout": 12.5, "max_retries": 3},
        )
        self.assertEqual(project.openai_client.responses.kwargs["max_output_tokens"], 321)
        self.assertEqual(project.openai_client.close_calls, 1)
        self.assertEqual(project.close_calls, 1)
        self.assertEqual(credential.close_calls, 1)

        await provider.aclose()
        self.assertEqual(project.openai_client.close_calls, 1, "close must be idempotent")

    async def test_foundry_lazy_initialization_is_thread_safe(self):
        FakeCredential.instances.clear()
        SlowProjectClient.instances.clear()
        provider = AzureFoundryProvider(endpoint="https://example", model="deployment")
        provider._load_sdk = lambda: (SlowProjectClient, FakeCredential)

        clients = await asyncio.gather(
            *(asyncio.to_thread(provider._ensure_client) for _ in range(8))
        )

        self.assertEqual(len({id(client) for client in clients}), 1)
        self.assertEqual(len(SlowProjectClient.instances), 1)
        self.assertEqual(len(FakeCredential.instances), 1)
        await provider.aclose()

    async def test_foundry_does_not_close_injected_resources(self):
        client = FakeFoundryClient()
        credential = FakeCredential()
        provider = AzureFoundryProvider(
            endpoint="https://example",
            model="deployment",
            credential=credential,
            client=client,
        )

        await provider.decide(request_fixture())
        provider.close()
        await provider.aclose()

        self.assertEqual(client.close_calls, 0)
        self.assertEqual(credential.close_calls, 0)

    async def test_foundry_keeps_injected_credential_but_closes_internal_clients(self):
        FakeProjectClient.instances.clear()
        credential = FakeCredential()
        provider = AzureFoundryProvider(
            endpoint="https://example",
            model="deployment",
            credential=credential,
        )
        provider._load_sdk = lambda: (FakeProjectClient, FakeCredential)

        await provider.decide(request_fixture())
        await provider.aclose()

        project = FakeProjectClient.instances[-1]
        self.assertEqual(credential.close_calls, 0)
        self.assertEqual(project.openai_client.close_calls, 1)
        self.assertEqual(project.close_calls, 1)

    async def test_ollama_reuses_but_does_not_close_injected_client(self):
        client = FakeOllamaClient()
        provider = OllamaProvider(model="qwen", client=client)

        await provider.decide(request_fixture())
        await provider.decide(request_fixture())
        await provider.aclose()

        self.assertEqual(client.chat_calls, 2)
        self.assertEqual(client.close_calls, 0)

    async def test_http_errors_are_classified_for_both_providers(self):
        for status in (400, 401, 403, 404):
            with self.subTest(provider="foundry", status=status):
                provider = AzureFoundryProvider(
                    model="deployment", client=RaisingFoundryClient(FakeHTTPError(status))
                )
                with self.assertRaises(ProviderConfigurationError):
                    await provider.decide(request_fixture())
            with self.subTest(provider="ollama", status=status):
                provider = OllamaProvider(model="qwen", client=RaisingOllamaClient(FakeHTTPError(status)))
                with self.assertRaises(ProviderConfigurationError):
                    await provider.decide(request_fixture())

        for status in (429, 500, 503):
            with self.subTest(provider="foundry", status=status):
                provider = AzureFoundryProvider(
                    model="deployment", client=RaisingFoundryClient(FakeHTTPError(status))
                )
                with self.assertRaises(ProviderUnavailableError):
                    await provider.decide(request_fixture())
            with self.subTest(provider="ollama", status=status):
                provider = OllamaProvider(model="qwen", client=RaisingOllamaClient(FakeHTTPError(status)))
                with self.assertRaises(ProviderUnavailableError):
                    await provider.decide(request_fixture())

    async def test_network_errors_are_unavailable_and_contract_errors_escape(self):
        for error in (ConnectionError("offline"), TimeoutError("slow")):
            with self.subTest(type=type(error).__name__):
                provider = AzureFoundryProvider(model="deployment", client=RaisingFoundryClient(error))
                with self.assertRaises(ProviderUnavailableError):
                    await provider.decide(request_fixture())

        for error_type in (TypeError, AssertionError):
            with self.subTest(provider="foundry", type=error_type.__name__):
                provider = AzureFoundryProvider(
                    model="deployment", client=RaisingFoundryClient(error_type("contract"))
                )
                with self.assertRaises(error_type):
                    await provider.decide(request_fixture())
            with self.subTest(provider="ollama", type=error_type.__name__):
                provider = OllamaProvider(
                    model="qwen", client=RaisingOllamaClient(error_type("contract"))
                )
                with self.assertRaises(error_type):
                    await provider.decide(request_fixture())

    async def test_invalid_response_shapes_are_output_errors(self):
        foundry_client = SimpleNamespace(
            responses=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output_text=None))
        )
        with self.assertRaises(InvalidProviderOutputError):
            await AzureFoundryProvider(model="deployment", client=foundry_client).decide(request_fixture())

        ollama_client = SimpleNamespace(chat=lambda **kwargs: _async_value({"message": {}}))
        with self.assertRaises(InvalidProviderOutputError):
            await OllamaProvider(model="qwen", client=ollama_client).decide(request_fixture())

        oversized = json.loads(json.dumps(DECISION))
        oversized["decisions"][0]["confidence"] = 10**400
        foundry_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(output_text=json.dumps(oversized))
            )
        )
        with self.assertRaises(InvalidProviderOutputError):
            await AzureFoundryProvider(
                model="deployment", client=foundry_client
            ).decide(request_fixture())

    def test_factory_defaults_to_azure(self):
        self.assertIsInstance(create_provider("azure"), AzureFoundryProvider)
        self.assertIsInstance(create_provider("ollama"), OllamaProvider)

    def test_openai_and_claude_are_reference_only(self):
        for name in ("openai", "claude", "anthropic"):
            with self.assertRaises(UnsupportedProviderError):
                create_provider(name)

    def test_transport_limit_validation(self):
        invalid_timeouts = (0, -1, float("inf"), float("nan"), 10**400, True, "30")
        for timeout in invalid_timeouts:
            with self.subTest(provider="foundry", timeout=timeout):
                with self.assertRaises(ValueError):
                    AzureFoundryProvider(timeout=timeout)
            with self.subTest(provider="ollama", timeout=timeout):
                with self.assertRaises(ValueError):
                    OllamaProvider(timeout=timeout)
        for value in (-1, 1.5, True):
            with self.subTest(max_retries=value):
                with self.assertRaises(ValueError):
                    AzureFoundryProvider(max_retries=value)
        for value in (0, -1, 1.5, True):
            with self.subTest(max_output_tokens=value):
                with self.assertRaises(ValueError):
                    AzureFoundryProvider(max_output_tokens=value)


class TestOllamaSyncLoopSafety(unittest.TestCase):
    def test_internal_client_is_created_and_closed_per_event_loop(self):
        PerCallOllamaClient.instances.clear()
        provider = OllamaProvider(host="http://ollama", model="qwen", timeout=8)
        provider._load_client_class = lambda: PerCallOllamaClient

        first = asyncio.run(provider.decide(request_fixture()))
        second = asyncio.run(provider.decide(request_fixture()))

        self.assertEqual(first.provider, "ollama")
        self.assertEqual(second.provider, "ollama")
        self.assertEqual(len(PerCallOllamaClient.instances), 2)
        self.assertIsNot(PerCallOllamaClient.instances[0], PerCallOllamaClient.instances[1])
        self.assertTrue(all(client.close_calls == 1 for client in PerCallOllamaClient.instances))
        self.assertTrue(all(client.host == "http://ollama" for client in PerCallOllamaClient.instances))
        self.assertTrue(all(client.timeout == 8.0 for client in PerCallOllamaClient.instances))


async def _async_value(value):
    return value


if __name__ == "__main__":
    unittest.main()
