# framapetitions: BE-15
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from petition import helpers
from petition.models import Petition
from .utils import add_default_data


@override_settings(SANITIZE_HTML_CACHE_TTL=60)
class SanitizeCacheTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        cache.clear()

    def test_result_is_cached_by_content(self):
        with mock.patch.object(helpers, '_sanitize_html', wraps=helpers._sanitize_html) as inner:
            first = helpers.sanitize_html('<p>Hello<script>alert(1)</script></p>')
            second = helpers.sanitize_html('<p>Hello<script>alert(1)</script></p>')
            self.assertEqual(first, second)
            self.assertNotIn('script', first)
            self.assertEqual(inner.call_count, 1)
            helpers.sanitize_html('<p>Other</p>')
            self.assertEqual(inner.call_count, 2)

    @override_settings(SANITIZE_HTML_CACHE_TTL=0)
    def test_disabled(self):
        with mock.patch.object(helpers, '_sanitize_html', wraps=helpers._sanitize_html) as inner:
            helpers.sanitize_html('<p>Hello</p>')
            helpers.sanitize_html('<p>Hello</p>')
            self.assertEqual(inner.call_count, 2)

    def test_edited_text_is_shown_immediately(self):
        petition = Petition.objects.filter(published=True).first()
        url = reverse('detail', args=[petition.id])
        petition.text = '<p>First version</p>'
        petition.save()
        self.assertContains(self.client.get(url), 'First version')
        petition.text = '<p>Second version<img src=x onerror=alert(1)></p>'
        petition.save()
        response = self.client.get(url)
        self.assertContains(response, 'Second version')
        self.assertNotContains(response, 'First version')
        self.assertNotContains(response, 'onerror')
