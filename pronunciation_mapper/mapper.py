"""결정적 발음 후보 생성기와 V1 호환 매퍼."""

import logging
import math
import re
from collections.abc import Mapping

from jamo import h2j, j2hcj

from .config import DEFAULT_THRESHOLD, DB_TERM_MAPPINGS, ENG_TO_KOR_SOUNDS, PRONUNCIATION_RULES
from .utils import convert_korean_numbers_correctly


logger = logging.getLogger(__name__)

KOREAN_PARTICLES = (
    "으로", "에서", "에게", "한테", "처럼", "같이", "보다",
    "께", "이", "가", "을", "를", "의", "에", "로", "과", "와",
    "은", "는", "도", "만",
)
LEXICAL_TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9_]+")


def _is_unit_interval_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return 0.0 <= value <= 1.0


def split_korean_particle(word):
    """단어 끝의 대표적인 한국어 조사를 ``(어간, 조사)``로 분리합니다."""
    for particle in KOREAN_PARTICLES:
        if word.endswith(particle) and len(word) > len(particle):
            return word[:-len(particle)], particle
    return word, ""


class PronunciationMapper:
    """V1 공개 API를 유지하는 로컬 발음 기반 매퍼.

    V2에서는 이 클래스가 네트워크 호출 전에 exact mapping과 top-k 후보를
    만드는 결정적 안전망으로 사용됩니다.
    """

    def __init__(self, db_terms, threshold=None, custom_mappings=None):
        if isinstance(db_terms, (str, bytes)):
            raise TypeError("db_terms must be an iterable of strings, not a string")
        raw_terms = list(db_terms)
        if any(not isinstance(term, str) or not term for term in raw_terms):
            raise ValueError("db_terms must contain only non-empty strings")
        if not _is_unit_interval_number(
            DEFAULT_THRESHOLD if threshold is None else threshold
        ):
            raise ValueError("threshold must be between 0 and 1")
        if custom_mappings is not None:
            if not isinstance(custom_mappings, Mapping):
                raise TypeError("custom_mappings must be a mapping")
            if any(
                not isinstance(source, str)
                or not source
                or not isinstance(target, str)
                or not target
                for source, target in custom_mappings.items()
            ):
                raise ValueError("custom_mappings must contain non-empty string pairs")

        self.db_terms = list(dict.fromkeys(raw_terms))
        self.threshold = DEFAULT_THRESHOLD if threshold is None else threshold
        self.eng_to_kor_sounds = ENG_TO_KOR_SOUNDS.copy()
        self.term_mappings = DB_TERM_MAPPINGS.copy()
        if custom_mappings:
            self.term_mappings.update(custom_mappings)

        self.pronunciation_rules = PRONUNCIATION_RULES["korean"]
        self._build_bidirectional_mappings()
        self._refresh_indexes()

    def _build_bidirectional_mappings(self):
        """발음 인덱스용 reverse alias를 direct rewrite 규칙과 분리합니다.

        canonical target을 ``term_mappings``에 역방향으로 넣으면 두 표기가 모두
        DB vocabulary일 때 이미 정규형인 target이 source로 되돌아갑니다.
        """
        self.reverse_aliases = {}
        for source, target in self.term_mappings.items():
            if target in self.db_terms and source != target:
                self.reverse_aliases.setdefault(target, source)

    def _refresh_indexes(self):
        self.aliases_by_target = {term: [] for term in self.db_terms}
        for source, target in self.term_mappings.items():
            if target in self.aliases_by_target and source != target:
                self.aliases_by_target[target].append(source)

        for aliases in self.aliases_by_target.values():
            aliases.sort(key=lambda value: (-len(value), value))

        self._alias_pairs = sorted(
            (
                (source, target)
                for source, target in self.term_mappings.items()
                if source and source != target and target in self.aliases_by_target
            ),
            key=lambda item: (-len(item[0]), item[0], item[1]),
        )
        self._canonical_terms_by_length = sorted(
            self.db_terms, key=lambda value: (-len(value), value)
        )
        self.db_term_pronunciations = {
            term: self._get_normalized_pronunciation(term) for term in self.db_terms
        }
        # 하나의 canonical term에 여러 전사가 있을 수 있습니다. 첫 reverse
        # alias 하나만 대표로 쓰면 사용자 alias의 작은 ASR 오차를 놓치므로,
        # canonical 표기와 모든 alias 발음 중 최소 거리를 사용합니다.
        self.pronunciations_by_target = {}
        for term in self.db_terms:
            pronunciations = [self._get_pronunciation(term)]
            pronunciations.extend(
                self._get_pronunciation(alias) for alias in self.aliases_by_target[term]
            )
            self.pronunciations_by_target[term] = tuple(dict.fromkeys(pronunciations))

    def _get_normalized_pronunciation(self, word):
        mapped = self.term_mappings.get(word)
        if mapped is not None:
            return self._get_pronunciation(mapped)
        return self._get_pronunciation(word)

    def _get_pronunciation(self, word):
        if any("가" <= char <= "힣" for char in word):
            return self._get_korean_pronunciation(word)
        return self._convert_eng_to_kor_sound(word.lower())

    def _get_korean_pronunciation(self, word):
        try:
            jamo_sequence = j2hcj(h2j(word))
            for pattern, replacement in self.pronunciation_rules:
                jamo_sequence = re.sub(pattern, replacement, jamo_sequence)
            return jamo_sequence
        except Exception:
            logger.exception("한글 자모 분리에 실패했습니다: %r", word)
            return word

    def _convert_eng_to_kor_sound(self, word):
        return "".join(self.eng_to_kor_sounds.get(char, char) for char in word)

    def _calculate_levenshtein_distance(self, s1, s2):
        if len(s1) < len(s2):
            return self._calculate_levenshtein_distance(s2, s1)
        if not s2:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for index, char1 in enumerate(s1):
            current_row = [index + 1]
            for column, char2 in enumerate(s2):
                insertions = previous_row[column + 1] + 1
                deletions = current_row[column] + 1
                substitutions = previous_row[column] + (char1 != char2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _normalized_distance(self, s1, s2):
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 0.0
        return self._calculate_levenshtein_distance(s1, s2) / max_len

    def _direct_target(self, source):
        target = self.term_mappings.get(source)
        return target if target in self.db_terms else None

    def replace_known_aliases(self, text):
        """명시적 alias만 부분 치환하고 나머지 문자는 그대로 보존합니다.

        연속된 두 alias는 검색어가 합쳐지지 않도록 공백으로 구분합니다.
        예: ``신규커스터머정보`` -> ``신규customer정보``,
        ``클라우드서버`` -> ``cloud server``.

        반환값은 ``(치환 문자열 또는 None, canonical term tuple)``입니다.
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        parts = []
        canonical_terms = []
        position = 0
        previous_was_known_term = False
        changed = False

        while position < len(text):
            matched = next(
                (
                    (alias, target)
                    for alias, target in self._alias_pairs
                    if text.startswith(alias, position)
                ),
                None,
            )
            if matched is None:
                canonical = next(
                    (
                        term
                        for term in self._canonical_terms_by_length
                        if text.startswith(term, position)
                    ),
                    None,
                )
                if canonical is not None:
                    if previous_was_known_term:
                        parts.append(" ")
                    parts.append(canonical)
                    canonical_terms.append(canonical)
                    position += len(canonical)
                    previous_was_known_term = True
                    continue
                parts.append(text[position])
                position += 1
                previous_was_known_term = False
                continue

            alias, target = matched
            if previous_was_known_term:
                parts.append(" ")
            parts.append(target)
            canonical_terms.append(target)
            position += len(alias)
            previous_was_known_term = True
            changed = True

        if not changed:
            return None, ()
        return "".join(parts), tuple(canonical_terms)

    def canonical_ranges(self, text):
        """이미 canonical인 DB term이 차지하는 비중첩 문자 범위를 반환합니다.

        punctuation을 포함한 식별자(``customer-id``, ``schema.table``)가
        lexical tokenizer에서 여러 조각으로 나뉘더라도 각 조각을 다시 fuzzy
        치환하지 않기 위한 보호 범위입니다.
        """
        ranges = []
        for term in sorted(self.db_terms, key=lambda value: (-len(value), value)):
            position = 0
            while True:
                start = text.find(term, position)
                if start < 0:
                    break
                end = start + len(term)
                ranges.append((start, end))
                position = end

        merged = []
        for start, end in sorted(ranges):
            if merged and start < merged[-1][1]:
                if end > merged[-1][1]:
                    merged[-1] = (merged[-1][0], end)
                continue
            merged.append((start, end))
        return tuple(merged)

    def rank_candidates(self, query_term, limit=5):
        """DB vocabulary 안에서 발음상 가까운 후보를 거리 오름차순으로 반환합니다.

        반환값은 ``[(replacement, distance), ...]``이며 조사가 있으면 replacement에
        보존됩니다. ``distance``는 V1과 동일하게 0이 가장 가깝습니다.
        """
        normalized = convert_korean_numbers_correctly(query_term)
        return self._rank_candidates_normalized(normalized, limit=limit)

    def _rank_candidates_normalized(self, normalized, limit=5):
        """이미 숫자 정규화된 토큰의 발음 후보를 반환합니다."""
        if limit < 1:
            return []

        scores = {}

        direct = self._direct_target(normalized)
        if direct:
            scores[direct] = 0.0

        if normalized in self.db_term_pronunciations:
            scores[normalized] = 0.0

        # identifier 또는 canonical term을 이미 포함한 토큰은 전체를 발음
        # 후보로 덮어쓰지 않습니다. explicit alias 부분 치환은 별도 계층에서
        # 처리하므로 account_id/XPN36prod 같은 suffix가 사라지지 않습니다.
        contains_canonical_substring = any(
            term != normalized and term in normalized for term in self.db_terms
        )
        is_ascii_alphanumeric_identifier = (
            normalized.isascii()
            and any(char.isalpha() for char in normalized)
            and any(char.isdigit() for char in normalized)
        )
        if (
            "_" in normalized
            or contains_canonical_substring
            or is_ascii_alphanumeric_identifier
        ):
            return sorted(scores.items(), key=lambda item: (item[1], item[0]))[:limit]

        whole_pronunciation = self._get_normalized_pronunciation(normalized)
        for term, pronunciations in self.pronunciations_by_target.items():
            distance = min(
                self._normalized_distance(whole_pronunciation, pronunciation)
                for pronunciation in pronunciations
            )
            scores[term] = min(distance, scores.get(term, 1.0))

        # 단어 끝이 조사처럼 보이더라도 전체 토큰 후보를 버리지 않습니다.
        # 조사 분리 후보에는 작은 penalty를 주어 ``엠에쓰아이``가 ``MSI이``로
        # 오염되는 것을 막고, 문맥 resolver에는 두 가능성을 모두 제공합니다.
        base, particle = split_korean_particle(normalized)
        if particle:
            base_direct = self._direct_target(base)
            if base_direct:
                scores[base_direct + particle] = 0.0
            if base in self.db_term_pronunciations:
                scores[base + particle] = 0.0

            base_pronunciation = self._get_normalized_pronunciation(base)
            particle_penalty = 0.15
            for term, pronunciations in self.pronunciations_by_target.items():
                distance = min(
                    self._normalized_distance(base_pronunciation, pronunciation)
                    for pronunciation in pronunciations
                )
                replacement = term + particle
                distance = min(1.0, distance + particle_penalty)
                scores[replacement] = min(distance, scores.get(replacement, 1.0))

        return sorted(scores.items(), key=lambda item: (item[1], item[0]))[:limit]

    def find_closest_term(self, query_term, threshold=None):
        """쿼리 용어와 가장 가까운 DB 용어를 ``(문자열, 거리)``로 반환합니다."""
        threshold = self.threshold if threshold is None else threshold
        if not _is_unit_interval_number(threshold):
            raise ValueError("threshold must be between 0 and 1")
        normalized = convert_korean_numbers_correctly(query_term)
        return self._find_closest_normalized(normalized, threshold)

    def _find_closest_normalized(self, normalized, threshold):
        """이미 숫자 정규화된 토큰에서 가장 가까운 DB 용어를 찾습니다."""
        direct = self._direct_target(normalized)
        if direct:
            return direct, 0.0
        if normalized in self.db_terms:
            return normalized, 0.0

        base, particle = split_korean_particle(normalized)
        base_direct = self._direct_target(base)
        if base_direct:
            return base_direct + particle, 0.0
        if base in self.db_terms:
            return base + particle, 0.0

        alias_replacement, _ = self.replace_known_aliases(normalized)
        if alias_replacement is not None:
            return alias_replacement, 0.1

        ranked = self._rank_candidates_normalized(normalized, limit=1)
        if ranked and ranked[0][1] <= threshold:
            return ranked[0]
        return normalized, 1.0

    def map_sentence(self, sentence):
        """공백과 구두점을 보존하며 문장 안의 lexical token을 매핑합니다."""
        normalized = convert_korean_numbers_correctly(sentence)
        canonical_ranges = self.canonical_ranges(normalized)

        def replace(match):
            overlaps_canonical = any(
                match.start() < end and match.end() > start
                for start, end in canonical_ranges
            )
            alias_replacement, _ = self.replace_known_aliases(match.group(0))
            if overlaps_canonical and alias_replacement is None:
                return match.group(0)
            mapped, _ = self._find_closest_normalized(
                match.group(0), self.threshold
            )
            return mapped

        return LEXICAL_TOKEN_PATTERN.sub(replace, normalized)

    def add_custom_mapping(self, source_term, target_term, add_to_db_terms=True):
        """사용자 매핑을 추가하고 후보 인덱스를 즉시 갱신합니다."""
        if not isinstance(source_term, str) or not source_term:
            raise ValueError("source_term must be a non-empty string")
        if not isinstance(target_term, str) or not target_term:
            raise ValueError("target_term must be a non-empty string")
        self.term_mappings[source_term] = target_term
        if add_to_db_terms and target_term not in self.db_terms:
            self.db_terms.append(target_term)
        self._build_bidirectional_mappings()
        self._refresh_indexes()
