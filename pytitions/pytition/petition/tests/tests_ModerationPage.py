from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ModerationPageTest(TestCase):
    """The moderation page is a valid document, without inline script, with keyboard-usable controls"""

    def setUp(self):
        get_user_model().objects.create_superuser('admin', 'admin@example.org', 'admin')
        self.client.login(username='admin', password='admin')

    def get_html(self):
        response = self.client.get(reverse('admin:moderatedelement_my_view'))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_page_starts_with_doctype(self):
        self.assertTrue(self.get_html().lstrip().startswith('<!DOCTYPE html>'))

    def test_behaviours_come_from_a_static_file(self):
        html = self.get_html()
        self.assertIn('js/fp-moderation.js', html)
        for attribute in ('onclick=', 'onkeyup=', 'style="'):
            self.assertNotIn(attribute, html)

    def test_sortable_headers_are_buttons(self):
        html = self.get_html()
        self.assertNotIn('<th onclick', html)
        self.assertIn('<th scope="col"><button type="button" class="fp-sort" data-sort-table="userTable" data-sort-col="3">', html)

    def test_actions_are_buttons_and_deletion_is_confirmed(self):
        html = self.get_html()
        self.assertIn('<button type="submit" name="action" value="moderate petition"', html)
        self.assertIn('data-fp-dialog-open="confirm-action_rep_petition"', html)
        self.assertNotIn('<select name="action">', html)
