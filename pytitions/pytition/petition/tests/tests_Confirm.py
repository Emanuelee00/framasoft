from unittest import mock

from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.models import Petition, Signature

class ConfirmViewTest(TestCase):
    """Test confirm view"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_ConfirmOk(self):
        data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
            'subscribed_to_mailinglist': False,
            'consent': 'on',
        }
        petition = Petition.objects.filter(published=True).first()
        response = self.client.post(reverse('create_signature', args=[petition.id]), data, follow=True)
        self.assertRedirects(response, petition.url)
        signature = Signature.objects.filter(petition=petition).first()
        self.assertEqual(signature.confirmed, False)
        confirm_hash = signature.confirmation_hash
        response = self.client.get(reverse('confirm', args=[petition.id, confirm_hash]), follow=True)
        self.assertRedirects(response, petition.url)
        signature = Signature.objects.filter(petition=petition).first() # Reload the object
        self.assertEqual(signature.confirmed, True)
        self.assertIsNotNone(signature.confirmed_at)
        self.assertIsNone(signature.newsletter_consent_at)

    @mock.patch('petition.views.subscribe_to_newsletter')
    def test_ConfirmNewsletterAfterConfirmation(self, subscribe):
        petition = Petition.objects.filter(published=True).first()
        petition.has_newsletter = True
        petition.save()
        data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
            'subscribed_to_mailinglist': True,
            'consent': 'on',
        }
        self.client.post(reverse('create_signature', args=[petition.id]), data)
        self.assertEqual(subscribe.call_count, 0)
        signature = Signature.objects.get(petition=petition, email='alan@john.org')
        self.assertTrue(signature.subscribed_to_mailinglist)
        url = reverse('confirm', args=[petition.id, signature.confirmation_hash])
        self.client.get(url)
        self.assertEqual(subscribe.call_count, 1)
        subscribe.assert_called_with(petition, 'alan@john.org')
        self.client.get(url)
        self.assertEqual(subscribe.call_count, 1)
        signature.refresh_from_db()
        self.assertTrue(signature.confirmed)
        self.assertIsNotNone(signature.newsletter_consent_at)
