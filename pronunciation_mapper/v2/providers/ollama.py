"""Ollama native API provider."""

import inspect
import json
import math
import os
from typing import Any

from ..errors import InvalidProviderOutputError, ProviderConfigurationError
from ..models import DECISION_SCHEMA, DecisionRequest, ProviderResponse, parse_provider_payload
from ..prompts import SYSTEM_INSTRUCTIONS
from .base import raise_classified_provider_error


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        host: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        max_output_tokens: int = 2048,
        keep_alive: str = "5m",
        client: Any | None = None,
    ):
        self.host = host or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
        self.model = model or os.getenv("OLLAMA_MODEL") or "qwen3.5:4b"
        self.timeout = _positive_float(timeout, "timeout")
        if (
            isinstance(max_output_tokens, bool)
            or not isinstance(max_output_tokens, int)
            or max_output_tokens <= 0
        ):
            raise ValueError("max_output_tokens must be a positive integer")
        self.max_output_tokens = max_output_tokens
        self.keep_alive = keep_alive
        self._client = client

    async def decide(self, request: DecisionRequest) -> ProviderResponse:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ProviderConfigurationError("Ollama model is missing; set OLLAMA_MODEL")

        owns_client = self._client is None
        try:
            client = self._client if self._client is not None else self._new_client()
        except ProviderConfigurationError:
            raise
        except Exception as error:
            raise_classified_provider_error("Ollama", error)

        payload = json.dumps(request.to_provider_payload(), ensure_ascii=False, separators=(",", ":"))
        response = None
        request_error: BaseException | None = None
        try:
            response = await client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": payload},
                ],
                format=DECISION_SCHEMA,
                stream=False,
                think=False,
                options={"temperature": 0, "num_predict": self.max_output_tokens},
                keep_alive=self.keep_alive,
            )
        except BaseException as error:
            request_error = error

        # An internally-created AsyncClient belongs to this invocation. This
        # avoids retaining a client bound to a completed asyncio.run() loop.
        if owns_client:
            try:
                await _close_async(client)
            except BaseException as close_error:
                if request_error is None:
                    if isinstance(close_error, Exception):
                        raise_classified_provider_error("Ollama client close", close_error)
                    raise

        if request_error is not None:
            if isinstance(request_error, Exception):
                raise_classified_provider_error("Ollama", request_error)
            raise request_error

        message = _value(response, "message")
        content = _value(message, "content")
        if not isinstance(content, str) or not content.strip():
            raise InvalidProviderOutputError("Ollama response did not contain message.content")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as error:
            raise InvalidProviderOutputError("Ollama returned invalid JSON") from error

        usage = {}
        for source_key, target_key in (
            ("prompt_eval_count", "input_tokens"),
            ("eval_count", "output_tokens"),
            ("total_duration", "total_duration_ns"),
            ("load_duration", "load_duration_ns"),
        ):
            value = _value(response, source_key)
            if isinstance(value, (int, float)):
                usage[target_key] = value

        return parse_provider_payload(
            parsed,
            provider=self.name,
            model=self.model,
            usage=usage,
        )

    def _new_client(self):
        AsyncClient = self._load_client_class()
        return AsyncClient(host=self.host, timeout=self.timeout)

    @staticmethod
    def _load_client_class():
        try:
            from ollama import AsyncClient
        except ImportError as error:
            raise ProviderConfigurationError(
                "Install the Ollama extra with: "
                "python -m pip install 'pronunciation-mapper[ollama]'"
            ) from error
        return AsyncClient

    async def aclose(self) -> None:
        """No-op: injected clients are caller-owned; internal clients are per-call."""

    def close(self) -> None:
        """No-op: injected clients are caller-owned; internal clients are per-call."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> bool:
        await self.aclose()
        return False


def _value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _positive_float(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    try:
        normalized = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a positive finite number") from error
    if normalized <= 0 or not math.isfinite(normalized):
        raise ValueError(f"{name} must be a positive finite number")
    return normalized


async def _close_async(resource: Any) -> None:
    close = getattr(resource, "close", None)
    if not callable(close):
        return
    result = close()
    if inspect.isawaitable(result):
        await result
