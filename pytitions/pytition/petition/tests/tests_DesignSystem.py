import re
from pathlib import Path

from django import forms
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import add_default_data

from petition.models import Petition


class LayoutTest(TestCase):
    """DS-03: header, landmarks, footer and scripts of the base layout"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def pages(self):
        petition = Petition.objects.filter(published=True).first()
        return [reverse('index'), reverse('detail', args=[petition.id]), reverse('login'), reverse('privacy_notice')]

    def test_landmarks(self):
        for url in self.pages():
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertIn('<html lang="en" class="no-js">', html)
                self.assertEqual(html.count('<header class="fp-header">'), 1)
                self.assertEqual(html.count('<main id="main"'), 1)
                self.assertEqual(html.count('<footer'), 1)
                self.assertNotIn('role="contentinfo"', html)
                self.assertIn('<nav aria-label="Main navigation">', html)
                self.assertLess(html.index('<header class="fp-header">'), html.index('<main id="main"'))
                self.assertLess(html.index('<main id="main"'), html.index('<footer class="fp-footer">'))

    def test_footer_links(self):
        html = self.client.get(reverse('login')).content.decode()
        footer = html[html.index('<footer class="fp-footer">'):]
        self.assertIn('href="{}"'.format(reverse('privacy_notice')), footer)
        self.assertIn('href="https://framasoft.org/"', footer)
        self.assertIn('<label for="fp-language" class="sr-only">', footer)

    def test_scripts_do_not_block_rendering(self):
        html = self.client.get(reverse('login')).content.decode()
        self.assertIn('<script src="https://framasoft.org/nav/nav.js" defer></script>', html)
        self.assertRegex(html, r'<script src="[^"]*js/fp-ui\.js" defer></script>')

    def test_user_area(self):
        html = self.client.get(reverse('index')).content.decode()
        self.assertIn('href="{}?next='.format(reverse('login')), html)
        self.assertNotIn('class="fp-menu"', html)
        self.client.login(username='julia', password='julia')
        html = self.client.get(reverse('index')).content.decode()
        self.assertIn('<details class="fp-menu">', html)
        self.assertIn('href="{}"'.format(reverse('user_dashboard')), html)
        self.assertIn('href="{}"'.format(reverse('org_dashboard', args=['rap'])), html)

    def test_dashboard_uses_the_shared_header(self):
        self.client.login(username='julia', password='julia')
        html = self.client.get(reverse('user_dashboard')).content.decode()
        self.assertEqual(html.count('<header class="fp-header">'), 1)
        self.assertIn('fp-container fp-container-fluid fp-header-bar', html)
        self.assertNotIn('navbar-dark', html)


class StyleguideTest(TestCase):
    """DS-05: the design system reference is only served in development"""

    def test_hidden_in_production(self):
        self.assertEqual(self.client.get(reverse('styleguide')).status_code, 404)

    @override_settings(DEBUG=True)
    def test_shows_every_component(self):
        response = self.client.get(reverse('styleguide'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for css_class in ('fp-btn-primary', 'fp-btn-secondary', 'fp-btn-tertiary', 'fp-btn-danger', 'fp-field',
                          'fp-petition-card', 'fp-badge', 'fp-alert', 'fp-table', 'fp-pagination', 'fp-tabs',
                          'fp-stepper', 'fp-empty', 'fp-progress-bar', 'fp-dialog', 'fp-menu'):
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, html)
        # Every example comes with its escaped markup
        self.assertGreaterEqual(html.count('<details class="fp-example-code">'), 20)
        self.assertIn('&lt;button type=&quot;button&quot; class=&quot;fp-btn fp-btn-primary&quot;&gt;', html)


class DemoForm(forms.Form):
    email = forms.EmailField(label="Email", help_text="We never show it.")
    city = forms.CharField(label="City", required=False)
    agree = forms.BooleanField(label="I agree")


class ComponentsTest(TestCase):
    """DS-04: template components"""

    def test_field_wires_help_and_errors(self):
        form = DemoForm(data={"email": "nope"})
        form.is_valid()
        html = render_to_string("components/field.html", {"field": form["email"]})
        self.assertIn('<label class="fp-label" for="id_email">Email</label>', html)
        self.assertIn('id="id_email-help"', html)
        self.assertIn('id="id_email-error"', html)
        tag = re.search(r'<input[^>]*name="email"[^>]*>', html).group(0)
        self.assertIn('class="fp-input"', tag)
        self.assertIn('aria-invalid="true"', tag)
        self.assertIn('aria-describedby="id_email-help id_email-error"', tag)

    def test_field_marks_optional_and_checkbox(self):
        form = DemoForm()
        html = render_to_string("components/field.html", {"field": form["city"]})
        self.assertIn('<span class="fp-optional">(optional)</span>', html)
        self.assertNotIn('aria-invalid', html)
        html = render_to_string("components/field.html", {"field": form["agree"]})
        self.assertIn('class="fp-check-input"', html)
        self.assertLess(html.index('<input'), html.index('<label'))

    def test_pagination(self):
        page = Paginator(range(200), 10).page(5)
        html = render_to_string("components/pagination.html", {"page": page, "query": "sort=asc"})
        self.assertIn('<nav class="fp-pagination" aria-label="Pagination">', html)
        self.assertIn('href="?page=5&amp;sort=asc" aria-current="page"', html)
        self.assertIn('rel="prev" href="?page=4&amp;sort=asc"', html)
        self.assertIn('rel="next" href="?page=6&amp;sort=asc"', html)
        self.assertIn('href="?page=20&amp;sort=asc"', html)
        self.assertNotIn('href="?page=10&amp;', html)
        self.assertEqual(render_to_string("components/pagination.html", {"page": Paginator(range(5), 10).page(1)}).strip(), "")

    def test_icon_is_decorative_unless_labelled(self):
        html = render_to_string("components/icon.html", {"name": "person"})
        self.assertIn('aria-hidden="true"', html)
        self.assertIn('fontawesome-free-6.5.2/sprite.svg#person"', html)
        html = render_to_string("components/icon.html", {"name": "globe", "label": "Language"})
        self.assertIn('role="img" aria-label="Language"', html)
        self.assertNotIn('aria-hidden', html)

    def test_every_icon_name_is_in_the_sprite(self):
        base = Path(__file__).resolve().parent.parent
        sprite = (base / "static/vendor/fontawesome-free-6.5.2/sprite.svg").read_text()
        symbols = set(re.findall(r'<symbol id="([a-z0-9-]+)"', sprite))
        used = set()
        for template in (base / "templates").rglob("*.html"):
            text = template.read_text()
            used.update(re.findall(r'components/icon\.html" with name="([a-z0-9-]+)"', text))
            used.update(re.findall(r'empty_state\.html" with icon="([a-z0-9-]+)"', text))
        self.assertTrue(used)
        self.assertEqual(used - symbols, set())
