from unittest import mock

from django.test import TestCase, override_settings

from .utils import add_default_data

from petition.models import Petition, PytitionUser
from petition.spam_management.detectors.akismet_detector import AkismetSpamDetector


class AkismetDetectorTest(TestCase):
    """Test the data sent to Akismet"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.pu = PytitionUser.objects.get(user__username='julia')
        self.petition = Petition.objects.filter(user=self.pu).first()

    @override_settings(AKISMET_KEY="")
    @mock.patch('petition.spam_management.detectors.akismet_detector.Akismet')
    def test_no_call_without_key(self, akismet):
        self.assertEqual(AkismetSpamDetector().is_spam(self.petition, self.pu), 0)
        akismet.assert_not_called()

    @override_settings(AKISMET_KEY="key", AKISMET_SEND_EMAIL=False, AKISMET_IS_TEST=False)
    @mock.patch('petition.spam_management.detectors.akismet_detector.Akismet')
    def test_no_email_sent(self, akismet):
        akismet.return_value.check.return_value = 0
        AkismetSpamDetector().is_spam(self.petition, self.pu)
        kwargs = akismet.return_value.check.call_args[1]
        self.assertNotIn('comment_author_email', kwargs)
        self.assertEqual(kwargs['is_test'], 0)
        self.assertEqual(kwargs['comment_author'], 'julia')

    @override_settings(AKISMET_KEY="key", AKISMET_SEND_EMAIL=True)
    @mock.patch('petition.spam_management.detectors.akismet_detector.Akismet')
    def test_email_sent_when_enabled(self, akismet):
        self.pu.user.email = 'julia@example.org'
        self.pu.user.save()
        akismet.return_value.check.return_value = 0
        AkismetSpamDetector().is_spam(self.petition, self.pu)
        self.assertEqual(akismet.return_value.check.call_args[1]['comment_author_email'], 'julia@example.org')
