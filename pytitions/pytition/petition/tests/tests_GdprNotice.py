from django import forms
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from .utils import add_default_data

from petition.forms import SignatureForm
from petition.models import Petition


class ConsentSignatureForm(SignatureForm):
    """Stand-in for the consent field added to SignatureForm by GD-03"""
    consent = forms.BooleanField(required=True, label="I agree", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))


class GdprNoticeTest(TestCase):
    """Privacy notice and consent slot in the signature form"""

    @classmethod
    def setUpTestData(cls):
        add_default_data()

    def setUp(self):
        self.petition = Petition.objects.filter(published=True).first()

    def render_form(self, form):
        return render_to_string('components/sign_form.html', {'form': form, 'petition': self.petition})

    def test_notice_is_shown_on_petition_page(self):
        response = self.client.get(reverse('detail', args=[self.petition.id]))
        self.assertContains(response, 'id="fp-gdpr-notice"')
        self.assertContains(response, self.petition.owner_name)
        self.assertContains(response, '<details class="fp-details">')
        self.assertContains(response, 'An unconfirmed signature is deleted after 7 days.')
        self.assertContains(response, 'neither approved nor endorsed')
        # GD-05: a new manage link can be requested from the petition page
        self.assertContains(response, 'href="%s" rel="nofollow"' % reverse('forgot_signature_link', args=[self.petition.id]))

    def test_consent_slot_is_empty_without_consent_field(self):
        form = SignatureForm(petition=self.petition)
        del form.fields['consent']
        html = self.render_form(form)
        self.assertNotIn('id_consent', html)

    def test_consent_checkbox_is_rendered_unchecked_and_described_by_notice(self):
        html = self.render_form(ConsentSignatureForm(petition=self.petition))
        self.assertIn('id="id_consent"', html)
        self.assertIn('<label class="form-check-label" for="id_consent">I agree', html)
        self.assertIn('fp-gdpr-notice', html)
        self.assertNotIn('checked', html)
        # consent comes before the notice and the submit button
        self.assertLess(html.index('id="id_consent"'), html.index('id="fp-gdpr-notice"'))
        self.assertLess(html.index('id="fp-gdpr-notice"'), html.index('type="submit"'))

    def test_missing_consent_error_is_linked_to_checkbox(self):
        form = ConsentSignatureForm(petition=self.petition, data={
            'first_name': 'Alan', 'last_name': 'John', 'email': 'alan@john.org'})
        self.assertFalse(form.is_valid())
        html = self.render_form(form)
        self.assertIn('href="#id_consent"', html)
        self.assertIn('id="id_consent-error"', html)
        self.assertIn('aria-invalid="true"', html)

    def test_newsletter_help_text_is_linked(self):
        self.petition.has_newsletter = True
        self.petition.newsletter_text = "Keep me informed"
        self.petition.save()
        form = SignatureForm(petition=self.petition)
        form.fields['subscribed_to_mailinglist'].help_text = "Sent to the creator"
        html = self.render_form(form)
        self.assertIn('aria-describedby="id_subscribed_to_mailinglist-help', html)
        self.assertIn('id="id_subscribed_to_mailinglist-help"', html)
        self.assertIn('Sent to the creator', html)
