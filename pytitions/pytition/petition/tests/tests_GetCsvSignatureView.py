from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import add_default_data

from petition.models import Petition, Signature, PytitionUser

class GetCsvSignatureViewTest(TestCase):
    """Test get_csv_signature view"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def login(self, name, password=None):
        self.client.login(username=name, password=password if password else name)
        self.pu = PytitionUser.objects.get(user__username=name)
        return self.pu

    def logout(self):
        self.client.logout()

    def test_GetCsvSignatureOk(self):
        julia = self.login('julia')
        petition = julia.petition_set.first()
        response = self.client.get(reverse('get_csv_signature', args=[petition.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        # TODO: add some csv parsing of the response

    def test_GetConfirmedSignatureOk(self):
        julia = self.login('julia')
        petition = julia.petition_set.first()
        response = self.client.get(reverse('get_csv_confirmed_signature', args=[petition.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        # TODO: add some csv parsing of the response

    def test_GetCsvSignatureOnlyConfirmedEscapedAndLogged(self):
        import csv
        import io
        from unittest import mock
        julia = self.login('julia')
        petition = julia.petition_set.first()
        Signature.objects.create(first_name='=SUM(1)', last_name='Conf', email='conf@example.org',
                                 phone='+33605040302', petition=petition, confirmed=True)
        Signature.objects.create(first_name='Pending', last_name='Sig', email='pending@example.org',
                                 petition=petition)
        for route in ('get_csv_signature', 'get_csv_confirmed_signature'):
            with mock.patch('petition.views.audit_logger') as audit:
                response = self.client.get(reverse(route, args=[petition.id]))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'text/csv')
            self.assertEqual(audit.info.call_count, 1)
            self.assertNotIn('conf@example.org', str(audit.info.call_args))
            content = b"".join(response.streaming_content).decode()
            rows = list(csv.reader(io.StringIO(content)))
            self.assertEqual(rows[0], ['first_name', 'last_name', 'phone', 'email', 'subscribed_to_mailinglist',
                                       'confirmed'])
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1][0], "'=SUM(1)")
            self.assertEqual(rows[1][2], '+33605040302')
            self.assertNotIn('pending@example.org', content)

    @override_settings(SIGNATURE_COLLECT_PHONE=False)
    def test_GetCsvSignatureWithoutPhone(self):
        julia = self.login('julia')
        petition = julia.petition_set.first()
        response = self.client.get(reverse('get_csv_confirmed_signature', args=[petition.id]))
        header = b"".join(response.streaming_content).decode().splitlines()[0]
        self.assertEqual(header, 'first_name,last_name,email,subscribed_to_mailinglist,confirmed')
