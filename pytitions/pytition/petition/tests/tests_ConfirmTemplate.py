from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.models import Petition


class ConfirmTemplateTest(TestCase):
    """petition/confirm.html: one page per state of the confirmation (view: GD-06 / FE-03)"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()
        self.request = RequestFactory().get('/')

    def render(self, state, **extra):
        ctx = {'petition': self.petition, 'state': state, 'confirmation_hash': 'abc123'}
        ctx.update(extra)
        return render_to_string('petition/confirm.html', ctx, request=self.request)

    def test_confirm_state_is_a_post_form_with_csrf(self):
        html = self.render('confirm')
        self.assertIn('method="post"', html)
        self.assertIn('action="{}"'.format(reverse('confirm', args=[self.petition.id, 'abc123'])), html)
        self.assertIn('csrfmiddlewaretoken', html)
        self.assertIn(self.petition.title, html)
        self.assertIn('<meta name="robots" content="noindex">', html)

    def test_confirmed_state(self):
        html = self.render('confirmed', manage_url='https://example.org/manage/xyz')
        self.assertIn('role="status"', html)
        self.assertIn('Your signature is counted', html)
        self.assertIn('href="https://example.org/manage/xyz"', html)
        self.assertNotIn('<form method="post"', html)

    def test_already_confirmed_state(self):
        html = self.render('already_confirmed')
        self.assertIn('Your signature was already confirmed', html)
        self.assertNotIn('<form method="post"', html)

    def test_invalid_link_state(self):
        html = self.render('invalid_link')
        self.assertIn('role="alert"', html)
        self.assertIn('This confirmation link is not valid', html)
        self.assertIn('href="{}#signer"'.format(self.petition.url), html)

    def test_expired_state(self):
        html = self.render('expired')
        self.assertIn('role="alert"', html)
        self.assertIn('This confirmation link has expired', html)
        self.assertNotIn('<form method="post"', html)
