from __future__ import annotations

import argparse
import math
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence


WORD_LENGTH = 5
DATA_DIR = Path(__file__).with_name("data")
DEFAULT_ANSWERS_FILE = DATA_DIR / "answers.txt"
DEFAULT_ALLOWED_FILE = DATA_DIR / "allowed_guesses.txt"
FULL_RANKING_CANDIDATE_LIMIT = 200
SHORTLIST_CANDIDATE_GUESSES = 200
SHORTLIST_PROBE_GUESSES = 200


def normalize_word(word: str, *, label: str = "word") -> str:
    normalized = word.strip().lower()
    if len(normalized) != WORD_LENGTH or not normalized.isalpha():
        raise ValueError(
            f"{label} must be a {WORD_LENGTH}-letter alphabetic word: {word!r}"
        )
    return normalized


def normalize_feedback(feedback: str) -> str:
    normalized = feedback.strip().lower()
    if len(normalized) != WORD_LENGTH or any(symbol not in {"g", "y", "b"} for symbol in normalized):
        raise ValueError(
            f"feedback must be {WORD_LENGTH} letters of g, y, or b: {feedback!r}"
        )
    return normalized


def load_word_list(path: Path) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            text = raw_line.strip()
            if not text:
                continue

            word = normalize_word(text, label=f"{path.name}:{line_number}")
            if word in seen:
                continue

            seen.add(word)
            words.append(word)

    return words


def merge_word_lists(*lists: Iterable[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for words in lists:
        for word in words:
            if word in seen:
                continue
            seen.add(word)
            merged.append(word)

    return merged


def load_solver_data(
    answers_file: Path = DEFAULT_ANSWERS_FILE,
    allowed_file: Path = DEFAULT_ALLOWED_FILE,
) -> tuple[list[str], list[str]]:
    answers = load_word_list(answers_file)
    extra_guesses = load_word_list(allowed_file)
    allowed_guesses = merge_word_lists(answers, extra_guesses)
    return answers, allowed_guesses


@lru_cache(maxsize=262_144)
def _score_guess_cached(answer: str, guess: str) -> str:
    feedback = ["b"] * WORD_LENGTH
    remaining_letters = [0] * 26

    for index in range(WORD_LENGTH):
        answer_letter = answer[index]
        guess_letter = guess[index]
        if answer_letter == guess_letter:
            feedback[index] = "g"
        else:
            remaining_letters[ord(answer_letter) - ord("a")] += 1

    for index in range(WORD_LENGTH):
        if feedback[index] == "g":
            continue

        guess_letter_index = ord(guess[index]) - ord("a")
        if remaining_letters[guess_letter_index] > 0:
            feedback[index] = "y"
            remaining_letters[guess_letter_index] -= 1

    return "".join(feedback)


def score_guess(answer: str, guess: str) -> str:
    answer = normalize_word(answer, label="answer")
    guess = normalize_word(guess, label="guess")
    return _score_guess_cached(answer, guess)


def filter_candidates(
    candidates: Sequence[str], guess: str, feedback: str
) -> list[str]:
    normalized_guess = normalize_word(guess, label="guess")
    normalized_feedback = normalize_feedback(feedback)
    return [
        candidate
        for candidate in candidates
        if _score_guess_cached(candidate, normalized_guess) == normalized_feedback
    ]


def apply_feedback_history(
    candidates: Sequence[str], history: Sequence[tuple[str, str]]
) -> list[str]:
    remaining = list(candidates)

    for guess, feedback in history:
        remaining = filter_candidates(remaining, guess, feedback)

    return remaining


def guess_entropy(candidates: Sequence[str], guess: str) -> float:
    total = len(candidates)
    if total == 0:
        return 0.0

    partitions = Counter(_score_guess_cached(answer, guess) for answer in candidates)
    entropy = 0.0

    for partition_size in partitions.values():
        probability = partition_size / total
        entropy -= probability * math.log2(probability)

    return entropy


def build_frequency_tables(
    candidates: Sequence[str],
) -> tuple[Counter[str], list[Counter[str]]]:
    letter_counts: Counter[str] = Counter()
    positional_counts = [Counter() for _ in range(WORD_LENGTH)]

    for candidate in candidates:
        seen_letters: set[str] = set()

        for index, letter in enumerate(candidate):
            positional_counts[index][letter] += 1
            if letter not in seen_letters:
                letter_counts[letter] += 1
                seen_letters.add(letter)

    return letter_counts, positional_counts


def heuristic_guess_score(
    guess: str,
    letter_counts: Counter[str],
    positional_counts: Sequence[Counter[str]],
) -> int:
    score = 0
    seen_letters: set[str] = set()

    for index, letter in enumerate(guess):
        score += positional_counts[index][letter]
        if letter not in seen_letters:
            score += letter_counts[letter]
            seen_letters.add(letter)

    return score


def build_guess_pool(
    candidates: Sequence[str], allowed_guesses: Sequence[str]
) -> list[str]:
    candidate_list = list(candidates)
    guess_list = list(allowed_guesses)

    if len(candidate_list) <= FULL_RANKING_CANDIDATE_LIMIT:
        return guess_list

    letter_counts, positional_counts = build_frequency_tables(candidate_list)

    ranked_candidates = sorted(
        candidate_list,
        key=lambda word: (
            -heuristic_guess_score(word, letter_counts, positional_counts),
            word,
        ),
    )[:SHORTLIST_CANDIDATE_GUESSES]

    candidate_guess_set = set(ranked_candidates)
    ranked_probes = sorted(
        (
            (
                heuristic_guess_score(guess, letter_counts, positional_counts),
                guess,
            )
            for guess in guess_list
            if guess not in candidate_guess_set
        ),
        key=lambda item: (-item[0], item[1]),
    )

    probe_guesses = [
        guess for _, guess in ranked_probes[:SHORTLIST_PROBE_GUESSES]
    ]
    return merge_word_lists(ranked_candidates, probe_guesses)


def rank_guesses(
    candidates: Sequence[str], allowed_guesses: Sequence[str], limit: int | None = 10
) -> list[tuple[str, float]]:
    candidate_list = list(candidates)
    if not candidate_list:
        return []

    candidate_set = set(candidate_list)
    guess_pool = build_guess_pool(candidate_list, allowed_guesses)
    ranked: list[tuple[str, float, bool]] = []

    for guess in guess_pool:
        entropy = guess_entropy(candidate_list, guess)
        ranked.append((guess, entropy, guess in candidate_set))

    ranked.sort(key=lambda item: (-item[1], not item[2], item[0]))
    trimmed = ranked if limit is None else ranked[:limit]
    return [(guess, entropy) for guess, entropy, _ in trimmed]


def choose_best_guess(candidates: Sequence[str], allowed_guesses: Sequence[str]) -> str | None:
    ranked = rank_guesses(candidates, allowed_guesses, limit=1)
    return ranked[0][0] if ranked else None


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple Wordle solver")
    parser.add_argument(
        "--guess",
        action="append",
        default=[],
        help="Guess word. Repeat with --feedback for multiple turns.",
    )
    parser.add_argument(
        "--feedback",
        action="append",
        default=[],
        help="Feedback pattern using g, y, and b. Repeat with --guess.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of ranked guesses to print (default: 10).",
    )
    parser.add_argument(
        "--answers-file",
        type=Path,
        default=DEFAULT_ANSWERS_FILE,
        help=f"Candidate answer list (default: {DEFAULT_ANSWERS_FILE}).",
    )
    parser.add_argument(
        "--allowed-file",
        type=Path,
        default=DEFAULT_ALLOWED_FILE,
        help=f"Extra allowed guess list (default: {DEFAULT_ALLOWED_FILE}).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if len(args.guess) != len(args.feedback):
        parser.error("Each --guess must have a matching --feedback.")
    if args.top < 1:
        parser.error("--top must be at least 1.")

    try:
        answers, allowed_guesses = load_solver_data(args.answers_file, args.allowed_file)
        normalized_guesses = [normalize_word(word, label="guess") for word in args.guess]
        normalized_feedbacks = [normalize_feedback(value) for value in args.feedback]
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    candidates = apply_feedback_history(
        answers, list(zip(normalized_guesses, normalized_feedbacks))
    )

    print(f"Remaining candidates: {len(candidates)}")

    if not candidates:
        print("No candidates match the supplied feedback.")
        return 0

    print("Top next guesses:")
    for index, (guess, entropy) in enumerate(
        rank_guesses(candidates, allowed_guesses, limit=args.top), start=1
    ):
        marker = " candidate" if guess in candidates else ""
        print(f"{index:>2}. {guess}  entropy={entropy:.3f}{marker}")

    best_guess = choose_best_guess(candidates, allowed_guesses)
    if best_guess:
        print(f"Best guess: {best_guess}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
