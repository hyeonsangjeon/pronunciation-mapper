# Pronunciation Mapper

한국어 및 영어 단어 간 발음 유사도 기반 매핑 시스템으로, ASR(Automatic Speech Recognition) 출력 결과를 데이터베이스 용어와 정확히 매칭하기 위한 도구입니다.

![Python Version](https://img.shields.io/badge/python-3.6-blue.svg) ~ ![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 소개

음성 인터페이스를 통해 데이터베이스에 질의할 때, ASR 결과물과 정형데이터의 용어 사이의 불일치는 큰 문제가 될 수 있습니다. 이 라이브러리는 이러한 불일치를 해소하기 위해 [DB_TERM_MAPPINGS]설정에 따라 발음 유사도를 기반으로 ASR 출력의 전사처리(예: "커스터머")을 고유명사 용어(예: "customer") 또는, 정확하지 않은 STT출력을 교정(예: "트랜잭숑"-->"트랜잭션" or "transaction")하는 로 매핑하는 솔루션을 제공합니다.

### 주요 기능

- 한국어-영어 간 발음 유사도 기반 매핑
- 자모 분리를 통한 한글 발음 분석
- Levenshtein 거리를 활용한 유사도 계산
- 문장 내 용어 자동 변환 지원
- 사용자 정의 매핑 추가 기능
- 명령행 인터페이스 제공

## 설치

```bash
# 소스에서 설치
git clone https://github.com/yourusername/pronunciation-mapper.git
cd pronunciation-mapper
pip install -e .
```

## 빠른 시작

### 기본 사용법

```python
from pronunciation_mapper import PronunciationMapper

# DB 정형데이터 용어 정의
db_terms = ["customer", "product", "transaction", "ground"]

# 매퍼 초기화
mapper = PronunciationMapper(db_terms)

# 단일 용어 매핑
result, score = mapper.find_closest_term("커스터머")
print(f"매핑 결과: {result}, 점수: {score}")
# 출력: 매핑 결과: customer, 점수: 0.0

# 문장 매핑
sentence = "그라운드에 있는 엑스피엔36 데이타배이스 써버의 트랜텍숑 로그를 확인해주세요. 서비스육십육 상품에서 삼백이십일번 트랜젝션 로그 찾아줘 어카운트넘버 사삼삼오삼칠 천국의계단. 나는 에스티주식회사 천만백부장이고 어카아이디는 아니아니 어카운트아이디는 공팔공팔팔이야"
mapped = mapper.map_sentence(sentence)
print(f"매핑된 문장: {mapped}")
# 출력: 매핑된 문장: ground에 있는 XPN36 데이터베이스 server의 transaction 로그를 확인해주세요. 서비스육십육 상품에서 321번 transaction log 찾아줘 account_no 433537 천국의계단. 나는 ST주식회사 천만백부장이고 account_id는 아니아니 account_id는 080882야
```

### 명령행 도구로 사용

```bash
# 단일 단어 매핑
pronunciation-mapper map-word 커스터머
# 출력: 커스터머 → customer (유사도: 1.00)

# 문장 매핑
pronunciation-mapper map-sentence "그라운드에 있는 데이타베이스 확인"
# 출력:
# 원문: 그라운드에 있는 데이타베이스 확인
# 매핑: ground에 있는 데이터베이스 확인

# 사용자 매핑 추가
pronunciation-mapper add-mapping 고객 customer --save
# 출력: 매핑 추가: 고객 → customer
#       매핑이 저장됨: /home/user/.pronunciation_mapper/mapping_cache.json
```

## 작동 원리

1. **발음 정규화**: 입력 단어와 DB 용어를 발음 형태로 변환
   - 한글: 자모 분리 (예: '안녕' → 'ㅇㅏㄴㄴㅕㅇ')
   - 영어: 한글 발음 매핑 (예: 'cloud' → 'ㅋㄹㅏㅜㄷ')

2. **유사도 계산**: Levenshtein 거리 기반 문자열 유사도 측정
   - 정규화된 거리 = 편집 거리 / max(len(s1), len(s2))

3. **최적 매핑 선택**: 임계값 이상의 유사도를 가진 가장 가까운 용어 선택

## 고급 사용법

### 사용자 정의 매핑 추가

```python
from pronunciation_mapper import PronunciationMapper

# 초기 DB 용어
db_terms = ["customer", "product", "database"]

# 사용자 정의 매핑
custom_mappings = {
    "고객": "customer",
    "제품": "product",
    "디비": "database"  # 약어 처리
}

# 매퍼 초기화 (사용자 정의 매핑 적용)
mapper = PronunciationMapper(db_terms, custom_mappings=custom_mappings)

# 매핑 테스트
result, score = mapper.find_closest_term("디비")
print(f"매핑 결과: {result}, 점수: {score}")
# 출력: 매핑 결과: database, 점수: 0.0
```

### 임계값 조정

```python
# 더 엄격한 매핑 (높은 정확도)
strict_match, score = mapper.find_closest_term("데이타베이스", threshold=0.3)

# 더 관대한 매핑 (다양한 변형 허용)
flexible_match, score = mapper.find_closest_term("데이타베이스", threshold=0.7)
```

## ASR 시스템과의 통합

발음 매퍼는 ASR 시스템과 쉽게 통합하여 음성 인식 결과를 데이터베이스 질의에 적합하게 변환할 수 있습니다.

```python
# ASR 결과 처리 예시
asr_result = "그라운드 서버에 있는 커스터머 데이터 조회해줘"
db_query = mapper.map_sentence(asr_result)
# 결과: "ground server에 있는 customer 데이터 조회해줘"

# 이제 이 결과를 구문 분석하여 실제 DB 쿼리로 변환할 수 있습니다
```

## DB_TERMS와 CUSTOM_MAPPINGS의 차이점

### 간단히 요약

- **DB_TERMS**: "무엇을 찾을지"를 정의하는 **목표 용어 목록**
- **CUSTOM_MAPPINGS**: "무엇을 무엇으로 변환할지"를 정의하는 **변환 규칙**

### 알기 쉬운 비유: 번역사전과 전화번호부

- **DB_TERMS**는 **전화번호부**와 같습니다:
  - 실제로 존재하는 사람/회사의 목록
  - 이 목록에 있는 용어만 찾을 수 있음

- **CUSTOM_MAPPINGS**는 **번역사전**과 같습니다:
  - "이 단어는 저 단어로 번역해라"라는 규칙 
  - 어떻게 변환할지 정의

### 실제 작동 방식

1. **DB_TERMS** (목표 용어 목록):
   ```python
   db_terms = ["customer", "product", "server"]
   ```
   - 시스템이 인식하고 매핑할 수 있는 '공식 용어' 목록
   - 최종적으로 변환되는 결과는 이 목록에 있는 용어만 가능
   - "우리 시스템이 이해하는 언어"

2. **CUSTOM_MAPPINGS** (변환 규칙):
   ```python
   custom_mappings = {
     "고객": "customer",    # 입력 → 출력
     "제품": "product",
     "서버": "server"
   }
   ```
   - 입력 단어를 어떤 공식 용어로 바꿀지 정의
   - 왼쪽(키)에 있는 단어가 들어오면 오른쪽(값)으로 변환
   - "번역 규칙"

### 두 요소의 관계

- **핵심 원칙**: CUSTOM_MAPPINGS의 **값(오른쪽)이 DB_TERMS에 있어야** 매핑이 작동함
- 예시:
  ```python
  db_terms = ["customer", "product"]
  custom_mappings = {"고객": "customer", "유저": "user"}
  ```
  - "고객"은 "customer"로 매핑됨 (성공, "customer"가 db_terms에 있음)
  - "유저"는 "user"로 매핑되지 않음 (실패, "user"가 db_terms에 없음)

### 명확한 예시: 메뉴판과 주문 번역

식당에서 메뉴를 주문하는 상황으로 비유해 볼게요:

- **DB_TERMS** = 실제 메뉴판에 있는 음식 목록:
  ```
  1. 햄버거
  2. 피자
  3. 파스타
  ```

- **CUSTOM_MAPPINGS** = 외국어-한국어 주문 변환 규칙:
  ```
  "burger" → "햄버거"
  "pizza" → "피자" 
  "noodle" → "라면"
  ```

이 경우:
- "burger"는 "햄버거"로 변환됨 (성공: 메뉴판에 있음)
- "pizza"는 "피자"로 변환됨 (성공: 메뉴판에 있음)
- "noodle"은 "라면"으로 변환 시도하지만 실패 (실패: "라면"이 메뉴판에 없음)

## API 문서

### `PronunciationMapper` 클래스

#### `__init__(db_terms, threshold=None, custom_mappings=None)`
- **매개변수**: 
  - `db_terms`: 데이터베이스 용어 목록 (리스트)
  - `threshold`: 유사도 임계값 (기본값 0.6)
  - `custom_mappings`: 사용자 정의 매핑 사전 (딕셔너리)

#### `find_closest_term(query_term, threshold=None)`
- **매개변수**: 
  - `query_term`: 매핑할 입력 단어
  - `threshold`: 유사도 임계값 (지정하지 않으면 초기화 시 값 사용)
- **반환값**: 
  - `(mapped_term, similarity_score)`: 매핑된 용어와 유사도 점수 튜플

#### `map_sentence(sentence)`
- **매개변수**: 
  - `sentence`: 매핑할 입력 문장
- **반환값**: 
  - 매핑된 문장 (문자열)

#### `add_custom_mapping(source_term, target_term)`
- **매개변수**: 
  - `source_term`: 원본 단어
  - `target_term`: 대상 단어 (DB 용어)
- **반환값**: 
  - 없음

## 예제

더 많은 예제는 [examples/](examples/) 디렉토리를 참조하세요.

## 기여하기

1. 이 저장소를 포크합니다.
2. 새로운 기능 브랜치를 만듭니다 (`git checkout -b feature/amazing-feature`).
3. 변경 사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`).
4. 브랜치를 푸시합니다 (`git push origin feature/amazing-feature`).
5. Pull Request를 엽니다.

## 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. [LICENSE](LICENSE) 파일을 참조하세요.

## 필수 패키지

- Python 3.6+
- NumPy
- jamo (한글 자모 분리 라이브러리)

---

이 프로젝트는 ASR 시스템과 데이터베이스의 통합을 원활하게 하기 위해 개발되었습니다. 
음성 인식 결과의 정확도를 향상시키고 일관된 데이터베이스 용어 사용을 가능하게 합니다.

## 연락처

질문이나 피드백이 있으시면 [GitHub 이슈](https://github.com/yourusername/pronunciation-mapper/issues)를 통해 문의해주세요.