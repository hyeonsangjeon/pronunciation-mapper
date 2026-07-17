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
    for kor in sorted(SPECIAL_NUMERIC_TERMS, key=len, reverse=True):
        num = SPECIAL_NUMERIC_TERMS[kor]
        text = text.replace(kor, num)
    
    # 개별 숫자 변환
    # (여기서는 간단한 대체만 수행, 실제로는 더 복잡한 로직이 필요할 수 있음)
    for kor in sorted(NUMBER_MAPPINGS, key=len, reverse=True):
        num = NUMBER_MAPPINGS[kor]
        text = text.replace(kor, num)
    
    return text


def convert_korean_numbers_correctly(text):
    """한글 숫자 표현을 보수적으로 아라비아 숫자로 변환합니다.

    한국어 숫자 음절은 일반 단어에도 자주 등장하므로 모든 일치 항목을
    무조건 바꾸지 않습니다. 단위가 있거나 전화번호처럼 충분히 긴 숫자열인
    경우만 변환하고, 알려진 고유명사는 먼저 보호합니다.
    """
    import re

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    proper_noun_patterns = (
        "천국", "천사", "천재", "천지", "천둥", "백화점", "백수", "십자가"
    )
    numeral_chars = "영공빵일이삼사오육륙칠팔구십백천만억조"
    protected = {}
    for index, term in enumerate(proper_noun_patterns):
        if term in text:
            marker = f"\ue000PM{index}\ue001"
            while marker in text or marker in protected:
                marker += "\ue002"
            pattern = rf"(?<![{numeral_chars}]){re.escape(term)}(?![{numeral_chars}])"
            updated, count = re.subn(pattern, marker, text)
            if count:
                text = updated
                protected[marker] = term

    digit_to_num = {
        '영': '0', '공': '0', '빵': '0',
        '일': '1', '이': '2', '삼': '3', '사': '4',
        '오': '5', '육': '6', '륙': '6', '칠': '7', '팔': '8', '구': '9',
    }
    units = set("십백천만억조")
    small_units = set("십백천")
    counters = set("년번개명원시분초호회층대건차월")
    trailing_particles = (
        "에서", "으로", "에게", "한테", "처럼", "보다", "의", "은", "는",
        "이", "가", "을", "를", "에", "로", "와", "과", "도", "만",
    )
    numeric_context_hints = (
        "번호", "넘버", "계정", "아이디", "전화", "주문", "코드",
        "account_id", "account", "number", "id",
    )
    number_pattern = re.compile(rf'[{numeral_chars}]+')

    def replace_number(match):
        token = match.group(0)
        has_unit = any(char in units for char in token)
        left = text[match.start() - 1:match.start()] if match.start() else ""
        right = text[match.end():match.end() + 1]
        suffix = text[match.end():]
        next_nonspace_match = re.search(r"\S", suffix)
        next_nonspace = next_nonspace_match.group(0) if next_nonspace_match else ""
        next_word_match = re.match(r"\s*([가-힣]+)", suffix)
        next_word = next_word_match.group(1) if next_word_match else ""
        prefix = text[:match.start()].rstrip()
        has_numeric_context = any(
            re.search(
                (
                    (r"(?<![A-Za-z0-9])" if hint.isascii() else "")
                    + rf"{re.escape(hint)}(?:은|는|이|가|을|를|의|에|로)?$"
                ),
                prefix,
                flags=re.IGNORECASE,
            )
            for hint in numeric_context_hints
        )
        has_counter_context = next_nonspace in counters
        is_entire_input = match.start() == 0 and match.end() == len(text)

        numeric_token = token
        spoken_suffix = ""
        if (
            not has_unit
            and has_numeric_context
            and token.endswith("이")
            and suffix.startswith(("야", "에요"))
        ):
            numeric_token = token[:-1]
            spoken_suffix = "이"

        # lexical term/identifier 뒤에 붙은 ``이``와 ``만``은 숫자 2나
        # 10,000이 아니라 한국어 조사입니다. 숫자 정규화를 다시 적용해도
        # 이미 rewrite된 canonical text가 변하지 않도록 보존합니다.
        attached_to_lexical_term = bool(
            (left and (left.isalnum() or left == "_"))
            or re.search(r"\w+[^\w\s]+$", prefix)
        )
        if attached_to_lexical_term and token in trailing_particles:
            return token

        # ``고객만``의 조사나 ``참조``의 끝 음절처럼 한 글자 단위가 일반
        # 단어에 붙어 있으면 보존합니다. 단독 ``십``/``백``은 변환됩니다.
        if has_unit and len(token) == 1 and any(
            side and '가' <= side <= '힣' for side in (left, right)
        ):
            return token

        # ``구조``, ``조사``처럼 [숫자 음절 + 큰 단위]로도 해석 가능한 짧은
        # 일반어는 오탐 비용이 높으므로 보존합니다. 명시적인 십/백/천 또는
        # 세 음절 이상의 수 표현은 아래에서 처리합니다.
        if (
            has_unit
            and not any(char in small_units for char in token)
            and len(token) == 2
            and not has_counter_context
        ):
            return token

        # 숫자 뒤에 일반 한글이 이어지면 고유명사일 가능성이 높습니다.
        if (
            right
            and '가' <= right <= '힣'
            and right not in counters
        ):
            if has_unit or len(numeric_token) < 5 or not (
                spoken_suffix
                or any(
                    suffix.startswith(particle) for particle in trailing_particles
                )
            ):
                return token

        if has_unit:
            # ``천만 다행``처럼 수 표현과 모양이 같은 일반 표현은 주변 문맥이
            # 숫자임을 뒷받침하지 않으면 비가역적으로 바꾸지 않습니다.
            if next_word and not has_counter_context:
                return token
            return korean_number_to_arabic(token)

        # 순수 숫자 음절은 ``일일이``/``사이사이`` 같은 일반어와 충돌합니다.
        # 긴 계정·전화번호, 명시적 counter, 또는 번호 문맥만 자동 변환합니다.
        if (
            (len(numeric_token) >= 5 and (is_entire_input or has_numeric_context))
            or has_counter_context
            or has_numeric_context
        ):
            return ''.join(digit_to_num[char] for char in numeric_token) + spoken_suffix
        return token

    text = number_pattern.sub(replace_number, text)
    for marker, term in protected.items():
        text = text.replace(marker, term)
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
        '오': 5, '육': 6, '륙': 6, '칠': 7, '팔': 8, '구': 9,
    }
    
    # 단위 매핑
    unit_dict = {'십': 10, '백': 100, '천': 1000, 
                '만': 10000, '억': 100000000, '조': 1000000000000}
    
    total = 0
    section = 0
    current_num = None

    for char in korean_str:
        if char in num_dict:
            current_num = num_dict[char]
            continue

        if char not in unit_dict:
            raise ValueError(f"지원하지 않는 한글 숫자 문자: {char}")

        unit_value = unit_dict[char]
        if unit_value < 10000:
            section += (1 if current_num is None else current_num) * unit_value
        else:
            section += 0 if current_num is None else current_num
            total += (section or 1) * unit_value
            section = 0
        current_num = None

    return str(total + section + (0 if current_num is None else current_num))
