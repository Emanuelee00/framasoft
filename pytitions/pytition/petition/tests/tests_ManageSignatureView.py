import json
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.helpers import make_manage_token
from petition.models import Petition, Signature


class ManageSignatureViewTest(TestCase):
    """Test manage_signature, manage_signature_export and forgot_signature_link views"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        cache.clear()
        self.petition = Petition.objects.filter(published=True).first()
        self.signature = Signature.objects.create(first_name='Alan', last_name='John', email='alan@john.org',
                                                  petition=self.petition, confirmed=True)
        self.token = make_manage_token(self.signature)

    def test_manage_signature_get(self):
        response = self.client.get(reverse('manage_signature', args=[self.token]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'petition/manage_signature.html')
        self.assertContains(response, 'alan@john.org')
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        self.assertEqual(response['X-Robots-Tag'], 'noindex')

    def test_manage_signature_bad_token(self):
        response = self.client.get(reverse('manage_signature', args=[self.token[:-2] + 'xx']))
        self.assertEqual(response.status_code, 404)

    def test_manage_signature_delete(self):
        url = reverse('manage_signature', args=[self.token])
        count = self.petition.get_signature_number(confirmed=True)
        response = self.client.post(url, {'action': 'delete', 'confirm': 'on'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'petition/signature_deleted.html')
        self.assertFalse(Signature.objects.filter(pk=self.signature.pk).exists())
        self.assertEqual(self.petition.get_signature_number(confirmed=True), count - 1)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_manage_signature_delete_requires_confirmation(self):
        url = reverse('manage_signature', args=[self.token])
        response = self.client.get(url)
        self.assertContains(response, 'name="confirm" required')
        response = self.client.post(url, {'action': 'delete'})
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'petition/manage_signature.html')
        self.assertContains(response, 'aria-invalid="true"', status_code=400)
        self.assertContains(response, 'Tick the box to confirm the deletion.', status_code=400)
        self.assertTrue(Signature.objects.filter(pk=self.signature.pk).exists())

    def test_manage_signature_delete_requires_csrf(self):
        from django.test import Client
        response = Client(enforce_csrf_checks=True).post(reverse('manage_signature', args=[self.token]),
                                                         {'action': 'delete', 'confirm': 'on'})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Signature.objects.filter(pk=self.signature.pk).exists())

    def test_manage_signature_newsletter_withdrawal(self):
        from django.utils import timezone
        Signature.objects.filter(pk=self.signature.pk).update(subscribed_to_mailinglist=True,
                                                              newsletter_consent_at=timezone.now())
        url = reverse('manage_signature', args=[self.token])
        self.assertContains(self.client.get(url), 'value="newsletter-off"')
        response = self.client.post(url, {'action': 'newsletter-off'}, follow=True)
        self.assertRedirects(response, url)
        self.assertContains(response, 'Your newsletter subscription has been withdrawn')
        self.assertNotContains(response, 'value="newsletter-off"')
        self.signature.refresh_from_db()
        self.assertFalse(self.signature.subscribed_to_mailinglist)
        self.assertIsNone(self.signature.newsletter_consent_at)

    @mock.patch('petition.views.subscribe_to_newsletter')
    def test_withdrawal_before_confirmation_prevents_subscription(self, subscribe):
        self.petition.has_newsletter = True
        self.petition.save()
        signature = Signature.objects.create(first_name='B', last_name='C', email='b@c.org', petition=self.petition,
                                             subscribed_to_mailinglist=True)
        self.client.post(reverse('manage_signature', args=[make_manage_token(signature)]), {'action': 'newsletter-off'})
        self.client.post(reverse('confirm', args=[self.petition.id, signature.confirmation_hash]))
        subscribe.assert_not_called()
        signature.refresh_from_db()
        self.assertTrue(signature.confirmed)

    def test_manage_signature_export(self):
        response = self.client.get(reverse('manage_signature_export', args=[self.token]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertEqual(data['email'], 'alan@john.org')
        self.assertEqual(data['first_name'], 'Alan')
        self.assertTrue(data['confirmed'])
        self.assertIn('petition', data)
        self.assertNotIn('confirmation_hash', data)
        self.assertNotIn('ipaddress', data)
        self.assertIn('attachment', response['Content-Disposition'])

    def test_forgot_signature_link_same_answer(self):
        url = reverse('forgot_signature_link', args=[self.petition.id])
        self.assertEqual(self.client.get(url).status_code, 200)
        mail.outbox = []
        r_known = self.client.post(url, {'email': 'alan@john.org'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(reverse('manage_signature', args=[make_manage_token(self.signature)]), mail.outbox[0].body)
        r_unknown = self.client.post(url, {'email': 'nobody@example.org'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual((r_known.status_code, r_known['Location']), (r_unknown.status_code, r_unknown['Location']))
        # throttled: no second email for the same signature
        self.client.post(url, {'email': 'alan@john.org'})
        self.assertEqual(len(mail.outbox), 1)

    def test_forgot_signature_link_prefers_confirmed_then_latest(self):
        url = reverse('forgot_signature_link', args=[self.petition.id])
        Signature.objects.create(first_name='Alan', last_name='John', email='alan@john.org',
                                 petition=self.petition, confirmed=False)
        mail.outbox = []
        self.client.post(url, {'email': 'alan@john.org'})
        self.assertIn(reverse('manage_signature', args=[make_manage_token(self.signature)]), mail.outbox[0].body)
        # only unconfirmed signatures: the latest one
        Signature.objects.create(first_name='Eve', last_name='Doe', email='eve@doe.org',
                                 petition=self.petition, confirmed=False)
        latest = Signature.objects.create(first_name='Eve', last_name='Doe', email='eve@doe.org',
                                          petition=self.petition, confirmed=False)
        self.client.post(url, {'email': 'eve@doe.org'})
        self.assertIn(reverse('manage_signature', args=[make_manage_token(latest)]), mail.outbox[1].body)

    def test_forgot_signature_link_ignores_case(self):
        self.client.post(reverse('forgot_signature_link', args=[self.petition.id]), {'email': 'Alan@John.ORG'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['alan@john.org'])
