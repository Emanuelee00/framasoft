from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import add_default_data

from petition.models import Petition, Signature


class SignStatesTest(TestCase):
    """Each outcome of the signature has its own visible and announced state"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()
        self.data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
            'subscribed_to_mailinglist': False,
            'consent': 'on',
        }

    def sign(self, **extra):
        data = dict(self.data, **extra)
        return self.client.post(reverse('create_signature', args=[self.petition.id]), data, follow=True)

    def test_pending_email_state_replaces_form(self):
        response = self.sign()
        self.assertRedirects(response, self.petition.url)
        self.assertEqual(response.context['sign_state'], 'pending_email')
        self.assertContains(response, 'role="status"')
        self.assertContains(response, 'Check your mailbox')
        self.assertContains(response, 'alan@john.org')
        self.assertNotContains(response, 'id="id_first_name"')
        self.assertNotContains(response, '.modal("show")')

    def test_form_is_back_on_next_visit(self):
        self.sign()
        response = self.client.get(self.petition.url)
        self.assertNotIn('sign_state', response.context)
        self.assertContains(response, 'id="id_first_name"')

    def test_confirmed_state(self):
        self.sign()
        signature = Signature.objects.get(petition=self.petition)
        response = self.client.post(reverse('confirm', args=[self.petition.id, signature.confirmation_hash]),
                                    follow=True)
        self.assertEqual(response.context['sign_state'], 'confirmed')
        self.assertContains(response, 'Thank you for confirming your signature to this petition!')
        self.assertNotContains(response, 'id="show_confirm_success"')
        self.assertNotIn('sessionid', self.client.cookies)  # confirming creates no session

    def test_cached_sign_fields_never_hold_typed_data(self):
        response = self.sign(first_name='Mallory', consent='')
        self.assertContains(response, 'value="Mallory"')
        self.assertNotContains(self.client.get(self.petition.url), 'Mallory')

    @override_settings(SIGNATURE_THROTTLE=0)
    def test_throttled_signature_shows_alert_and_keeps_form(self):
        self.sign()
        response = self.client.post(reverse('create_signature', args=[self.petition.id]),
                                    dict(self.data, first_name='Bob', email='bob@john.org'))
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'role="alert"', status_code=429)
        self.assertContains(response, 'Too many signatures', status_code=429)
        self.assertContains(response, 'Your signature has not been recorded', status_code=429)
        self.assertContains(response, 'value="Bob"', status_code=429)

    def render_alerts(self, *msgs):
        return render_to_string('components/alerts.html', {
            'messages': list(msgs),
            'DEFAULT_MESSAGE_LEVELS': constants.DEFAULT_LEVELS,
        })

    def test_throttled_tag_has_dedicated_text(self):
        html = self.render_alerts(Message(constants.ERROR, 'Please wait', extra_tags='throttled'))
        self.assertIn('role="alert"', html)
        self.assertIn('Your signature has not been recorded', html)
        self.assertIn('Please wait', html)

    def test_alert_roles_follow_level(self):
        html = self.render_alerts(Message(constants.ERROR, 'Boom'))
        self.assertIn('role="alert"', html)
        html = self.render_alerts(Message(constants.INFO, 'Noted'))
        self.assertIn('role="status"', html)
        self.assertNotIn('role="alert"', html)

    def test_closed_state(self):
        html = render_to_string('components/sign_state.html', {'sign_state': 'closed', 'messages': [],
                                                                 'petition': self.petition})
        self.assertIn('This petition no longer accepts signatures', html)
        self.assertIn('role="alert"', html)
