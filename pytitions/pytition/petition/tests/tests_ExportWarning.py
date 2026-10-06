from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.models import PytitionUser, Signature


class ExportWarningTest(TestCase):
    """The CSV export links are behind an explicit warning step"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_export_links_are_inside_the_warning(self):
        self.client.login(username='julia', password='julia')
        petition = PytitionUser.objects.get(user__username='julia').petition_set.first()
        response = self.client.get(reverse('show_signatures', args=[petition.id]))
        html = response.content.decode()
        start = html.index('<details class="fp-details fp-export">')
        end = html.index('</details>', start)
        self.assertIn('You are about to download the personal data of your signatories.', html[start:end])
        self.assertIn(reverse('get_csv_signature', args=[petition.id]), html[start:end])
        self.assertIn(reverse('get_csv_confirmed_signature', args=[petition.id]), html[start:end])
        self.assertNotIn(reverse('get_csv_signature', args=[petition.id]), html[:start] + html[end:])


class PhoneColumnTest(TestCase):
    """The phone column follows SIGNATURE_COLLECT_PHONE (GD-10)"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()
        # The table is only rendered when there is at least one signature (empty state otherwise)
        petition = PytitionUser.objects.get(user__username='julia').petition_set.first()
        Signature.objects.create(petition=petition, first_name='Ada', last_name='L', email='ada@example.org')

    def get(self):
        self.client.login(username='julia', password='julia')
        petition = PytitionUser.objects.get(user__username='julia').petition_set.first()
        return self.client.get(reverse('show_signatures', args=[petition.id]))

    def test_phone_column_shown_by_default(self):
        self.assertContains(self.get(), '<th>Phone</th>')

    def test_phone_column_hidden_when_not_collected(self):
        with self.settings(SIGNATURE_COLLECT_PHONE=False):
            self.assertNotContains(self.get(), '<th>Phone</th>')
