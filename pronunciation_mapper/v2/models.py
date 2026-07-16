"""Provider 중립적인 V2 데이터 계약."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping

from .errors import InvalidProviderOutputError


class DecisionAction(str, Enum):
    REPLACE = "replace"
    KEEP = "keep"
    ABSTAIN = "abstain"


class ReasonCode(str, Enum):
    PHONETIC = "phonetic"
    ALIAS = "alias"
    CONTEXT = "context"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"


@dataclass(frozen=True, slots=True)
class Candidate:
    id: str
    replacement: str
    canonical_terms: tuple[str, ...]
    distance: float
    method: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["canonical_terms"] = list(self.canonical_terms)
        return value


@dataclass(frozen=True, slots=True)
class CandidateSpan:
    id: str
    start: int
    end: int
    source: str
    candidates: tuple[Candidate, ...]
    deterministic_candidate_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "source": self.source,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "deterministic_candidate_id": self.deterministic_candidate_id,
        }


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    text: str
    spans: tuple[CandidateSpan, ...]
    locale: str = "ko-KR"

    def to_provider_payload(self) -> dict[str, Any]:
        """모델에는 전체 DB 사전 대신 로컬에서 축소한 후보만 전달합니다."""
        return {
            "text": self.text,
            "locale": self.locale,
            "spans": [
                {
                    "span_id": span.id,
                    "source": span.source,
                    "candidates": [
                        {
                            "candidate_id": candidate.id,
                            "replacement": candidate.replacement,
                            "distance": round(candidate.distance, 6),
                            "method": candidate.method,
                        }
                        for candidate in span.candidates
                    ],
                }
                for span in self.spans
            ],
        }


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    span_id: str
    action: DecisionAction
    candidate_id: str | None
    confidence: float
    reason_code: ReasonCode


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    selections: tuple[ProviderSelection, ...]
    provider: str
    model: str
    usage: Mapping[str, int | float | str | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AppliedDecision:
    span_id: str
    source: str
    replacement: str
    action: str
    confidence: float
    reason_code: str
    candidate_id: str | None
    distance: float | None


@dataclass(frozen=True, slots=True)
class RewriteResult:
    original_text: str
    normalized_text: str
    rewritten_text: str
    provider: str
    model: str
    fallback_used: bool
    decisions: tuple[AppliedDecision, ...]
    latency_ms: float
    usage: Mapping[str, int | float | str | None] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "rewritten_text": self.rewritten_text,
            "provider": self.provider,
            "model": self.model,
            "fallback_used": self.fallback_used,
            "decisions": [asdict(decision) for decision in self.decisions],
            "latency_ms": self.latency_ms,
            "usage": dict(self.usage),
            "diagnostics": list(self.diagnostics),
        }


DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "span_id": {"type": "string"},
                    "action": {"type": "string", "enum": [action.value for action in DecisionAction]},
                    "candidate_id": {"type": ["string", "null"]},
                    "confidence": {"type": "number"},
                    "reason_code": {"type": "string", "enum": [reason.value for reason in ReasonCode]},
                },
                "required": ["span_id", "action", "candidate_id", "confidence", "reason_code"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["decisions"],
    "additionalProperties": False,
}


def parse_provider_payload(
    payload: Any,
    *,
    provider: str,
    model: str,
    usage: Mapping[str, int | float | str | None] | None = None,
) -> ProviderResponse:
    """구조화 출력이더라도 신뢰하지 않고 로컬에서 계약을 다시 검사합니다."""
    if not isinstance(payload, dict) or set(payload) != {"decisions"}:
        raise InvalidProviderOutputError("provider output must contain only 'decisions'")
    raw_decisions = payload["decisions"]
    if not isinstance(raw_decisions, list):
        raise InvalidProviderOutputError("'decisions' must be a list")

    selections = []
    seen_spans = set()
    required = {"span_id", "action", "candidate_id", "confidence", "reason_code"}
    for raw in raw_decisions:
        if not isinstance(raw, dict) or set(raw) != required:
            raise InvalidProviderOutputError("each decision must match the exact schema")
        span_id = raw["span_id"]
        candidate_id = raw["candidate_id"]
        confidence = raw["confidence"]
        if not isinstance(span_id, str) or not span_id or span_id in seen_spans:
            raise InvalidProviderOutputError("span_id must be a unique non-empty string")
        if candidate_id is not None and not isinstance(candidate_id, str):
            raise InvalidProviderOutputError("candidate_id must be a string or null")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise InvalidProviderOutputError("confidence must be numeric")
        if not 0.0 <= confidence <= 1.0:
            raise InvalidProviderOutputError("confidence must be between 0 and 1")
        try:
            action = DecisionAction(raw["action"])
            reason_code = ReasonCode(raw["reason_code"])
        except ValueError as error:
            raise InvalidProviderOutputError(str(error)) from error
        if action is DecisionAction.REPLACE and not candidate_id:
            raise InvalidProviderOutputError("replace requires candidate_id")
        if action is not DecisionAction.REPLACE and candidate_id is not None:
            raise InvalidProviderOutputError("keep/abstain must use a null candidate_id")

        seen_spans.add(span_id)
        selections.append(
            ProviderSelection(
                span_id=span_id,
                action=action,
                candidate_id=candidate_id,
                confidence=float(confidence),
                reason_code=reason_code,
            )
        )

    return ProviderResponse(
        selections=tuple(selections),
        provider=provider,
        model=model,
        usage={} if usage is None else dict(usage),
    )
