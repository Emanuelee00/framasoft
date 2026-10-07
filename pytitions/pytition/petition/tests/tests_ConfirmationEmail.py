from django.core import mail
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils.html import strip_tags

from .utils import add_default_data

from petition.helpers import make_manage_token
from petition.models import Petition


class ConfirmationEmailTest(TestCase):
    """Content of the signature confirmation email (GD-11)"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_full_context(self):
        html = render_to_string('petition/confirmation_email.html', {
            'firstname': 'Alan', 'url': 'https://example.org/confirm/abc',
            'petition_title': 'Save the bees', 'creator_name': 'Julia',
            'manage_url': 'https://example.org/manage/xyz', 'days': 7,
            'privacy_url': 'https://example.org/privacy'})
        text = strip_tags(html)
        self.assertIn('Hello Alan,', text)
        self.assertIn('“Save the bees”', text)
        self.assertIn('https://example.org/confirm/abc', text)
        self.assertIn('within 7 days', text)
        self.assertIn('https://example.org/manage/xyz', text)
        self.assertIn('Julia', text)
        self.assertIn('https://example.org/privacy', text)

    def test_text_version_is_a_real_text_template(self):
        petition = Petition.objects.filter(published=True).first()
        petition.title = '<b>Bees &amp; flowers</b>'
        petition.save()
        data = {'first_name': 'Alan', 'last_name': 'John', 'email': 'alan@john.org', 'consent': 'on'}
        self.client.post(reverse('create_signature', args=[petition.id]), data)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        signature = petition.signature_set.get()
        body = message.body
        self.assertEqual(message.subject, 'Confirm your signature: “Bees & flowers”')
        self.assertIn('Hello Alan,', body)
        self.assertNotIn('🤍', body)
        self.assertIn('“Bees & flowers”', body)
        self.assertNotIn('<', body)
        self.assertNotIn('&amp;', body)
        self.assertIn('http://testserver' + reverse('confirm', args=[petition.id, signature.confirmation_hash]), body)
        self.assertIn('http://testserver' + reverse('manage_signature', args=[make_manage_token(signature)]), body)
        self.assertIn('http://testserver' + reverse('privacy_notice'), body)
        self.assertIn('within 7 days', body)
        self.assertIn(petition.owner_name, body)
        self.assertIn('Keep this message', body)
        self.assertNotIn('\n\n\n', body)
        html_body, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('Bees &amp; flowers', html_body)

    def test_text_version_in_french(self):
        petition = Petition.objects.filter(published=True).first()
        data = {'first_name': 'Alan', 'last_name': 'John', 'email': 'alan@john.org', 'consent': 'on'}
        self.client.post(reverse('create_signature', args=[petition.id]), data, HTTP_ACCEPT_LANGUAGE='fr')
        message = mail.outbox[0]
        self.assertTrue(message.subject.startswith('Confirmez votre signature : « '))
        self.assertIn('Bonjour Alan,', message.body)
        self.assertIn('Sans confirmation de votre part sous 7 jours', message.body)
        self.assertIn('Plus d\'informations sur vos données :', message.body)
