"""구조화 판정 provider가 구현해야 하는 최소 계약과 오류 분류."""

import asyncio
from typing import NoReturn, Protocol, runtime_checkable

from ..errors import ProviderConfigurationError, ProviderUnavailableError
from ..models import DecisionRequest, ProviderResponse


@runtime_checkable
class DecisionProvider(Protocol):
    name: str
    model: str

    async def decide(self, request: DecisionRequest) -> ProviderResponse:
        """각 span에 대한 bounded selection을 반환합니다."""

    async def aclose(self) -> None:
        """provider가 소유한 리소스를 해제합니다."""

    def close(self) -> None:
        """동기 컨텍스트에서 provider가 소유한 리소스를 해제합니다."""


def raise_classified_provider_error(provider: str, error: Exception) -> NoReturn:
    """SDK별 예외 타입에 결합하지 않고 HTTP/전송 오류를 공통 분류합니다.

    ``TypeError``와 ``AssertionError``는 SDK 호출 계약이 바뀌었거나 테스트
    불변식이 깨졌다는 신호일 수 있으므로 운영 장애로 위장하지 않습니다.
    """
    if isinstance(error, (TypeError, AssertionError)):
        raise error
    if isinstance(error, (ProviderConfigurationError, ProviderUnavailableError)):
        raise error

    status_code = _status_code(error)
    if status_code in {400, 401, 403, 404, 422} or _is_authentication_error(error):
        raise ProviderConfigurationError(
            f"{provider} request was rejected by configuration or authorization "
            f"(HTTP {status_code})"
        ) from error
    if status_code == 429 or (status_code is not None and status_code >= 500):
        raise ProviderUnavailableError(
            f"{provider} is temporarily unavailable (HTTP {status_code})"
        ) from error
    if _is_network_error(error):
        raise ProviderUnavailableError(
            f"{provider} network request failed ({type(error).__name__})"
        ) from error

    # Unknown SDK/runtime failures remain provider failures, but must not expose
    # credentials, request bodies, or potentially sensitive response content.
    suffix = f" (HTTP {status_code})" if status_code is not None else f" ({type(error).__name__})"
    raise ProviderUnavailableError(f"{provider} request failed{suffix}") from error


def _status_code(error: Exception) -> int | None:
    for value in (error, getattr(error, "response", None)):
        status = getattr(value, "status_code", None)
        if isinstance(status, int) and not isinstance(status, bool):
            return status
    return None


def _is_network_error(error: Exception) -> bool:
    if isinstance(error, (ConnectionError, TimeoutError, OSError, asyncio.TimeoutError)):
        return True

    # Azure/OpenAI and Ollama currently use httpx underneath. Avoid a hard
    # dependency on httpx while still recognizing its transport exceptions.
    module = type(error).__module__.split(".", 1)[0]
    name = type(error).__name__.lower()
    if module == "httpx" and any(token in name for token in ("connect", "timeout", "network", "transport")):
        return True

    cause = error.__cause__
    return isinstance(cause, Exception) and cause is not error and _is_network_error(cause)


def _is_authentication_error(error: Exception) -> bool:
    name = type(error).__name__.lower()
    if any(token in name for token in ("authentication", "authorization", "credential")):
        return True
    cause = error.__cause__
    return (
        isinstance(cause, Exception)
        and cause is not error
        and _is_authentication_error(cause)
    )
