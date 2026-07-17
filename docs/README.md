# 문서와 기록 안내

이 디렉터리는 사용법, 설계 결정, 운영 설정, 릴리스 증빙을 구분해 보관합니다.

## 사용자 문서

- [GitHub Pages 사용 매뉴얼](index.html): 설치, provider 선택, Python/CLI 사용법, 운영 명령
- [한국어 README](../README.md): 전체 기능과 빠른 시작
- [English README](../README-EN.md): compact English quick start

## 설계와 운영

- [V2 아키텍처 결정 기록](V2_ARCHITECTURE.md): bounded agent 구조, provider 선택, guardrail, 평가 전략
- [아키텍처 결정 기록 index](decisions/README.md): 구조를 선택한 이유와 결과
- [GitHub Actions와 external-tenant Foundry 설정](CI_SETUP.md): OIDC, Environment, RBAC, live workflow
- [PyPI 릴리스 운영](PYPI_RELEASE.md): Trusted Publisher, OIDC publish workflow, 첫 게시와 복구 절차

## 변경과 릴리스

- [CHANGELOG](../CHANGELOG.md): 버전별 사용자 영향 변경
- [V2.0.1 릴리스 기록](releases/v2.0.1.md): 패치 범위, 소스 감사, 검증 증빙, 게시 체크리스트
- [V2.0.0 릴리스 기록](releases/v2.0.0.md): V2 최초 구현 범위와 첫 PyPI 게시 증빙

## 평가 자산

- [Golden cases](../evals/cases.jsonl): 입력과 기대 rewrite
- [Canonical vocabulary](../evals/vocabulary.json): 평가 대상 DB term과 mapping
- [Evaluation runner](../evals/run_v2.py): offline, Foundry, Ollama 공통 측정

생성된 `evals/results/*.json`은 로컬·CI 산출물이므로 Git에 커밋하지 않습니다. 재현 가능한 입력, runner, release gate만 버전 관리하고 실행 결과는 CI artifact 또는 릴리스 기록의 요약값으로 보존합니다.
