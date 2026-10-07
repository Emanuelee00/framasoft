import datetime

from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from petition.models import Organization, Petition


class PetitionPageDesignTest(TestCase):
    """Petition page on the design system (PUB-03)"""

    @classmethod
    def setUpTestData(cls):
        org = Organization.objects.create(name="Vélo Lyon")
        cls.petition = Petition.objects.create(title="Des pistes cyclables", text="<p>Texte</p>", org=org,
                                               published=True, has_mastodon_share_button=True,
                                               has_email_share_button=True)

    def get_html(self):
        return self.client.get(reverse('detail', args=[self.petition.id])).content.decode()

    def test_owner_is_linked_and_form_uses_design_system(self):
        html = self.get_html()
        self.assertIn('Petition by <a href="{}">Vélo Lyon</a>'.format(reverse('org_profile', args=['velo-lyon'])), html)
        self.assertIn('<section class="fp-sign-panel fp-anim-tilt" id="petition" aria-labelledby="sign-title">', html)
        self.assertRegex(html, r'class="fp-btn fp-btn-primary fp-btn-lg fp-btn-block fp-sign-btn fp-anim-tilt">'
                               r'<svg class="fp-icon"[^>]*><use href="[^"]*#signature"></use></svg>Sign the petition</button>')
        self.assertNotIn('Fields marked with * are required.', html)
        self.assertNotIn('css/petition.css', html)

    def test_mastodon_share_needs_no_inline_script(self):
        html = self.get_html()
        self.assertIn('<dialog id="MastodonModal" class="fp-dialog"', html)
        self.assertIn('<li class="rrssb-mastodon" hidden>', html)
        self.assertIn('js/share-mastodon.js', html)
        self.assertNotIn('msbConfig', html)
        self.assertNotIn('vendor/msb/js/mastodon.js', html)
        self.assertNotIn('data-toggle="modal"', html)

    def test_errors_put_the_form_first_on_small_screens(self):
        response = self.client.post(reverse('create_signature', args=[self.petition.id]), {'first_name': 'Alan'})
        self.assertContains(response, 'class="fp-petition-layout fp-sign-first"')
        self.assertContains(response, '<h3 class="fp-error-summary-title">')


class ExpiryNoticeTest(TestCase):
    """Deletion date of the petition, shown when Petition.expires_at is set (PUB-03)"""

    @classmethod
    def setUpTestData(cls):
        org = Organization.objects.create(name="Vélo Lyon")
        cls.petition = Petition.objects.create(title="Des pistes cyclables", org=org, published=True)

    def test_no_date_no_notice(self):
        self.petition.expires_at = None
        html = render_to_string("components/expiry_notice.html", {"petition": self.petition})
        self.assertNotIn('fp-expiry', html)

    def test_date_is_localized(self):
        self.petition.expires_at = datetime.date(2027, 3, 14)
        html = render_to_string("components/gdpr_notice.html", {"petition": self.petition})
        self.assertIn('<p class="fp-expiry">', html)
        self.assertIn('will be deleted on <strong>March 14, 2027</strong>', html)
        with translation.override('fr'):
            html = render_to_string("components/expiry_notice.html", {"petition": self.petition})
        self.assertIn('14 mars 2027', html)
