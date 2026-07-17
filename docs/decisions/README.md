# 아키텍처 결정 기록

현재 구조는 [V2 아키텍처 문서](../V2_ARCHITECTURE.md)에 설명합니다. 이 디렉터리는 이후에도 바뀌지 않아야 할 “왜 이 선택을 했는가”를 짧은 결정 단위로 보존합니다.

| ID | 결정 | 상태 |
| --- | --- | --- |
| [0001](0001-bounded-candidate-agent.md) | 자유 rewrite 대신 bounded candidate agent 사용 | Accepted |
| [0002](0002-foundry-default-provider-routing.md) | Foundry 기본, Ollama 명시 선택, OpenAI·Claude reference-only | Accepted |
| [0003](0003-exact-eval-and-oidc-live-gate.md) | exact-match eval과 OIDC live gate를 분리 | Accepted |

새 결정은 기존 번호를 바꾸지 않고 다음 번호로 추가합니다. 결정이 대체되면 원문을 삭제하지 않고 상태를 `Superseded by 000N`으로 변경합니다.
