from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.db import connection
from django.test.utils import CaptureQueriesContext

from .utils import add_default_data

from petition.models import Petition, Signature


class CreateSignatureViewTest(TestCase):
    """Test create_signature view"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_CreateSignaturePOSTOk(self):
        data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
            'phone': '0605040302',
            'subscribed_to_mailinglist': False,
            'consent': 'on',
        }
        petition = Petition.objects.filter(published=True).first()
        response = self.client.post(reverse('create_signature', args=[petition.id]), data, follow=True)
        self.assertRedirects(response, petition.url)
        signature = Signature.objects.filter(petition=petition).first()
        self.assertEqual(signature.confirmed, False)
        self.assertEqual(signature.email, 'alan@john.org')
        self.assertEqual(signature.phone, '+33605040302')
        self.assertEqual(signature.first_name, 'Alan')
        self.assertEqual(signature.last_name, 'John')
        self.assertEqual(signature.subscribed_to_mailinglist, False)
        self.assertEqual(signature.notice_version, settings.PRIVACY_NOTICE_VERSION)

    def test_CreateSignaturePOSTNok(self):
        data = {
            'first_name': 'Alan',
            'last_name': '',
            'email': 'wrong-mail.org',
            'phone': '060504030201',
        }
        petition = Petition.objects.filter(published=True).first()
        response = self.client.post(reverse('create_signature', args=[petition.id]), data)
        self.assertEqual(Signature.objects.count(), 0)
        self.assertTemplateUsed(response, 'petition/petition_detail.html')
        self.assertContains(response, 'This field is required')
        self.assertContains(response, 'Enter a valid phone number')
        self.assertContains(response, 'Enter a valid email address')

    def test_CreateSignatureGETOk(self):
        petition = Petition.objects.filter(published=True).first()
        response = self.client.get(reverse('create_signature', args=[petition.id]), follow=True)
        self.assertRedirects(response, petition.url)

    def test_CreateSignatureQueryCount(self):
        # Upper bound on the number of SQL queries of the signature path: lower it after
        # each optimisation so that regressions are caught.
        data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
            'phone': '',
        }
        petition = Petition.objects.filter(published=True).first()
        with CaptureQueriesContext(connection) as ctx:
            self.client.post(reverse('create_signature', args=[petition.id]), data)
        self.assertLessEqual(len(ctx.captured_queries), 8)
        signature = Signature.objects.get(petition=petition, email='alan@john.org')
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse('confirm', args=[petition.id, signature.confirmation_hash]))
        self.assertLessEqual(len(ctx.captured_queries), 12)

    def test_CreateSignatureDoesNotSavePetition(self):
        petition = Petition.objects.filter(published=True).first()
        before = petition.last_modification_date
        self.assertFalse(petition.cron_to_schedule)
        for i in range(2):
            data = {'first_name': 'Alan', 'last_name': 'John', 'email': 'alan%d@john.org' % i, 'phone': ''}
            self.client.post(reverse('create_signature', args=[petition.id]), data)
        petition.refresh_from_db()
        self.assertEqual(petition.last_modification_date, before)
        self.assertTrue(petition.cron_to_schedule)
        self.assertEqual(Signature.objects.filter(petition=petition).count(), 2)

    def test_CreateSignatureKeepsConcurrentModeration(self):
        # the petition is loaded by the view, then moderated by someone else before the
        # signature is saved: the signature must not overwrite the moderation
        petition = Petition.objects.filter(published=True).first()
        loaded = Petition.objects.get(pk=petition.pk)

        def load_then_moderate(petition_id):
            Petition.objects.filter(pk=petition_id).update(moderated=True)
            return loaded

        data = {'first_name': 'Alan', 'last_name': 'John', 'email': 'alan@john.org', 'phone': ''}
        with mock.patch('petition.views.petition_from_id', side_effect=load_then_moderate):
            self.client.post(reverse('create_signature', args=[petition.id]), data)
        petition.refresh_from_db()
        self.assertTrue(petition.moderated)

    def test_CreateSignatureDuplicateSameResponse(self):
        cache.clear()
        petition = Petition.objects.filter(published=True).first()
        Signature.objects.create(first_name='A', last_name='B', email='dup@example.org', petition=petition,
                                 confirmed=True)
        mail.outbox = []
        url = reverse('create_signature', args=[petition.id])
        base = {'first_name': 'Alan', 'last_name': 'John', 'subscribed_to_mailinglist': False, 'consent': 'on'}
        r_new = self.client.post(url, dict(base, email='new@example.org'))
        r_dup = self.client.post(url, dict(base, email='dup@example.org'))
        self.assertEqual((r_new.status_code, r_new['Location']), (r_dup.status_code, r_dup['Location']))
        self.assertEqual(Signature.objects.filter(email='dup@example.org').count(), 1)
        self.assertEqual([m.to for m in mail.outbox], [['new@example.org'], ['dup@example.org']])
        self.assertIn(petition.title, mail.outbox[1].body)
        self.assertIn('/signature/manage/', mail.outbox[1].body)
        self.assertIn('/signature/manage/', mail.outbox[1].body)
        # a second attempt within the throttle window does not send another email
        r_dup2 = self.client.post(url, dict(base, email='dup@example.org'), follow=True)
        self.assertEqual(len(mail.outbox), 2)
        self.assertNotContains(r_dup2, 'already signed')

    def test_CreateSignatureWithoutConsent(self):
        data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
        }
        petition = Petition.objects.filter(published=True).first()
        response = self.client.get(petition.url)
        self.assertContains(response, 'name="consent"')
        self.assertNotContains(response, 'name="consent" checked')
        response = self.client.post(reverse('create_signature', args=[petition.id]), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'petition/petition_detail.html')
        self.assertTrue(response.context['form'].has_error('consent'))
        self.assertEqual(Signature.objects.count(), 0)

    @override_settings(SIGNATURE_COLLECT_PHONE=False)
    def test_CreateSignatureWithoutPhoneCollection(self):
        data = {
            'first_name': 'Alan',
            'last_name': 'John',
            'email': 'alan@john.org',
            'phone': '0605040302',
            'consent': 'on',
        }
        petition = Petition.objects.filter(published=True).first()
        response = self.client.get(petition.url)
        self.assertNotContains(response, 'name="phone"')
        self.client.post(reverse('create_signature', args=[petition.id]), data)
        signature = Signature.objects.get(email='alan@john.org')
        self.assertEqual(str(signature.phone), '')
