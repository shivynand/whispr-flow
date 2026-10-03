import unittest

from whispr.cleanup import clean


class CleanupTests(unittest.TestCase):
    def test_strips_fillers_and_adds_period(self) -> None:
        self.assertEqual(
            clean("um hey team uh the review moved"),
            "Hey team the review moved.",
        )

    def test_spoken_punctuation(self) -> None:
        self.assertEqual(
            clean("hey team comma the review moved period"),
            "Hey team, the review moved.",
        )

    def test_self_correction(self) -> None:
        self.assertEqual(
            clean("let's meet at 5 actually 6"),
            "Let's meet at 6.",
        )

    def test_scratch_that(self) -> None:
        self.assertEqual(
            clean("send the deck scratch that send the notes"),
            "Send the notes.",
        )

    def test_list(self) -> None:
        text = clean("shopping list number one apples number two bananas")
        self.assertIn("1. Apples", text)
        self.assertIn("2. Bananas", text)

    def test_empty(self) -> None:
        self.assertEqual(clean("   "), "")


if __name__ == "__main__":
    unittest.main()
