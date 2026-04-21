import random
from typing import Dict, List


def sanitize_cards(cards: List[Dict]) -> List[Dict]:
    sanitized: List[Dict] = []
    for card in cards:
        question = str(card.get("question", "")).strip()
        answer = str(card.get("answer", "")).strip()
        difficulty = str(card.get("difficulty", "medium")).strip().lower()
        card_type = str(card.get("card_type", "concept")).strip().lower()
        if not question or not answer:
            continue
        if difficulty not in {"easy", "medium", "hard"}:
            difficulty = "medium"
        if card_type not in {"definition", "concept", "application", "trick"}:
            card_type = "concept"
        sanitized.append(
            {
                "question": question,
                "answer": answer,
                "difficulty": difficulty,
                "card_type": card_type,
            }
        )
    return sanitized


def filter_by_mode(cards: List[Dict], mode: str, responses: Dict[int, bool]) -> List[int]:
    if not cards:
        return []
    if mode == "Hard Only":
        hard = [i for i, c in enumerate(cards) if c.get("difficulty") == "hard"]
        return hard or list(range(len(cards)))
    if mode == "Review Mistakes":
        mistakes = [i for i, known in responses.items() if not known and 0 <= i < len(cards)]
        return mistakes or list(range(len(cards)))
    if mode == "Unknown First":
        unknown = [i for i, known in responses.items() if not known and 0 <= i < len(cards)]
        remainder = [i for i in range(len(cards)) if i not in unknown]
        return unknown + remainder
    return list(range(len(cards)))


def weighted_review_order(indices: List[int], responses: Dict[int, bool], shuffle: bool) -> List[int]:
    weighted: List[int] = []
    for idx in indices:
        known = responses.get(idx)
        if known is False:
            weighted.extend([idx, idx, idx])
        elif known is True:
            weighted.extend([idx])
        else:
            weighted.extend([idx, idx])
    if shuffle:
        random.shuffle(weighted)
    return weighted or indices


def calculate_metrics(cards: List[Dict], responses: Dict[int, bool], streak: int, xp: int) -> Dict[str, float]:
    total = len(cards)
    known = sum(1 for value in responses.values() if value)
    unknown = sum(1 for value in responses.values() if value is False)
    answered = known + unknown
    accuracy = (known / answered * 100) if answered else 0.0
    mastery = (known / total * 100) if total else 0.0
    completion = (answered / total * 100) if total else 0.0
    return {
        "total": total,
        "known": known,
        "unknown": unknown,
        "answered": answered,
        "accuracy": accuracy,
        "mastery": mastery,
        "completion": completion,
        "streak": streak,
        "xp": xp,
    }
