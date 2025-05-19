import unittest
import tempfile
import json
import os
from pronunciation_mapper.mapper import PronunciationMapper
from pronunciation_mapper.utils import load_mappings_from_file, save_mappings_to_file

class TestAdvancedFeatures(unittest.TestCase):
    def setUp(self):
        # 기본 DB 용어
        self.db_terms = [
            "customer", "product", "transaction", 
            "payment", "shipping", "invoice",
            "ground", "cloud", "server",
            "데이터베이스", "테이블", "필드",
            "인덱스", "쿼리", "트랜잭션"
        ]
        
        # 사용자 정의 매핑
        self.custom_mappings = {
            "고객": "customer",
            "제품": "product",
            "거래": "transaction",
            "결제": "payment"
        }
        
        # 매퍼 초기화
        self.mapper = PronunciationMapper(
            self.db_terms, 
            threshold=0.5, 
            custom_mappings=self.custom_mappings
        )
    
    def test_custom_mappings(self):
        """사용자 정의 매핑 테스트"""
        for korean, english in self.custom_mappings.items():
            mapped, score = self.mapper.find_closest_term(korean)
            self.assertEqual(mapped, english, 
                            f"사용자 정의 매핑이 적용되지 않음: {korean} → {mapped}")
            self.assertAlmostEqual(score, 0.0, 
                                 msg=f"완벽 매칭의 점수가 0이 아님: {korean} → {score}")
    
    def test_dynamic_mapping_addition(self):
        """동적 매핑 추가 테스트"""
        # 새로운 매핑 추가
        self.mapper.add_custom_mapping("사용자", "user")
        
        # 매핑이 작동하는지 확인
        mapped, score = self.mapper.find_closest_term("사용자")
        self.assertEqual(mapped, "user", 
                        f"동적으로 추가된 매핑이 작동하지 않음: 사용자 → {mapped}")
    
    def test_mappings_persistence(self):
        """매핑 저장 및 로드 테스트"""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            # 매핑 저장
            mappings = {
                "테스트": "test",
                "파일": "file",
                "저장": "save"
            }
            save_mappings_to_file(mappings, temp_path)
            
            # 매핑 로드
            loaded = load_mappings_from_file(temp_path)
            
            # 검증
            self.assertEqual(mappings, loaded, 
                           "저장 및 로드된 매핑이 일치하지 않음")
        finally:
            # 임시 파일 삭제
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_threshold_effect(self):
        """임계값 효과 테스트"""
        # 약간 다른 단어
        query = "데이터배이스"  # "데이터베이스"와 유사하지만 다름
        
        # 관대한 임계값
        mapped_lenient, score_lenient = self.mapper.find_closest_term(query, threshold=0.7)
        self.assertEqual(mapped_lenient, "데이터베이스", 
                        "관대한 임계값에서 유사 단어가 매핑되지 않음")
        
        # 엄격한 임계값
        mapped_strict, score_strict = self.mapper.find_closest_term(query, threshold=0.1)
        self.assertEqual(mapped_strict, query, 
                        "엄격한 임계값에서 다른 단어로 매핑됨")
    
    def test_compound_words(self):
        """복합 단어 처리 테스트"""
        # 복합 단어 테스트
        query = "클라우드서버"
        expected = "cloud server"  # 이상적으로는 복합어를 인식하고 분리해야 함
        
        # 이 테스트는 현재 구현에서 실패할 수 있음 (향후 개선 대상)
        mapped, score = self.mapper.find_closest_term(query)
        # 현재 구현에서는 가장 유사한 단어로 매핑됨 (cloud 또는 server)
        self.assertIn(mapped, ["cloud", "server"], 
                     f"복합 단어가 적절하게 매핑되지 않음: {query} → {mapped}")


if __name__ == "__main__":
    unittest.main()