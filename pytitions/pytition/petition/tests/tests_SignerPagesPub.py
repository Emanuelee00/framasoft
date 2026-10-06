import datetime

from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse

from petition.helpers import make_manage_token
from petition.models import Organization, Petition, Signature


class SignerPagesDesignTest(TestCase):
    """Confirmation, manage, lost link and deleted pages (PUB-04)"""

    @classmethod
    def setUpTestData(cls):
        org = Organization.objects.create(name="Vélo Lyon")
        cls.petition = Petition.objects.create(title="Des pistes cyclables", org=org, published=True)
        cls.signature = Signature.objects.create(petition=cls.petition, first_name="Alan", last_name="John",
                                                 email="alan@john.org")

    def test_confirmation_shows_the_steps(self):
        url = reverse('confirm', args=[self.petition.id, self.signature.confirmation_hash])
        html = self.client.get(url).content.decode()
        self.assertIn('<ol class="fp-stepper" aria-label="Steps of the signature">', html)
        self.assertIn('<li class="fp-step" aria-current="step">', html)
        self.assertIn('<span class="fp-sr-only">(completed)</span>', html)

    def test_confirmation_and_manage_pages_show_the_deletion_date(self):
        self.petition.expires_at = datetime.date(2027, 3, 14)
        request = RequestFactory().get('/')
        for template, ctx in (("petition/confirm.html", {"confirm_state": "pending", "confirmation_hash": "abc"}),
                              ("petition/confirm.html", {"confirm_state": "already_confirmed"}),
                              ("petition/manage_signature.html", {"signature": self.signature,
                                                                  "token": make_manage_token(self.signature)})):
            ctx["petition"] = self.petition
            html = render_to_string(template, ctx, request=request)
            self.assertIn('will be deleted on <strong>March 14, 2027</strong>', html, template)

    def test_manage_page_structure(self):
        html = self.client.get(reverse('manage_signature', args=[make_manage_token(self.signature)])).content.decode()
        self.assertIn('<dl class="fp-datalist">', html)
        self.assertIn('<span class="fp-badge fp-badge-warning">awaiting confirmation</span>', html)
        self.assertIn('class="fp-signer-section fp-danger-zone ', html)
        # every petition has a deletion date (EXP-01), shown to the signer
        self.assertIn('class="fp-expiry"', html)

    def test_lost_link_errors_are_tied_to_the_field(self):
        response = self.client.post(reverse('forgot_signature_link', args=[self.petition.id]), {'email': 'nope'})
        self.assertContains(response, 'aria-invalid="true" aria-describedby="id_email-error"')
        self.assertContains(response, '<p class="fp-field-error" id="id_email-error">')
