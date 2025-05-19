def convert_korean_numbers_correctly(text, special_cases=None):
    """한글로 표현된 숫자를 아라비아 숫자로 정확하게 변환
    
    Args:
        text (str): 변환할 텍스트
        special_cases (dict, optional): 직접 매핑할 특별 케이스. 기본값은 None.
    
    Returns:
        str: 숫자가 변환된 텍스트
    """
    # 특별 케이스가 있는 경우에만 처리
    if special_cases:
        # 특별 케이스 처리
        for k, v in special_cases.items():
            text = text.replace(k, v)
    
    import re
    
    # 1. 단위가 포함된 패턴 (예: 삼백이십일, 오백구십구)
    # 여러 단위가 연속해서 나오는 패턴을 하나로 매칭
    unit_pattern = r'([영일이삼사오육칠팔구십백천만억조]+)'
    
    # 문자열에서 패턴 찾기
    matches = list(re.finditer(unit_pattern, text))
    
    # 각 매치에 대해 처리
    result = text
    processed_ranges = []  # 이미 처리된 범위를 저장
    
    for match in matches:
        start, end = match.span()
        korean_str = match.group()
        
        # 이미 처리된 부분은 건너뜀
        if any(start >= r[0] and end <= r[1] for r in processed_ranges):
            continue
            
        # 숫자와 단위 포함 패턴인지 확인 (십, 백, 천 등의 단위가 하나라도 있는지)
        if any(unit in korean_str for unit in ['십', '백', '천', '만', '억', '조']):
            # 단위가 있는 숫자 변환
            try:
                arabic_num = korean_number_to_arabic(korean_str)
                result = result[:start] + arabic_num + result[end:]
                processed_ranges.append((start, end))
            except:
                pass
        # 숫자만 연속된 패턴 (예: 팔이사오)
        elif all(char in "영일이삼사오육칠팔구" for char in korean_str) and len(korean_str) > 1:
            # 한 글자씩 변환
            arabic_num = ''.join(korean_digit_to_arabic(digit) for digit in korean_str)
            result = result[:start] + arabic_num + result[end:]
            processed_ranges.append((start, end))
    
    return result

def korean_digit_to_arabic(char):
    """한 글자 한글 숫자를 아라비아 숫자로 변환"""
    mapping = {'영': '0', '일': '1', '이': '2', '삼': '3', '사': '4', 
              '오': '5', '육': '6', '칠': '7', '팔': '8', '구': '9'}
    return mapping.get(char, char)

def korean_number_to_arabic(korean_str):
    """단위가 포함된 한글 숫자를 아라비아 숫자로 변환"""
    
    # 숫자 매핑
    num_dict = {'영': 0, '일': 1, '이': 2, '삼': 3, '사': 4, 
               '오': 5, '육': 6, '칠': 7, '팔': 8, '구': 9}
    
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
test_cases = {
    '삼백이십일': '321',
    '이천이십삼년': '2023년',
    '삼천사백오십육': '3456',
    '천삼백이십사': '1324',
    '팔이사오': '8245',
    '이천이십오년': '2025년',
    '오백칠십팔': '578',
    '오백구십구': '599',
    '이천사백구십구': '2499',
    '이천구백구십구': '2999',
    '천구백구십구': '1999',
    '오더육십육': '오더66',
    '사만삼천오백사': '43504',
    '십': '10',
    '백': '100',
    '백일': '101',
    '이백삼십사': '234',
    '오더일이삼':'오더123',
    '사이오사다시삼삼삼칠':'4254다시3337',
    '케이엠디육십육':'케이엠디66'
    
}

for input_text, expected in test_cases.items():
    result = convert_korean_numbers_correctly(input_text)
    print(f"{input_text} → {result} (기대값: {expected})")
    assert result == expected, f"변환 실패: {result} != {expected}"

print("모든 테스트 통과!")