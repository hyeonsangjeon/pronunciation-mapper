# 0001. 자유 rewrite 대신 bounded candidate agent 사용

- 상태: Accepted
- 결정일: 2026-07-16

## 배경

한국어 ASR 고유명사 정규화는 자유로운 문장 생성보다 DB vocabulary의 정확한 lexical match가 중요합니다. LLM이 replacement 문자열을 직접 만들면 식별자 훼손, vocabulary 밖 생성, 재현성 저하와 비용 증가가 발생합니다. 반대로 V1 발음 거리만으로는 문맥상 모호한 후보를 선택하거나 거부하기 어렵습니다.

## 결정

V1 휴리스틱을 deterministic candidate retrieval로 유지하고 각 span의 top-K 후보 ID만 model에 제공합니다. Model은 `replace`, `keep`, `abstain` 중 하나를 반환하며 replacement 문자열을 만들 수 없습니다. 로컬 validator가 schema, span, candidate ID, confidence와 DB vocabulary를 다시 검사합니다.

## 결과

- 자유 생성보다 모델 권한과 prompt surface가 작아집니다.
- exact alias는 network 호출 없이 결정됩니다.
- model 출력이 잘못돼도 vocabulary 밖 값은 적용되지 않습니다.
- candidate retrieval 품질이 상한이므로 대규모 vocabulary에서는 별도 인덱스가 필요합니다.
