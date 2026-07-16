"""하이브리드 V2 orchestrator."""

import asyncio
import math
import time
from collections.abc import Mapping
from typing import Any

from pronunciation_mapper.mapper import LEXICAL_TOKEN_PATTERN, PronunciationMapper
from pronunciation_mapper.utils import convert_korean_numbers_correctly

from .candidates import CandidateGenerator
from .errors import InvalidProviderOutputError, ProviderError
from .models import (
    AppliedDecision,
    Candidate,
    CandidateSpan,
    DecisionAction,
    DecisionRequest,
    ProviderResponse,
    ProviderSelection,
    ReasonCode,
    RewriteResult,
)
from .providers import DecisionProvider, create_provider


MAX_USAGE_INTEGER = 2**63 - 1


class AgenticPronunciationMapper:
    """Azure Foundry 기본, Ollama 선택형의 bounded decision mapper."""

    def __init__(
        self,
        db_terms,
        *,
        custom_mappings=None,
        provider: str | DecisionProvider | None = None,
        threshold: float | None = None,
        top_k: int = 5,
        candidate_threshold: float = 0.65,
        minimum_confidence: float = 0.55,
        fallback_strategy: str = "heuristic",
        provider_options: dict[str, Any] | None = None,
        max_input_chars: int = 4096,
        max_spans: int = 64,
        max_token_chars: int = 256,
    ):
        if isinstance(minimum_confidence, bool) or not isinstance(
            minimum_confidence, (int, float)
        ) or not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if fallback_strategy not in {"heuristic", "original", "raise"}:
            raise ValueError("fallback_strategy must be heuristic, original, or raise")
        if threshold is not None and not _is_unit_interval_number(threshold):
            raise ValueError("threshold must be between 0 and 1")
        if (
            isinstance(max_input_chars, bool)
            or not isinstance(max_input_chars, int)
            or max_input_chars < 1
        ):
            raise ValueError("max_input_chars must be at least 1")

        self.heuristic_mapper = PronunciationMapper(
            db_terms,
            threshold=threshold,
            custom_mappings=custom_mappings,
        )
        self.candidate_generator = CandidateGenerator(
            self.heuristic_mapper,
            top_k=top_k,
            candidate_threshold=candidate_threshold,
            max_spans=max_spans,
            max_token_chars=max_token_chars,
        )
        self._owns_provider = provider is None or isinstance(provider, str)
        if provider is None or isinstance(provider, str):
            self.provider = create_provider(provider, **(provider_options or {}))
        else:
            self.provider = provider
        self.minimum_confidence = minimum_confidence
        self.fallback_strategy = fallback_strategy
        # V2 장애 fallback은 V1 기본값(0.5)보다 보수적으로 둡니다. 호출자가
        # threshold를 명시한 경우에는 그 정책을 그대로 존중합니다.
        self.fallback_threshold = 0.35 if threshold is None else float(threshold)
        self.max_input_chars = max_input_chars
        self.max_spans = max_spans
        self.max_token_chars = max_token_chars

    async def rewrite(self, text: str) -> RewriteResult:
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if len(text) > self.max_input_chars:
            raise ValueError(f"text exceeds max_input_chars={self.max_input_chars}")

        started = time.perf_counter()
        normalized = convert_korean_numbers_correctly(text)
        lexical_tokens = tuple(LEXICAL_TOKEN_PATTERN.finditer(normalized))
        if len(lexical_tokens) > self.max_spans:
            raise ValueError(f"text exceeds max_spans={self.max_spans}")
        if any(len(match.group(0)) > self.max_token_chars for match in lexical_tokens):
            raise ValueError(
                f"text contains a token exceeding max_token_chars={self.max_token_chars}"
            )
        spans = self.candidate_generator.generate(normalized)
        diagnostics = []
        if normalized != text:
            diagnostics.append("number-normalization-applied")

        selected: dict[str, Candidate | None] = {}
        applied: dict[str, AppliedDecision] = {}
        unresolved = []

        for span in spans:
            deterministic = self._candidate_by_id(span, span.deterministic_candidate_id)
            if deterministic is None:
                unresolved.append(span)
                continue
            self._assert_candidate_is_safe(deterministic)
            selected[span.id] = deterministic
            applied[span.id] = self._applied(
                span,
                deterministic,
                action=DecisionAction.REPLACE.value,
                confidence=1.0,
                reason_code=ReasonCode.ALIAS.value,
            )

        fallback_used = False
        provider_name = "local-deterministic"
        model_name = ""
        usage = {}

        if unresolved:
            request = DecisionRequest(text=normalized, spans=tuple(unresolved))
            try:
                response = await self.provider.decide(request)
                self._validate_response(response, unresolved)
                provider_name = response.provider
                model_name = response.model
                usage = dict(response.usage)
                selection_by_span = {
                    selection.span_id: selection for selection in response.selections
                }
                for span in unresolved:
                    selection = selection_by_span[span.id]
                    candidate = self._candidate_by_id(span, selection.candidate_id)
                    if (
                        selection.action is DecisionAction.REPLACE
                        and selection.confidence >= self.minimum_confidence
                        and candidate is not None
                    ):
                        self._assert_candidate_is_safe(candidate)
                        selected[span.id] = candidate
                        applied[span.id] = self._applied(
                            span,
                            candidate,
                            action=selection.action.value,
                            confidence=selection.confidence,
                            reason_code=selection.reason_code.value,
                        )
                    elif selection.action is DecisionAction.REPLACE:
                        diagnostics.append(f"low-confidence:{span.id}")
                        selected[span.id] = None
                        applied[span.id] = self._applied(
                            span,
                            None,
                            action=DecisionAction.KEEP.value,
                            confidence=selection.confidence,
                            reason_code=ReasonCode.AMBIGUOUS.value,
                        )
                    else:
                        selected[span.id] = None
                        applied[span.id] = self._applied(
                            span,
                            None,
                            action=selection.action.value,
                            confidence=selection.confidence,
                            reason_code=selection.reason_code.value,
                        )
            except (ProviderError, ConnectionError, TimeoutError, OSError) as error:
                if self.fallback_strategy == "raise":
                    raise
                fallback_used = True
                provider_name = getattr(self.provider, "name", "unknown")
                model_name = getattr(self.provider, "model", "")
                diagnostics.append(f"provider-fallback:{type(error).__name__}")
                self._apply_fallback(unresolved, selected, applied)

        rewritten = self._render(normalized, spans, selected)
        ordered_decisions = tuple(
            applied[span.id] for span in spans if span.id in applied
        )
        return RewriteResult(
            original_text=text,
            normalized_text=normalized,
            rewritten_text=rewritten,
            provider=provider_name,
            model=model_name,
            fallback_used=fallback_used,
            decisions=ordered_decisions,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            usage=usage,
            diagnostics=tuple(diagnostics),
        )

    def rewrite_sync(self, text: str) -> RewriteResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.rewrite(text))
        raise RuntimeError("rewrite_sync cannot run inside an event loop; use 'await rewrite(...)'")

    def map_sentence(self, sentence: str) -> str:
        """동기 애플리케이션을 위한 간단한 문자열 projection."""
        return self.rewrite_sync(sentence).rewritten_text

    def close(self) -> None:
        """이 mapper가 factory로 만든 provider 리소스를 해제합니다."""
        if not self._owns_provider:
            return
        close = getattr(self.provider, "close", None)
        if callable(close):
            close()

    async def aclose(self) -> None:
        """이 mapper가 factory로 만든 provider 리소스를 비동기로 해제합니다."""
        if not self._owns_provider:
            return
        aclose = getattr(self.provider, "aclose", None)
        if callable(aclose):
            await aclose()
            return
        close = getattr(self.provider, "close", None)
        if callable(close):
            await asyncio.to_thread(close)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> bool:
        await self.aclose()
        return False

    def _validate_response(self, response: ProviderResponse, spans: list[CandidateSpan]) -> None:
        if not isinstance(response, ProviderResponse):
            raise InvalidProviderOutputError("provider must return ProviderResponse")
        if not isinstance(response.provider, str) or not response.provider:
            raise InvalidProviderOutputError("provider name must be a non-empty string")
        if not isinstance(response.model, str):
            raise InvalidProviderOutputError("provider model must be a string")
        if not isinstance(response.usage, Mapping):
            raise InvalidProviderOutputError("provider usage must be a mapping")
        for key, value in response.usage.items():
            if not isinstance(key, str):
                raise InvalidProviderOutputError("provider usage keys must be strings")
            if isinstance(value, bool) or not isinstance(value, (int, float, str, type(None))):
                raise InvalidProviderOutputError(
                    "provider usage values have an unsupported type"
                )
            if isinstance(value, int) and value > MAX_USAGE_INTEGER:
                raise InvalidProviderOutputError("provider usage integer is too large")
            if isinstance(value, (int, float)) and not _is_nonnegative_number(value):
                raise InvalidProviderOutputError(
                    "provider usage numbers must be finite and non-negative"
                )
        if not isinstance(response.selections, tuple):
            raise InvalidProviderOutputError("provider selections must be a tuple")

        expected = {span.id for span in spans}
        span_by_id = {span.id: span for span in spans}
        received = set()
        for selection in response.selections:
            if not isinstance(selection, ProviderSelection):
                raise InvalidProviderOutputError("each selection must be ProviderSelection")
            if not isinstance(selection.span_id, str) or not selection.span_id:
                raise InvalidProviderOutputError("selection span_id must be a non-empty string")
            if selection.span_id not in expected or selection.span_id in received:
                raise InvalidProviderOutputError("provider returned an unknown or duplicate span_id")
            if not isinstance(selection.action, DecisionAction):
                raise InvalidProviderOutputError("selection action must be DecisionAction")
            if not isinstance(selection.reason_code, ReasonCode):
                raise InvalidProviderOutputError("selection reason_code must be ReasonCode")
            if isinstance(selection.confidence, bool) or not isinstance(
                selection.confidence, (int, float)
            ):
                raise InvalidProviderOutputError("selection confidence must be numeric")
            if not _is_unit_interval_number(selection.confidence):
                raise InvalidProviderOutputError(
                    "selection confidence must be finite and between 0 and 1"
                )

            if selection.action is DecisionAction.REPLACE:
                if not isinstance(selection.candidate_id, str) or not selection.candidate_id:
                    raise InvalidProviderOutputError("replace requires a candidate_id")
                candidate = self._candidate_by_id(
                    span_by_id[selection.span_id], selection.candidate_id
                )
                if candidate is None:
                    raise InvalidProviderOutputError("candidate_id is not allowed for this span")
            elif selection.candidate_id is not None:
                raise InvalidProviderOutputError("keep/abstain must use a null candidate_id")
            received.add(selection.span_id)

        if received != expected or len(response.selections) != len(expected):
            raise InvalidProviderOutputError(
                "provider must return exactly one decision per requested span"
            )

    def _apply_fallback(
        self,
        spans: list[CandidateSpan],
        selected: dict[str, Candidate | None],
        applied: dict[str, AppliedDecision],
    ) -> None:
        for span in spans:
            candidate = None
            if self.fallback_strategy == "heuristic" and span.candidates:
                first = span.candidates[0]
                if first.distance <= self.fallback_threshold:
                    candidate = first
            if candidate is not None:
                self._assert_candidate_is_safe(candidate)
                selected[span.id] = candidate
                applied[span.id] = self._applied(
                    span,
                    candidate,
                    action=DecisionAction.REPLACE.value,
                    confidence=max(0.0, 1.0 - candidate.distance),
                    reason_code=ReasonCode.PHONETIC.value,
                )
            else:
                selected[span.id] = None
                applied[span.id] = self._applied(
                    span,
                    None,
                    action=DecisionAction.KEEP.value,
                    confidence=0.0,
                    reason_code=ReasonCode.NO_MATCH.value,
                )

    def _assert_candidate_is_safe(self, candidate: Candidate) -> None:
        db_terms = set(self.heuristic_mapper.db_terms)
        if (
            not isinstance(candidate.replacement, str)
            or not candidate.replacement
            or isinstance(candidate.distance, bool)
            or not isinstance(candidate.distance, (int, float))
            or not _is_unit_interval_number(candidate.distance)
            or not candidate.canonical_terms
            or any(term not in db_terms for term in candidate.canonical_terms)
        ):
            raise InvalidProviderOutputError("candidate is outside the canonical DB vocabulary")

    @staticmethod
    def _candidate_by_id(span: CandidateSpan, candidate_id: str | None) -> Candidate | None:
        if candidate_id is None:
            return None
        return next((candidate for candidate in span.candidates if candidate.id == candidate_id), None)

    @staticmethod
    def _applied(
        span: CandidateSpan,
        candidate: Candidate | None,
        *,
        action: str,
        confidence: float,
        reason_code: str,
    ) -> AppliedDecision:
        return AppliedDecision(
            span_id=span.id,
            source=span.source,
            replacement=span.source if candidate is None else candidate.replacement,
            action=action,
            confidence=round(float(confidence), 6),
            reason_code=reason_code,
            candidate_id=None if candidate is None else candidate.id,
            distance=None if candidate is None else round(candidate.distance, 6),
        )

    @staticmethod
    def _render(text: str, spans: tuple[CandidateSpan, ...], selected: dict[str, Candidate | None]) -> str:
        parts = []
        cursor = 0
        for span in spans:
            candidate = selected.get(span.id)
            if candidate is None:
                continue
            parts.append(text[cursor:span.start])
            parts.append(candidate.replacement)
            cursor = span.end
        parts.append(text[cursor:])
        return "".join(parts)


def _is_unit_interval_number(value: int | float) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return 0.0 <= value <= 1.0


def _is_nonnegative_number(value: int | float) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return value >= 0
