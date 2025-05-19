from pronunciation_mapper import PronunciationMapper
from pronunciation_mapper.utils import convert_korean_numbers_correctly
# 테스트 코드
def test_number_conversion():
    test_cases = {
        '구십구':'99',
        '삼백이십일': '321',
        '천구백구십구': '1999',
        '이천이십삼년': '2023년',
        '오더육십육': '오더66',
        '삼천사백오십육': '3456',
        '십': '10',
        '백': '100',
        '백일': '101',
        '이백삼십사': '234'
    }
    
    for input_text, expected in test_cases.items():
        result = convert_korean_numbers_correctly(input_text)
        print(f"{input_text} → {result} (기대값: {expected})")
        assert result == expected, f"변환 실패: {result} != {expected}"
    
    print("모든 테스트 통과!")

# 테스트 실행
test_number_conversion()