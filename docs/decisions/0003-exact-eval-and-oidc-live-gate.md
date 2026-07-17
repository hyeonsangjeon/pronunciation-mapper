# 0003. Exact-match eval과 OIDC live gate 분리

- 상태: Accepted
- 결정일: 2026-07-17

## 배경

이 도메인의 정답은 canonical DB term이므로 LLM judge보다 exact match가 직접적인 release signal입니다. 또한 provider 장애 뒤 heuristic fallback 결과가 우연히 정답이면 accuracy만으로는 live 연결 실패를 발견할 수 없습니다. 외부 tenant credential을 일반 PR CI에 노출해서도 안 됩니다.

## 결정

- 모든 PR에서 offline golden eval, Python matrix, wheel과 Pages 검증을 실행합니다.
- Foundry live 검증은 `workflow_dispatch`와 `foundry-external` Environment로 분리합니다.
- GitHub OIDC로 Azure에 로그인하고 API key/client secret을 저장하지 않습니다.
- Live gate는 exact accuracy뿐 아니라 fallback rate 0과 실제 provider 결과 1건 이상을 요구합니다.
- 임시 deployment cleanup은 명시적 입력, 동일한 테스트 대상, `ci-` prefix를 모두 만족할 때만 수행합니다.

## 결과

- PR CI는 외부 credential 없이 재현 가능합니다.
- provider outage가 heuristic fallback으로 숨겨지지 않습니다.
- GitHub Environment/FIC/RBAC는 코드와 별도인 운영 prerequisite입니다.
- Live report는 실행 commit, 입력 hash, 버전, credential 종류와 gate를 기록하되 endpoint·tenant는 저장하지 않습니다.
