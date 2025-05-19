import numpy as np
import re
from jamo import h2j, j2hcj
from .config import DEFAULT_THRESHOLD, ENG_TO_KOR_SOUNDS, DB_TERM_MAPPINGS, PRONUNCIATION_RULES

class PronunciationMapper:
    def __init__(self, db_terms, threshold=None, custom_mappings=None):
        """
        db_terms: 데이터베이스 용어 목록
        threshold: 유사도 임계값 (기본값은 설정 파일에서 로드)
        custom_mappings: 사용자 정의 매핑 (기본 매핑에 추가됨)
        """
        self.db_terms = db_terms
        self.threshold = threshold if threshold is not None else DEFAULT_THRESHOLD
        
        # 기본 매핑 로드
        self.eng_to_kor_sounds = ENG_TO_KOR_SOUNDS.copy()
        self.term_mappings = DB_TERM_MAPPINGS.copy()
        
        # 사용자 정의 매핑 처리
        if custom_mappings:
            # 매핑 방향 유지 (한글->영어 또는 영어->한글)
            for source, target in custom_mappings.items():
                # 기존 매핑에 추가
                self.term_mappings[source] = target
                
                # target이 DB 용어 목록에 있는 경우 역방향 매핑도 추가
                if target in self.db_terms and source not in self.term_mappings:
                    # 중복되지 않게 역방향 추가
                    self.term_mappings[target] = source
        
        # DB 용어에 있는 모든 단어에 대한 역방향 매핑 구성
        self._build_bidirectional_mappings()
        
        # 발음 규칙
        self.pronunciation_rules = PRONUNCIATION_RULES['korean']
        
        # 사전 계산된 DB 용어 발음 사전 구축
        self.db_term_pronunciations = {}
        for term in db_terms:
            self.db_term_pronunciations[term] = self._get_normalized_pronunciation(term)
    

    def _build_bidirectional_mappings(self):
        """양방향 매핑을 구성합니다"""
        # 한글-영어 매핑을 기반으로 역방향 매핑 구성
        kor_to_eng_mappings = {}
        eng_to_kor_mappings = {}
        
        # 기존 매핑 분류
        for source, target in self.term_mappings.items():
            # 한글 -> 영어 매핑인 경우
            if (any('\uAC00' <= c <= '\uD7A3' for c in source) and 
                target in self.db_terms and 
                not any('\uAC00' <= c <= '\uD7A3' for c in target)):
                kor_to_eng_mappings[source] = target
            # 영어 -> 한글 매핑인 경우
            elif (source in self.db_terms and 
                any('\uAC00' <= c <= '\uD7A3' for c in target) and 
                not any('\uAC00' <= c <= '\uD7A3' for c in source)):
                eng_to_kor_mappings[source] = target
        
        # 누락된 역방향 매핑 추가
        for kor, eng in kor_to_eng_mappings.items():
            if eng not in self.term_mappings:
                self.term_mappings[eng] = kor
        
        for eng, kor in eng_to_kor_mappings.items():
            if kor not in self.term_mappings:
                self.term_mappings[kor] = eng


    def _get_normalized_pronunciation(self, word):
        """단어를 정규화된 발음으로 변환"""
        # 직접 매핑이 있는 경우 매핑된 발음 사용
        if word in self.term_mappings:
            return self._get_pronunciation(self.term_mappings[word])
        
        return self._get_pronunciation(word)
    
    def _get_pronunciation(self, word):
        """단어를 음소로 변환"""
        # 한글인 경우
        if any('\uAC00' <= c <= '\uD7A3' for c in word):
            # 한글 자모 분리
            return self._get_korean_pronunciation(word)
        
        # 영어인 경우 영한 발음 변환 
        return self._convert_eng_to_kor_sound(word.lower())
    
    def _get_korean_pronunciation(self, word):
        """한글 단어를 자모 시퀀스로 변환"""
        try:
            # 한글 자모 분리 (예: '안녕' -> 'ㅇㅏㄴㄴㅕㅇ')
            jamo_sequence = j2hcj(h2j(word))
            
            # 발음 규칙 적용
            for pattern, replacement in self.pronunciation_rules:
                jamo_sequence = re.sub(pattern, replacement, jamo_sequence)
                
            return jamo_sequence
        except Exception as e:
            print(f"자모 분리 오류: {str(e)}")
            return word
    
    def _convert_eng_to_kor_sound(self, word):
        """영어 단어를 한글 발음으로 변환"""
        result = []
        for char in word:
            if char in self.eng_to_kor_sounds:
                result.append(self.eng_to_kor_sounds[char])
            else:
                result.append(char)
        return ''.join(result)
    
    def _calculate_levenshtein_distance(self, s1, s2):
        """두 문자열 간의 편집 거리 계산"""
        if len(s1) < len(s2):
            return self._calculate_levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _normalized_distance(self, s1, s2):
        """정규화된 편집 거리 (0~1 사이 값)"""
        distance = self._calculate_levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 0
        return distance / max_len
    

    def find_closest_term(self, query_term, threshold=None):
        """쿼리 용어와 가장 유사한 DB 용어 찾기"""
        if threshold is None:
            threshold = self.threshold
        
        # 숫자 표현 전처리
        from .utils import convert_korean_numbers_correctly
        query_term = convert_korean_numbers_correctly(query_term)
        
        # 원본 단어 저장
        original_query = query_term
        
        # 매핑 대상 후보
        mapping_candidates = []
        
        # 한글 조사 패턴 정의 (대표적인 조사들)
        import re
        josa_pattern = r'(이|가|을|를|의|에|에서|로|으로|과|와|은|는|도|만|께|에게|한테|보다|처럼|같이)$'
        
        # 1. 전체 단어에 대한 직접 매핑 확인
        if query_term in self.term_mappings:
            mapped = self.term_mappings[query_term]
            if mapped in self.db_terms:
                return mapped, 0.0  # 완벽 매칭
        
        # 2. 복합어 처리: 알려진 DB 용어를 단어 내에서 찾기
        for db_term in self.db_terms:
            # 한글 단어에서 영문 DB 용어를 찾는 것은 의미가 없으므로 건너뜀
            if any('\uAC00' <= c <= '\uD7A3' for c in query_term) and all(ord(c) < 128 for c in db_term):
                continue
                
            # DB 용어의 한글 매핑 확인
            korean_term = None
            for k, v in self.term_mappings.items():
                if v == db_term:
                    korean_term = k
                    break
            
            # 한글 원본과 한글 매핑 모두 확인
            check_terms = [db_term]
            if korean_term:
                check_terms.append(korean_term)
                
            for term in check_terms:
                if term in query_term:
                    # 부분 매칭 찾음 (예: "로그" in "트랜잭션로그")
                    if term != db_term:  # 한글 -> 영문 변환 필요
                        # 단어 위치와 주변 문맥 고려
                        start_idx = query_term.find(term)
                        end_idx = start_idx + len(term)
                        
                        # 뒤에 조사가 있는지 확인
                        remaining = query_term[end_idx:]
                        josa_match = re.match(r'^([가-힣]+)', remaining)
                        
                        if josa_match:
                            josa = josa_match.group(1)
                            new_query = query_term[:start_idx] + db_term + josa + remaining[len(josa):]
                        else:
                            new_query = query_term[:start_idx] + db_term + remaining
                        
                        mapping_candidates.append((new_query, 0.1))  # 낮은 점수(높은 우선순위)
        
        # 3. 발음 유사도 기반 매핑 (전체 단어에 대해)
        query_pronunciation = self._get_normalized_pronunciation(query_term)
        best_match = None
        best_score = float('inf')
        
        for term, pronunciation in self.db_term_pronunciations.items():
            score = self._normalized_distance(query_pronunciation, pronunciation)
            if score < best_score:
                best_score = score
                best_match = term
        
        if best_score <= threshold:
            # 조사 추출 시도
            josa_match = re.search(josa_pattern, query_term)
            if josa_match:
                josa = josa_match.group(0)
                # 원래 단어에서 조사 제외한 부분을 매핑하고 조사를 유지
                base_term = query_term[:-len(josa)]
                new_term = best_match + josa
                mapping_candidates.append((new_term, best_score))
            else:
                mapping_candidates.append((best_match, best_score))
        
        # 4. 부분 단어 매핑 (한글 + 기타 문자 조합)
        parts = re.findall(r'[가-힣]+|[a-zA-Z0-9]+', query_term)
        
        if len(parts) > 1:
            for i, part in enumerate(parts):
                # 각 부분에 대해 매핑 시도
                if any('\uAC00' <= c <= '\uD7A3' for c in part):  # 한글 부분만 매핑
                    # 직접 매핑 확인
                    if part in self.term_mappings:
                        mapped_part = self.term_mappings[part]
                        if mapped_part in self.db_terms:
                            # 전체 문장에서 해당 부분의 위치 찾기
                            start_pos = query_term.find(part)
                            if start_pos >= 0:
                                end_pos = start_pos + len(part)
                                
                                # 뒤에 조사가 있는지 확인
                                remaining = query_term[end_pos:]
                                josa_match = re.match(r'^([가-힣]+)', remaining)
                                
                                # 새로운 문장 구성
                                if josa_match:
                                    josa = josa_match.group(1)
                                    new_query = query_term[:start_pos] + mapped_part + josa + remaining[len(josa):]
                                else:
                                    new_query = query_term[:start_pos] + mapped_part + remaining
                                
                                mapping_candidates.append((new_query, 0.2))
                    
                    # 발음 유사도 기반 매핑
                    part_pronunciation = self._get_normalized_pronunciation(part)
                    best_part_match = None
                    best_part_score = float('inf')
                    
                    for term, pronunciation in self.db_term_pronunciations.items():
                        score = self._normalized_distance(part_pronunciation, pronunciation)
                        if score < best_part_score:
                            best_part_score = score
                            best_part_match = term
                    
                    if best_part_score <= threshold:
                        # 전체 문장에서 해당 부분의 위치 찾기
                        start_pos = query_term.find(part)
                        if start_pos >= 0:
                            end_pos = start_pos + len(part)
                            
                            # 뒤에 조사가 있는지 확인
                            remaining = query_term[end_pos:]
                            josa_match = re.match(r'^([가-힣]+)', remaining)
                            
                            # 새로운 문장 구성
                            if josa_match:
                                josa = josa_match.group(1)
                                new_query = query_term[:start_pos] + best_part_match + josa + remaining[len(josa):]
                            else:
                                new_query = query_term[:start_pos] + best_part_match + remaining
                            
                            mapping_candidates.append((new_query, best_part_score + 0.3))
        
        # 최적의 매핑 선택 (가장 낮은 점수)
        if mapping_candidates:
            mapping_candidates.sort(key=lambda x: x[1])  # 점수 기준 정렬
            return mapping_candidates[0]
        
        # 매칭되는 항목이 없으면 원래 단어 반환
        return original_query, 1.0
    


    
    def map_sentence(self, sentence):
        """문장 내 단어들을 DB 용어로 매핑"""
        # 숫자 표현 전처리 - 먼저 전체 문장에 대해 수행
        from .utils import convert_korean_numbers_correctly
        sentence = convert_korean_numbers_correctly(sentence)
        
        words = sentence.split()
        mapped_words = []
        
        for word in words:
            mapped_term, score = self.find_closest_term(word)
            mapped_words.append(mapped_term)
        
        return ' '.join(mapped_words)



    def add_custom_mapping(self, source_term, target_term, add_to_db_terms=True):
        """
        사용자 정의 매핑 추가
        
        Args:
            source_term: 원본 용어
            target_term: 대상 용어
            add_to_db_terms: True일 경우 target_term을 DB 용어 목록에 자동 추가
        """
        self.term_mappings[source_term] = target_term
        
        # 매핑 대상을 DB 용어에 자동 추가 (선택적)
        if add_to_db_terms and target_term not in self.db_terms:
            self.db_terms.append(target_term)
            # DB 용어 발음 사전 업데이트
            self.db_term_pronunciations[target_term] = self._get_normalized_pronunciation(target_term)
        
        # 역방향 매핑도 추가 (필요시)
        if target_term not in self.term_mappings:
            self.term_mappings[target_term] = source_term
        
        # 발음 사전 업데이트 (항목이 이미 DB 용어에 있는 경우)
        elif target_term in self.db_terms and target_term not in self.db_term_pronunciations:
            self.db_term_pronunciations[target_term] = self._get_normalized_pronunciation(target_term)