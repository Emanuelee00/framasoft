# framapetitions: S13/GD-15
import os
import re

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from petition.csp import build_policy
from petition.models import Organization, Petition, PytitionUser
from .utils import add_default_data

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
SCRIPT_TAG = re.compile(r'<script\b[^>]*>', re.I)
NONCE = re.compile(r"'nonce-([A-Za-z0-9_-]+)'")
INLINE_HANDLER = re.compile(r'<[^>]+\son[a-z]+\s*=', re.I)


def inline_scripts(html):
    return [tag for tag in SCRIPT_TAG.findall(html) if 'src=' not in tag]


class TemplateRulesTest(TestCase):
    """Templates follow the CSP rules: nonce on inline scripts, no inline event handlers."""

    def template_files(self):
        for root, _dirs, files in os.walk(TEMPLATES_DIR):
            for name in files:
                if name.endswith('.html'):
                    path = os.path.join(root, name)
                    with open(path, encoding='utf-8') as f:
                        yield os.path.relpath(path, TEMPLATES_DIR), f.read()

    def test_inline_scripts_have_a_nonce(self):
        for name, content in self.template_files():
            for tag in inline_scripts(content):
                self.assertIn('nonce="{{ request.csp_nonce }}"', tag, name)

    def test_no_inline_event_handlers_or_javascript_urls(self):
        for name, content in self.template_files():
            self.assertIsNone(INLINE_HANDLER.search(content), name)
            self.assertNotIn('javascript:', content.lower(), name)

    def test_tinymce_callbacks_are_not_evaluated(self):
        # django-tinymce evals callbacks containing "(", and looks up plain names on window
        for key in ('images_upload_handler', 'setup'):
            self.assertNotIn('(', settings.TINYMCE_DEFAULT_CONFIG[key])
        self.assertIn('js/fp-tinymce.js', settings.TINYMCE_EXTRA_MEDIA['js'])


class SecurityHeadersTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def login(self, name):
        self.client.login(username=name, password=name)
        return PytitionUser.objects.get(user__username=name)

    def assert_nonce_matches(self, response):
        policy = response['Content-Security-Policy']
        nonces = NONCE.findall(policy)
        self.assertEqual(len(nonces), 1)
        html = response.content.decode()
        for tag in inline_scripts(html):
            self.assertIn('nonce="%s"' % nonces[0], tag)
        self.assertIsNone(INLINE_HANDLER.search(html))
        return nonces[0]

    def test_main_pages(self):
        petition = Petition.objects.filter(published=True, user__isnull=False).first()
        for url in (reverse('index'), reverse('detail', args=[petition.id]), reverse('login'),
                    reverse('search'), reverse('user_profile', args=['julia']), reverse('privacy_notice')):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assert_nonce_matches(response)
            self.assertEqual(response['Referrer-Policy'], 'same-origin')
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_creator_pages(self):
        julia = self.login('julia')
        petition = julia.petition_set.first()
        org = Organization.objects.get(name='Les Amis de la Terre')
        for url in (reverse('user_dashboard'), reverse('edit_petition', args=[petition.id]),
                    reverse('user_petition_wizard'), reverse('show_signatures', args=[petition.id]),
                    reverse('account_settings'), reverse('org_dashboard', args=[org.slugname])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assert_nonce_matches(response)

    def test_nonce_changes_on_each_request(self):
        first = self.assert_nonce_matches(self.client.get(reverse('login')))
        second = self.assert_nonce_matches(self.client.get(reverse('login')))
        self.assertNotEqual(first, second)

    def test_policy_restricts_scripts(self):
        policy = self.client.get(reverse('login'))['Content-Security-Policy']
        directives = dict(part.split(' ', 1) for part in policy.split('; '))
        self.assertNotIn("'unsafe-inline'", directives['script-src'])
        self.assertNotIn("'unsafe-eval'", directives['script-src'])
        self.assertEqual(directives['object-src'], "'none'")
        self.assertEqual(directives['base-uri'], "'self'")
        self.assertEqual(directives['frame-ancestors'], "'self'")
        # the preview tab of the petition settings frames the petition page (same origin, also over http)
        self.assertIn("'self'", directives['frame-src'].split())

    @override_settings(CSP_REPORT_ONLY=True)
    def test_report_only(self):
        response = self.client.get(reverse('login'))
        self.assertNotIn('Content-Security-Policy', response)
        self.assertIn("'nonce-", response['Content-Security-Policy-Report-Only'])

    @override_settings(CSP_DIRECTIVES=None)
    def test_disabled(self):
        response = self.client.get(reverse('login'))
        self.assertNotIn('Content-Security-Policy', response)
        self.assertNotIn('Content-Security-Policy-Report-Only', response)

    def test_build_policy(self):
        policy = build_policy({'script-src': ["'self'", '{nonce}'], 'object-src': ["'none'"]}, 'abc')
        self.assertEqual(policy, "script-src 'self' 'nonce-abc'; object-src 'none'")

    def test_hsts_on_https(self):
        response = self.client.get(reverse('login'), secure=True)
        self.assertEqual(response['Strict-Transport-Security'],
                         'max-age=%d' % settings.SECURE_HSTS_SECONDS)
        self.assertNotIn('Strict-Transport-Security', self.client.get(reverse('login')))

    def test_session_and_csrf_cookies(self):
        response = self.client.post(reverse('login'), {'username': 'julia', 'password': 'julia'})
        session = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(session['httponly'])
        self.assertEqual(session['samesite'], 'Lax')
        self.assertEqual(bool(session['secure']), settings.SESSION_COOKIE_SECURE)
        csrf = self.client.get(reverse('login')).cookies.get(settings.CSRF_COOKIE_NAME) \
            or response.cookies[settings.CSRF_COOKIE_NAME]
        self.assertTrue(csrf['httponly'])
        self.assertEqual(csrf['samesite'], 'Lax')

    def test_secure_cookie_defaults(self):
        # Without environment overrides, cookies are Secure and HSTS lasts one year
        if 'PYTITION_HTTPS' in os.environ or 'SESSION_COOKIE_SECURE' in os.environ:
            self.skipTest('overridden by the environment')
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertEqual(settings.SECURE_HSTS_SECONDS, 31536000)
