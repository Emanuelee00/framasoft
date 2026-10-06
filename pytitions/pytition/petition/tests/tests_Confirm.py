from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .utils import add_default_data

from petition.models import Petition, Signature

class ConfirmViewTest(TestCase):
    """Test confirm view: GET shows a button, POST confirms (FE-03)"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()

    def create(self, email='a@example.org', **extra):
        return Signature.objects.create(first_name="A", last_name="B", email=email, petition=self.petition, **extra)

    def url(self, signature_or_hash):
        h = getattr(signature_or_hash, 'confirmation_hash', signature_or_hash)
        return reverse('confirm', args=[self.petition.id, h])

    def test_ConfirmOk(self):
        data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
            'subscribed_to_mailinglist': False,
            'consent': 'on',
        }
        response = self.client.post(reverse('create_signature', args=[self.petition.id]), data, follow=True)
        self.assertRedirects(response, self.petition.url)
        signature = Signature.objects.filter(petition=self.petition).first()
        self.assertEqual(signature.confirmed, False)
        response = self.client.post(self.url(signature), follow=True)
        self.assertRedirects(response, self.petition.url)
        self.assertEqual(response.context['sign_state'], 'confirmed')
        signature.refresh_from_db()
        self.assertEqual(signature.confirmed, True)
        self.assertIsNotNone(signature.confirmed_at)
        self.assertIsNone(signature.newsletter_consent_at)

    def test_GetShowsButtonWithoutConfirming(self):
        signature = self.create()
        response = self.client.get(self.url(signature))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['confirm_state'], 'pending')
        self.assertContains(response, '<form method="post" action="%s">' % self.url(signature))
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, '<meta name="robots" content="noindex">')
        self.assertEqual(response['X-Robots-Tag'], 'noindex')
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        self.assertIn('no-cache', response['Cache-Control'])
        signature.refresh_from_db()
        self.assertFalse(signature.confirmed)
        self.assertIsNone(signature.confirmed_at)

    def test_HeadDoesNotConfirm(self):
        signature = self.create()
        self.client.head(self.url(signature))
        signature.refresh_from_db()
        self.assertFalse(signature.confirmed)

    def test_PostRequiresCsrf(self):
        signature = self.create()
        from django.test import Client
        response = Client(enforce_csrf_checks=True).post(self.url(signature))
        self.assertEqual(response.status_code, 403)
        signature.refresh_from_db()
        self.assertFalse(signature.confirmed)

    def test_AlreadyConfirmed(self):
        signature = self.create(confirmed=True)
        for method in (self.client.get, self.client.post):
            response = method(self.url(signature))
            self.assertEqual(response.context['confirm_state'], 'already_confirmed')
            self.assertContains(response, 'Your signature was already confirmed')
            self.assertContains(response, '/signature/manage/')

    def test_SecondPostKeepsFirstConfirmationDate(self):
        signature = self.create()
        self.client.post(self.url(signature))
        signature.refresh_from_db()
        first = signature.confirmed_at
        response = self.client.post(self.url(signature))
        self.assertEqual(response.context['confirm_state'], 'already_confirmed')
        signature.refresh_from_db()
        self.assertEqual(signature.confirmed_at, first)

    def test_ExpiredLinkDoesNotConfirm(self):
        signature = self.create()
        Signature.objects.filter(pk=signature.pk).update(date=timezone.now() - timedelta(days=8))
        for method in (self.client.get, self.client.post):
            response = method(self.url(signature))
            self.assertEqual(response.context['confirm_state'], 'expired')
            self.assertContains(response, 'This confirmation link has expired', status_code=200)
            self.assertNotContains(response, '<form method="post"')
        signature.refresh_from_db()
        self.assertFalse(signature.confirmed)

    @override_settings(UNCONFIRMED_SIGNATURE_RETENTION_DAYS=None)
    def test_NoExpiryWhenRetentionDisabled(self):
        signature = self.create()
        Signature.objects.filter(pk=signature.pk).update(date=timezone.now() - timedelta(days=30))
        self.client.post(self.url(signature))
        signature.refresh_from_db()
        self.assertTrue(signature.confirmed)

    def test_ConfirmDeletesOtherSignaturesOfTheSameAddress(self):
        first = self.create(email='dup@example.org')
        second = self.create(email='dup@example.org')
        self.client.post(self.url(second))
        self.assertFalse(Signature.objects.filter(pk=first.pk).exists())
        self.assertEqual(self.petition.get_signature_number(confirmed=True), 1)
        response = self.client.post(self.url(first))
        self.assertEqual(response.context['confirm_state'], 'invalid_link')

    def test_InvalidLink(self):
        for method in (self.client.get, self.client.post):
            response = method(self.url('not-a-hash'))
            self.assertEqual(response.context['confirm_state'], 'invalid_link')
            self.assertContains(response, 'This confirmation link is not valid')

    def test_HashOfAnotherPetitionIsInvalid(self):
        other = Petition.objects.exclude(pk=self.petition.pk).filter(published=True).first()
        signature = Signature.objects.create(first_name="A", last_name="B", email="o@example.org", petition=other)
        response = self.client.post(self.url(signature))
        self.assertEqual(response.context['confirm_state'], 'invalid_link')
        signature.refresh_from_db()
        self.assertFalse(signature.confirmed)

    @mock.patch('petition.views.subscribe_to_newsletter')
    def test_ConfirmNewsletterAfterConfirmation(self, subscribe):
        self.petition.has_newsletter = True
        self.petition.save()
        data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
            'subscribed_to_mailinglist': True,
            'consent': 'on',
        }
        self.client.post(reverse('create_signature', args=[self.petition.id]), data)
        self.assertEqual(subscribe.call_count, 0)
        signature = Signature.objects.get(petition=self.petition, email='alan@john.org')
        self.assertTrue(signature.subscribed_to_mailinglist)
        url = self.url(signature)
        self.client.get(url)
        self.assertEqual(subscribe.call_count, 0)
        self.client.post(url)
        self.assertEqual(subscribe.call_count, 1)
        subscribe.assert_called_with(self.petition, 'alan@john.org')
        self.client.post(url)
        self.assertEqual(subscribe.call_count, 1)
        signature.refresh_from_db()
        self.assertTrue(signature.confirmed)
        self.assertIsNotNone(signature.newsletter_consent_at)

    @mock.patch('petition.views.subscribe_to_newsletter')
    def test_NoNewsletterWithoutOptIn(self, subscribe):
        self.petition.has_newsletter = True
        self.petition.save()
        signature = self.create()
        self.client.post(self.url(signature))
        subscribe.assert_not_called()
        signature.refresh_from_db()
        self.assertIsNone(signature.newsletter_consent_at)


class ConfirmCsrfTest(TestCase):
    """The confirmation form passes the CSRF check as a browser sends it (Origin of the site)"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_post_with_csrf_checks_and_origin(self):
        from django.test import Client
        petition = Petition.objects.filter(published=True).first()
        signature = Signature.objects.create(first_name="A", last_name="B", email="o@example.org", petition=petition)
        url = reverse('confirm', args=[petition.id, signature.confirmation_hash])
        client = Client(enforce_csrf_checks=True)
        response = client.get(url)
        # with "no-referrer" browsers send "Origin: null" and the CSRF check fails (403)
        self.assertNotEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertNotContains(response, 'content="no-referrer"')
        token = response.context['csrf_token']
        response = client.post(url, {'csrfmiddlewaretoken': str(token)}, HTTP_ORIGIN='http://testserver')
        self.assertNotEqual(response.status_code, 403)
        signature.refresh_from_db()
        self.assertTrue(signature.confirmed)
        # the same request with "Origin: null" is what no-referrer produced
        other = Signature.objects.create(first_name="C", last_name="D", email="n@example.org", petition=petition)
        url = reverse('confirm', args=[petition.id, other.confirmation_hash])
        client.get(url)
        self.assertEqual(client.post(url, {'csrfmiddlewaretoken': str(token)}, HTTP_ORIGIN='null').status_code, 403)
