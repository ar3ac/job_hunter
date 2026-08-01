from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable


DEFAULT_RULES: dict[str, Any] = {
    "minimum_score": 50,
    "notify_score": 60,
    "duplicate_window_days": 45,
    "hard_exclude": [
        "corso di formazione", "formazione gratuita", "corso gratuito",
        "academy", "masterclass", "webinar", "annuncio test", "job name: test",
    ],
    "seniority_exclude": [
        "senior", "sr.", "lead", "head of", "director", "dirigente",
    ],
    "contract_preferred": ["tempo indeterminato", "permanent"],
    "contract_exclude": [],
    "experience_max_years": None,
    "weights": {
        "title_required": 38,
        "description_required": 18,
        "positive_title": 10,
        "positive_description": 4,
        "preferred_contract": 12,
        "junior": 8,
        "location": 5,
        "missing_required": -45,
        "negative": -25,
        "seniority": -45,
        "experience_too_high": -30,
        "excluded_contract": -35,
    },
}


@dataclass(frozen=True)
class Evaluation:
    score: int
    status: str
    reasons: tuple[str, ...]
    matched_keywords: tuple[str, ...]
    contract_type: str | None
    experience_min: int | None
    experience_max: int | None
    seniority: str | None


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9+#]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _items(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item]


def _contains(text: str, phrase: str) -> bool:
    needle = normalize_text(phrase)
    if not needle:
        return False
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", text) is not None


def _matches(text: str, phrases: Iterable[str]) -> list[str]:
    return [phrase for phrase in phrases if _contains(text, phrase)]


def merge_rules(global_rules: dict | None, search: dict | None) -> dict[str, Any]:
    result = json.loads(json.dumps(DEFAULT_RULES))
    for source in (global_rules or {}, (search or {}).get("rules", {})):
        for key, value in source.items():
            if key == "weights":
                result["weights"].update(value or {})
            else:
                result[key] = value
    return result


def detect_contract(text: str) -> str | None:
    patterns = (
        ("tempo_indeterminato", ("tempo indeterminato", "contratto indeterminato", "permanent")),
        ("apprendistato", ("apprendistato",)),
        ("tirocinio", ("tirocinio", "stage", "internship")),
        ("partita_iva", ("partita iva", "p iva", "freelance")),
        ("somministrazione", ("somministrazione",)),
        ("tempo_determinato", ("tempo determinato", "contratto determinato", "fixed term")),
    )
    for name, terms in patterns:
        if any(_contains(text, term) for term in terms):
            return name
    return None


def detect_experience(text: str) -> tuple[int | None, int | None]:
    matches: list[tuple[int, int]] = []
    for pattern in (
        r"(?:almeno|minimo|min)\s*(\d{1,2})\s*anni",
        r"(\d{1,2})\s*(?:-|–|a)\s*(\d{1,2})\s*anni",
        r"(\d{1,2})\+?\s*anni\s+(?:di\s+)?esperienza",
        r"esperienza\s+(?:di\s+)?(?:almeno\s+)?(\d{1,2})\s*anni",
    ):
        for match in re.finditer(pattern, text):
            low = int(match.group(1))
            high = int(match.group(2)) if match.lastindex and match.lastindex > 1 else low
            if 0 < low <= high <= 50:
                matches.append((low, high))
    if not matches:
        return None, None
    return min(item[0] for item in matches), max(item[1] for item in matches)


def evaluate_job(job: dict, search: dict, global_rules: dict | None = None) -> Evaluation:
    rules = merge_rules(global_rules, search)
    weights = rules["weights"]
    title = normalize_text(job.get("title"))
    description = normalize_text(job.get("description"))
    combined = f"{title} {description}".strip()

    required = _items(search.get("required_any") or search.get("keywords"))
    positive = _items(search.get("positive_keywords"))
    negative = _items(search.get("exclude_keywords"))
    hard_exclude = _items(rules.get("hard_exclude"))
    seniority_exclude = _items(rules.get("seniority_exclude"))
    contract_exclude = _items(rules.get("contract_exclude"))

    title_required = _matches(title, required)
    description_required = _matches(description, required)
    positive_title = _matches(title, positive)
    positive_description = _matches(description, positive)
    negative_matches = _matches(combined, negative)
    hard_matches = _matches(combined, hard_exclude)
    senior_matches = _matches(combined, seniority_exclude)

    score = 35
    reasons: list[str] = []
    matched: list[str] = []
    rejected = False

    if title_required:
        score += weights["title_required"]
        matched.extend(title_required)
        reasons.append(f"ruolo richiesto nel titolo: {', '.join(title_required)}")
    elif description_required:
        score += weights["description_required"]
        matched.extend(description_required)
        reasons.append(f"ruolo richiesto nella descrizione: {', '.join(description_required)}")
    else:
        score += weights["missing_required"]
        reasons.append("nessuna keyword obbligatoria trovata")

    if positive_title:
        score += min(20, weights["positive_title"] * len(positive_title))
        matched.extend(positive_title)
        reasons.append(f"keyword preferite nel titolo: {', '.join(positive_title)}")
    if positive_description:
        score += min(12, weights["positive_description"] * len(positive_description))
        matched.extend(positive_description)
        reasons.append(f"keyword preferite nella descrizione: {', '.join(positive_description)}")
    if negative_matches:
        score += weights["negative"] * len(negative_matches)
        reasons.append(f"keyword fuori target: {', '.join(negative_matches)}")
    if hard_matches:
        rejected = True
        reasons.append(f"contenuto escluso: {', '.join(hard_matches)}")
    if senior_matches:
        score += weights["seniority"]
        rejected = True
        reasons.append(f"seniority non compatibile: {', '.join(senior_matches)}")

    seniority = None
    if senior_matches:
        seniority = "senior"
    elif _matches(combined, ("junior", "entry level", "prima esperienza")):
        seniority = "junior"
        score += weights["junior"]
        reasons.append("livello junior compatibile")

    contract = detect_contract(combined)
    preferred_contracts = _items(rules.get("contract_preferred"))
    if contract == "tempo_indeterminato" or _matches(combined, preferred_contracts):
        score += weights["preferred_contract"]
        reasons.append("contratto preferito: tempo indeterminato")
    if contract and contract in contract_exclude:
        score += weights["excluded_contract"]
        rejected = True
        reasons.append(f"contratto escluso: {contract}")

    experience_min, experience_max = detect_experience(combined)
    allowed_experience = rules.get("experience_max_years")
    if allowed_experience is not None and experience_min is not None:
        if experience_min > int(allowed_experience):
            score += weights["experience_too_high"]
            rejected = True
            reasons.append(f"esperienza minima troppo alta: {experience_min} anni")

    wanted_location = normalize_text(search.get("location"))
    actual_location = normalize_text(job.get("location_actual") or job.get("loc_company"))
    if wanted_location and actual_location and wanted_location in actual_location:
        score += weights["location"]
        reasons.append("località compatibile")

    score = max(0, min(100, int(score)))
    if rejected:
        status = "rejected"
    elif score >= int(rules["notify_score"]):
        status = "recommended"
    elif score >= int(rules["minimum_score"]):
        status = "review"
    else:
        status = "rejected"

    return Evaluation(
        score=score,
        status=status,
        reasons=tuple(reasons),
        matched_keywords=tuple(dict.fromkeys(matched)),
        contract_type=contract,
        experience_min=experience_min,
        experience_max=experience_max,
        seniority=seniority,
    )


def apply_evaluation(job: dict, search: dict, global_rules: dict | None = None) -> dict:
    enriched = dict(job)
    result = evaluate_job(enriched, search, global_rules)
    enriched.update(
        score=result.score,
        status=result.status,
        score_reasons=list(result.reasons),
        matched_keywords=list(result.matched_keywords),
        contract_type=result.contract_type,
        experience_min=result.experience_min,
        experience_max=result.experience_max,
        seniority=result.seniority,
        search=search.get("name") or "Ricerca",
        search_location=search.get("location"),
    )
    return enriched
