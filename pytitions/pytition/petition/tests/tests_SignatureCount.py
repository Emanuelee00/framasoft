from django.core.cache import cache
from django.test import TestCase, override_settings

from .utils import add_default_data

from petition.models import Petition, Signature


class SignatureCountCacheTest(TestCase):
    """Test the cache of the displayed number of signatures"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        cache.clear()
        self.petition = Petition.objects.filter(published=True).first()
        Signature.objects.create(petition=self.petition, first_name='A', last_name='B',
                                 email='a@b.org', confirmed=True)

    @override_settings(SIGNATURE_COUNT_CACHE_TTL=30)
    def test_count_is_cached(self):
        with self.assertNumQueries(1):
            self.assertEqual(self.petition.signature_number, 1)
        with self.assertNumQueries(0):
            self.assertEqual(self.petition.signature_number, 1)
            # shared by all instances of the petition
            self.assertEqual(Petition(pk=self.petition.pk).signature_number, 1)
        Signature.objects.create(petition=self.petition, first_name='C', last_name='D',
                                 email='c@d.org', confirmed=True)
        # up to SIGNATURE_COUNT_CACHE_TTL seconds late
        self.assertEqual(self.petition.signature_number, 1)
        self.assertEqual(self.petition.get_signature_number(True), 2)

    @override_settings(SIGNATURE_COUNT_CACHE_TTL=0)
    def test_no_cache_with_ttl_zero(self):
        self.assertEqual(self.petition.signature_number, 1)
        Signature.objects.create(petition=self.petition, first_name='C', last_name='D',
                                 email='c@d.org', confirmed=True)
        with self.assertNumQueries(1):
            self.assertEqual(self.petition.signature_number, 2)
