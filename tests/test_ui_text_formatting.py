from __future__ import annotations

import unittest

from ui.text_formatting import format_long_text_html


class TestUITextFormatting(unittest.TestCase):
    def test_formats_inline_math_as_readable_fallback(self) -> None:
        html = format_long_text_html("公式是 $E=mc^2$。")

        self.assertIn('class="math-inline"', html)
        self.assertIn("E=mc^2", html)

    def test_formats_display_math_as_readable_block(self) -> None:
        html = format_long_text_html("求和：$$\\sum_{i=1}^n i$$")

        self.assertIn('class="math-block"', html)
        self.assertIn("\\sum_{i=1}^n i", html)

    def test_does_not_treat_prices_as_math(self) -> None:
        html = format_long_text_html("价格是 $10，不是公式。")

        self.assertNotIn('class="math-inline"', html)
        self.assertIn("$10", html)

    def test_escapes_html_and_preserves_bold(self) -> None:
        html = format_long_text_html("**重点** <script>alert(1)</script>")

        self.assertIn("<strong>重点</strong>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)


if __name__ == "__main__":
    unittest.main()
