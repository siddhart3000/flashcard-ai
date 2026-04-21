import json
from typing import Dict, List

from groq import Groq

MAX_INPUT_CHARS = 12000

SYSTEM_PROMPT = """You are an expert teacher.

Generate exactly {num_cards} high-quality flashcards.

Each card must include:
- Clear conceptual question
- Concise but complete answer
- Difficulty: easy, medium, hard
- card_type: definition, concept, application, trick

Include:
- Definitions
- Conceptual understanding
- Application-based questions
- Edge cases

Avoid:
- Repetition
- Shallow questions

Make it exam-ready and useful for revision.

Return ONLY valid JSON:
{
  "flashcards": [
    {
      "question": "Question text",
      "answer": "Answer text",
      "difficulty": "easy | medium | hard",
      "card_type": "definition | concept | application | trick"
    }
  ]
}
"""


def _clean_json(raw: str) -> Dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def generate_flashcards_with_ai(
    api_key: str,
    source_text: str,
    num_cards: int,
    difficulty_focus: str,
    study_style: str,
) -> List[Dict]:
    client = Groq(api_key=api_key)
    difficulty_instruction = (
        "Use a balanced mix of easy, medium, and hard cards."
        if difficulty_focus == "mixed"
        else f"Focus mostly on {difficulty_focus} difficulty cards."
    )
    style_instruction = (
        "Prioritize conceptual understanding and why-questions."
        if study_style == "conceptual"
        else "Prioritize exam-style prompts, edge cases, and quick recall."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(num_cards=num_cards)},
            {
                "role": "user",
                "content": (
                    f"{difficulty_instruction}\n"
                    f"{style_instruction}\n\n"
                    f"Create exactly {num_cards} unique cards from this content:\n\n"
                    f"{source_text[:MAX_INPUT_CHARS]}"
                ),
            },
        ],
        temperature=0.3,
    )
    content = response.choices[0].message.content
    parsed = _clean_json(content)
    cards = parsed.get("flashcards", [])
    if not isinstance(cards, list):
        raise ValueError("Invalid flashcard response format from AI.")
    return cards[:num_cards]


def generate_deeper_explanation(api_key: str, question: str, answer: str) -> str:
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are an expert tutor. Provide a deeper but concise explanation with one practical example.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\nCurrent answer: {answer}\nExplain this better for revision.",
            },
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()
