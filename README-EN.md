# Pronunciation Mapper

A Korean-English pronunciation similarity-based mapping system designed for **Query Rewriting to accurately match ASR (Automatic Speech Recognition) output with database terms**. Specifically optimized for **Lexical Search (keyword-based search) environments where exact keyword matching of proper nouns, technical terms, and database field names is essential**, with additional benefits for improving Semantic Search (vector search) performance.

![Python Version](https://img.shields.io/badge/python-3.6-blue.svg) ~ ![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Introduction

When querying databases through voice interfaces, mismatches between ASR output and structured data terminology can cause significant issues. This library uses **Query Rewriting techniques** to resolve inconsistencies such as:

- **STT Error Correction**: "트랜잭숑" → "transaction"
- **Korean-English Pronunciation Conversion**: "커스터머" → "customer"
- **Proper Noun Normalization**: "서비스어카운트" → "svc_accnt"
- **Abbreviation Expansion**: "디비" → "데이터베이스"

This enables **accurate keyword matching of proper nouns and technical terms in Lexical Search (BM25, TF-IDF, Elasticsearch, etc.)**, and additionally improves Semantic Search accuracy by normalizing queries during the embedding preprocessing stage.

### Query Rewriting and Search Performance Enhancement

#### Lexical Search (Keyword Search) - Primary Goal 🎯
```
Before: "커스터머 데이터" → No "customer" in DB → Search fails
After:  "customer 데이터" → "customer" exists in DB → Search succeeds
```
- **Specialized for proper nouns and technical terms requiring exact keyword matching**
- Guarantees accurate matching of database field names, service names, account IDs, etc.
- Perfect compatibility with keyword-based search engines like BM25, Elasticsearch, TF-IDF
- Examples: Searching for proper nouns like "account_no", "XPN36", "ST Corporation"

#### Semantic Search (Vector Search) - Additional Benefit
```
Before: "트랜잭숑 로그" → [embedding] → Less relevant results
After:  "transaction 로그" → [embedding] → Accurate results
```
- Embedding with correct terms improves vector similarity
- Prevents embedding quality degradation from typos or pronunciation errors

#### Hybrid Search
```
Lexical Search (70%) + Semantic Search (30%) weighted average
→ Query Rewriting significantly improves Lexical Search accuracy
```

### Key Features

- **Proper noun and technical term normalization**: Accurate keyword matching for Lexical Search
- Korean-English pronunciation similarity-based mapping
- Korean pronunciation analysis through jamo decomposition
- Similarity calculation using Levenshtein distance
- Automatic term conversion in sentences (Query Rewriting)
- User-defined mapping support
- Command-line interface

## Installation

```bash
# Install from source
git clone https://github.com/yourusername/pronunciation-mapper.git
cd pronunciation-mapper
pip install -e .
```

## Quick Start

### Basic Usage

Use PronunciationMapper as follows:

```python
from pronunciation_mapper import PronunciationMapper

# Define DB structured data terms (Lexical Search targets)
db_terms = [
    'customer', 'product', 'transaction',
    'payment', 'shipping', 'invoice',
    'ground',  'server',
    '데이터베이스', '테이블', '필드',
    '인덱스', '쿼리', 'svc66','log','account_no','account_id', '서버',
    'konlpy', 'XPN36', 'ST주식회사','KF주식회사','SF주식회사','SMTA','svc_accnt'
]

# Add custom vocabulary mappings from dictionary
custom_mappings = {
    # Korean voice initial output -> DB index dictionary proper noun mapping (Query Rewriting)
    '서비스어카운트': 'svc_accnt',
    '에스티주식회사':'ST주식회사',
    '어커운트넘버': 'account_no',
    '어카운트아이디': 'account_id',
    '어카아이디': 'account_id',
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

# Initialize mapper
mapper = PronunciationMapper(db_terms, custom_mappings=custom_mappings)

# Single term mapping (Query Rewriting)
result, score = mapper.find_closest_term("커스터머")

# Sentence mapping (Query Rewriting)
sentence = "그라운드에 있는 엑스피엔36 데이타배이스 써버의 트랜텍숑 로그를 확인해주세요. 서비스육십육 상품에서 삼백이십일번 트랜젝션 로그 찾아줘 어카운트넘버 사삼삼오삼칠 천국의계단. 나는 에스티주식회사 천만백부장이고 어카아이디는 아니아니 어카운트아이디는 공팔공팔팔이야"
mapped = mapper.map_sentence(sentence)
```

**Single Term Mapping Result:**
```
Mapping result: customer, proximity score: 0.0, similarity: 1.00
```

**Sentence Mapping Result:**
```
Initial STT output: 그라운드에 있는 엑스피엔36 데이타배이스 써버의 트랜텍숑 로그를 확인해주세요. 서비스육십육 상품에서 삼백이십일번 트랜젝션 로그 찾아줘 어카운트넘버 사삼삼오삼칠 천국의계단. 나는 에스티주식회사 천만백부장이고 어카아이디는 아니아니 어카운트아이디는 공팔공팔팔이야

After Query Rewriting: ground에 있는 XPN36 데이터베이스 server의 transaction 로그를 확인해주세요. 서비스육십육 상품에서 321번 transaction log 찾아줘 account_no 433537 천국의계단. 나는 ST주식회사 천만백부장이고 account_id는 아니아니 account_id는 080882야
```

### Command-Line Tool Usage

```bash
# Single word mapping
pronunciation-mapper map-word 커스터머
# Output: 커스터머 → customer (similarity: 1.00)

# Sentence mapping (Query Rewriting)
pronunciation-mapper map-sentence "그라운드에 있는 데이타베이스 확인"
# Output:
# Original: 그라운드에 있는 데이타베이스 확인
# After Query Rewriting: ground에 있는 데이터베이스 확인

# Add user mapping
pronunciation-mapper add-mapping 고객 customer --save
# Output: Mapping added: 고객 → customer
#         Mapping saved: /home/user/.pronunciation_mapper/mapping_cache.json
```

## How It Works

1. **Pronunciation Normalization**: Convert input words and DB terms to pronunciation form
   - Korean: Jamo decomposition (e.g., '안녕' → 'ㅇㅏㄴㄴㅕㅇ')
   - English: Korean pronunciation mapping (e.g., 'cloud' → 'ㅋㄹㅏㅜㄷ')

2. **Similarity Calculation**: Measure string similarity based on Levenshtein distance
   - Normalized distance = edit distance / max(len(s1), len(s2))

3. **Optimal Mapping Selection**: Choose the closest term with similarity above threshold

## RAG System Integration Example

### Proper Noun-Centric Lexical Search Pipeline

```python
from pronunciation_mapper import PronunciationMapper
from elasticsearch import Elasticsearch

# 1. Initialize Pronunciation Mapper (Query Rewriting)
db_terms = ["account_no", "account_id", "transaction", "XPN36", "svc_accnt"]
mapper = PronunciationMapper(db_terms, custom_mappings={
    "어카운트넘버": "account_no",
    "어카운트아이디": "account_id",
    "트랜잭션": "transaction",
    "엑스피엔36": "XPN36",
    "서비스어카운트": "svc_accnt"
})

# 2. User query (STT output) - with proper nouns
user_query = "엑스피엔36 서버에서 어카운트넘버 사삼삼오삼칠의 트랜잭숑 로그"

# 3. Apply Query Rewriting - normalize proper nouns
rewritten_query = mapper.map_sentence(user_query)
# Result: "XPN36 서버에서 account_no 433537의 transaction 로그"

# 4. Lexical Search (keyword search) - exact proper noun matching
es = Elasticsearch()
lexical_results = es.search(index="logs", body={
    "query": {
        "bool": {
            "must": [
                {"match": {"server_name": "XPN36"}},      # Exact server name
                {"match": {"account_no": "433537"}},      # Exact account number
                {"match": {"log_type": "transaction"}}    # Exact log type
            ]
        }
    }
})

# 5. Optional: Add Semantic Search (hybrid)
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()
vectorstore = FAISS.load_local("./vectorstore", embeddings)
semantic_results = vectorstore.similarity_search(rewritten_query, k=3)

# 6. Hybrid Search (Lexical priority)
# Lexical Search finds proper nouns accurately, Semantic Search supplements context
final_results = combine_results(
    lexical_results,    # 70% weight - proper noun matching
    semantic_results,   # 30% weight - semantic similarity
    weights=[0.7, 0.3]
)
```

### Lexical Search Performance Comparison (Proper Noun Search)

```python
# Without Query Rewriting - proper noun matching fails
query = "서비스어카운트 사삼삼오삼칠"
# Elasticsearch BM25 search → 0 results (keyword matching fails)
# Reason: Cannot find "svc_accnt" and "433537"

# With Query Rewriting - accurate proper noun matching
rewritten = mapper.map_sentence(query)  # "svc_accnt 433537"
# Elasticsearch BM25 search → 25 results (accurate keyword matching)
# Reason: Database field names and account numbers match exactly

# Real-world example: AWS monitoring
query = "엑스피엔36 써버 트랜잭숑 로그"
rewritten = "XPN36 server transaction log"
# → Accurately searches "XPN36" (server name), "transaction" (log type)
```

## Advanced Usage

### Adding Custom Mappings

```python
from pronunciation_mapper import PronunciationMapper

# Initial DB terms
db_terms = ["customer", "product", "database"]

# Custom mappings (Query Rewriting rules)
custom_mappings = {
    "고객": "customer",
    "제품": "product",
    "디비": "database"  # Handle abbreviation
}

# Initialize mapper (apply custom mappings)
mapper = PronunciationMapper(db_terms, custom_mappings=custom_mappings)

# Test mapping
result, score = mapper.find_closest_term("디비")
print(f"Mapping result: {result}, score: {score}")
# Output: Mapping result: database, score: 0.0
```

### Adjusting Threshold

```python
# Stricter matching (higher accuracy)
strict_match, score = mapper.find_closest_term("데이타베이스", threshold=0.3)

# More flexible matching (allow more variations)
flexible_match, score = mapper.find_closest_term("데이타베이스", threshold=0.7)
```

## ASR System Integration

The pronunciation mapper easily integrates with ASR systems to convert speech recognition results to accurate proper nouns and technical terms.

```python
# ASR result processing example (Query Rewriting) - proper noun focus
asr_result = "엑스피엔36 서버에서 어카운트넘버 사삼삼오삼칠 조회"
db_query = mapper.map_sentence(asr_result)
# Result: "XPN36 서버에서 account_no 433537 조회"

# Now proper nouns match exactly for Lexical Search
# 1. Lexical Search (primary):
#    - server_name = "XPN36" (exact server name)
#    - account_no = "433537" (exact account number)
# 2. Semantic Search (supplementary): embedding(db_query)
```

## Difference Between DB_TERMS and CUSTOM_MAPPINGS

### Quick Summary

- **DB_TERMS**: "What to find" - **target term list** (core search targets for Lexical Search)
- **CUSTOM_MAPPINGS**: "What to convert to what" - **Query Rewriting rules**

### Easy Analogy: Dictionary vs Directory

- **DB_TERMS** is like a **phone directory**:
  - List of people/companies that actually exist
  - These indexed terms are proper nouns in structured data (account numbers, server names, field names, etc.)
  - **Keywords that must be exactly matched in Lexical Search**

- **CUSTOM_MAPPINGS** is like a **translation dictionary**:
  - Query Rewriting rules saying "translate this word to that word"
  - Defines how to transform

### How It Actually Works

1. **DB_TERMS** (target term list - Lexical Search keywords):
   ```python
   db_terms = ["account_no", "XPN36", "transaction"]
   ```
   - List of 'official terms' the system can recognize and map
   - Final conversion results can only be terms in this list
   - "Proper nouns searchable in our database/system"
   - **Keywords that must be exactly matched in Lexical Search**

2. **CUSTOM_MAPPINGS** (Query Rewriting rules - proper noun conversion):
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
   - Defines which input word (STT output) converts to which official term (DB proper noun)
   - When word on left (key) appears, convert to right (value)
   - "Proper noun conversion rules"

### Relationship Between the Two

- **Core principle**: CUSTOM_MAPPINGS **values (right side) must be in DB_TERMS** to match in Lexical Search
- Example:
  ```python
  db_terms = ["account_no", "XPN36"]
  custom_mappings = {"어카운트넘버": "account_no", "서버이름": "server_name"}
  ```
  - "어카운트넘버" maps to "account_no" (success, "account_no" is in db_terms)
  - "서버이름" doesn't map to "server_name" (fail, "server_name" is not in db_terms)

### Clear Example: Database Search

Let's use a database account search scenario as analogy:

- **DB_TERMS** = Field names that actually exist in the database:
  ```
  1. account_no (account number)
  2. account_id (account ID)
  3. transaction (transaction history)
  ```

- **CUSTOM_MAPPINGS** = Rules to convert STT output to DB field names:
  ```
  "어카운트넘버" → "account_no"
  "어카운트아이디" → "account_id"
  "서버이름" → "server_name"
  ```

In this case:
- "어카운트넘버" converts to "account_no" (success: field exists in DB)
- "어카운트아이디" converts to "account_id" (success: field exists in DB)
- "서버이름" attempts to convert to "server_name" but fails (fail: "server_name" field doesn't exist in DB)

## API Documentation

### `PronunciationMapper` Class

#### `__init__(db_terms, threshold=None, custom_mappings=None)`
- **Parameters**:
  - `db_terms`: Database term list (list) - Lexical Search targets
  - `threshold`: Similarity threshold (default 0.6)
  - `custom_mappings`: User-defined mapping dictionary (dict) - Query Rewriting rules

#### `find_closest_term(query_term, threshold=None)`
- **Parameters**:
  - `query_term`: Input word to map (Query Rewriting target)
  - `threshold`: Similarity threshold (uses initialization value if not specified)
- **Returns**:
  - `(mapped_term, similarity_score)`: Tuple of mapped term and similarity score

#### `map_sentence(sentence)`
- **Parameters**:
  - `sentence`: Input sentence to map (Query Rewriting target)
- **Returns**:
  - Mapped sentence (string)

#### `add_custom_mapping(source_term, target_term)`
- **Parameters**:
  - `source_term`: Source word
  - `target_term`: Target word (DB term)
- **Returns**:
  - None

## Examples

See the [tests/](tests/) directory for sample examples.

## Contributing

1. Fork this repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add some amazing feature'`).
4. Push the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Required Packages

- Python 3.6+
- NumPy
- jamo (Korean jamo decomposition library)

---

This project was developed to facilitate seamless integration between ASR systems and databases.
**Through Query Rewriting**, it improves the accuracy of speech recognition results and serves as an essential preprocessing tool in **Lexical Search environments where proper nouns, technical terms, and database field names must be matched exactly**.

## Contact

For questions or feedback, please contact us through [GitHub Issues](https://github.com/hyeonsangjeon/pronunciation-mapper/issues).
