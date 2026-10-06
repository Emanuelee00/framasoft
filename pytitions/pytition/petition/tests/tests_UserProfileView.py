from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data


class UserProfileViewTest(TestCase):
    """Test user_profile view"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def test_UserProfileViewOk(self):
        response = self.client.get(reverse('user_profile', args=["max"]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "petition/user_profile.html")

    def test_UserProfileViewKo(self):
        response = self.client.get(reverse('user_profile', args=["not_existing_user"]))
        self.assertEqual(response.status_code, 404)

    def test_profile_of_a_user_does_not_log_the_visitor_in_as_this_user(self):
        html = self.client.get(reverse('user_profile', args=['max'])).content.decode()
        self.assertNotIn('fp-account-name', html)
        self.assertIn(reverse('login'), html)
        self.assertIn('<h1>max</h1>', html)
        self.assertIn('10 published petitions', html)

    def test_profile_of_a_user_keeps_the_visitor_account_menu(self):
        self.client.login(username='julia', password='julia')
        html = self.client.get(reverse('user_profile', args=['max'])).content.decode()
        self.assertIn('<span class="fp-account-name">julia</span>', html)
