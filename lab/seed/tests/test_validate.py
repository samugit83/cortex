import unittest

from shop.util.validate import is_valid_email, is_valid_sku, normalize_phone


class ValidateTests(unittest.TestCase):
    def test_email(self):
        self.assertTrue(is_valid_email("ana@example.com"))
        self.assertFalse(is_valid_email("not an email"))

    def test_phone_digits(self):
        self.assertEqual(normalize_phone("333 123 4567"), "3331234567")

    def test_sku(self):
        self.assertTrue(is_valid_sku("MUG-001"))
        self.assertFalse(is_valid_sku("mug-1"))


if __name__ == "__main__":
    unittest.main()
