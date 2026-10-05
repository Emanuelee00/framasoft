from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ModerationPageTest(TestCase):
    """The moderation admin page is a valid document (no markup before the doctype)"""

    def test_page_starts_with_doctype(self):
        get_user_model().objects.create_superuser('admin', 'admin@example.org', 'admin')
        self.client.login(username='admin', password='admin')
        response = self.client.get(reverse('admin:moderatedelement_my_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.decode().lstrip().startswith('<!DOCTYPE html>'))
        self.assertContains(response, 'function toggle(source, name)')
