import unittest

from solver import (
    apply_feedback_history,
    choose_best_guess,
    filter_candidates,
    score_guess,
)


class SolverTests(unittest.TestCase):
    def test_score_guess_handles_duplicate_letters_in_guess(self) -> None:
        self.assertEqual(score_guess("cigar", "array"), "bybgb")

    def test_score_guess_handles_duplicate_letters_in_answer(self) -> None:
        self.assertEqual(score_guess("belle", "level"), "ygbyy")

    def test_score_guess_handles_exact_match(self) -> None:
        self.assertEqual(score_guess("cigar", "cigar"), "ggggg")

    def test_score_guess_handles_no_match(self) -> None:
        self.assertEqual(score_guess("cigar", "blush"), "bbbbb")

    def test_filter_candidates_keeps_only_words_with_matching_feedback(self) -> None:
        candidates = ["cigar", "caper", "carry", "cairn"]
        self.assertEqual(filter_candidates(candidates, "array", "bybgb"), ["cigar"])

    def test_filter_candidates_supports_exact_match_feedback(self) -> None:
        candidates = ["cigar", "rebut"]
        self.assertEqual(filter_candidates(candidates, "cigar", "ggggg"), ["cigar"])

    def test_filter_candidates_supports_no_match_feedback(self) -> None:
        candidates = ["cigar", "tempo", "blush"]
        self.assertEqual(
            filter_candidates(candidates, "blush", "bbbbb"),
            ["cigar", "tempo"],
        )

    def test_choose_best_guess_prefers_a_candidate_on_entropy_ties(self) -> None:
        candidates = ["cigar", "rebut"]
        allowed_guesses = ["crane", "cigar", "rebut"]
        self.assertEqual(choose_best_guess(candidates, allowed_guesses), "cigar")

    def test_apply_feedback_history_filters_multiple_rounds(self) -> None:
        answers = ["cigar", "humor", "robot", "storm"]
        history = [("crane", "bybbb"), ("storm", "bbyyy")]
        self.assertEqual(apply_feedback_history(answers, history), ["humor"])


if __name__ == "__main__":
    unittest.main()
