from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


def page_script():
    # The page script is a static file since the Content-Security-Policy (S13)
    with open(finders.find('js/spam_page.js'), encoding='utf-8') as f:
        return f.read()


class ModerationPageTest(TestCase):
    """The moderation admin page is a valid document (no markup before the doctype)"""

    def test_page_starts_with_doctype(self):
        get_user_model().objects.create_superuser('admin', 'admin@example.org', 'admin')
        self.client.login(username='admin', password='admin')
        response = self.client.get(reverse('admin:moderatedelement_my_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.decode().lstrip().startswith('<!DOCTYPE html>'))
        self.assertContains(response, 'js/spam_page.js')
        self.assertIn('function toggle(source, name)', page_script())

    def test_sortable_headers_are_buttons(self):
        get_user_model().objects.create_superuser('admin', 'admin@example.org', 'admin')
        self.client.login(username='admin', password='admin')
        html = self.client.get(reverse('admin:moderatedelement_my_view')).content.decode()
        self.assertNotIn('<th onclick', html)
        self.assertIn('<th scope="col"><button type="button" class="sort-btn" data-sort-table="userTable" data-sort-col="2">', html)
        self.assertIn("setAttribute('aria-sort', 'descending')", page_script())
        self.assertIn('function sortTable(table_id, column)', page_script())
