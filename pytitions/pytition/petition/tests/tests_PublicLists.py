from django.test import TestCase, override_settings
from django.urls import reverse

from .utils import add_default_data


@override_settings(PAGINATOR_COUNT=4, INDEX_PAGE="HOME")
class PublicListsTest(TestCase):
    """Home, search and profiles share the design system list (PUB-01, PUB-02)"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_home_lists_cards_with_sort_and_pagination(self):
        html = self.client.get(reverse('index')).content.decode()
        self.assertIn('<ul class="fp-card-grid fp-petition-grid">', html)
        self.assertEqual(html.count('class="fp-card fp-card-interactive fp-petition-card"'), 4)
        self.assertIn('<nav class="fp-sort" aria-label="Sort petitions">', html)
        self.assertIn('href="?sort=desc#petitions" aria-current="true"', html)
        self.assertIn('rel="next" href="?page=2&amp;sort=desc"', html)
        self.assertIn('id="hero-title"', html)
        self.assertNotIn('petition-list-row', html)

    def test_home_next_pages_skip_the_introduction(self):
        html = self.client.get(reverse('index') + '?page=2&sort=asc').content.decode()
        self.assertNotIn('id="hero-title"', html)
        self.assertIn('<h1 id="petitions-title"', html)
        self.assertIn('href="?sort=asc#petitions" aria-current="true"', html)

    def test_search_has_a_visible_label_and_counts_results(self):
        html = self.client.get(reverse('search') + '?q=Petition+C').content.decode()
        self.assertIn('<label class="fp-label" for="search-q">', html)
        self.assertIn('value="Petition C"', html)
        self.assertIn('15 petitions match “Petition C”', html)
        self.assertIn('Only the first 15 results are shown', html)

    def test_search_without_result_shows_an_empty_state(self):
        html = self.client.get(reverse('search') + '?q=nothing-here').content.decode()
        self.assertIn('class="fp-empty ', html)
        self.assertIn('No petition found', html)
        self.assertNotIn('<style>', html)

    def test_organization_profile_with_no_petition(self):
        html = self.client.get(reverse('org_profile', args=['rap'])).content.decode()
        self.assertIn('<h1>RAP</h1>', html)
        self.assertIn('This organization has not published any petition yet', html)
        self.assertNotIn('class="fp-sort"', html)
