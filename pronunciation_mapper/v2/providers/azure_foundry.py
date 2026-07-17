"""Microsoft Foundry Project Responses API provider."""

import asyncio
import json
import math
import os
import threading
from typing import Any

from ..errors import InvalidProviderOutputError, ProviderConfigurationError
from ..models import DECISION_SCHEMA, DecisionRequest, ProviderResponse, parse_provider_payload
from ..prompts import SYSTEM_INSTRUCTIONS
from .base import raise_classified_provider_error


class AzureFoundryProvider:
    """Entra ID로 인증되는 Microsoft Foundry 기본 provider.

    ``AIProjectClient.get_openai_client()``가 반환하는 OpenAI-compatible client는
    Azure 전송 클라이언트일 뿐이며 ``OPENAI_API_KEY``를 사용하지 않습니다.
    """

    name = "azure-foundry"

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        model: str | None = None,
        credential: Any | None = None,
        client: Any | None = None,
        timeout: float = 30.0,
        max_retries: int = 1,
        max_output_tokens: int = 2048,
    ):
        self.endpoint = endpoint or os.getenv("FOUNDRY_PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        self.model = (
            model
            or os.getenv("FOUNDRY_MODEL")
            or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
            or os.getenv("FOUNDRY_MODEL_NAME")
            or ""
        )
        self.timeout = _positive_float(timeout, "timeout")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")
        self.max_retries = max_retries
        self.max_output_tokens = max_output_tokens
        self._credential = credential
        self._client = client
        self._project_client = None
        self._owns_credential = False
        self._owns_client = False
        self._owns_project_client = False
        self._client_lock = threading.Lock()

    async def decide(self, request: DecisionRequest) -> ProviderResponse:
        # Validate the deployment before importing SDKs or allocating credentials.
        if not isinstance(self.model, str) or not self.model.strip():
            raise ProviderConfigurationError(
                "Foundry model deployment is missing; set FOUNDRY_MODEL or AZURE_AI_MODEL_DEPLOYMENT_NAME"
            )
        client = self._ensure_client()

        payload = json.dumps(request.to_provider_payload(), ensure_ascii=False, separators=(",", ":"))

        def call():
            return client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTIONS,
                input=payload,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "pronunciation_mapper_v2_decision",
                        "description": "Bounded candidate selections for Korean ASR query rewriting",
                        "strict": True,
                        "schema": DECISION_SCHEMA,
                    }
                },
                store=False,
                max_output_tokens=self.max_output_tokens,
            )

        try:
            response = await asyncio.to_thread(call)
        except Exception as error:
            raise_classified_provider_error("Microsoft Foundry", error)

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise InvalidProviderOutputError("Foundry response did not contain output_text")
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as error:
            raise InvalidProviderOutputError("Foundry returned invalid JSON") from error

        return parse_provider_payload(
            parsed,
            provider=self.name,
            model=self.model,
            usage=_extract_usage(getattr(response, "usage", None)),
        )

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        with self._client_lock:
            if self._client is not None:
                return self._client
            return self._create_client()

    def _create_client(self):
        if not isinstance(self.endpoint, str) or not self.endpoint.strip():
            raise ProviderConfigurationError(
                "Foundry project endpoint is missing; set FOUNDRY_PROJECT_ENDPOINT"
            )
        AIProjectClient, DefaultAzureCredential = self._load_sdk()

        credential = self._credential
        owns_credential = credential is None
        project_client = None
        try:
            if credential is None:
                credential = DefaultAzureCredential()
            project_client = AIProjectClient(endpoint=self.endpoint, credential=credential)
            client = project_client.get_openai_client(
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        except Exception as error:
            # Nothing is published onto self until the entire construction has
            # succeeded, so a retry cannot accidentally retain a partial client.
            try:
                if project_client is not None:
                    _close_sync(project_client)
                if owns_credential and credential is not None:
                    _close_sync(credential)
            except (TypeError, AssertionError):
                raise
            # Preserve the primary creation failure; close is best effort.
            except Exception:  # nosec B110
                pass
            raise_classified_provider_error("Microsoft Foundry", error)

        self._credential = credential
        self._project_client = project_client
        self._client = client
        self._owns_credential = owns_credential
        self._owns_project_client = True
        self._owns_client = True
        return client

    @staticmethod
    def _load_sdk():
        try:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
        except ImportError as error:
            raise ProviderConfigurationError(
                "Install the Foundry extra with: "
                "python -m pip install 'pronunciation-mapper[foundry]'"
            ) from error
        return AIProjectClient, DefaultAzureCredential

    def close(self) -> None:
        """Close only resources allocated by this provider, in dependency order."""
        errors: list[Exception] = []
        with self._client_lock:
            resources = (
                ("_client", "_owns_client"),
                ("_project_client", "_owns_project_client"),
                ("_credential", "_owns_credential"),
            )
            for resource_name, ownership_name in resources:
                if not getattr(self, ownership_name):
                    continue
                resource = getattr(self, resource_name)
                setattr(self, ownership_name, False)
                setattr(self, resource_name, None)
                try:
                    _close_sync(resource)
                except Exception as error:
                    errors.append(error)
        if errors:
            raise errors[0]

    async def aclose(self) -> None:
        await asyncio.to_thread(self.close)

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


def _extract_usage(usage: Any) -> dict[str, int | float | str | None]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        raw = usage.model_dump()
    elif isinstance(usage, dict):
        raw = usage
    else:
        raw = {
            key: getattr(usage, key, None)
            for key in ("input_tokens", "output_tokens", "total_tokens")
        }
    return {
        key: value
        for key, value in raw.items()
        if key in {"input_tokens", "output_tokens", "total_tokens"}
        and isinstance(value, (int, float, str))
    }


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


def _close_sync(resource: Any) -> None:
    if resource is None:
        return
    close = getattr(resource, "close", None)
    if callable(close):
        close()
