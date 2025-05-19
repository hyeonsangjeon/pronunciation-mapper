from pronunciation_mapper import PronunciationMapper

# 초기화
# DB rows 추출 고유명사 추출값
db_terms = ["customer", "product", "ground", "데이터베이스"]

mapper = PronunciationMapper(db_terms)

# 단어 매핑 스왑
ins = "커스터머"
result, score = mapper.find_closest_term(ins)
print(f"매핑 결과: {result}, 오류 점수: {score}")
# 점수는 거리이므로 작을수록 유사도가 높음 (0이 완벽 일치)
print(f"{ins} → {result} (유사도: {1-score:.2f})")




# STT 오류 교정
ins = "데이타배이쓰"
result, score = mapper.find_closest_term(ins)
print(f"매핑 결과: {result}, 오류 점수: {score}")
# 점수는 거리이므로 작을수록 유사도가 높음 (0이 완벽 일치)
print(f"{ins} → {result} (유사도: {1-score:.2f})")



