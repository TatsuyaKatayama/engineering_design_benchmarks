from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PACKAGE_ROOT / "knowledge"
PAST_FAILURES_PATH = KNOWLEDGE_DIR / "public_past_failures.jsonl"
GENERATION_SPECS_PATH = KNOWLEDGE_DIR / "public_generation_specs.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[一-龯ぁ-んァ-ヶー]+")


@dataclass(frozen=True)
class SearchResult:
    id: str
    title: str
    summary: str
    lesson: str
    tags: list[str]
    generation: str | None
    severity: str
    confidence: str
    applicability: str
    contradicts: list[str]
    score: float
    matched_terms: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "lesson": self.lesson,
            "tags": self.tags,
            "generation": self.generation,
            "severity": self.severity,
            "confidence": self.confidence,
            "applicability": self.applicability,
            "contradicts": self.contradicts,
            "score": round(self.score, 6),
            "matched_terms": self.matched_terms,
        }


def search_failure_knowledge(
    query: str,
    top_k: int = 5,
    path: Path = PAST_FAILURES_PATH,
) -> dict[str, Any]:
    if not query.strip():
        raise ValueError("query must not be empty")
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    records = load_past_failures(path)
    query_tokens = tokenize(query)
    scored = [score_record(record, query, query_tokens, records) for record in records]
    results = [result for result in scored if result.score > 0]
    results.sort(key=lambda r: (-r.score, severity_rank(r.severity), r.id))

    return {
        "query": query,
        "top_k": top_k,
        "result_count": min(len(results), top_k),
        "results": [result.to_dict() for result in results[:top_k]],
    }


def get_generation_specs(
    generation: str | None = None,
    path: Path = GENERATION_SPECS_PATH,
) -> dict[str, Any]:
    data = load_json(path)
    generations = data["generations"]
    if generation is None:
        return data
    if generation not in generations:
        raise ValueError(f"unknown generation: {generation}")
    return {"generation": generation, "specs": generations[generation]}


def load_past_failures(path: Path = PAST_FAILURES_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            validate_past_failure_record(record, line_number)
            records.append(record)
    return records


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def score_record(
    record: dict[str, Any],
    raw_query: str,
    query_tokens: list[str],
    corpus: list[dict[str, Any]],
) -> SearchResult:
    title_tokens = set(tokenize(record["title"]))
    summary_tokens = set(tokenize(record["summary"]))
    lesson_tokens = set(tokenize(record["lesson"]))
    tag_tokens = {normalize_token(tag) for tag in record["tags"]}
    body_tokens = title_tokens | summary_tokens | lesson_tokens | tag_tokens
    corpus_size = len(corpus)
    score = 0.0
    matched_terms: list[str] = []

    for token in query_tokens:
        if token in tag_tokens:
            score += 5.0
            matched_terms.append(token)
        if token in title_tokens:
            score += 3.0
            matched_terms.append(token)
        if token in summary_tokens:
            score += 1.5
            matched_terms.append(token)
        if token in lesson_tokens:
            score += 1.2
            matched_terms.append(token)
        if token in body_tokens:
            score += inverse_document_frequency(token, corpus, corpus_size)

    normalized_query = normalize_text(raw_query)
    normalized_title = normalize_text(record["title"])
    normalized_summary = normalize_text(record["summary"])
    if normalized_query and normalized_query in normalized_title:
        score += 4.0
    if normalized_query and normalized_query in normalized_summary:
        score += 2.0

    score *= applicability_multiplier(record["applicability"])
    score *= confidence_multiplier(record["confidence"])
    score -= deprecation_penalty(record)

    return SearchResult(
        id=record["id"],
        title=record["title"],
        summary=record["summary"],
        lesson=record["lesson"],
        tags=list(record["tags"]),
        generation=record.get("generation"),
        severity=record["severity"],
        confidence=record["confidence"],
        applicability=record["applicability"],
        contradicts=list(record.get("contradicts", [])),
        score=max(score, 0.0),
        matched_terms=sorted(set(matched_terms)),
    )


def tokenize(text: str) -> list[str]:
    return [normalize_token(match.group(0)) for match in TOKEN_RE.finditer(text)]


def normalize_token(token: str) -> str:
    return token.lower().replace("-", "_")


def normalize_text(text: str) -> str:
    return " ".join(tokenize(text))


def inverse_document_frequency(
    token: str,
    corpus: list[dict[str, Any]],
    corpus_size: int,
) -> float:
    containing = 0
    for record in corpus:
        haystack = " ".join(
            [
                record["title"],
                record["summary"],
                record["lesson"],
                " ".join(record["tags"]),
            ]
        )
        if token in set(tokenize(haystack)):
            containing += 1
    return math.log((1.0 + corpus_size) / (1.0 + containing)) + 1.0


def applicability_multiplier(value: str) -> float:
    return {"high": 1.25, "medium": 1.0, "low": 0.55}.get(value, 1.0)


def confidence_multiplier(value: str) -> float:
    return {"high": 1.1, "medium": 1.0, "low": 0.85}.get(value, 1.0)


def deprecation_penalty(record: dict[str, Any]) -> float:
    if record.get("generation") == "gen1" and record["applicability"] == "low":
        return 1.5
    return 0.0


def severity_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity, 4)


def validate_past_failure_record(record: dict[str, Any], line_number: int) -> None:
    required = {
        "id",
        "title",
        "summary",
        "lesson",
        "tags",
        "severity",
        "confidence",
        "applicability",
    }
    missing = sorted(required - set(record))
    if missing:
        raise ValueError(f"line {line_number}: missing fields: {', '.join(missing)}")
    if not isinstance(record["tags"], list) or not all(isinstance(tag, str) for tag in record["tags"]):
        raise ValueError(f"line {line_number}: tags must be a list of strings")
    if "contradicts" in record and not isinstance(record["contradicts"], list):
        raise ValueError(f"line {line_number}: contradicts must be a list")

