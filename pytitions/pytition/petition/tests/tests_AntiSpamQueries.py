from django.test import TestCase

from .utils import add_default_data

from petition.models import Petition
from petition.spam_management.anti_bot_tests.check_signature_number import check_signature_number, \
    check_signature_variation, check_creation_signatures


class AntiSpamQueriesTest(TestCase):
    """Each number of signatures is counted once per anti-spam check"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()
        # create the reasons, so that get_or_create is a single SELECT
        check_signature_number(self.petition)
        check_signature_variation(self.petition, "yesterday")
        check_creation_signatures(self.petition)

    def test_check_signature_number(self):
        # 2 reasons + 1 count
        with self.assertNumQueries(3):
            self.assertFalse(check_signature_number(self.petition))

    def test_check_signature_variation(self):
        # 2 reasons + number to compare + 1 count
        with self.assertNumQueries(4):
            self.assertFalse(check_signature_variation(self.petition, "yesterday"))

    def test_check_creation_signatures(self):
        # 2 reasons + 1 count
        with self.assertNumQueries(3):
            self.assertFalse(check_creation_signatures(self.petition))
