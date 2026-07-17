"""로컬 exact/phonetic retrieval로 모델 입력을 bounded top-k로 축소합니다."""

from dataclasses import replace

from pronunciation_mapper.mapper import LEXICAL_TOKEN_PATTERN, PronunciationMapper, split_korean_particle

from .models import Candidate, CandidateSpan


class CandidateGenerator:
    def __init__(
        self,
        mapper: PronunciationMapper,
        *,
        top_k: int = 5,
        candidate_threshold: float = 0.65,
        max_spans: int = 64,
        max_token_chars: int = 256,
    ):
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be at least 1")
        if (
            isinstance(candidate_threshold, bool)
            or not isinstance(candidate_threshold, (int, float))
            or not 0.0 <= candidate_threshold <= 1.0
        ):
            raise ValueError("candidate_threshold must be between 0 and 1")
        if (
            isinstance(max_spans, bool)
            or not isinstance(max_spans, int)
            or max_spans < 1
        ):
            raise ValueError("max_spans must be at least 1")
        if (
            isinstance(max_token_chars, bool)
            or not isinstance(max_token_chars, int)
            or max_token_chars < 1
        ):
            raise ValueError("max_token_chars must be at least 1")
        self.mapper = mapper
        self.top_k = top_k
        self.candidate_threshold = candidate_threshold
        self.max_spans = max_spans
        self.max_token_chars = max_token_chars
        self._terms_by_length = sorted(mapper.db_terms, key=lambda term: (-len(term), term))

    def generate(self, text: str) -> tuple[CandidateSpan, ...]:
        spans = []
        canonical_ranges = self.mapper.canonical_ranges(text)
        for token_index, match in enumerate(LEXICAL_TOKEN_PATTERN.finditer(text)):
            source = match.group(0)
            overlaps_canonical = any(
                match.start() < end and match.end() > start
                for start, end in canonical_ranges
            )
            alias_replacement, _ = self.mapper.replace_known_aliases(source)
            if overlaps_canonical and alias_replacement is None:
                continue
            if len(source) > self.max_token_chars:
                continue
            candidates = self._candidates_for(source)
            if not candidates:
                continue

            span_id = f"s{token_index}"
            candidates = tuple(
                replace(candidate, id=f"{span_id}:c{candidate_index}")
                for candidate_index, candidate in enumerate(candidates)
            )
            deterministic = next(
                (
                    candidate.id
                    for candidate in candidates
                    if candidate.distance == 0.0 and candidate.method in {"direct", "compound"}
                ),
                None,
            )
            spans.append(
                CandidateSpan(
                    id=span_id,
                    start=match.start(),
                    end=match.end(),
                    source=source,
                    candidates=candidates,
                    deterministic_candidate_id=deterministic,
                )
            )
            if len(spans) >= self.max_spans:
                break
        return tuple(spans)

    def _candidates_for(self, source: str) -> tuple[Candidate, ...]:
        if source in self.mapper.db_terms and self.mapper._direct_target(source) is None:
            return ()

        by_replacement = {}

        direct_replacement = self._exact_replacement(source)
        if direct_replacement and direct_replacement != source:
            canonical = self._canonical_terms(direct_replacement)
            if canonical:
                by_replacement[direct_replacement] = Candidate(
                    id="",
                    replacement=direct_replacement,
                    canonical_terms=canonical,
                    distance=0.0,
                    method="direct",
                )

        alias_replacement, canonical = self.mapper.replace_known_aliases(source)
        if alias_replacement and alias_replacement != source and canonical:
            method = "compound" if len(canonical) > 1 else "direct"
            replacement_text = alias_replacement
            by_replacement[replacement_text] = Candidate(
                id="",
                replacement=replacement_text,
                canonical_terms=canonical,
                distance=0.0,
                method=method,
            )

        # Engine already normalizes the full sentence. Re-normalizing an isolated
        # token here would lose particle context (for example ``C++만``) and
        # could reinterpret the bare particle as a number.
        for replacement_text, distance in self.mapper._rank_candidates_normalized(
            source, limit=self.top_k + 2
        ):
            if replacement_text == source or distance > self.candidate_threshold:
                continue
            canonical = self._canonical_terms(replacement_text)
            if not canonical:
                continue
            candidate = Candidate(
                id="",
                replacement=replacement_text,
                canonical_terms=canonical,
                distance=float(distance),
                method="phonetic",
            )
            current = by_replacement.get(replacement_text)
            if current is None or candidate.distance < current.distance:
                by_replacement[replacement_text] = candidate

        priority = {"direct": 0, "compound": 1, "phonetic": 2}
        ordered = sorted(
            by_replacement.values(),
            key=lambda candidate: (
                candidate.distance,
                priority.get(candidate.method, 9),
                candidate.replacement,
            ),
        )
        return tuple(ordered[: self.top_k])

    def _exact_replacement(self, source: str) -> str | None:
        target = self.mapper.term_mappings.get(source)
        if target in self.mapper.db_terms:
            return target

        base, particle = split_korean_particle(source)
        target = self.mapper.term_mappings.get(base)
        if target in self.mapper.db_terms:
            return target + particle
        if base in self.mapper.db_terms and particle:
            return base + particle
        return None

    def _canonical_terms(self, replacement_text: str) -> tuple[str, ...]:
        base, particle = split_korean_particle(replacement_text)
        if particle and base in self.mapper.db_terms:
            return (base,)
        if replacement_text in self.mapper.db_terms:
            return (replacement_text,)

        parts = base.split()
        if parts and all(part in self.mapper.db_terms for part in parts):
            return tuple(parts)

        # 영어/식별자 target 뒤에 붙은 조사를 안전하게 인식합니다.
        for term in self._terms_by_length:
            if replacement_text.startswith(term):
                suffix = replacement_text[len(term):]
                if suffix and split_korean_particle("X" + suffix) == ("X", suffix):
                    return (term,)
        return ()
