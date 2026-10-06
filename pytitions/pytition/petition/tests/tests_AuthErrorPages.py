from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import add_default_data


class AuthPagesTest(TestCase):
    """Login, registration and password reset on the design system (PUB-07)"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_login_has_labelled_fields_and_a_summary_on_error(self):
        html = self.client.get(reverse('login')).content.decode()
        self.assertIn('<label class="fp-label" for="id_username">', html)
        self.assertIn('<label class="fp-label" for="id_password">', html)
        self.assertNotIn('placeholder="Username"', html)
        response = self.client.post(reverse('login'), {'username': 'julia', 'password': 'wrong'})
        self.assertContains(response, 'class="fp-error-summary" role="alert"')
        self.assertContains(response, "Your username and password didn")

    @override_settings(ALLOW_REGISTER=True)
    def test_register_lists_errors_with_links_to_fields(self):
        self.client.get(reverse('register'))
        response = self.client.post(reverse('register'), {'username': 'new', 'answer': 0})
        self.assertContains(response, 'href="#id_email"')
        self.assertContains(response, '<div class="fp-help" id="id_password1-help">')
        self.assertNotContains(response, '<style>')

    def test_password_reset_pages(self):
        html = self.client.get(reverse('password_reset')).content.decode()
        self.assertIn('<label class="fp-label" for="id_email">', html)
        html = self.client.get(reverse('password_reset_done')).content.decode()
        self.assertIn('role="status"', html)
        html = self.client.get(reverse('password_reset_confirm', args=['MQ', 'set-password'])).content.decode()
        self.assertIn('This link is no longer valid', html)
        self.assertIn('class="fp-container fp-auth"', html)


@override_settings(DEBUG=False)
class ErrorPagesTest(TestCase):
    """Error pages (PUB-08)"""

    def test_404_uses_the_site_layout(self):
        response = self.client.get('/petition/user/nobody-here')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found', status_code=404)
        self.assertContains(response, 'class="fp-header"', status_code=404)

    def test_500_renders_without_context(self):
        html = render_to_string('500.html')
        self.assertTrue(html.startswith('<!DOCTYPE html>'))
        self.assertIn('css/fp-components.css', html)
        self.assertNotIn('<script', html)
