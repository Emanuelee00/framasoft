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
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertEqual(response['X-Robots-Tag'], 'noindex')

    def test_manage_signature_bad_token(self):
        response = self.client.get(reverse('manage_signature', args=[self.token[:-2] + 'xx']))
        self.assertEqual(response.status_code, 404)

    def test_manage_signature_delete(self):
        url = reverse('manage_signature', args=[self.token])
        count = self.petition.get_signature_number(confirmed=True)
        response = self.client.post(url, {'action': 'delete'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'petition/signature_deleted.html')
        self.assertFalse(Signature.objects.filter(pk=self.signature.pk).exists())
        self.assertEqual(self.petition.get_signature_number(confirmed=True), count - 1)
        self.assertEqual(self.client.get(url).status_code, 404)

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

    def test_confirmation_email_context_has_manage_url(self):
        from django.template.loader import render_to_string
        data = {'first_name': 'Bob', 'last_name': 'Doe', 'email': 'bob@doe.org', 'subscribed_to_mailinglist': False,
                'consent': 'on'}
        with mock.patch('petition.helpers.render_to_string', wraps=render_to_string) as rts:
            self.client.post(reverse('create_signature', args=[self.petition.id]), data)
        signature = Signature.objects.get(email='bob@doe.org')
        ctx = rts.call_args[0][1]
        self.assertTrue(ctx['manage_url'].endswith(reverse('manage_signature', args=[make_manage_token(signature)])))
        for key in ('firstname', 'url', 'petition_title', 'petition_url', 'creator_name', 'days'):
            self.assertIn(key, ctx)

    def test_privacy_notice(self):
        from django.conf import settings
        response = self.client.get(reverse('privacy_notice'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'petition/privacy_notice.html')
        self.assertContains(response, settings.PRIVACY_NOTICE_VERSION)
