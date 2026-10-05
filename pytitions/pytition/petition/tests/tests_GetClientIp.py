from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

from .utils import add_default_data

from petition.helpers import get_client_ip
from petition.models import Petition


class GetClientIpTest(TestCase):
    """Test get_client_ip helper"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_default_ignores_x_forwarded_for(self):
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='1.2.3.4', REMOTE_ADDR='5.6.7.8')
        self.assertEqual(get_client_ip(request), '5.6.7.8')

    @override_settings(PYTITION_TRUSTED_PROXY_COUNT=1)
    def test_one_trusted_proxy(self):
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='spoof, 9.9.9.9', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(get_client_ip(request), '9.9.9.9')

    @override_settings(PYTITION_TRUSTED_PROXY_COUNT=2)
    def test_two_trusted_proxies(self):
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='spoof, 9.9.9.9, 10.0.0.1',
                                   REMOTE_ADDR='127.0.0.1')
        self.assertEqual(get_client_ip(request), '9.9.9.9')

    @override_settings(PYTITION_TRUSTED_PROXY_COUNT=2)
    def test_chain_shorter_than_proxy_count(self):
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='9.9.9.9', REMOTE_ADDR='5.6.7.8')
        self.assertEqual(get_client_ip(request), '5.6.7.8')

    @override_settings(PYTITION_TRUSTED_PROXY_COUNT=1)
    def test_trusted_proxy_without_header(self):
        request = self.factory.get('/', REMOTE_ADDR='5.6.7.8')
        self.assertEqual(get_client_ip(request), '5.6.7.8')


class ThrottleClientIpTest(TestCase):
    """Changing X-Forwarded-For must not change the address used by the throttle"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    @override_settings(SIGNATURE_THROTTLE=2)
    def test_x_forwarded_for_does_not_bypass_throttle(self):
        petition = Petition.objects.filter(published=True).first()
        for i in range(4):
            data = {
                'first_name': 'Alan',
                'last_name': 'John',
                'email': 'alan%d@john.org' % i,
                'phone': '',
            }
            response = self.client.post(reverse('create_signature', args=[petition.id]), data,
                                        HTTP_X_FORWARDED_FOR='10.0.0.%d' % i)
        self.assertContains(response, 'Too many signatures from your IP address', status_code=response.status_code)
