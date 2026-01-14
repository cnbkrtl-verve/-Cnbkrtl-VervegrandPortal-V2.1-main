import unittest
from utils_ui import render_badge

class TestUtilsUI(unittest.TestCase):

    def test_render_badge_default(self):
        expected = '<span class="badge badge-neutral">Test Badge</span>'
        result = render_badge("Test Badge")
        self.assertEqual(result, expected)

    def test_render_badge_variants(self):
        variants = ['success', 'warning', 'error', 'info', 'neutral']
        for variant in variants:
            expected = f'<span class="badge badge-{variant}">Test</span>'
            result = render_badge("Test", variant)
            self.assertEqual(result, expected)

    def test_render_badge_invalid_variant(self):
        expected = '<span class="badge badge-neutral">Test</span>'
        result = render_badge("Test", "invalid_variant")
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()
