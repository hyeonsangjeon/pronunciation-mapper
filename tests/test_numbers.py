import unittest

from pronunciation_mapper.utils import convert_korean_numbers, convert_korean_numbers_correctly


class TestKoreanNumbers(unittest.TestCase):
    def test_units_and_spoken_digits(self):
        cases = {
            "구십구": "99",
            "삼백이십일": "321",
            "천구백구십구": "1999",
            "이천이십삼년": "2023년",
            "오더육십육": "오더66",
            "십": "10",
            "백": "100",
            "백일": "101",
            "사삼삼오삼칠": "433537",
            "백만": "1000000",
            "일억이천만": "120000000",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(convert_korean_numbers_correctly(source), expected)

    def test_proper_nouns_and_ambiguous_short_words_are_preserved(self):
        for value in (
            "천국", "천사", "백화점", "십자가", "사이", "이사",
            "고객만 조회", "시스템 구조 확인", "자료 조사 요청",
            "설계 참조", "업무 협조", "클라우드서버만",
            "일일이 확인", "사이사이 확인", "사사오입 처리",
            "삼삼오오 모였다", "사이사이사이 확인", "천만 다행",
            "android 사이사이 간격", "fluid 사이사이 간격",
        ):
            with self.subTest(value=value):
                self.assertEqual(convert_korean_numbers_correctly(value), value)

    def test_large_units_with_explicit_counter_are_converted(self):
        cases = {
            "삼만 원": "30000 원",
            "일억 원": "100000000 원",
            "일조 원": "1000000000000 원",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(convert_korean_numbers_correctly(source), expected)

    def test_internal_protection_marker_cannot_collide_with_input(self):
        for value in ("__PM_PROTECTED_0__ 천국", "\ue000PM0\ue001 천국"):
            with self.subTest(value=value):
                self.assertEqual(convert_korean_numbers_correctly(value), value)

    def test_long_spoken_number_requires_number_context_in_a_sentence(self):
        self.assertEqual(
            convert_korean_numbers_correctly("어카운트넘버 사삼삼오삼칠 조회"),
            "어카운트넘버 433537 조회",
        )
        self.assertEqual(
            convert_korean_numbers_correctly("전화번호 공일공일이삼사오육칠팔이야"),
            "전화번호 01012345678이야",
        )
        self.assertEqual(
            convert_korean_numbers_correctly("user_id 일이삼사"),
            "user_id 1234",
        )

    def test_legacy_simple_converter_no_longer_imports_missing_symbol(self):
        self.assertEqual(convert_korean_numbers("육십육"), "66")


if __name__ == "__main__":
    unittest.main()
