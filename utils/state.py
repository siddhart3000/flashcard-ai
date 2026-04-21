import random
from typing import Dict, List

import streamlit as st

from services.flashcards import filter_by_mode, weighted_review_order


def init_state() -> None:
    defaults = {
        "cards": [],
        "responses": {},
        "review_sequence": [],
        "review_pointer": 0,
        "show_answer": False,
        "study_mode": "Normal",
        "shuffle_mode": False,
        "exam_mode": True,
        "streak": 0,
        "xp": 0,
        "explanations": {},
        "generation_success": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_study_state(cards: List[Dict], study_mode: str, shuffle_mode: bool, exam_mode: bool) -> None:
    st.session_state.cards = cards
    st.session_state.responses = {}
    st.session_state.review_pointer = 0
    st.session_state.show_answer = not exam_mode
    st.session_state.streak = 0
    st.session_state.xp = 0
    st.session_state.explanations = {}
    st.session_state.study_mode = study_mode
    st.session_state.shuffle_mode = shuffle_mode
    st.session_state.exam_mode = exam_mode
    refresh_sequence()


def refresh_sequence() -> None:
    cards = st.session_state.cards
    indices = filter_by_mode(cards, st.session_state.study_mode, st.session_state.responses)
    weighted = weighted_review_order(indices, st.session_state.responses, st.session_state.shuffle_mode)
    if st.session_state.shuffle_mode:
        random.shuffle(weighted)
    st.session_state.review_sequence = weighted
    st.session_state.review_pointer = min(st.session_state.review_pointer, max(len(weighted) - 1, 0))


def get_current_card_index() -> int:
    sequence = st.session_state.review_sequence
    if not sequence:
        return 0
    pointer = max(0, min(st.session_state.review_pointer, len(sequence) - 1))
    st.session_state.review_pointer = pointer
    return sequence[pointer]


def next_card() -> None:
    if st.session_state.review_pointer < len(st.session_state.review_sequence) - 1:
        st.session_state.review_pointer += 1
    else:
        refresh_sequence()
        st.session_state.review_pointer = 0
    if st.session_state.exam_mode:
        st.session_state.show_answer = False


def previous_card() -> None:
    if st.session_state.review_pointer > 0:
        st.session_state.review_pointer -= 1
    if st.session_state.exam_mode:
        st.session_state.show_answer = False


def record_answer(knew: bool) -> None:
    card_idx = get_current_card_index()
    st.session_state.responses[card_idx] = knew
    if knew:
        st.session_state.streak += 1
        st.session_state.xp += 10
    else:
        st.session_state.streak = 0
        st.session_state.xp += 3
    refresh_sequence()
    next_card()
