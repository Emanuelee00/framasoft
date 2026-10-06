import re
from pathlib import Path

from django.test import SimpleTestCase

CSS = Path(__file__).resolve().parent.parent / "static" / "css"


def luminance(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


class ContrastTest(SimpleTestCase):
    """FE-05: WCAG 2.1 AA contrast of the design tokens and of the colours used on the signer pages"""

    def setUp(self):
        self.tokens = dict(re.findall(r'--(fp-[\w-]+):\s*(#[0-9a-fA-F]{6})', (CSS / "fp-tokens.css").read_text()))

    def t(self, name):
        return self.tokens[name] if name.startswith("fp-") else name

    def test_text_pairs(self):
        white = "#ffffff"
        pairs = [
            ("fp-text", white), ("fp-text", "fp-primary-soft"), ("fp-text", "fp-success-bg"),
            ("fp-text", "fp-danger-bg"), ("fp-text", "fp-warning-bg"),
            ("fp-text-muted", white), ("fp-text-muted", "fp-primary-soft"),
            ("fp-primary", white), ("fp-primary-strong", "fp-primary-soft"),
            ("fp-primary-strong", "fp-success-bg"), ("fp-primary-strong", "fp-danger-bg"),
            ("fp-primary-strong", "fp-warning-bg"), ("fp-accent-text", white),
            ("fp-success", white), ("fp-danger", white), ("fp-danger", "fp-danger-bg"),
            (white, "fp-primary"), (white, "fp-primary-strong"), (white, "fp-danger"),
            # Design system (DS-01)
            ("fp-text", "fp-surface-alt"), ("fp-text-muted", "fp-surface-alt"), ("fp-text-muted", "fp-surface-muted"),
            ("fp-text-subtle", white), ("fp-primary", "fp-surface-alt"), ("fp-primary-strong", "fp-primary-subtle"),
            (white, "fp-primary-hover"), (white, "fp-danger-hover"), ("fp-text-on-primary", "fp-primary"),
            ("fp-disabled-text", "fp-disabled-bg"), ("fp-warning", "fp-warning-bg"), ("fp-success", "fp-success-bg"),
            ("fp-info", "fp-info-bg"), ("fp-accent-text", "fp-accent-soft"),
        ]
        for fg, bg in pairs:
            with self.subTest(fg=fg, bg=bg):
                self.assertGreaterEqual(contrast(self.t(fg), self.t(bg)), 4.5)

    def test_large_text_and_ui_pairs(self):
        pairs = [
            ("fp-success", "fp-success-bg"), ("fp-warning", "fp-warning-bg"),
            ("fp-border-strong", "#ffffff"), ("fp-primary-strong", "#ffffff"),
            ("fp-primary", "fp-primary-soft"), ("fp-accent", "#ffffff"),
            # Design system (DS-01): borders of controls, orange brand half (24px), kicker (white on orange, 20px)
            ("fp-success-border", "#ffffff"), ("fp-border-strong", "fp-surface-alt"), ("#ffffff", "fp-accent"),
        ]
        for fg, bg in pairs:
            with self.subTest(fg=fg, bg=bg):
                self.assertGreaterEqual(contrast(self.t(fg), self.t(bg)), 3)

    def test_text_on_the_veil_over_a_painting(self):
        """BRAND-04: text on --fp-veil stays readable whatever the painting below, even black"""
        veil = re.search(r'--fp-veil:\s*rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', (CSS / "fp-tokens.css").read_text())
        alpha = float(veil.group(4))
        worst = "#" + "".join("%02x" % round(int(veil.group(i)) * alpha) for i in (1, 2, 3))
        for fg in ("fp-text", "fp-text-muted"):
            with self.subTest(fg=fg):
                self.assertGreaterEqual(contrast(self.t(fg), worst), 4.5)

    def test_brand_icons(self):
        """BRAND-04: icons in rings and the badge of round paintings"""
        for fg, bg in (("fp-orange-6", "#ffffff"), ("fp-violet-6", "#ffffff"), ("fp-primary", "#ffffff"),
                       ("fp-text-on-primary", "fp-primary")):
            with self.subTest(fg=fg, bg=bg):
                self.assertGreaterEqual(contrast(self.t(fg), self.t(bg)), 3)

    def test_share_buttons_keep_white_labels_readable(self):
        components = (CSS / "fp-components.css").read_text()
        colours = re.findall(r'\.fp-share \.rrssb-buttons li\.rrssb-\w+ a(?::hover)? \{ background-color: (#[0-9a-fA-F]{6}); \}', components)
        self.assertGreaterEqual(len(colours), 6)
        for colour in colours:
            with self.subTest(colour=colour):
                self.assertGreaterEqual(contrast("#ffffff", colour), 4.5)

    def test_focus_ring_wins_over_bootstrap(self):
        tokens = (CSS / "fp-tokens.css").read_text()
        self.assertIn(":is(a, button, input, select, textarea, summary, [tabindex]):focus-visible", tokens)
        self.assertNotIn(":where(a, button", tokens)
