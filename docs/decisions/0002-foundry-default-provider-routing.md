# 0002. Foundry 기본 provider와 명시적 provider routing

- 상태: Accepted
- 결정일: 2026-07-16

## 배경

기본 운영 환경은 Microsoft Foundry external tenant이며 OpenAI·Claude API token은 제공되지 않습니다. 로컬 실행에는 Ollama가 유용하지만 Azure와 로컬은 데이터 경계, model 품질, capacity가 다릅니다.

## 결정

- Microsoft Foundry Project Responses API와 Entra ID를 기본 provider로 사용합니다.
- Ollama는 호출자가 `provider="ollama"`로 명시할 때만 사용합니다.
- Azure 장애 시 Ollama로 자동 전환하지 않습니다.
- OpenAI·Claude는 `DecisionProvider` 확장 계약 참고용으로만 두고 adapter를 제공하지 않습니다.

## 결과

- API key/client secret 없이 Azure identity와 RBAC를 사용할 수 있습니다.
- provider 장애가 다른 데이터 경계로 조용히 전환되지 않습니다.
- Ollama를 사용하려면 모델 설치와 별도 품질 eval이 필요합니다.
- 다른 provider를 추가하려면 같은 bounded decision schema와 validation 계약을 구현해야 합니다.
