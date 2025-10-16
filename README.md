# Pronunciation Mapper

한국어 및 영어 단어 간 발음 유사도 기반 매핑 시스템으로, **Query Rewriting을 통해 ASR(Automatic Speech Recognition) 출력 결과를 데이터베이스 용어와 정확히 매칭**하기 위한 도구입니다. 특히 **고유명사, 기술 용어, 데이터베이스 필드명 등 정확한 키워드 매칭이 필수적인 Lexical Search(키워드 검색)** 환경을 위해 설계되었으며, 부가적으로 Semantic Search(벡터 검색) 성능도 향상시킵니다.

![Python Version](https://img.shields.io/badge/python-3.6-blue.svg) ~ ![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 소개

음성 인터페이스를 통해 데이터베이스에 질의할 때, ASR 결과물과 정형데이터의 용어 사이의 불일치는 큰 문제가 될 수 있습니다. 이 라이브러리는 **Query Rewriting 기법**을 활용하여 다음과 같은 불일치를 해소합니다:

- **STT 오류 교정**: "트랜잭숑" → "transaction"
- **한영 발음 변환**: "커스터머" → "customer" 
- **고유명사 정규화**: "서비스어카운트" → "svc_accnt"
- **약어 확장**: "디비" → "데이터베이스"

이를 통해 **Lexical Search(BM25, TF-IDF, Elasticsearch 등)에서 고유명사와 기술 용어의 정확한 키워드 매칭**을 가능하게 하며, 부가적으로 임베딩 전처리 단계에서 쿼리를 정규화하여 Semantic Search의 정확도도 향상시킵니다.

### Query Rewriting과 검색 성능 향상

#### Lexical Search (키워드 검색) - 주 목적 🎯
```
Before: "커스터머 데이터" → DB에 "customer" 없음 → 검색 실패
After:  "customer 데이터" → DB에 "customer" 있음 → 검색 성공
```
- **정확한 키워드 매칭이 필수**인 고유명사, 기술 용어에 특화
- 데이터베이스 필드명, 서비스명, 계정ID 등의 정확한 매칭 보장
- BM25, Elasticsearch, TF-IDF 등 키워드 기반 검색 엔진과의 완벽한 호환
- 예: "account_no", "XPN36", "ST주식회사" 같은 고유명사 검색

#### Semantic Search (벡터 검색) - 부가 효과
```
Before: "트랜잭숑 로그" → [임베딩] → 관련성 낮은 결과
After:  "transaction 로그" → [임베딩] → 정확한 결과
```
- 올바른 용어로 변환 후 임베딩하면 벡터 유사도 향상
- 오타나 발음 표기 오류로 인한 임베딩 품질 저하 방지

#### Hybrid Search (하이브리드 검색)
```
Lexical Search (70%) + Semantic Search (30%) 가중 평균
→ Query Rewriting으로 Lexical Search 정확도 크게 향상
```

### 주요 기능

- **고유명사 및 기술 용어 정규화**: Lexical Search를 위한 정확한 키워드 매칭
- 한국어-영어 간 발음 유사도 기반 매핑
- 자모 분리를 통한 한글 발음 분석
- Levenshtein 거리를 활용한 유사도 계산
- 문장 내 용어 자동 변환 지원 (Query Rewriting)
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

다음과 같이 PronunciationMapper를 사용할 수 있습니다:

```python
from pronunciation_mapper import PronunciationMapper

# DB 정형데이터 용어 정의 (Lexical Search 대상)
db_terms = [
    'customer', 'product', 'transaction', 
    'payment', 'shipping', 'invoice',
    'ground',  'server',
    '데이터베이스', '테이블', '필드',
    '인덱스', '쿼리', 'svc66','log','account_no','account_id' ,'서버', 'konlpy', 'XPN36', 'ST주식회사','KF주식회사','SF주식회사','SMTA','svc_accnt'
]

# 단어사전에서 사용자 정의 Custom Vocabulary 대응 매핑 추가
custom_mappings = {
    # 한글 음성 초기 출력 -> DB인덱스 사전의 고유명사 매핑 (Query Rewriting)
    '서비스어카운트': 'svc_accnt',          
    '에스티주식회사':'ST주식회사',
    '어커운트넘버': 'account_no', 
    '어카운트아이디': 'account_id',
    '어카아이디 ': 'account_id',
    '트랜잭션': 'transaction',
    '페이먼트': 'payment',
    '쉬핑': 'shipping',
    '인보이스': 'invoice',
    '그라운드': 'ground',
    '클라우드': 'cloud',
    '서버': 'server',    
    '엑스피엔36': 'XPN36',
    '엑스피엔삼심육': 'XPN36',
    '케이에프주식회사':'KF주식회사'
}

# 매퍼 초기화
mapper = PronunciationMapper(db_terms,  custom_mappings=custom_mappings)


# 단일 용어 매핑 (Query Rewriting)
result, score = mapper.find_closest_term("커스터머")

# 문장 매핑 (Query Rewriting)
sentence = "그라운드에 있는 엑스피엔36 데이타배이스 써버의 트랜텍숑 로그를 확인해주세요. 서비스육십육 상품에서 삼백이십일번 트랜젝션 로그 찾아줘 어카운트넘버 사삼삼오삼칠 천국의계단. 나는 에스티주식회사 천만백부장이고 어카아이디는 아니아니 어카운트아이디는 공팔공팔팔이야"
mapped = mapper.map_sentence(sentence)
```

**단일 용어 매핑 결과:**
```
매핑 결과: customer, 근접 점수: 0.0, 유사도: 1.00
```

**문장 매핑 결과:**
```
STT 초기 출력 문장: 그라운드에 있는 엑스피엔36 데이타배이스 써버의 트랜텍숑 로그를 확인해주세요. 서비스육십육 상품에서 삼백이십일번 트랜젝션 로그 찾아줘 어카운트넘버 사삼삼오삼칠 천국의계단. 나는 에스티주식회사 천만백부장이고 어카아이디는 아니아니 어카운트아이디는 공팔공팔팔이야

Query Rewriting 후: ground에 있는 XPN36 데이터베이스 server의 transaction 로그를 확인해주세요. 서비스육십육 상품에서 321번 transaction log 찾아줘 account_no 433537 천국의계단. 나는 ST주식회사 천만백부장이고 account_id는 아니아니 account_id는 080882야
```


### 명령행 도구로 사용

```bash
# 단일 단어 매핑
pronunciation-mapper map-word 커스터머
# 출력: 커스터머 → customer (유사도: 1.00)

# 문장 매핑 (Query Rewriting)
pronunciation-mapper map-sentence "그라운드에 있는 데이타베이스 확인"
# 출력:
# 원문: 그라운드에 있는 데이타베이스 확인
# Query Rewriting 후: ground에 있는 데이터베이스 확인

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

## RAG 시스템 통합 예시

### 고유명사 중심의 Lexical Search 파이프라인

```python
from pronunciation_mapper import PronunciationMapper
from elasticsearch import Elasticsearch

# 1. Pronunciation Mapper 초기化 (Query Rewriting)
db_terms = ["account_no", "account_id", "transaction", "XPN36", "svc_accnt"]
mapper = PronunciationMapper(db_terms, custom_mappings={
    "어카운트넘버": "account_no",
    "어카운트아이디": "account_id",
    "트랜잭션": "transaction",
    "엑스피엔36": "XPN36",
    "서비스어카운트": "svc_accnt"
})

# 2. 사용자 쿼리 (STT 출력) - 고유명사 포함
user_query = "엑스피엔36 서버에서 어카운트넘버 사삼삼오삼칠의 트랜잭숑 로그"

# 3. Query Rewriting 적용 - 고유명사 정규화
rewritten_query = mapper.map_sentence(user_query)
# 결과: "XPN36 서버에서 account_no 433537의 transaction 로그"

# 4. Lexical Search (키워드 검색) - 정확한 고유명사 매칭
es = Elasticsearch()
lexical_results = es.search(index="logs", body={
    "query": {
        "bool": {
            "must": [
                {"match": {"server_name": "XPN36"}},      # 정확한 서버명
                {"match": {"account_no": "433537"}},      # 정확한 계정번호
                {"match": {"log_type": "transaction"}}    # 정확한 로그타입
            ]
        }
    }
})

# 5. 선택적: Semantic Search 추가 (하이브리드)
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()
vectorstore = FAISS.load_local("./vectorstore", embeddings)
semantic_results = vectorstore.similarity_search(rewritten_query, k=3)

# 6. Hybrid Search (Lexical 우선)
# Lexical Search가 고유명사를 정확히 찾고, Semantic Search가 맥락 보완
final_results = combine_results(
    lexical_results,    # 70% 가중치 - 고유명사 매칭
    semantic_results,   # 30% 가중치 - 의미 유사도
    weights=[0.7, 0.3]
)
```

### Lexical Search 성능 비교 (고유명사 검색)

```python
# Query Rewriting 없이 - 고유명사 매칭 실패
query = "서비스어카운트 사삼삼오삼칠"
# Elasticsearch BM25 검색 → 0건 (키워드 매칭 실패)
# 이유: "svc_accnt"와 "433537"을 찾을 수 없음

# Query Rewriting 적용 - 정확한 고유명사 매칭
rewritten = mapper.map_sentence(query)  # "svc_accnt 433537"
# Elasticsearch BM25 검색 → 25건 (정확한 키워드 매칭)
# 이유: 데이터베이스 필드명과 계정번호가 정확히 매칭됨

# 실무 예시: AWS 모니터링
query = "엑스피엔36 써버 트랜잭숑 로그"
rewritten = "XPN36 server transaction log"
# → "XPN36"(서버명), "transaction"(로그타입) 정확히 검색
```

## 고급 사용법

### 사용자 정의 매핑 추가

```python
from pronunciation_mapper import PronunciationMapper

# 초기 DB 용어
db_terms = ["customer", "product", "database"]

# 사용자 정의 매핑 (Query Rewriting 규칙)
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

발음 매퍼는 ASR 시스템과 쉽게 통합하여 음성 인식 결과를 정확한 고유명사와 기술 용어로 변환합니다.

```python
# ASR 결과 처리 예시 (Query Rewriting) - 고유명사 중심
asr_result = "엑스피엔36 서버에서 어카운트넘버 사삼삼오삼칠 조회"
db_query = mapper.map_sentence(asr_result)
# 결과: "XPN36 서버에서 account_no 433537 조회"

# 이제 고유명사가 정확히 매칭되어 Lexical Search 가능
# 1. Lexical Search (주요): 
#    - server_name = "XPN36" (정확한 서버명)
#    - account_no = "433537" (정확한 계정번호)
# 2. Semantic Search (보조): embedding(db_query)
```

## DB_TERMS와 CUSTOM_MAPPINGS의 차이점

### 간단히 요약

- **DB_TERMS**: "무엇을 찾을지"를 정의하는 **목표 용어 목록** (Lexical Search의 핵심 검색 대상)
- **CUSTOM_MAPPINGS**: "무엇을 무엇으로 변환할지"를 정의하는 **Query Rewriting 규칙**

### 알기 쉬운 비유: 번역사전과 전화번호부

- **DB_TERMS**는 **전화번호부**와 같습니다:
  - 실제로 존재하는 사람/회사의 목록
  - 이 인덱스 목록에 있는 용어는 정형데이터의 고유 명사들 (계정번호, 서버명, 필드명 등)
  - **Lexical Search에서 정확히 매칭되어야 하는 키워드**

- **CUSTOM_MAPPINGS**는 **번역사전**과 같습니다:
  - "이 단어는 저 단어로 번역해라"라는 Query Rewriting 규칙
  - 어떻게 변환할지 정의

### 실제 작동 방식

1. **DB_TERMS** (목표 용어 목록 - Lexical Search 키워드):
   ```python
   db_terms = ["account_no", "XPN36", "transaction"]
   ```
   - 시스템이 인식하고 매핑할 수 있는 '공식 용어' 목록
   - 최종적으로 변환되는 결과는 이 목록에 있는 용어만 가능
   - "우리 데이터베이스/시스템에서 검색 가능한 고유명사"
   - **Lexical Search에서 정확히 매칭되어야 하는 키워드**

2. **CUSTOM_MAPPINGS** (Query Rewriting 규칙 - 고유명사 변환):
   ```python
   custom_mappings = {
     "어카운트넘버": "account_no",
     "엑스피엔36": "XPN36",
     "엑스피엔삼심육": "XPN36",
     "트랜잭션": "transaction",
     "트랜젝션": "transaction",
     "서비스어카운트": "svc_accnt"
   }
   ```
   - 입력 단어(STT 출력)를 어떤 공식 용어(DB 고유명사)로 바꿀지 정의
   - 왼쪽(키)에 있는 단어가 들어오면 오른쪽(값)으로 변환
   - "고유명사 변환 규칙"

### 두 요소의 관계

- **핵심 원칙**: CUSTOM_MAPPINGS의 **값(오른쪽)이 DB_TERMS에 있어야** Lexical Search에서 매칭됨
- 예시:
  ```python
  db_terms = ["account_no", "XPN36"]
  custom_mappings = {"어카운트넘버": "account_no", "서버이름": "server_name"}
  ```
  - "어카운트넘버"는 "account_no"로 매핑됨 (성공, "account_no"가 db_terms에 있음)
  - "서버이름"은 "server_name"로 매핑되지 않음 (실패, "server_name"이 db_terms에 없음)

### 명확한 예시: 데이터베이스 검색

데이터베이스에서 계정을 검색하는 상황으로 비유해 볼게요:

- **DB_TERMS** = 데이터베이스에 실제로 존재하는 필드명 목록:
  ```
  1. account_no (계정번호)
  2. account_id (계정ID)
  3. transaction (거래내역)
  ```

- **CUSTOM_MAPPINGS** = STT 출력을 DB 필드명으로 변환하는 규칙:
  ```
  "어카운트넘버" → "account_no"
  "어카운트아이디" → "account_id" 
  "서버이름" → "server_name"
  ```

이 경우:
- "어카운트넘버"는 "account_no"로 변환됨 (성공: DB에 필드 존재)
- "어카운트아이디"는 "account_id"로 변환됨 (성공: DB에 필드 존재)
- "서버이름"은 "server_name"로 변환 시도하지만 실패 (실패: "server_name" 필드가 DB에 없음)

## API 문서

### `PronunciationMapper` 클래스

#### `__init__(db_terms, threshold=None, custom_mappings=None)`
- **매개변수**: 
  - `db_terms`: 데이터베이스 용어 목록 (리스트) - Lexical Search 대상
  - `threshold`: 유사도 임계값 (기본값 0.6)
  - `custom_mappings`: 사용자 정의 매핑 사전 (딕셔너리) - Query Rewriting 규칙

#### `find_closest_term(query_term, threshold=None)`
- **매개변수**: 
  - `query_term`: 매핑할 입력 단어 (Query Rewriting 대상)
  - `threshold`: 유사도 임계값 (지정하지 않으면 초기화 시 값 사용)
- **반환값**: 
  - `(mapped_term, similarity_score)`: 매핑된 용어와 유사도 점수 튜플

#### `map_sentence(sentence)`
- **매개변수**: 
  - `sentence`: 매핑할 입력 문장 (Query Rewriting 대상)
- **반환값**: 
  - 매핑된 문장 (문자열)

#### `add_custom_mapping(source_term, target_term)`
- **매개변수**: 
  - `source_term`: 원본 단어
  - `target_term`: 대상 단어 (DB 용어)
- **반환값**: 
  - 없음

## 예제

샘플 예제는 [tests/](tests/) 디렉토리를 참조하세요.

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
**Query Rewriting을 통해** 음성 인식 결과의 정확도를 향상시키고, 특히 **고유명사, 기술 용어, 데이터베이스 필드명 등이 정확히 매칭되어야 하는 Lexical Search 환경**에서 필수적인 전처리 도구로 활용됩니다.

## 연락처

질문이나 피드백이 있으시면 [GitHub 이슈](https://github.com/hyeonsangjeon/pronunciation-mapper/issues)를 통해 문의해주세요.
