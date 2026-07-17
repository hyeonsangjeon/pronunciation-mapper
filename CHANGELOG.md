# 변경 기록

이 파일에는 사용자와 운영자에게 의미 있는 변경만 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르고, 버전은 [Semantic Versioning](https://semver.org/lang/ko/) 기준으로 관리합니다.

## [Unreleased]

릴리스 이후 변경 사항은 여기에 기록합니다.

## [2.0.0] - 2026-07-17

### Added

- 로컬 발음 top-K 후보에서만 선택하는 `AgenticPronunciationMapper` bounded decision agent.
- Microsoft Foundry Project Responses API 기본 provider와 Entra ID 인증.
- 명시적으로 선택하는 Ollama native provider와 structured-output 계약.
- span별 결정, confidence, 거리, latency, usage, fallback 진단을 제공하는 `RewriteResult`.
- provider 독립 golden set과 offline/Foundry/Ollama 평가 runner.
- Python 3.10–3.13 테스트, offline eval, wheel build, GitHub Pages 검증 CI.
- external-tenant Foundry OIDC live workflow와 `ci-` 임시 배포 cleanup guard.
- GitHub Pages 사용 매뉴얼과 Foundry/Ollama/V1 입력·출력 예제.

### Changed

- V1 휴리스틱을 제거하지 않고 V2의 deterministic candidate/fallback 계층으로 재사용.
- 숫자처럼 보이는 일반어와 고유명사를 보존하도록 한국어 숫자 정규화를 보수적으로 변경.
- 기본 heuristic fallback threshold를 V1보다 보수적인 `0.35`로 분리.
- 패키지 기준 Python을 3.10 이상으로 올리고 provider별 optional dependency를 분리.
- License metadata를 SPDX/PEP 639 형식으로 갱신.

### Security

- 모델은 로컬에서 허용한 candidate ID만 반환할 수 있고 DB vocabulary 밖 문자열은 적용할 수 없음.
- 입력 길이, span 수, token 길이, timeout, retry, output token에 기본 상한 적용.
- Azure 장애 시 Ollama로 자동 전환하지 않으며 provider 간 데이터 경계를 호출자가 결정.
- live CI는 API key/client secret 대신 GitHub OIDC를 사용하고 `foundry-external` Environment의 `main` branch 정책을 요구.

### Compatibility

- 기존 `PronunciationMapper`와 V1 CLI 명령은 그대로 유지.
- OpenAI와 Claude는 provider 구현 없이 확장 계약 참고용으로만 유지.

상세 범위와 검증 결과는 [V2.0.0 릴리스 기록](docs/releases/v2.0.0.md)을 참고하세요.

## [0.1.0] - 2025-11-15

태그가 없던 V1 기간의 마지막 전용 commit(`315aecf`)을 historical baseline으로 기록합니다. `0.1.0` 버전 문자열은 저장소 초기부터 사용했습니다.

### Added

- 한국어 자모 분해와 영문 발음 치환 기반의 pronunciation similarity mapper.
- Levenshtein 거리, 직접 mapping, 한국어 조사 보존, 숫자 변환.
- 단어·문장 mapping과 사용자 mapping 저장을 위한 V1 API 및 CLI.

[Unreleased]: https://github.com/hyeonsangjeon/pronunciation-mapper/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/hyeonsangjeon/pronunciation-mapper/compare/315aecf...v2.0.0
[0.1.0]: https://github.com/hyeonsangjeon/pronunciation-mapper/tree/315aecf
