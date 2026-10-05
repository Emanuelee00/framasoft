from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from .utils import add_default_data

from petition.models import Petition, Signature
from petition.templatetags.petition_extras import grouped, progress_percent


class ProgressFiltersTest(TestCase):

    def test_progress_percent(self):
        self.assertEqual(progress_percent(0, 500), 0)
        self.assertEqual(progress_percent(250, 500), 50)
        self.assertEqual(progress_percent(600, 500), 100)
        self.assertEqual(progress_percent(5, 0), 0)
        self.assertEqual(progress_percent(5, None), 0)

    def test_grouped_is_localized(self):
        with translation.override('fr'):
            self.assertEqual(grouped(1234567), '1\xa0234\xa0567')
        with translation.override('en'):
            self.assertEqual(grouped(1234567), '1,234,567')


class PetitionPageTest(TestCase):
    """Mobile-first petition page with a server-side counter"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        cache.clear()  # the displayed counter is cached (SIGNATURE_COUNT_CACHE_TTL)
        self.petition = Petition.objects.filter(published=True).first()
        self.petition.text = "<p>We ask for &laquo; better &raquo; things. " + "Lorem ipsum. " * 40 + "</p>"
        self.petition.save()

    def get(self):
        return self.client.get(reverse('detail', args=[self.petition.id]))

    def add_signatures(self, n):
        Signature.objects.bulk_create([
            Signature(petition=self.petition, first_name='A', last_name='B', email='s%d@example.org' % i,
                      confirmed=True) for i in range(n)])

    def test_counter_and_progress_are_rendered_without_js(self):
        self.petition.target = 4
        self.petition.save()
        self.add_signatures(1)
        response = self.get()
        self.assertContains(response, '<progress class="fp-progress-bar" max="100" value="25"')
        self.assertContains(response, 'out of 4')
        self.assertNotContains(response, 'js/petition.js')
        self.assertNotContains(response, 'dataLayer')
        self.assertNotContains(response, 'id="show-form"')

    def test_goal_reached_is_capped(self):
        self.petition.target = 2
        self.petition.save()
        self.add_signatures(3)
        response = self.get()
        self.assertContains(response, 'value="100"')
        self.assertContains(response, 'Goal reached!')

    def test_zero_goal_shows_only_the_count(self):
        self.petition.target = 0
        self.petition.save()
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<progress')

    def test_call_to_action_points_to_the_form(self):
        response = self.get()
        self.assertContains(response, 'href="#signer"')
        self.assertContains(response, 'id="signer"')

    def test_meta_description_is_a_short_summary(self):
        response = self.get()
        self.assertContains(response, '<meta name="description" content="We ask for « better » things.')
        html = response.content.decode()
        start = html.index('<meta name="description" content="') + len('<meta name="description" content="')
        self.assertLessEqual(len(html[start:html.index('"', start)]), 160)
