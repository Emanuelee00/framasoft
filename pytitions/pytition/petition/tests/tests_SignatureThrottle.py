from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import add_default_data

from petition.models import Petition, Signature


@override_settings(SIGNATURE_THROTTLE=2, MODERATION_EMAIL='moderation@example.org')
class SignatureThrottleTest(TestCase):
    """Test the per IP address signature throttle of create_signature"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        cache.clear()
        self.petition = Petition.objects.filter(published=True).first()

    def sign(self, i, ip='1.2.3.4', **extra):
        data = {'first_name': 'Alan%d' % i, 'last_name': 'John', 'email': 'alan%d@john.org' % i, 'phone': '', 'consent': 'on'}
        return self.client.post(reverse('create_signature', args=[self.petition.id]), data, REMOTE_ADDR=ip, **extra)

    def moderation_mails(self):
        return [m for m in mail.outbox if m.to == ['moderation@example.org']]

    def test_throttled_signature_is_refused_with_429(self):
        for i in range(3):
            self.assertEqual(self.sign(i).status_code, 302)
        response = self.sign(3)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '86400')
        self.assertTemplateUsed(response, 'petition/petition_detail.html')
        self.assertContains(response, 'Too many signatures from your IP address', status_code=429)
        # the form is repopulated
        self.assertContains(response, 'alan3@john.org', status_code=429)
        self.assertEqual(Signature.objects.filter(petition=self.petition).count(), 3)

    def test_one_moderation_mail_per_ip(self):
        for i in range(8):
            self.sign(i)
        self.assertEqual(Signature.objects.filter(petition=self.petition).count(), 3)
        moderation_mails = self.moderation_mails()
        self.assertEqual(len(moderation_mails), 1)
        # no data about the signer in the moderation mail
        self.assertNotIn('Alan', moderation_mails[0].body)
        self.assertNotIn('alan', moderation_mails[0].body)
        self.assertIn(str(self.petition.id), moderation_mails[0].body)

    def test_other_ip_is_not_throttled(self):
        for i in range(4):
            self.sign(i)
        self.assertEqual(self.sign(10, ip='5.6.7.8').status_code, 302)
        self.assertEqual(Signature.objects.filter(petition=self.petition).count(), 4)

    def test_x_forwarded_for_does_not_bypass_throttle(self):
        statuses = [self.sign(i, HTTP_X_FORWARDED_FOR='10.0.0.%d' % i).status_code for i in range(4)]
        self.assertEqual(statuses, [302, 302, 302, 429])
