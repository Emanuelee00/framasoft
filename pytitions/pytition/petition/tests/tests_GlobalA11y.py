from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.models import Petition


class GlobalAccessibilityTest(TestCase):
    """Skip link, main landmark and labelled navigation controls"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_petition_and_login_pages(self):
        petition = Petition.objects.filter(published=True).first()
        for url in (reverse('detail', args=[petition.id]), reverse('login')):
            response = self.client.get(url)
            html = response.content.decode()
            self.assertIn('<a class="fp-skip-link" href="#main">', html)
            self.assertEqual(html.count('<main id="main"'), 1)
            self.assertLess(html.index('fp-skip-link'), html.index('<nav'))
            self.assertIn('<label for="fp-search" class="sr-only">', html)
            self.assertIn('<label for="fp-language" class="sr-only">', html)
            self.assertNotIn('onchange=', html)
