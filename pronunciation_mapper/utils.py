"""
발음 매퍼를 위한 유틸리티 함수
"""
import json
import os
from pathlib import Path

def load_mappings_from_file(file_path):
    """
    JSON 파일에서 매핑 정보 로드
    
    Args:
        file_path: JSON 매핑 파일 경로
        
    Returns:
        dict: 매핑 사전
    """
    if not os.path.exists(file_path):
        return {}
        
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_mappings_to_file(mappings, file_path):
    """
    매핑 정보를 JSON 파일로 저장
    
    Args:
        mappings: 저장할 매핑 사전
        file_path: 저장할 파일 경로
    """
    # 디렉토리가 없으면 생성
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

def extract_db_terms(db_config):
    """
    데이터베이스 설정에서 용어 추출
    
    Args:
        db_config: 데이터베이스 설정 정보
        
    Returns:
        list: 추출된 데이터베이스 용어 리스트
    """
    terms = []
    
    # 테이블명 추출
    if 'tables' in db_config:
        terms.extend(db_config['tables'])
    
    # 필드명 추출
    if 'fields' in db_config:
        for table, fields in db_config['fields'].items():
            terms.extend(fields)
    
    # 중복 제거 및 정렬
    return sorted(list(set(terms)))

def get_cache_path():
    """매핑 캐시 파일 경로 반환"""
    home_dir = Path.home()
    cache_dir = home_dir / '.pronunciation_mapper'
    return cache_dir / 'mapping_cache.json'


def convert_korean_numbers(text):
    """한글로 표현된 숫자를 아라비아 숫자로 변환"""
    from .config import NUMBER_MAPPINGS, SPECIAL_NUMERIC_TERMS
    
    # 특수 숫자 표현 먼저 확인 (완전 매칭)
    for kor, num in SPECIAL_NUMERIC_TERMS.items():
        text = text.replace(kor, num)
    
    # 개별 숫자 변환
    # (여기서는 간단한 대체만 수행, 실제로는 더 복잡한 로직이 필요할 수 있음)
    for kor, num in NUMBER_MAPPINGS.items():
        text = text.replace(kor, num)
    
    return text


def convert_korean_numbers_correctly(text):
    """한글로 표현된 숫자를 아라비아 숫자로 정확하게 변환"""
    import re
    
    # 고유명사 패턴
    proper_noun_patterns = ["천국", "천사", "천재", "천지", "천둥", "백화점", "백수", "십자가"]
    
    # 고유명사 보존을 위한 임시 치환
    for term in proper_noun_patterns:
        if term in text:
            text = text.replace(term, f"__PRESERVE_{term}__")
    
    # 숫자 문자 정의 (0 표현 추가)
    digits = "영일이삼사오육칠팔구공빵"
    digit_to_num = {
        '영': '0', '공': '0', '빵': '0',
        '일': '1', '이': '2', '삼': '3', '사': '4',
        '오': '5', '육': '6', '칠': '7', '팔': '8', '구': '9'
    }
    
    units = ['십', '백', '천', '만', '억', '조']
    
    # 복합 숫자 패턴 (단위 포함)
    # 예: 삼백이십일, 천구백팔십, 육십사
    complex_pattern = r'([' + digits + r']+[백천만억조])+[' + digits + r']*(십)?[' + digits + r']*'
    
    # 단순 숫자 패턴 (숫자만 연속)
    # 예: 일이삼, 사오육, 칠팔구공
    simple_pattern = r'[' + digits + r']{2,}'
    
    # 텍스트에서 복합 숫자 패턴 찾기
    for match in re.finditer(complex_pattern, text):
        korean_num = match.group()
        try:
            # 변환 시도
            arabic = korean_number_to_arabic(korean_num)
            
            # 변환된 숫자로 교체
            text = text.replace(korean_num, arabic)
        except Exception as e:
            print(f"복합 숫자 변환 실패: {korean_num} - {str(e)}")
    
    # 텍스트에서 단순 숫자 패턴 찾기
    for match in re.finditer(simple_pattern, text):
        korean_num = match.group()
        # 단순 숫자는 한자리씩 변환
        arabic = ''.join(digit_to_num.get(char, char) for char in korean_num)
        text = text.replace(korean_num, arabic)
        
    # 보존된 고유명사 복원
    for term in proper_noun_patterns:
        text = text.replace(f"__PRESERVE_{term}__", term)
    
    return text

def korean_digit_to_arabic(char):
    """한 글자 한글 숫자를 아라비아 숫자로 변환"""
    mapping = {
        '영': '0', '공': '0', '빵': '0',  # 0의 다양한 표현
        '일': '1', '하나': '1', '한': '1',
        '이': '2', '둘': '2', '두': '2',
        '삼': '3', '셋': '3', '세': '3',
        '사': '4', '넷': '4', '네': '4',
        '오': '5', '다섯': '5',
        '육': '6', '륙': '6', '여섯': '6',
        '칠': '7', '일곱': '7',
        '팔': '8', '여덟': '8',
        '구': '9', '아홉': '9'
    }
    return mapping.get(char, char)

def korean_number_to_arabic(korean_str):
    """단위가 포함된 한글 숫자를 아라비아 숫자로 변환"""
    
    # 숫자 매핑 (0의 다양한 표현 포함)
    num_dict = {
        '영': 0, '공': 0, '빵': 0,
        '일': 1, '이': 2, '삼': 3, '사': 4, 
        '오': 5, '육': 6, '칠': 7, '팔': 8, '구': 9
    }
    
    # 단위 매핑
    unit_dict = {'십': 10, '백': 100, '천': 1000, 
                '만': 10000, '억': 100000000, '조': 1000000000000}
    
    result = 0
    temp_sum = 0
    current_num = 0
    
    i = 0
    while i < len(korean_str):
        char = korean_str[i]
        
        # 숫자인 경우
        if char in num_dict:
            current_num = num_dict[char]
            i += 1
        # 단위인 경우
        elif char in unit_dict:
            unit_value = unit_dict[char]
            
            # 앞에 숫자가 없으면 1로 가정
            if current_num == 0:
                current_num = 1
                
            # 만, 억, 조 단위인 경우
            if unit_value >= 10000:
                temp_sum += current_num
                result += temp_sum * unit_value
                temp_sum = 0
            # 십, 백, 천 단위인 경우
            else:
                temp_sum += current_num * unit_value
            
            current_num = 0
            i += 1
        else:
            i += 1
    
    # 남은 숫자 처리
    result += temp_sum + current_num
    
    return str(result)