from unittest import mock

import requests
from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.helpers import subscribe_to_newsletter, NEWSLETTER_HTTP_TIMEOUT
from petition.models import Petition, Signature


class NewsletterSubscriptionTest(TestCase):
    """The newsletter subscription must never break nor block a signature"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()
        self.petition.has_newsletter = True
        self.petition.newsletter_subscribe_method = 'POST'
        self.petition.newsletter_subscribe_http_url = 'http://newsletter.invalid/subscribe'
        self.petition.newsletter_subscribe_http_mailfield = 'email'
        self.petition.save()

    def test_http_calls_have_a_timeout(self):
        with mock.patch('petition.helpers.requests.post') as post:
            subscribe_to_newsletter(self.petition, 'alan@john.org')
        self.assertEqual(post.call_args.kwargs['timeout'], NEWSLETTER_HTTP_TIMEOUT)
        self.petition.newsletter_subscribe_method = 'GET'
        with mock.patch('petition.helpers.requests.get') as get:
            subscribe_to_newsletter(self.petition, 'alan@john.org')
        self.assertEqual(get.call_args.kwargs['timeout'], NEWSLETTER_HTTP_TIMEOUT)

    def test_signature_ok_when_newsletter_times_out(self):
        data = {'first_name': 'Alan', 'last_name': 'John', 'email': 'alan@john.org', 'phone': '',
                'subscribed_to_mailinglist': 'on', 'consent': 'on'}
        response = self.client.post(reverse('create_signature', args=[self.petition.id]), data)
        self.assertEqual(response.status_code, 302)
        signature = Signature.objects.get(petition=self.petition, email='alan@john.org')
        # the subscription happens on confirmation (GD-06)
        with mock.patch('petition.helpers.requests.post', side_effect=requests.Timeout) as post:
            response = self.client.post(reverse('confirm', args=[self.petition.id, signature.confirmation_hash]))
        self.assertTrue(post.called)
        self.assertEqual(response.status_code, 302)
        signature.refresh_from_db()
        self.assertTrue(signature.confirmed)

    def test_mail_method_uses_the_smtp_server_of_the_petition(self):
        self.petition.newsletter_subscribe_method = 'MAIL'
        self.petition.newsletter_subscribe_mail_smtp_host = 'smtp.example.org'
        with mock.patch('petition.helpers.get_connection') as get_connection:
            subscribe_to_newsletter(self.petition, 'alan@john.org')
        kwargs = get_connection.call_args.kwargs
        self.assertEqual(kwargs['backend'], 'django.core.mail.backends.smtp.EmailBackend')
        self.assertEqual(kwargs['host'], 'smtp.example.org')
        self.assertIn('timeout', kwargs)
