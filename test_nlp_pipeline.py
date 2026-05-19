import unittest

from nlp.pipeline import process_interim_text
from nlp.filters.repetition_filter import remove_overlap


class TestNlpPipeline(unittest.TestCase):
    def test_trim_incomplete_rish(self) -> None:
        # input: "my name is rish" , prev: "my name is" -> output: "my name is"
        res = process_interim_text("my name is rish", "my name is")
        self.assertEqual("my name is", res["text"])

    def test_blocklist_prefix(self) -> None:
        # Remove hallucinated prefix like "yeah" / "thank you" at the start.
        res = process_interim_text("yeah thank you for joining", "")
        self.assertEqual("for joining", res["text"])

    def test_noise_annotation_removal(self) -> None:
        # Remove (noise), [applause], and timestamps.
        res = process_interim_text("hello (noise) world [applause] [00:01:23]", "")
        self.assertEqual("hello world", res["text"])

    def test_chunk_overlap_cleanup(self) -> None:
        # Previous final + new interim that overlaps at the boundary.
        prev = "My name is Rishi"
        current = "Rishi is a developer"
        combined = remove_overlap(prev, current, {"min_overlap_chars": 3})
        self.assertEqual("My name is Rishi is a developer", combined)

    def test_no_false_prefix_when_no_overlap(self) -> None:
        # When there is no real overlap, we should not prefix the new
        # sentence with the previous one (e.g. avoid "my name This is ...").
        prev = "my name"
        current = "This is an python test."
        combined = remove_overlap(prev, current, {"min_overlap_chars": 3})
        self.assertEqual(current, combined)


if __name__ == "__main__":
    unittest.main()
