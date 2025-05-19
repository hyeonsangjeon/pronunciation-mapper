import unittest
from pronunciation_mapper.mapper import PronunciationMapper

class TestPronunciationMapper(unittest.TestCase):
    def setUp(self):
        # 테스트용 데이터베이스 용어 샘플
        self.db_terms = [
            "customer", "product", "transaction", 
            "payment", "shipping", "invoice",
            "ground", "cloud", "server",
            "데이터베이스", "테이블", "필드",
            "인덱스", "쿼리", "트랜잭션"
        ]
        
        # 매퍼 초기화
        self.mapper = PronunciationMapper(self.db_terms)
    
    def test_korean_to_english_mapping(self):
        """한글 -> 영어 매핑 테스트"""
        test_cases = [
            ("커스터머", "customer"),
            ("프로덕트", "product"),
            ("트랜잭션", "transaction"),
            ("페이먼트", "payment"),
            ("쉬핑", "shipping"),
            ("인보이스", "invoice"),
            ("그라운드", "ground"),
            ("클라우드", "cloud"),
            ("서버", "server")
        ]
        
        for input_term, expected_term in test_cases:
            mapped_term, score = self.mapper.find_closest_term(input_term)
            self.assertEqual(mapped_term, expected_term, 
                            f"Expected '{input_term}' to map to '{expected_term}', but got '{mapped_term}'")
    
    def test_korean_to_korean_mapping(self):
        """한글 -> 한글 매핑 테스트 (약간의 차이가 있는 경우)"""
        test_cases = [
            ("데이타베이스", "데이터베이스")
        ]
        
        for input_term, expected_term in test_cases:
            mapped_term, score = self.mapper.find_closest_term(input_term)
            self.assertEqual(mapped_term, expected_term,
                            f"Expected '{input_term}' to map to '{expected_term}', but got '{mapped_term}'")
    
    def test_sentence_mapping(self):
        """문장 매핑 테스트"""
        test_sentence = "그라운드에 있는 데이타베이스 서버의 트랜잭션 로그를 확인해주세요"
        expected_sentence = "ground에 있는 데이터베이스 server의 transaction 로그를 확인해주세요"
        
        mapped_sentence = self.mapper.map_sentence(test_sentence)
        self.assertEqual(mapped_sentence, expected_sentence,
                        f"Sentence mapping didn't produce expected result")

if __name__ == "__main__":
    unittest.main()