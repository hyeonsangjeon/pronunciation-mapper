"""V2 provider와 출력 검증에서 사용하는 예외 계층."""


class PronunciationMapperV2Error(Exception):
    """V2 오류의 기본 클래스."""


class ProviderError(PronunciationMapperV2Error):
    """외부 모델 provider 호출 오류."""


class ProviderConfigurationError(ProviderError):
    """provider 실행에 필요한 설정이 없습니다."""


class ProviderUnavailableError(ProviderError):
    """provider 또는 로컬 모델에 연결할 수 없습니다."""


class InvalidProviderOutputError(ProviderError):
    """provider 출력이 V2의 제한된 결정 계약을 위반했습니다."""


class UnsupportedProviderError(ProviderConfigurationError):
    """구현하지 않았거나 reference-only인 provider입니다."""
