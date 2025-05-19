#!/usr/bin/env python
"""
사용자 정의 매핑 예제
"""
from pronunciation_mapper import PronunciationMapper

# DB 용어 정의
db_terms = [
    "customer", "product", "transaction", 
    "user", "admin", "database", "server"
]

# 사용자 정의 매핑
custom_mappings = {
    "고객": "customer",
    "제품": "product",
    "거래": "transaction",
    "사용자": "user",
    "관리자": "admin",
    "디비": "database",  # 약어 처리
    "서버": "server"
}

# 매퍼 초기화 (사용자 정의 매핑 적용)
mapper = PronunciationMapper(db_terms, custom_mappings=custom_mappings)

# 매핑 테스트
test_terms = ["고객", "제품", "디비", "서버"]

print("=== 사용자 정의 매핑 테스트 ===")
for term in test_terms:
    mapped_term, score = mapper.find_closest_term(term)
    print(f"{term} → {mapped_term} (유사도: {1-score:.2f})")

# 매핑 추가
mapper.add_custom_mapping("시스템", "system")

# 추가된 매핑 테스트
mapped_term, score = mapper.find_closest_term("쉬스템")
print(f"\n추가 매핑 테스트: 쉬스템 → {mapped_term} (유사도: {1-score:.2f})")


# DB단어사전에 없는 명사 매핑 테스트
# 그대로 출력되어야함.
mapped_term, score = mapper.find_closest_term("시소라운드")
print(f"\n추가 매핑 테스트: 시소라운드 → {mapped_term} (유사도: {1-score:.2f})")
