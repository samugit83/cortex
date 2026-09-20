import unittest

from shop.util.text import normalize_whitespace, pluralize, slugify, truncate


class TextTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Blue Mug (Large)"), "blue-mug-large")

    def test_truncate_short_text_is_untouched(self):
        self.assertEqual(truncate("short", 10), "short")

    def test_pluralize(self):
        self.assertEqual(pluralize(1, "item"), "1 item")
        self.assertEqual(pluralize(3, "item"), "3 items")
        self.assertEqual(pluralize(2, "box", "boxes"), "2 boxes")

    def test_normalize_whitespace(self):
        self.assertEqual(normalize_whitespace("  a \t b\n"), "a b")


if __name__ == "__main__":
    unittest.main()
