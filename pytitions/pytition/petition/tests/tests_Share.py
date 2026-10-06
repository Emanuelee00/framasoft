from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.models import Petition


class ShareTest(TestCase):
    """FE-06: share links outside the signature form, encoded, without third-party scripts"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()
        self.petition.title = 'Eau & air ? #maintenant'
        for flag in ['email', 'facebook', 'tumblr', 'linkedin', 'twitter', 'whatsapp', 'mastodon']:
            setattr(self.petition, 'has_%s_share_button' % flag, True)
        self.petition.save()

    def test_links_are_encoded_and_outside_the_form(self):
        html = self.client.get(reverse('detail', args=[self.petition.id])).content.decode()
        self.assertIn('https://twitter.com/intent/tweet?text=Eau%20%26%20air%20%3F%20%23maintenant&amp;url=http%3A%2F%2Ftestserver%2F', html)
        self.assertIn('https://wa.me/?text=', html)
        self.assertNotIn('whatsapp://', html)
        self.assertNotIn('http://www.linkedin.com', html)
        self.assertNotIn('http://tumblr.com', html)
        self.assertIn('<a href="#MastodonModal" role="button" class="mastodon-share-button"', html)
        self.assertLess(html.index('</form>', html.index('<form')), html.index('class="fp-share '))

    def test_share_stays_visible_after_signing(self):
        data = {'first_name': 'Alan', 'last_name': 'John', 'email': 'alan@john.org', 'consent': 'on'}
        response = self.client.post(reverse('create_signature', args=[self.petition.id]), data, follow=True)
        html = response.content.decode()
        self.assertIn('Check your mailbox', html)  # signature state shown instead of the form
        self.assertNotIn('class="fp-sign-form"', html)
        self.assertIn('class="fp-share ', html)
        self.assertIn('Share the petition', html)

    def test_no_share_block_without_share_buttons(self):
        for flag in ['email', 'facebook', 'tumblr', 'linkedin', 'twitter', 'whatsapp', 'mastodon']:
            setattr(self.petition, 'has_%s_share_button' % flag, False)
        self.petition.save()
        html = self.client.get(reverse('detail', args=[self.petition.id])).content.decode()
        self.assertNotIn('class="fp-share ', html)
