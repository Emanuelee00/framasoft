from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import add_default_data

from petition.helpers import normalize_ip, signature_ip_hash
from petition.models import Petition, Signature


class SignatureIpHashTest(TestCase):
    """Test the pseudonymisation of signers IP addresses"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.p1, self.p2 = Petition.objects.filter(published=True)[:2]

    def test_normalize_ip(self):
        self.assertEqual(normalize_ip('1.2.3.4'), '1.2.3.4')
        self.assertEqual(normalize_ip(' 1.2.3.4 '), '1.2.3.4')
        self.assertEqual(normalize_ip('2001:db8:1:2:aaaa::1'), '2001:db8:1:2::')
        self.assertEqual(normalize_ip('not an ip'), '')
        self.assertEqual(normalize_ip(None), '')

    def test_hash_is_deterministic_hex_sha256(self):
        h = signature_ip_hash(self.p1, '1.2.3.4')
        self.assertEqual(h, signature_ip_hash(self.p1, '1.2.3.4'))
        self.assertEqual(len(h), 64)
        self.assertNotIn('1.2.3.4', h)

    def test_hash_depends_on_petition_and_ip(self):
        self.assertNotEqual(signature_ip_hash(self.p1, '1.2.3.4'), signature_ip_hash(self.p2, '1.2.3.4'))
        self.assertNotEqual(signature_ip_hash(self.p1, '1.2.3.4'), signature_ip_hash(self.p1, '1.2.3.5'))

    def test_ipv6_same_64_network_same_hash(self):
        self.assertEqual(signature_ip_hash(self.p1, '2001:db8:1:2::1'),
                         signature_ip_hash(self.p1, '2001:db8:1:2:ffff::2'))
        self.assertNotEqual(signature_ip_hash(self.p1, '2001:db8:1:2::1'),
                            signature_ip_hash(self.p1, '2001:db8:1:3::1'))

    def test_hash_depends_on_key(self):
        with override_settings(SIGNATURE_IP_HMAC_KEY='key-a'):
            a = signature_ip_hash(self.p1, '1.2.3.4')
        with override_settings(SIGNATURE_IP_HMAC_KEY='key-b'):
            b = signature_ip_hash(self.p1, '1.2.3.4')
        self.assertNotEqual(a, b)

    def test_signature_stores_hash(self):
        data = {'first_name': 'Alan', 'last_name': 'John', 'email': 'alan@john.org', 'phone': '', 'consent': 'on'}
        self.client.post(reverse('create_signature', args=[self.p1.id]), data, REMOTE_ADDR='1.2.3.4')
        signature = Signature.objects.get(petition=self.p1, email='alan@john.org')
        self.assertEqual(signature.ipaddress, signature_ip_hash(self.p1, '1.2.3.4'))
