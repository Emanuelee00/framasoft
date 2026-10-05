from django.db import connection
from django.conf import settings
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .utils import add_default_data

from petition.models import Organization, Petition, PytitionUser


class PetitionListQueriesTest(TestCase):
    """Petition lists must not load every petition nor query each owner"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()
        org = Organization.objects.get(name='Greenpeace')
        user = PytitionUser.objects.get(user__username='max')
        for i in range(30):
            Petition.objects.create(title='List %d' % i, org=org, published=True)
            Petition.objects.create(title='List %d' % i, user=user, published=True)
        Petition.objects.create(title='Hidden org', org=Organization.objects.get(name='Attac'), published=True)
        Organization.objects.filter(name='Attac').update(moderated=True)
        PytitionUser.objects.filter(user__username='julia').update(moderated=True)

    def test_moderated_owners_are_hidden(self):
        response = self.client.get(reverse('search'), {'q': 'Hidden'})
        self.assertEqual(len(response.context['petitions']), 0)
        response = self.client.get(reverse('search'))
        titles = [p.title for p in response.context['petitions'].paginator.object_list]
        self.assertNotIn('Hidden org', titles)
        for p in response.context['petitions'].paginator.object_list:
            self.assertFalse(p.is_moderated)

    def test_search_keeps_15_visible_results(self):
        response = self.client.get(reverse('search'), {'q': 'List'})
        self.assertEqual(len(response.context['petitions']), 15)

    @override_settings(SIGNATURE_COUNT_CACHE_TTL=0)
    def test_list_query_count(self):
        # a constant number of queries plus one signature count per displayed petition
        # (it was about 100 queries for this data set, growing with the number of petitions)
        for url in (reverse('search'), reverse('index')):
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(url)
            self.assertLessEqual(len(ctx.captured_queries), 4 + settings.PAGINATOR_COUNT)
